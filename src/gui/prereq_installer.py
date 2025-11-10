"""
Prerequisite installer GUI using tkinter (available by default on most systems)
Shown when required prerequisites are missing
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import shutil
from typing import List
import sys

try:
    from ..core.prerequisites import Prerequisite, PrerequisiteChecker
except ImportError:
    # Handle direct execution
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.core.prerequisites import Prerequisite, PrerequisiteChecker


class PrerequisiteInstallerGUI:
    """GUI for installing missing prerequisites"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gattrose-NG - Prerequisite Installation")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.checker = PrerequisiteChecker()
        self.prerequisites = self.checker.check_all()
        self.missing_required = self.checker.get_missing_required()
        self.missing_optional = self.checker.get_missing_optional()

        self.installing = False
        self.install_thread = None

        self._setup_ui()
        self._populate_prerequisites()

    def _setup_ui(self):
        """Setup the user interface"""

        # Header
        header_frame = tk.Frame(self.root, bg="#2b2b2b", height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="Gattrose-NG - Prerequisite Installation",
            font=("Arial", 16, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_label.pack(pady=10)

        subtitle_label = tk.Label(
            header_frame,
            text="Install required tools for wireless penetration testing",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#cccccc"
        )
        subtitle_label.pack()

        # Main content area
        content_frame = tk.Frame(self.root, bg="#1e1e1e")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Status label
        self.status_label = tk.Label(
            content_frame,
            text=f"Missing {len(self.missing_required)} required, {len(self.missing_optional)} optional prerequisites",
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#ff9900" if self.missing_required else "#00ff00"
        )
        self.status_label.pack(pady=(0, 10))

        # Notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Required tab
        self.required_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.required_frame, text="Required")

        # Optional tab
        self.optional_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.optional_frame, text="Optional")

        # Installed tab
        self.installed_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.installed_frame, text="Installed")

        # Log output
        log_label = tk.Label(
            content_frame,
            text="Installation Log:",
            font=("Arial", 10, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        )
        log_label.pack(pady=(10, 5), anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            content_frame,
            height=8,
            bg="#0d0d0d",
            fg="#00ff00",
            font=("Courier", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=False)

        # Button frame
        button_frame = tk.Frame(self.root, bg="#1e1e1e")
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.install_btn = tk.Button(
            button_frame,
            text="Install Required Tools",
            command=self.install_required,
            bg="#0066cc",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10,
            state=tk.NORMAL if self.missing_required else tk.DISABLED
        )
        self.install_btn.pack(side=tk.LEFT, padx=5)

        self.install_optional_btn = tk.Button(
            button_frame,
            text="Install Optional Tools",
            command=self.install_optional,
            bg="#006600",
            fg="#ffffff",
            font=("Arial", 11),
            padx=20,
            pady=10,
            state=tk.NORMAL if self.missing_optional else tk.DISABLED
        )
        self.install_optional_btn.pack(side=tk.LEFT, padx=5)

        self.continue_btn = tk.Button(
            button_frame,
            text="Continue to Gattrose",
            command=self.continue_to_app,
            bg="#009900",
            fg="#ffffff",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10,
            state=tk.NORMAL if not self.missing_required else tk.DISABLED
        )
        self.continue_btn.pack(side=tk.RIGHT, padx=5)

        self.quit_btn = tk.Button(
            button_frame,
            text="Exit",
            command=self.quit_app,
            bg="#cc0000",
            fg="#ffffff",
            font=("Arial", 11),
            padx=20,
            pady=10
        )
        self.quit_btn.pack(side=tk.RIGHT, padx=5)

    def _populate_prerequisites(self):
        """Populate the prerequisite lists"""
        self._populate_list(self.required_frame, self.missing_required, "Required Prerequisites")
        self._populate_list(self.optional_frame, self.missing_optional, "Optional Prerequisites")
        self._populate_list(self.installed_frame, self.checker.get_installed(), "Installed Prerequisites")

    def _populate_list(self, parent_frame, prereqs: List[Prerequisite], title: str):
        """Populate a list of prerequisites in a frame"""
        # Create treeview
        tree_frame = tk.Frame(parent_frame, bg="#1e1e1e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        tree = ttk.Treeview(
            tree_frame,
            columns=("Name", "Version", "Description"),
            show="headings",
            yscrollcommand=scrollbar.set
        )
        tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)

        # Configure columns
        tree.heading("Name", text="Name")
        tree.heading("Version", text="Version")
        tree.heading("Description", text="Description")

        tree.column("Name", width=150)
        tree.column("Version", width=100)
        tree.column("Description", width=400)

        # Add items
        for prereq in prereqs:
            tree.insert("", tk.END, values=(
                prereq.name,
                prereq.version or "N/A",
                prereq.description
            ))

    def log(self, message: str):
        """Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def install_required(self):
        """Install all required prerequisites"""
        self._install_prerequisites(self.missing_required, "required")

    def install_optional(self):
        """Install all optional prerequisites"""
        self._install_prerequisites(self.missing_optional, "optional")

    def _install_prerequisites(self, prereqs: List[Prerequisite], category: str):
        """Install a list of prerequisites"""
        if self.installing:
            messagebox.showwarning("Installation in Progress", "Please wait for current installation to complete")
            return

        if not prereqs:
            messagebox.showinfo("Nothing to Install", f"All {category} prerequisites are already installed")
            return

        # Confirm installation
        result = messagebox.askyesno(
            "Confirm Installation",
            f"Install {len(prereqs)} {category} prerequisites?\n\nThis will run sudo commands and may require your password."
        )

        if not result:
            return

        self.installing = True
        self.install_btn.config(state=tk.DISABLED)
        self.install_optional_btn.config(state=tk.DISABLED)

        # Run installation in thread
        self.install_thread = threading.Thread(
            target=self._run_installation,
            args=(prereqs, category),
            daemon=True
        )
        self.install_thread.start()

    def _run_installation(self, prereqs: List[Prerequisite], category: str):
        """Run installation (in background thread)"""
        self.log(f"\n{'='*60}")
        self.log(f"Installing {category} prerequisites...")
        self.log(f"{'='*60}\n")

        # Test sudo access first
        self.log("[*] Checking sudo access...")
        try:
            # Use pkexec if available (graphical sudo prompt)
            sudo_cmd = "pkexec" if shutil.which("pkexec") else "sudo"

            # Test sudo access
            test_result = subprocess.run(
                [sudo_cmd, "true"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if test_result.returncode != 0:
                self.log("[!] Failed to authenticate!")
                self.log("[!] Please run the installer with: sudo python3 gattrose.py")
                self.log("[!] Or ensure you have sudo privileges")
                return

            self.log(f"[+] Using {sudo_cmd} for installation")

        except Exception as e:
            self.log(f"[!] Sudo authentication error: {e}")
            self.log("[!] Please run with: sudo python3 gattrose.py")
            return

        # Update package lists first
        self.log("[*] Updating package lists...")
        try:
            result = subprocess.run(
                [sudo_cmd, "apt-get", "update"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                self.log("[+] Package lists updated")
            else:
                self.log(f"[!] Warning: apt-get update returned {result.returncode}")
                if "permission" in result.stderr.lower() or "authentication" in result.stderr.lower():
                    self.log("[!] Authentication failed. Please run with: sudo python3 gattrose.py")
                    return
        except Exception as e:
            self.log(f"[!] Error updating package lists: {e}")

        # Install each prerequisite
        success_count = 0
        fail_count = 0

        for prereq in prereqs:
            if not prereq.install_command:
                self.log(f"[!] No install command for {prereq.name}, skipping")
                continue

            # Replace 'sudo' with our determined sudo_cmd (might be pkexec)
            cmd_parts = prereq.install_command.split()
            if cmd_parts[0] == "sudo":
                cmd_parts[0] = sudo_cmd

            self.log(f"\n[*] Installing {prereq.name}...")
            self.log(f"    Command: {' '.join(cmd_parts)}")

            try:
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    self.log(f"[+] {prereq.name} installed successfully")
                    success_count += 1
                else:
                    self.log(f"[!] Failed to install {prereq.name}")
                    if result.stderr:
                        error_msg = result.stderr[:200]
                        # Filter out authentication spam
                        if "Authentication failed" not in error_msg:
                            # Check for common package issues
                            if "has no installation candidate" in error_msg:
                                self.log(f"    Package not available on this system")
                                if not prereq.required:
                                    self.log(f"    {prereq.name} is optional - continuing...")
                            else:
                                self.log(f"    Error: {error_msg}")
                    fail_count += 1

            except Exception as e:
                self.log(f"[!] Error installing {prereq.name}: {e}")
                fail_count += 1

        # Summary
        self.log(f"\n{'='*60}")
        self.log(f"Installation complete: {success_count} succeeded, {fail_count} failed")
        if category == "optional":
            self.log(f"Note: Optional tools may not be available on all systems")
        self.log(f"{'='*60}\n")

        # Re-check prerequisites
        self.log("[*] Re-checking prerequisites...")
        self.prerequisites = self.checker.check_all()
        self.missing_required = self.checker.get_missing_required()
        self.missing_optional = self.checker.get_missing_optional()

        # Update UI
        self.root.after(0, self._installation_complete)

    def _installation_complete(self):
        """Called when installation completes"""
        self.installing = False

        # Update status
        self.status_label.config(
            text=f"Missing {len(self.missing_required)} required, {len(self.missing_optional)} optional prerequisites",
            fg="#ff9900" if self.missing_required else "#00ff00"
        )

        # Update buttons
        self.install_btn.config(state=tk.NORMAL if self.missing_required else tk.DISABLED)
        self.install_optional_btn.config(state=tk.NORMAL if self.missing_optional else tk.DISABLED)
        self.continue_btn.config(state=tk.NORMAL if not self.missing_required else tk.DISABLED)

        # Refresh lists
        for widget in self.required_frame.winfo_children():
            widget.destroy()
        for widget in self.optional_frame.winfo_children():
            widget.destroy()
        for widget in self.installed_frame.winfo_children():
            widget.destroy()

        self._populate_prerequisites()

        if not self.missing_required:
            messagebox.showinfo(
                "Installation Complete",
                "All required prerequisites are installed!\n\nYou can now continue to Gattrose."
            )

    def continue_to_app(self):
        """Continue to main application"""
        if self.missing_required:
            messagebox.showerror(
                "Prerequisites Missing",
                "Cannot continue: Required prerequisites are missing.\n\nPlease install them first."
            )
            return

        self.root.quit()
        self.root.destroy()

    def quit_app(self):
        """Quit application"""
        if self.installing:
            messagebox.showwarning("Installation in Progress", "Please wait for installation to complete")
            return

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self) -> bool:
        """Run the GUI and return True if user wants to continue"""
        if not self.missing_required:
            # No missing required prerequisites, continue automatically
            return True

        self.root.mainloop()

        # Return True if window was closed normally (not via Exit button)
        return not self.missing_required


def main():
    """Entry point for testing"""
    app = PrerequisiteInstallerGUI()
    should_continue = app.run()

    if should_continue:
        print("Continuing to main application...")
    else:
        print("User chose to exit")


if __name__ == "__main__":
    main()
