"""
Folder Locker - Graphical User Interface
Module implementing high-quality custom Canvas widgets and layout styling in Tkinter.
"""

import tkinter as tk
from tkinter import filedialog
import threading
import time

def apply_dark_title_bar(window):
    """
    Applies standard Windows dark mode theme to the OS title bar of the window if supported.
    """
    try:
        import ctypes
        window.update()
        # DWM attribute for immersive dark mode
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(2)  # 2 = enable dark theme
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        # Fallback gracefully if not on Windows or unsupported version
        pass

def run_in_background(func, *args, **kwargs):
    """
    Helper function to run functions in a background thread to prevent GUI freezing.
    """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread

class ModernButton(tk.Canvas):
    """
    A custom-drawn button with rounded corners, responsive hover effects, press down micro-animations,
    and visual disabled states.
    """
    def __init__(self, parent, text, command=None, width=120, height=36, radius=10,
                 bg_color="#1E1E2E", normal_color="#89B4FA", hover_color="#B4BFE8",
                 click_color="#585B70", text_color="#11111B", font=("Segoe UI", 10, "bold"), **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        self.command = command
        self.text = text
        self.radius = radius
        self.bg_color = bg_color
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.click_color = click_color
        self.text_color = text_color
        self.font = font
        self.width = width
        self.height = height
        
        self.rect_id = None
        self.text_id = None
        self.pressed = False
        self.enabled = True
        
        self.draw_button(0, 0)
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        
    def draw_button(self, dx=0, dy=0):
        self.delete("all")
        x1, y1 = 2 + dx, 2 + dy
        x2, y2 = self.width - 2 + dx, self.height - 2 + dy
        
        if not self.enabled:
            fill_color = "#313244"
            fg_color = "#7F849C"
        else:
            fill_color = self.click_color if self.pressed else self.normal_color
            fg_color = self.text_color
            
        self.rect_id = self.draw_rounded_rect(x1, y1, x2, y2, self.radius, fill=fill_color, outline="")
        self.text_id = self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=self.text, fill=fg_color, font=self.font)

    def draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1, y1 + radius,
            x1, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.draw_button()

    def on_enter(self, event):
        if self.enabled and not self.pressed:
            self.itemconfig(self.rect_id, fill=self.hover_color)
            
    def on_leave(self, event):
        if self.enabled:
            self.pressed = False
            self.draw_button(0, 0)
            
    def on_press(self, event):
        if self.enabled:
            self.pressed = True
            self.draw_button(1, 1)
        
    def on_release(self, event):
        if self.enabled and self.pressed:
            self.pressed = False
            self.draw_button(0, 0)
            if 0 <= event.x <= self.width and 0 <= event.y <= self.height:
                if self.command:
                    self.command()


