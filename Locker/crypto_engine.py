"""
Folder Locker - Cryptographic Engine
Module for secure chunk-by-chunk stream encryption, decryption, and secure shredding.
"""

import os
import stat
import struct
import secrets
import base64
import shutil
import zipfile
import tempfile
from typing import Callable, Optional, List

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import cryptography.exceptions

# --- CUSTOM EXCEPTIONS ---

class FolderLockerError(Exception):
    """Base exception for Folder Locker operations."""
    pass

class InvalidPasswordError(FolderLockerError):
    """Raised when the password is incorrect or lockbox integrity check fails."""
    pass

class LockboxCorruptedError(FolderLockerError):
    """Raised when the lockbox file is corrupted, malformed, or truncated."""
    pass


# --- KEY DERIVATION ---

def derive_key(password: str, salt: bytes, iterations: int = 120000) -> bytes:
    """
    Derives a 32-byte key from a password and salt using PBKDF2HMAC + SHA256,
    returning a base64 URL-safe encoded version suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    derived = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


# --- SECURITY UTILITIES ---

def is_safe_path(base_dir: str, path: str) -> bool:
    """
    Checks if a target path lies within the base directory to prevent Zip Slip / path traversal.
    """
    base_dir = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, path))
    return target_path.startswith(base_dir + os.sep) or target_path == base_dir


def get_temp_filepath(parent_dir: str, prefix: str = "tmp_locker_", suffix: str = ".tmp") -> str:
    """
    Creates a temporary file name within a specified directory in the workspace.
    """
    os.makedirs(parent_dir, exist_ok=True)
    fd, path = tempfile.mkstemp(dir=parent_dir, prefix=prefix, suffix=suffix)
    os.close(fd)
    return path


# --- WINDOWS-SPECIFIC SECURE SHREDDING ---

def secure_shred_file(filepath: str, chunk_size: int = 65536) -> None:
    """
    Overwrites the specified file with cryptographically secure random bytes (via secrets.token_bytes),
    flushes buffers, calls os.fsync, truncates file size to 0, and removes it from disk.
    Removes read-only attributes on Windows if present.
    """
    if not os.path.exists(filepath):
        return

    try:
        # Remove read-only attributes on Windows if set
        try:
            os.chmod(filepath, stat.S_IWRITE)
        except Exception:
            pass

        file_size = os.path.getsize(filepath)
        if file_size > 0:
            with open(filepath, "r+b") as f:
                bytes_written = 0
                while bytes_written < file_size:
                    to_write = min(chunk_size, file_size - bytes_written)
                    f.write(secrets.token_bytes(to_write))
                    bytes_written += to_write
                
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    # Catch cases where fsync is not supported by underlying FS
                    pass
                f.seek(0)
                f.truncate(0)

        os.remove(filepath)
    except Exception as e:
        raise FolderLockerError(f"Failed to securely shred file '{filepath}': {str(e)}")


def secure_shred_directory(directory_path: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Recursively shreds all files inside a directory and removes subdirectories and parent directories
    bottom-up to avoid 'directory not empty' errors.
    """
    if not os.path.exists(directory_path):
        return

    all_files: List[str] = []
    all_dirs: List[str] = []

    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            all_files.append(os.path.join(root, file))
        for d in dirs:
            all_dirs.append(os.path.join(root, d))

    total_files = len(all_files)

    # 1. Shred all files inside the tree
    for index, filepath in enumerate(all_files):
        if progress_callback:
            # Shredding spans progress 50% to 95% during locking
            pct = 50.0 + (index / max(1, total_files)) * 45.0
            progress_callback(
                pct,
                f"Shredding file {index + 1}/{total_files}: {os.path.basename(filepath)}"
            )
        secure_shred_file(filepath)

    # 2. Delete all subdirectories bottom-up
    all_dirs.sort(key=len, reverse=True)
    for dirpath in all_dirs:
        try:
            os.chmod(dirpath, stat.S_IWRITE)
        except Exception:
            pass
        try:
            os.rmdir(dirpath)
        except Exception as e:
            raise FolderLockerError(f"Failed to remove subdirectory '{dirpath}': {str(e)}")

    # 3. Finally, remove the root directory
    try:
        os.chmod(directory_path, stat.S_IWRITE)
    except Exception:
        pass
    try:
        os.rmdir(directory_path)
    except Exception as e:
        raise FolderLockerError(f"Failed to remove root directory '{directory_path}': {str(e)}")


# --- STREAM ZIP COMPRESSION & EXTRACTION ---

