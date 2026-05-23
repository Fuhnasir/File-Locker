"""
Folder Locker - Main Entry Orchestrator
Binds the user interface logic to the cryptographic backend engine and manages runtime lifecycle.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

# --- AUTOMATIC DEPENDENCY CHECKS & INSTALLS ---

try:
    import cryptography
except ImportError:
    # Attempt automatic dependency download and install via subprocess pip
    print("Required package 'cryptography' is missing. Attempting automatic installation...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
        import cryptography
        print("Dependency 'cryptography' successfully installed.")
    except Exception as e:
        print(f"Failed to automatically install 'cryptography' dependency: {e}")
        # Create a tiny hidden Tk window to display a clean OS-native error box
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Missing Dependencies",
            "This application requires the 'cryptography' package to secure your folders.\n\n"
            "We tried to install it automatically but encountered an error.\n"
            "Please install it manually by running this command in your terminal:\n\n"
            "pip install cryptography\n\n"
            f"Detailed Error: {e}"
        )
        sys.exit(1)

# --- APPLICATION ORCHESTRATION ---

import crypto_engine
from app_gui import FolderLockerGUI

def main():
    root = tk.Tk()
    app = FolderLockerGUI(root)

    # 1. Binder for Locking Callback
    def on_lock(folder_path, password, progress_cb):
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            raise ValueError(f"Folder '{folder_path}' does not exist or is not a valid directory.")

        folder_abs = os.path.abspath(folder_path)
        parent_dir = os.path.dirname(folder_abs)
        folder_name = os.path.basename(folder_abs)
        
        # Output lockbox target filename
        lockbox_path = os.path.join(parent_dir, f"{folder_name}.lockbox")

        # Guard: Check if a lockbox file already exists
        if os.path.exists(lockbox_path):
            raise FileExistsError(
                f"A lockbox file named '{folder_name}.lockbox' already exists in the destination folder.\n"
                "Please rename or move the existing lockbox before locking."
            )

        # Trigger high-level cryptographic engine locking
        crypto_engine.lock_directory(
            src_dir=folder_abs,
            dest_lockbox=lockbox_path,
            password=password,
            shred_original=True,
            progress_callback=progress_cb
        )

        # Display success dialog in main thread thread-safely
        root.after(0, lambda: messagebox.showinfo(
            "Lock Success",
            f"Folder successfully locked and encrypted!\n\n"
            f"Lockbox File:\n{lockbox_path}\n\n"
            "The original files have been completely and securely shredded from disk."
        ))

    # 2. Binder for Unlocking Callback
    def on_unlock(lockbox_path, password, progress_cb):
        if not os.path.exists(lockbox_path):
            raise FileNotFoundError(f"Lockbox file '{lockbox_path}' does not exist.")

        lockbox_abs = os.path.abspath(lockbox_path)
        parent_dir = os.path.dirname(lockbox_abs)
        lockbox_name = os.path.basename(lockbox_abs)

        if not lockbox_name.endswith(".lockbox"):
            raise ValueError("Selected file is not a valid '.lockbox' file.")

        folder_name = lockbox_name[:-8]  # strip '.lockbox' extension
        dest_folder = os.path.join(parent_dir, folder_name)

        # Guard: Prevent overwriting existing folders
        if os.path.exists(dest_folder):
            raise FileExistsError(
                f"A folder named '{folder_name}' already exists in the destination folder.\n"
                "Please move, rename, or delete it before unlocking."
            )

        # Trigger high-level cryptographic engine unlocking
        crypto_engine.unlock_directory(
            src_lockbox=lockbox_abs,
            dest_dir=dest_folder,
            password=password,
            progress_callback=progress_cb
        )

        # Display success dialog in main thread thread-safely
        root.after(0, lambda: messagebox.showinfo(
            "Unlock Success",
            f"Lockbox successfully unlocked and decrypted!\n\n"
            f"Restored Folder:\n{dest_folder}"
        ))

    # Assign hooks to the GUI interface
    app.lock_callback = on_lock
    app.unlock_callback = on_unlock

    # Launch GUI Event Loop
    root.mainloop()

if __name__ == "__main__":
    main()