class ModernEntry(tk.Canvas):
    """
    A stylish text box inside a custom-drawn canvas border that glows in the accent color when focused,
    and supports active placeholder text and an integrated Show/Hide password toggle.
    """
    def __init__(self, parent, width=300, height=38, radius=8, is_password=False, placeholder="",
                 bg_color="#181825", entry_bg="#11111B", border_color="#313244",
                 focus_color="#89B4FA", text_color="#CDD6F4", placeholder_color="#7F849C", **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        self.width = width
        self.height = height
        self.radius = radius
        self.bg_color = bg_color
        self.entry_bg = entry_bg
        self.border_color = border_color
        self.focus_color = focus_color
        self.text_color = text_color
        self.placeholder_color = placeholder_color
        self.placeholder = placeholder
        self.is_password = is_password
        self.show_password = not is_password
        self.is_placeholder_active = False
        
        self.rect_id = None
        self.focused = False
        
        show_char = "*" if is_password else ""
        self.entry = tk.Entry(self, bg=entry_bg, fg=text_color, insertbackground=text_color,
                              bd=0, relief="flat", show=show_char, font=("Segoe UI", 10))
        
        # Calculate margins
        right_margin = 55 if is_password else 15
        self.entry_window = self.create_window(15, height/2, anchor="w", window=self.entry,
                                                width=width - 15 - right_margin)
        
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        
        self.draw_border()
        
        if is_password:
            self.draw_toggle_btn()
            
        if self.placeholder:
            self.is_placeholder_active = True
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=self.placeholder_color)
            if self.is_password:
                self.entry.config(show="")
            self.entry.bind("<FocusIn>", self.clear_placeholder, add="+")
            self.entry.bind("<FocusOut>", self.restore_placeholder, add="+")

    def draw_border(self):
        if self.rect_id:
            self.delete(self.rect_id)
        color = self.focus_color if self.focused else self.border_color
        width = 2 if self.focused else 1
        
        points = [
            2, 2 + self.radius,
            2, 2,
            2 + self.radius, 2,
            self.width - 2 - self.radius, 2,
            self.width - 2, 2,
            self.width - 2, 2 + self.radius,
            self.width - 2, self.height - 2 - self.radius,
            self.width - 2, self.height - 2,
            self.width - 2 - self.radius, self.height - 2,
            2 + self.radius, self.height - 2,
            2, self.height - 2,
            2, self.height - 2 - self.radius,
        ]
        self.rect_id = self.create_polygon(points, fill=self.entry_bg, outline=color, width=width, smooth=True)
        self.tag_lower("all")

    def draw_toggle_btn(self):
        self.delete("toggle_btn")
        x = self.width - 15
        y = self.height / 2
        text = "Hide" if self.show_password else "Show"
        
        self.create_text(x, y, text=text, fill=self.focus_color, font=("Segoe UI", 9, "bold"),
                         tags="toggle_btn", anchor="e")
        self.tag_bind("toggle_btn", "<Button-1>", self.toggle_visibility)
        
    def toggle_visibility(self, event):
        self.show_password = not self.show_password
        show_char = "" if self.show_password else "*"
        if not self.is_placeholder_active:
            self.entry.config(show=show_char)
        self.draw_toggle_btn()

    def on_focus_in(self, event):
        self.focused = True
        self.draw_border()
        
    def on_focus_out(self, event):
        self.focused = False
        self.draw_border()

    def clear_placeholder(self, event):
        if self.is_placeholder_active:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=self.text_color)
            self.is_placeholder_active = False
            if self.is_password and not self.show_password:
                self.entry.config(show="*")

    def restore_placeholder(self, event):
        if not self.entry.get():
            self.is_placeholder_active = True
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=self.placeholder_color)
            if self.is_password:
                self.entry.config(show="")

    def get(self):
        if self.is_placeholder_active:
            return ""
        return self.entry.get()

    def set(self, text):
        self.clear_placeholder(None)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)
        self.is_placeholder_active = False
        self.entry.config(fg=self.text_color)
        if self.is_password and not self.show_password:
            self.entry.config(show="*")