def zip_directory(directory_path: str, zip_filepath: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Packs a directory recursively into a ZIP archive, retaining empty folders.
    """
    items_to_zip = []
    directory_path = os.path.abspath(directory_path)

    for root, dirs, files in os.walk(directory_path):
        for d in dirs:
            dir_path = os.path.join(root, d)
            arcname = os.path.relpath(dir_path, directory_path).replace("\\", "/") + "/"
            items_to_zip.append((dir_path, arcname, True))
        for f in files:
            file_path = os.path.join(root, f)
            arcname = os.path.relpath(file_path, directory_path).replace("\\", "/")
            items_to_zip.append((file_path, arcname, False))

    total_items = len(items_to_zip)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for index, (path, arcname, is_dir) in enumerate(items_to_zip):
            if progress_callback:
                progress_callback(
                    (index / max(1, total_items)) * 15.0,
                    f"Packing item {index + 1}/{total_items}: {arcname}"
                )
            if is_dir:
                zip_info = zipfile.ZipInfo(arcname)
                zip_info.external_attr = 16  # MS-DOS Directory Attribute
                zip_file.writestr(zip_info, '')
            else:
                zip_file.write(path, arcname)


def extract_zip(zip_filepath: str, dest_directory: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> List[str]:
    """
    Extracts a ZIP archive to a destination directory with safety validations and progress reporting.
    Returns a list of extracted file/folder paths.
    """
    extracted_paths: List[str] = []
    os.makedirs(dest_directory, exist_ok=True)

    with zipfile.ZipFile(zip_filepath, 'r') as zip_file:
        infolist = zip_file.infolist()
        total_items = len(infolist)

        for index, zip_info in enumerate(infolist):
            if progress_callback:
                pct = 40.0 + (index / max(1, total_items)) * 50.0
                progress_callback(pct, f"Extracting item {index + 1}/{total_items}: {zip_info.filename}")

            # Zip Slip Prevention
            if not is_safe_path(dest_directory, zip_info.filename):
                raise FolderLockerError(
                    f"Security Warning: Path traversal attempt detected in ZIP archive: '{zip_info.filename}'"
                )

            zip_file.extract(zip_info, dest_directory)
            extracted_paths.append(os.path.join(dest_directory, zip_info.filename))

    return extracted_paths


# --- STREAM ENCRYPTION & DECRYPTION ---

def encrypt_file_stream(
    src_filepath: str,
    dest_filepath: str,
    derived_key: bytes,
    salt: bytes,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> None:
    """
    Encrypts a file chunk-by-chunk using Fernet and writes the stream format to dest_filepath.
    """
    chunk_size = 65536
    fernet = Fernet(derived_key)
    file_size = os.path.getsize(src_filepath)
    bytes_read = 0

    with open(src_filepath, 'rb') as f_in, open(dest_filepath, 'wb') as f_out:
        # Write 16-byte salt header
        f_out.write(salt)

        while True:
            chunk = f_in.read(chunk_size)
            if not chunk:
                break

            bytes_read += len(chunk)
            encrypted_payload = fernet.encrypt(chunk)

            # Write 4-byte big-endian payload length followed by payload itself
            f_out.write(struct.pack('>I', len(encrypted_payload)))
            f_out.write(encrypted_payload)

            if progress_callback:
                pct = 15.0 + (bytes_read / max(1, file_size)) * 35.0
                progress_callback(
                    pct,
                    f"Encrypting data stream: {bytes_read // 1024} KB / {file_size // 1024} KB"
                )


def decrypt_file_stream(
    src_filepath: str,
    dest_filepath: str,
    password: str,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> bytes:
    """
    Decrypts a lockbox file stream chunk-by-chunk to dest_filepath.
    Returns the derived Fernet key on success, or raises LockboxCorruptedError/InvalidPasswordError.
    """
    chunk_size_header = 4
    file_size = os.path.getsize(src_filepath)
    if file_size < 16:
        raise LockboxCorruptedError("Invalid lockbox: file size is smaller than the required 16-byte salt header.")

    bytes_read = 0

    with open(src_filepath, 'rb') as f_in:
        # Read the 16-byte salt
        salt = f_in.read(16)
        bytes_read += 16

        # Derive key
        derived_key = derive_key(password, salt)
        fernet = Fernet(derived_key)

        with open(dest_filepath, 'wb') as f_out:
            while bytes_read < file_size:
                length_bytes = f_in.read(chunk_size_header)
                if not length_bytes:
                    break
                if len(length_bytes) < chunk_size_header:
                    raise LockboxCorruptedError("Corrupted lockbox: unexpected EOF within chunk length header.")

                bytes_read += chunk_size_header
                payload_len = struct.unpack('>I', length_bytes)[0]

                payload = f_in.read(payload_len)
                if len(payload) < payload_len:
                    raise LockboxCorruptedError("Corrupted lockbox: unexpected EOF within payload data chunk.")

                bytes_read += payload_len

                try:
                    decrypted_chunk = fernet.decrypt(payload)
                except (cryptography.fernet.InvalidToken, cryptography.exceptions.InvalidSignature):
                    raise InvalidPasswordError("Authentication failed: incorrect password or corrupted lockbox data.")
                except Exception as e:
                    raise FolderLockerError(f"Decryption error: {str(e)}")

                f_out.write(decrypted_chunk)

                if progress_callback:
                    pct = (bytes_read / max(1, file_size)) * 40.0
                    progress_callback(
                        pct,
                        f"Decrypting data stream: {bytes_read // 1024} KB / {file_size // 1024} KB"
                    )

    return derived_key


# --- HIGH-LEVEL LOCK / UNLOCK ENGINE FUNCTIONS ---

def lock_directory(
    src_dir: str,
    dest_lockbox: str,
    password: str,
    shred_original: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> None:
    """
    Compresses a directory recursively to a ZIP, encrypts it in chunks to dest_lockbox,
    and secure-shreds the original files and folders if requested.
    """
    if not os.path.exists(src_dir):
        raise FileNotFoundError(f"Source directory '{src_dir}' does not exist.")
    if not os.path.isdir(src_dir):
        raise ValueError(f"Source path '{src_dir}' is not a valid directory.")

    dest_dir = os.path.dirname(os.path.abspath(dest_lockbox))
    temp_zip = get_temp_filepath(dest_dir, prefix="lockbox_archive_", suffix=".zip")

    try:
        # Step 1: Compress (0% to 15%)
        if progress_callback:
            progress_callback(0.0, "Initiating folder compression...")
        zip_directory(src_dir, temp_zip, progress_callback)

        # Step 2: Key derivation and encryption (15% to 50%)
        if progress_callback:
            progress_callback(15.0, "Deriving cryptographic keys...")
        salt = secrets.token_bytes(16)
        derived_key = derive_key(password, salt)
        
        encrypt_file_stream(temp_zip, dest_lockbox, derived_key, salt, progress_callback)

        # Step 3: Secure shredding of originals if requested (50% to 95%)
        if shred_original:
            if progress_callback:
                progress_callback(50.0, "Securely shredding original files...")
            secure_shred_directory(src_dir, progress_callback)
        else:
            if progress_callback:
                progress_callback(95.0, "Skipping file shredding, finalizing lockbox...")

        if progress_callback:
            progress_callback(100.0, "Folder locking complete.")

    except Exception as e:
        # Rollback partially written lockbox
        if os.path.exists(dest_lockbox):
            try:
                os.remove(dest_lockbox)
            except Exception:
                pass
        raise e
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_zip):
            try:
                os.remove(temp_zip)
            except Exception:
                pass


def unlock_directory(
    src_lockbox: str,
    dest_dir: str,
    password: str,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> None:
    """
    Decrypts a lockbox stream chunk-by-chunk to a temporary ZIP, extracts it safely to dest_dir,
    and securely shreds the decrypted temporary ZIP. Performs a clean rollback on failures.
    """
    if not os.path.exists(src_lockbox):
        raise FileNotFoundError(f"Lockbox file '{src_lockbox}' does not exist.")

    parent_dir = os.path.dirname(os.path.abspath(dest_dir))
    temp_zip = get_temp_filepath(parent_dir, prefix="unlock_archive_", suffix=".zip")

    extracted_paths: List[str] = []

    try:
        # Step 1: Stream Decrypt (0% to 40%)
        if progress_callback:
            progress_callback(0.0, "Decrypting lockbox...")
        decrypt_file_stream(src_lockbox, temp_zip, password, progress_callback)

        # Step 2: Extraction with path safety check (40% to 90%)
        if progress_callback:
            progress_callback(40.0, "Extracting folders...")
        extracted_paths = extract_zip(temp_zip, dest_dir, progress_callback)

        # Step 3: Shred the temporary ZIP to prevent plaintext residual data and shred lockbox (90% to 100%)
        if progress_callback:
            progress_callback(90.0, "Cleaning up decrypted temp storage and shredding lockbox...")
        secure_shred_file(temp_zip)
        secure_shred_file(src_lockbox)

        if progress_callback:
            progress_callback(100.0, "Folder unlocking complete.")

    except Exception as e:
        # Rollback Decrypted temp archive
        if os.path.exists(temp_zip):
            try:
                secure_shred_file(temp_zip)
            except Exception:
                pass

        # Rollback partially extracted files and folders
        extracted_paths.sort(key=len, reverse=True)  # Remove deepest paths first
        for path in extracted_paths:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        os.rmdir(path)
                    else:
                        os.remove(path)
                except Exception:
                    pass
        raise e