class ModernProgressBar(tk.Canvas):
    """
    A custom-drawn progress bar displaying progress fills with smooth rounded corners.
    """
    def __init__(self, parent, width=400, height=8, bg_color="#181825", bar_bg="#11111B",
                 fill_color="#89B4FA", radius=4, **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        self.width = width
        self.height = height
        self.bar_bg = bar_bg
        self.fill_color = fill_color
        self.radius = radius
        self.progress = 0.0
        
        self.draw_bg()
        
    def draw_bg(self):
        self.delete("all")
        self.draw_rounded_rect(0, 0, self.width, self.height, self.radius, fill=self.bar_bg)
        
    def draw_rounded_rect(self, x1, y1, x2, y2, radius, fill="", **kwargs):
        points = [
            x1, y1 + radius,
            x1, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
        ]
        return self.create_polygon(points, fill=fill, outline="", smooth=True, **kwargs)
        
    def set_progress(self, value):
        """Sets progress as a float between 0.0 and 1.0"""
        self.progress = max(0.0, min(1.0, value))
        self.draw_progress()
        
    def draw_progress(self):
        self.delete("fill")
        if self.progress <= 0:
            return
        
        fill_width = self.width * self.progress
        if fill_width < self.radius * 2:
            fill_width = self.radius * 2
            
        self.draw_rounded_rect(0, 0, fill_width, self.height, self.radius, fill=self.fill_color, tags="fill")


class ModernTabBar(tk.Canvas):
    """
    A custom dark mode navigation header with a smooth underline accent matching the selected view.
    """
    def __init__(self, parent, tab_labels, on_tab_changed, width=600, height=50, bg_color="#181825",
                 active_color="#89B4FA", inactive_color="#A6ADC8", font=("Segoe UI", 10, "bold"), **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, bd=0, **kwargs)
        self.tab_labels = tab_labels
        self.on_tab_changed = on_tab_changed
        self.width = width
        self.height = height
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.font = font
        self.active_idx = 0
        
        self.draw_tabs()
        self.bind("<Button-1>", self.on_click)

    def draw_tabs(self):
        self.delete("all")
        num_tabs = len(self.tab_labels)
        self.tab_width = self.width / num_tabs
        
        for i, label in enumerate(self.tab_labels):
            cx = (i + 0.5) * self.tab_width
            cy = self.height / 2
            
            color = self.active_color if i == self.active_idx else self.inactive_color
            self.create_text(cx, cy, text=label, fill=color, font=self.font, tags=f"tab_{i}")
            
        # Accent Underline Indicator
        line_w = 140
        lx1 = (self.active_idx + 0.5) * self.tab_width - line_w / 2
        lx2 = lx1 + line_w
        ly = self.height - 3
        self.create_line(lx1, ly, lx2, ly, fill=self.active_color, width=3, tags="underline")

    def on_click(self, event):
        clicked_idx = int(event.x // self.tab_width)
        if clicked_idx != self.active_idx and clicked_idx < len(self.tab_labels):
            self.active_idx = clicked_idx
            self.draw_tabs()
            self.on_tab_changed(self.active_idx)


class FolderLockerGUI:
    """
    Main Folder Locker user interface styling and layout definition. Handles state logic,
    path selections, input locking, threads execution safely, and provides callback hooks.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("File Locker")
        self.root.configure(bg="#1E1E2E")
        
        # Lock geometry and prevent resizing
        self.window_width = 600
        self.window_height = 520
        self.center_window()
        self.root.resizable(False, False)
        
        # Apply dark mode to Windows title bar
        apply_dark_title_bar(self.root)
        
        # Separation of Concerns: Callback hooks for crypto operations
        self.lock_callback = None
        self.unlock_callback = None
        
        # Tab Header Selection bar
        self.tab_bar = ModernTabBar(self.root, ["LOCK FOLDER", "UNLOCK LOCKBOX"], self.show_tab, width=600, height=50)
        self.tab_bar.pack(fill="x", side="top")
        
        # Central Body View Container
        self.body_container = tk.Frame(self.root, bg="#1E1E2E")
        self.body_container.pack(fill="both", expand=True, padx=20, pady=(15, 0))
        
        # Build views
        self.create_lock_view()
        self.create_unlock_view()
        
        # Bottom Utility Footer Row
        self.footer = tk.Frame(self.root, bg="#1E1E2E")
        self.footer.pack(fill="x", side="bottom", padx=20, pady=(0, 15))
        
        self.btn_shortcut = ModernButton(
            self.footer, text="CREATE DESKTOP SHORTCUT", width=220, height=32, radius=8,
            normal_color="#181825", hover_color="#313244", text_color="#CDD6F4",
            font=("Segoe UI", 8, "bold"), command=self.add_shortcut
        )
        self.btn_shortcut.pack(side="left")
        
        # Start at Lock tab
        self.show_tab(0)

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

    def show_tab(self, index):
        if index == 0:
            self.unlock_frame.pack_forget()
            self.lock_frame.pack(fill="both", expand=True)
            self.tab_bar.active_color = "#89B4FA" # Blue accent
            self.tab_bar.draw_tabs()
        else:
            self.lock_frame.pack_forget()
            self.unlock_frame.pack(fill="both", expand=True)
            self.tab_bar.active_color = "#A6E3A1" # Emerald accent
            self.tab_bar.draw_tabs()

    def create_lock_view(self):
        self.lock_frame = tk.Frame(self.body_container, bg="#1E1E2E")
        
        # Folder Selector Card
        f_card = tk.Frame(self.lock_frame, bg="#181825", padx=15, pady=12)
        f_card.pack(fill="x", pady=(0, 10))
        
        tk.Label(f_card, text="FOLDER PATH TO LOCK", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        row = tk.Frame(f_card, bg="#181825")
        row.pack(fill="x")
        self.lock_folder_entry = ModernEntry(row, width=420, height=36, placeholder="Click Browse to select folder...")
        self.lock_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_lock_browse = ModernButton(row, text="Browse", width=90, height=36, normal_color="#89B4FA", text_color="#11111B", command=self.browse_folder)
        self.btn_lock_browse.pack(side="right")
        
        # Password Entry Card
        p_card = tk.Frame(self.lock_frame, bg="#181825", padx=15, pady=12)
        p_card.pack(fill="x", pady=10)
        
        tk.Label(p_card, text="CHOOSE PASSWORD", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.lock_pass_entry = ModernEntry(p_card, width=530, height=36, is_password=True, placeholder="Create a secure access password...")
        self.lock_pass_entry.pack(fill="x", pady=(0, 8))
        
        tk.Label(p_card, text="CONFIRM PASSWORD", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.lock_confirm_entry = ModernEntry(p_card, width=530, height=36, is_password=True, placeholder="Confirm access password...")
        self.lock_confirm_entry.pack(fill="x")
        
        # Progress and Locking Actions Card
        a_card = tk.Frame(self.lock_frame, bg="#181825", padx=15, pady=12)
        a_card.pack(fill="x", pady=10)
        
        status_row = tk.Frame(a_card, bg="#181825")
        status_row.pack(fill="x", pady=(0, 5))
        
        self.lock_status_label = tk.Label(status_row, text="Ready to lock folder.", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9))
        self.lock_status_label.pack(side="left")
        
        self.lock_percent_label = tk.Label(status_row, text="0%", bg="#181825", fg="#89B4FA", font=("Segoe UI", 9, "bold"))
        self.lock_percent_label.pack(side="right")
        
        self.lock_progress_bar = ModernProgressBar(a_card, width=530, height=8, fill_color="#89B4FA")
        self.lock_progress_bar.pack(fill="x", pady=(0, 12))
        
        self.btn_lock = ModernButton(a_card, text="LOCK FOLDER", width=530, height=38, normal_color="#89B4FA", text_color="#11111B", command=self.start_lock_operation)
        self.btn_lock.pack(fill="x")

    def create_unlock_view(self):
        self.unlock_frame = tk.Frame(self.body_container, bg="#1E1E2E")
        
        # Lockbox Selector Card
        l_card = tk.Frame(self.unlock_frame, bg="#181825", padx=15, pady=12)
        l_card.pack(fill="x", pady=(0, 10))
        
        tk.Label(l_card, text="LOCKBOX FILE TO DECRYPT", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        
        row = tk.Frame(l_card, bg="#181825")
        row.pack(fill="x")
        self.unlock_file_entry = ModernEntry(row, width=420, height=36, placeholder="Click Browse to select lockbox file...")
        self.unlock_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_unlock_browse = ModernButton(row, text="Browse", width=90, height=36, normal_color="#A6E3A1", text_color="#11111B", command=self.browse_lockbox)
        self.btn_unlock_browse.pack(side="right")
        
        # Password Validation Card
        pv_card = tk.Frame(self.unlock_frame, bg="#181825", padx=15, pady=12)
        pv_card.pack(fill="x", pady=10)
        
        tk.Label(pv_card, text="VERIFY PASSWORD", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.unlock_pass_entry = ModernEntry(pv_card, width=530, height=36, is_password=True, placeholder="Enter password to unlock...")
        self.unlock_pass_entry.pack(fill="x")
        
        # Progress and Decrypt Actions Card
        da_card = tk.Frame(self.unlock_frame, bg="#181825", padx=15, pady=12)
        da_card.pack(fill="x", pady=10)
        
        status_row = tk.Frame(da_card, bg="#181825")
        status_row.pack(fill="x", pady=(0, 5))
        
        self.unlock_status_label = tk.Label(status_row, text="Ready to decrypt lockbox.", bg="#181825", fg="#A6ADC8", font=("Segoe UI", 9))
        self.unlock_status_label.pack(side="left")
        
        self.unlock_percent_label = tk.Label(status_row, text="0%", bg="#181825", fg="#A6E3A1", font=("Segoe UI", 9, "bold"))
        self.unlock_percent_label.pack(side="right")
        
        self.unlock_progress_bar = ModernProgressBar(da_card, width=530, height=8, fill_color="#A6E3A1")
        self.unlock_progress_bar.pack(fill="x", pady=(0, 12))
        
        self.btn_unlock = ModernButton(da_card, text="UNLOCK LOCKBOX", width=530, height=38, normal_color="#A6E3A1", text_color="#11111B", command=self.start_unlock_operation)
        self.btn_unlock.pack(fill="x")

    # Browse Methods
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Lock")
        if folder:
            self.lock_folder_entry.set(folder)
            
    def browse_lockbox(self):
        file = filedialog.askopenfilename(
            title="Select Lockbox File",
            filetypes=[("Lockbox Files", "*.lockbox"), ("All Files", "*.*")]
        )
        if file:
            self.unlock_file_entry.set(file)

    # State Status Setters
    def set_lock_status(self, text, is_error=False, is_success=False):
        self.lock_status_label.config(text=text)
        if is_error:
            self.lock_status_label.config(fg="#F38BA8")
        elif is_success:
            self.lock_status_label.config(fg="#A6E3A1")
        else:
            self.lock_status_label.config(fg="#A6ADC8")
            
    def set_unlock_status(self, text, is_error=False, is_success=False):
        self.unlock_status_label.config(text=text)
        if is_error:
            self.unlock_status_label.config(fg="#F38BA8")
        elif is_success:
            self.unlock_status_label.config(fg="#A6E3A1")
        else:
            self.unlock_status_label.config(fg="#A6ADC8")

    # Disable & Enable Input states to prevent overlapping operations
    def disable_lock_inputs(self):
        self.lock_folder_entry.entry.config(state="disabled")
        self.lock_pass_entry.entry.config(state="disabled")
        self.lock_confirm_entry.entry.config(state="disabled")
        self.btn_lock_browse.set_enabled(False)
        self.btn_lock.set_enabled(False)
        
    def enable_lock_inputs(self):
        self.lock_folder_entry.entry.config(state="normal")
        self.lock_pass_entry.entry.config(state="normal")
        self.lock_confirm_entry.entry.config(state="normal")
        self.btn_lock_browse.set_enabled(True)
        self.btn_lock.set_enabled(True)

    def disable_unlock_inputs(self):
        self.unlock_file_entry.entry.config(state="disabled")
        self.unlock_pass_entry.entry.config(state="disabled")
        self.btn_unlock_browse.set_enabled(False)
        self.btn_unlock.set_enabled(False)
        
    def enable_unlock_inputs(self):
        self.unlock_file_entry.entry.config(state="normal")
        self.unlock_pass_entry.entry.config(state="normal")
        self.btn_unlock_browse.set_enabled(True)
        self.btn_unlock.set_enabled(True)

    # Thread-Safe Progress updates
    def update_lock_progress(self, percentage, status_text):
        """Thread-safe callback interface to safely update the GUI from other threads."""
        self.root.after(0, self._safe_update_lock_progress, percentage, status_text)

    def _safe_update_lock_progress(self, percentage, status_text):
        val = percentage / 100.0 if percentage > 1.0 else percentage
        self.lock_progress_bar.set_progress(val)
        self.lock_percent_label.config(text=f"{int(val * 100)}%")
        self.set_lock_status(status_text)
        if val >= 1.0:
            self.set_lock_status(status_text, is_success=True)

    def update_unlock_progress(self, percentage, status_text):
        """Thread-safe callback interface to safely update the GUI from other threads."""
        self.root.after(0, self._safe_update_unlock_progress, percentage, status_text)

    def _safe_update_unlock_progress(self, percentage, status_text):
        val = percentage / 100.0 if percentage > 1.0 else percentage
        self.unlock_progress_bar.set_progress(val)
        self.unlock_percent_label.config(text=f"{int(val * 100)}%")
        self.set_unlock_status(status_text)
        if val >= 1.0:
            self.set_unlock_status(status_text, is_success=True)

    # Action operations
    def start_lock_operation(self):
        folder = self.lock_folder_entry.get().strip()
        passwd = self.lock_pass_entry.get()
        confirm = self.lock_confirm_entry.get()
        
        # Validation checks
        if not folder:
            self.set_lock_status("Error: Please select a folder to lock.", is_error=True)
            return
        if not passwd:
            self.set_lock_status("Error: Password cannot be empty.", is_error=True)
            return
        if passwd != confirm:
            self.set_lock_status("Error: Passwords do not match.", is_error=True)
            return
        if len(passwd) < 4:
            self.set_lock_status("Error: Password must be at least 4 characters.", is_error=True)
            return
            
        # Warning confirmation
        from tkinter import messagebox
        ans = messagebox.askyesno(
            "Security Warning",
            "WARNING: Locking this folder will encrypt its contents and securely shred the original files "
            "using cryptographically random byte overwriting. This action is PERMANENT and cannot be undone.\n\n"
            "Are you absolutely sure you want to proceed?",
            icon="warning"
        )
        if not ans:
            self.set_lock_status("Locking cancelled.", is_error=False)
            return
            
        self.set_lock_status("Preparing to lock...", is_error=False)
        self.disable_lock_inputs()
        
        def run():
            try:
                if self.lock_callback:
                    self.lock_callback(folder, passwd, self.update_lock_progress)
                else:
                    # Self-contained testing fallback demo
                    for i in range(101):
                        time.sleep(0.015)
                        self.update_lock_progress(i, f"Encrypting files... {i}%")
                    self.update_lock_progress(100, "Folder encrypted into lockbox successfully!")
            except Exception as e:
                self.update_lock_progress(0, f"Error: {str(e)}")
                self.set_lock_status(f"Error: {str(e)}", is_error=True)
            finally:
                self.root.after(0, self.enable_lock_inputs)
                
        run_in_background(run)

    def start_unlock_operation(self):
        file = self.unlock_file_entry.get().strip()
        passwd = self.unlock_pass_entry.get()
        
        # Validation checks
        if not file:
            self.set_unlock_status("Error: Please select a lockbox file.", is_error=True)
            return
        if not passwd:
            self.set_unlock_status("Error: Password cannot be empty.", is_error=True)
            return
            
        self.set_unlock_status("Preparing to unlock...", is_error=False)
        self.disable_unlock_inputs()
        
        def run():
            try:
                if self.unlock_callback:
                    self.unlock_callback(file, passwd, self.update_unlock_progress)
                else:
                    # Self-contained testing fallback demo
                    for i in range(101):
                        time.sleep(0.015)
                        self.update_unlock_progress(i, f"Decrypting lockbox... {i}%")
                    self.update_unlock_progress(100, "Lockbox unlocked and folder restored successfully!")
            except Exception as e:
                self.update_unlock_progress(0, f"Error: {str(e)}")
                self.set_unlock_status(f"Error: {str(e)}", is_error=True)
        run_in_background(run)

    def add_shortcut(self):
        import sys
        import os
        from tkinter import messagebox
        import subprocess
        
        if getattr(sys, 'frozen', False):
            exe_path = os.path.abspath(sys.executable)
        else:
            exe_path = os.path.abspath(sys.argv[0])
            
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, "File Locker.lnk")
        
        powershell_cmd = (
            f'$WshShell = New-Object -ComObject WScript.Shell; '
            f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
            f'$Shortcut.TargetPath = "{exe_path}"; '
            f'$Shortcut.IconLocation = "{exe_path},0"; '
            f'$Shortcut.Save()'
        )
        
        try:
            subprocess.run(
                ["powershell", "-Command", powershell_cmd],
                capture_output=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            messagebox.showinfo("Shortcut Created", "A desktop shortcut to AntiGrav Locker has been successfully created!")
        except Exception as e:
            messagebox.showerror("Shortcut Error", f"Failed to create desktop shortcut:\n{e}")


# Standard standalone execution entry for GUI testing
if __name__ == "__main__":
    root = tk.Tk()
    app = FolderLockerGUI(root)
    root.mainloop()
