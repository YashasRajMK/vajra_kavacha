mport tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import os
import json
from PIL import Image, ImageTk
from face_elements import FaceSketchCanvas
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from skimage.feature import local_binary_pattern
from skimage.transform import resize
import pywhatkit
import threading

def send_whatsapp_via_pywhatkit(to_phone, message, wait_time=10):
    """
    Send OTP using pywhatkit (WhatsApp Web automation).
    Requires the user to be logged into WhatsApp Web on this PC.
    """
    # Validate format: must start with + followed by country code and digits only
    if not to_phone.startswith('+') or not to_phone[1:].isdigit():
        raise ValueError("Invalid phone number format. Use international format like +919876543210.")
    
    # Do NOT remove the '+' - pywhatkit expects it
    # to_phone = to_phone.replace('+', '')  # <-- Remove or comment this line
    
    pywhatkit.sendwhatmsg_instantly(
        to_phone,
        message,
        wait_time=wait_time,
        tab_close=True,
        close_time=3
    )

class FaceSketchApp:
    def _init_(self):
        self.root = tk.Tk()
        self.root.title("Forensic Face Sketch App")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
       
        # Setup data directories
        self.app_dir = os.path.dirname(os.path.abspath(_file_))
        self.data_dir = self.app_dir
        os.makedirs(self.data_dir, exist_ok=True)
       
        # Use data directory for credentials
        self.credentials_file = os.path.join(self.data_dir, "saved_credentials.json")
        self.load_saved_credentials()
       
        # Initialize image labels
        self.sketch_label = None
        self.matched_sketch_label = None
        self.result_label = None
        self.similarity_label = None
        self.result_info_frame = None
        self.current_sketch = None
        self.user_phone = ""
       
        # resend timer after id holder
        self._resend_after_id = None
       
        self.setup_styles()
        self.create_login_frame()
       
    def setup_styles(self):
        style = ttk.Style()
        style.configure('Custom.TButton',
                       padding=10,
                       font=('Helvetica', 12))
        style.configure('Title.TLabel',
                       font=('Helvetica', 24, 'bold'),
                       padding=20,
                       background='#f0f0f0')
        style.configure('Menu.TButton',
                       padding=20,
                       font=('Helvetica', 14))
        style.configure('Login.TFrame',
                       background='#ffffff')
        style.configure('Feature.TButton',
                       padding=10,
                       font=('Helvetica', 12))
                      
    def load_saved_credentials(self):
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    self.saved_credentials = json.load(f)
            else:
                self.saved_credentials = {}
        except:
            self.saved_credentials = {}
           
    def save_credentials(self, username, password):
        self.saved_credentials = {
            'username': username,
            'password': password
        }
        with open(self.credentials_file, 'w') as f:
            json.dump(self.saved_credentials, f)
           
    def clear_saved_credentials(self):
        if os.path.exists(self.credentials_file):
            os.remove(self.credentials_file)
        self.saved_credentials = {}
                      
    def create_login_frame(self):
        # Clear any existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
           
        # Create main login container with white background
        self.main_frame = ttk.Frame(self.root, style='Login.TFrame')
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")
       
        # Add logo or app name
        title = ttk.Label(
            self.main_frame,
            text="Forensic Face Sketch App",
            style='Title.TLabel'
        )
        title.pack(pady=20)
       
        subtitle = ttk.Label(
            self.main_frame,
            text="Forensic Face Sketch System",
            font=('Helvetica', 14),
            background='#ffffff'
        )
        subtitle.pack(pady=(0, 30))
       
        # Login frame
        self.login_frame = ttk.Frame(self.main_frame, style='Login.TFrame')
        self.login_frame.pack(padx=40, pady=20)
       
        # Username
        username_frame = ttk.Frame(self.login_frame)
        username_frame.pack(fill=tk.X, pady=5)
       
        ttk.Label(
            username_frame,
            text="Username:",
            font=('Helvetica', 12),
            background='#ffffff'
        ).pack(anchor='w')
       
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.pack(fill=tk.X, pady=5)
       
        # Password
        password_frame = ttk.Frame(self.login_frame)
        password_frame.pack(fill=tk.X, pady=5)
       
        ttk.Label(
            password_frame,
            text="Password:",
            font=('Helvetica', 12),
            background='#ffffff'
        ).pack(anchor='w')
       
        self.password_entry = ttk.Entry(
            password_frame,
            width=30,
            show="*"
        )
        self.password_entry.pack(fill=tk.X, pady=5)
       
        # Phone Number
        phone_frame = ttk.Frame(self.login_frame)
        phone_frame.pack(fill=tk.X, pady=5)
       
        ttk.Label(
            phone_frame,
            text="Phone Number:",
            font=('Helvetica', 12),
            background='#ffffff'
        ).pack(anchor='w')
       
        self.phone_entry = ttk.Entry(phone_frame, width=30)
        self.phone_entry.pack(fill=tk.X, pady=5)
        self.phone_entry.insert(0, "+91")
        # Bind validation for Indian phone numbers
        self.phone_entry.bind('<KeyRelease>', self.validate_indian_phone)
       
        # Remember me checkbox
        self.remember_var = tk.BooleanVar(value=bool(self.saved_credentials))
        remember_frame = ttk.Frame(self.login_frame)
        remember_frame.pack(fill=tk.X, pady=10)
       
        ttk.Checkbutton(
            remember_frame,
            text="Remember Me",
            variable=self.remember_var,
            style='TCheckbutton'
        ).pack(side=tk.LEFT)
       
        # Login button
        ttk.Button(
            self.login_frame,
            text="Login",
            style='Custom.TButton',
            command=self.verify_login
        ).pack(pady=20, fill=tk.X)
       
        # Fill in saved credentials if they exist
        if self.saved_credentials:
            self.username_entry.insert(0, self.saved_credentials.get('username', ''))
            self.password_entry.insert(0, self.saved_credentials.get('password', ''))
           
    def validate_indian_phone(self, event=None):
        """Validate and format Indian phone number"""
        phone = self.phone_entry.get()
       
        # Ensure it starts with +91
        if not phone.startswith('+91'):
            if phone.startswith('+'):
                # If it starts with + but not +91, allow user to type
                pass
            elif phone and not phone.startswith('+'):
                # If user types without +, add +91
                if phone.isdigit():
                    self.phone_entry.delete(0, tk.END)
                    self.phone_entry.insert(0, '+91' + phone)
                else:
                    # Remove non-digit characters except +
                    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
                    if cleaned and not cleaned.startswith('+'):
                        cleaned = '+91' + cleaned.replace('+', '')
                    self.phone_entry.delete(0, tk.END)
                    self.phone_entry.insert(0, cleaned)
       
        # Limit to +91 followed by 10 digits
        phone = self.phone_entry.get()
        if phone.startswith('+91'):
            digits_after = phone[3:]
            if len(digits_after) > 10:
                self.phone_entry.delete(0, tk.END)
                self.phone_entry.insert(0, '+91' + digits_after[:10])
           
    def verify_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        phone = self.phone_entry.get()
       
        # Validate Indian phone number format
        if phone and not phone.startswith('+91'):
            messagebox.showerror("Error", "Please enter a valid Indian phone number starting with +91")
            return
       
        if phone and len(phone) != 13: # +91 + 10 digits = 13 characters
            messagebox.showerror("Error", "Indian phone number must be 10 digits after +91 (e.g., +91XXXXXXXXXX)")
            return
       
        if username and password and phone: # Basic validation
            if self.remember_var.get():
                self.save_credentials(username, password)
            else:
                self.clear_saved_credentials()
            self.user_phone = phone
            self.generate_otp()
        else:
            messagebox.showerror("Error",
                               "Please enter username, password, and phone number")
           
    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        # send OTP via WhatsApp in a background thread
        def send_otp():
            try:
                send_whatsapp_via_pywhatkit(
                    self.user_phone,
                    f"Your OTP is: {self.otp}"
                )
                self.root.after(0, lambda: messagebox.showinfo(
                    "OTP Sent",
                    f"OTP sent to WhatsApp: {self.user_phone}"
                ))
            except Exception as e:
                # fallback if sending fails
                print("WhatsApp send failed:", e)
                self.root.after(0, lambda: messagebox.showwarning(
                    "Fallback OTP",
                    f"WhatsApp send failed: {str(e)}\nOTP: {self.otp}"
                ))
        threading.Thread(target=send_otp, daemon=True).start()
        # show verification screen immediately
        self.show_otp_verification()
       
    def show_otp_verification(self):
        # Hide login frame
        self.main_frame.place_forget()
       
        # Create OTP verification frame
        self.otp_frame = ttk.Frame(self.root, style='Login.TFrame')
        self.otp_frame.place(relx=0.5, rely=0.5, anchor="center")
       
        # Title
        ttk.Label(
            self.otp_frame,
            text="Verify Your Phone",
            style='Title.TLabel'
        ).pack(pady=10)
       
        # Phone number display (Indian format: +91****XXXX)
        if self.user_phone.startswith('+91') and len(self.user_phone) == 13:
            masked_phone = "+91****" + self.user_phone[-4:]
        else:
            masked_phone = self.user_phone[:3] + "*" + self.user_phone[-4:] if len(self.user_phone) > 7 else "*"
        ttk.Label(
            self.otp_frame,
            text=f"We've sent a 6-digit code to {masked_phone}",
            font=('Helvetica', 12),
            background='#ffffff',
            foreground='#666666'
        ).pack(pady=10)
       
        ttk.Label(
            self.otp_frame,
            text="Enter the code below:",
            font=('Helvetica', 11),
            background='#ffffff',
            foreground='#666666'
        ).pack(pady=(0, 20))
       
        # Create OTP input boxes (WhatsApp style)
        otp_container = ttk.Frame(self.otp_frame)
        otp_container.pack(pady=10)
       
        self.otp_entries = []
        for i in range(6):
            entry = tk.Entry(
                otp_container,
                width=3,
                font=('Helvetica', 20, 'bold'),
                justify='center',
                relief='solid',
                borderwidth=2,
                highlightthickness=2,
                highlightbackground='#cccccc',
                highlightcolor='#007bff'
            )
            entry.pack(side='left', padx=5)
            # use default arg to capture current i in lambda
            entry.bind('<KeyRelease>', lambda e, idx=i: self.on_otp_key_release(e, idx))
            entry.bind('<BackSpace>', lambda e, idx=i: self.on_otp_backspace(e, idx))
            entry.bind('<FocusIn>', lambda e, entry=entry: entry.select_range(0, tk.END))
            self.otp_entries.append(entry)
       
        # Focus on first entry
        self.otp_entries[0].focus_set()
       
        # Verify button
        self.verify_btn = ttk.Button(
            self.otp_frame,
            text="Verify",
            style='Custom.TButton',
            command=self.verify_otp,
            state='disabled'
        )
        self.verify_btn.pack(pady=20)
       
        # Resend OTP section
        resend_frame = ttk.Frame(self.otp_frame)
        resend_frame.pack(pady=10)
       
        ttk.Label(
            resend_frame,
            text="Didn't receive the code?",
            font=('Helvetica', 11),
            background='#ffffff',
            foreground='#666666'
        ).pack(side='left', padx=5)
       
        self.resend_btn = ttk.Button(
            resend_frame,
            text="Resend",
            command=self.resend_otp,
            style='Custom.TButton'
        )
        self.resend_btn.pack(side='left', padx=5)
       
        self.resend_timer_label = ttk.Label(
            resend_frame,
            text="",
            font=('Helvetica', 11),
            background='#ffffff',
            foreground='#666666'
        )
        self.resend_timer_label.pack(side='left', padx=5)
       
        # Initialize resend timer
        self.resend_countdown = 60
        self.resend_timer_running = False
        self.start_resend_timer()
       
        # Back button
        ttk.Button(
            self.otp_frame,
            text="← Back to Login",
            style='Custom.TButton',
            command=self.back_to_login
        ).pack(pady=10)
       
    def on_otp_key_release(self, event, idx):
        """Handle key release in OTP entry boxes"""
        entry = self.otp_entries[idx]
        value = entry.get()
       
        # Only allow digits
        if value and not value.isdigit():
            entry.delete(0, tk.END)
            return
       
        # Limit to one digit
        if len(value) > 1:
            entry.delete(1, tk.END)
            value = value[0]
       
        # Auto-focus to next entry
        if value and idx < 5:
            self.otp_entries[idx + 1].focus_set()
            self.otp_entries[idx + 1].select_range(0, tk.END)
       
        # Check if all entries are filled
        self.check_otp_complete()
       
    def on_otp_backspace(self, event, idx):
        """Handle backspace in OTP entry boxes"""
        entry = self.otp_entries[idx]
        if not entry.get() and idx > 0:
            # Move to previous entry if current is empty
            self.otp_entries[idx - 1].focus_set()
            self.otp_entries[idx - 1].select_range(0, tk.END)
        self.check_otp_complete()
       
    def check_otp_complete(self):
        """Check if all OTP digits are entered and enable verify button"""
        otp_value = ''.join([entry.get() for entry in self.otp_entries])
        if len(otp_value) == 6:
            self.verify_btn.config(state='normal')
            # Auto-verify after a short delay (like WhatsApp)
            self.root.after(300, self.verify_otp)
        else:
            self.verify_btn.config(state='disabled')
                 
    def verify_otp(self):
        otp_value = ''.join([entry.get() for entry in self.otp_entries])
        if otp_value == self.otp:
            # Stop resend timer and cancel pending callback
            self.resend_timer_running = False
            try:
                if hasattr(self, "_resend_after_id") and self._resend_after_id:
                    self.root.after_cancel(self._resend_after_id)
            except Exception:
                pass
            self._resend_after_id = None
            self.otp_frame.place_forget()
            self.create_main_menu()
        else:
            messagebox.showerror("Error", "Invalid OTP. Please try again.")
            # Clear all entries
            for entry in self.otp_entries:
                entry.delete(0, tk.END)
            self.otp_entries[0].focus_set()
            self.verify_btn.config(state='disabled')
           
    def resend_otp(self):
        """Resend OTP with new code"""
        if not self.resend_timer_running:
            # generate new OTP and restart timer
            self.generate_otp()
            # Clear all entries
            for entry in self.otp_entries:
                entry.delete(0, tk.END)
            self.otp_entries[0].focus_set()
            self.verify_btn.config(state='disabled')
            # Restart timer safely
            self.resend_countdown = 60
            self.start_resend_timer()
            messagebox.showinfo("OTP Resent", f"New OTP has been sent to {self.user_phone}")
           
    def start_resend_timer(self):
        """Start countdown timer for resend OTP"""
        # Ensure any previous scheduled callback is cancelled first
        try:
            if hasattr(self, "_resend_after_id") and self._resend_after_id:
                self.root.after_cancel(self._resend_after_id)
        except Exception:
            pass
        self.resend_timer_running = True
        try:
            self.resend_btn.config(state='disabled')
        except Exception:
            pass
        # Kick off the timer loop and save the after id
        self._resend_after_id = self.root.after(1000, self.update_resend_timer)
    def update_resend_timer(self):
        """Update resend timer countdown"""
        try:
            # Defensive: make sure relevant widgets still exist before updating
            if not hasattr(self, 'resend_timer_label') or not getattr(self, 'resend_timer_label').winfo_exists():
                # Nothing to update — stop timer and avoid scheduling more callbacks
                self.resend_timer_running = False
                self._resend_after_id = None
                return
            if self.resend_timer_running and self.resend_countdown > 0:
                self.resend_timer_label.config(text=f"({self.resend_countdown}s)")
                self.resend_countdown -= 1
                # schedule next tick and save id
                self._resend_after_id = self.root.after(1000, self.update_resend_timer)
            else:
                # countdown finished or stopped
                self.resend_timer_running = False
                # Only update UI if widget still exists
                if getattr(self, 'resend_timer_label').winfo_exists():
                    self.resend_timer_label.config(text="")
                if getattr(self, 'resend_btn').winfo_exists():
                    self.resend_btn.config(state='normal')
                self._resend_after_id = None
        except tk.TclError:
            # widget was destroyed while callback was running — stop quietly
            self.resend_timer_running = False
            try:
                if hasattr(self, "_resend_after_id") and self._resend_after_id:
                    self.root.after_cancel(self._resend_after_id)
            except Exception:
                pass
            self._resend_after_id = None
    def back_to_login(self):
        """Go back to login screen"""
        # Stop resend timer and cancel scheduled after
        self.resend_timer_running = False
        try:
            if hasattr(self, "_resend_after_id") and self._resend_after_id:
                self.root.after_cancel(self._resend_after_id)
        except Exception:
            pass
        self._resend_after_id = None
        self.create_login_frame()
           
    def create_main_menu(self):
        # Clear any existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
           
        # Create menu container
        menu_frame = ttk.Frame(self.root)
        menu_frame.pack(expand=True)
       
        # Title
        title = ttk.Label(
            menu_frame,
            text="Forensic Face Sketch App",
            style='Title.TLabel'
        )
        title.pack(pady=20)
       
        # Upload Sketch button
        ttk.Button(
            menu_frame,
            text="Upload Sketch",
            style='Menu.TButton',
            command=self.show_main_application
        ).pack(pady=20)
       
        # Create New Sketch button
        ttk.Button(
            menu_frame,
            text="Create New Sketch",
            style='Menu.TButton',
            command=self.show_sketch_creation
        ).pack(pady=20)
       
        # Logout button
        logout_btn = ttk.Button(
            menu_frame,
            text="Logout",
            style='Menu.TButton',
            command=self.logout
        )
        logout_btn.pack(pady=10)
       
    def upload_sketch_window(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
           
        # Create main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
       
        # Title
        title = ttk.Label(
            main_frame,
            text="Upload and Match Sketch",
            style='Title.TLabel'
        )
        title.pack(pady=20)
       
        # Instructions
        ttk.Label(
            main_frame,
            text="Upload a face sketch to find matching photos in the database.",
            font=('Helvetica', 12)
        ).pack(pady=10)
       
        # Upload frame
        upload_frame = ttk.Frame(main_frame)
        upload_frame.pack(pady=20)
       
        # Gender selection
        self.gender_var = tk.StringVar(value="all")
        gender_frame = ttk.Frame(upload_frame)
        gender_frame.pack(pady=10)
       
        ttk.Label(
            gender_frame,
            text="Filter by gender:",
            font=('Helvetica', 12)
        ).pack(side='left', padx=5)
       
        ttk.Radiobutton(
            gender_frame,
            text="All",
            variable=self.gender_var,
            value="all"
        ).pack(side='left', padx=5)
       
        ttk.Radiobutton(
            gender_frame,
            text="Male",
            variable=self.gender_var,
            value="male"
        ).pack(side='left', padx=5)
       
        ttk.Radiobutton(
            gender_frame,
            text="Female",
            variable=self.gender_var,
            value="female"
        ).pack(side='left', padx=5)
       
        # Upload section
        self.upload_label = ttk.Label(
            upload_frame,
            text="No sketch selected",
            font=('Helvetica', 12)
        )
        self.upload_label.pack(pady=10)
       
        # Preview frame
        self.preview_frame = ttk.Frame(upload_frame, borderwidth=1, relief='solid', width=300, height=300)
        self.preview_frame.pack_propagate(False)
        self.preview_frame.pack(pady=10)
       
        # Create empty preview label
        empty_img = Image.new('RGB', (300, 300), 'white')
        empty_photo = ImageTk.PhotoImage(empty_img)
        self.preview_label = ttk.Label(self.preview_frame, image=empty_photo)
        self.preview_label.image = empty_photo
        self.preview_label.pack(expand=True, fill='both')
       
        # Upload button
        upload_btn = ttk.Button(
            upload_frame,
            text="Select Sketch",
            style='Custom.TButton',
            command=self.upload_sketch
        )
        upload_btn.pack(pady=10)
       
        # Results frame with scrollbar
        results_container = ttk.Frame(main_frame)
        results_container.pack(pady=20, fill='both', expand=True)
       
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_container)
        scrollbar.pack(side='right', fill='y')
       
        # Create canvas for scrolling
        self.results_canvas = tk.Canvas(results_container, yscrollcommand=scrollbar.set)
        self.results_canvas.pack(side='left', fill='both', expand=True)
       
        scrollbar.config(command=self.results_canvas.yview)
       
        # Create frame inside canvas for results
        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_canvas.create_window((0, 0), window=self.results_frame, anchor='nw')
       
        # Configure canvas scrolling
        self.results_frame.bind('<Configure>', lambda e: self.results_canvas.configure(
            scrollregion=self.results_canvas.bbox('all')
        ))
       
        # Back button
        back_btn = ttk.Button(
            main_frame,
            text="Back to Menu",
            style='Custom.TButton',
            command=self.create_main_menu
        )
        back_btn.pack(pady=20)
       
    def upload_sketch(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            try:
                # Load and process the uploaded sketch
                uploaded_sketch = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                if uploaded_sketch is None:
                    raise Exception("Failed to load image")
               
                # Update label with filename (if upload UI used)
                try:
                    if hasattr(self, 'upload_label'):
                        self.upload_label.config(text=f"Selected: {os.path.basename(file_path)}")
                except Exception:
                    pass
               
                # Ensure image is in uint8 format
                uploaded_sketch = cv2.normalize(uploaded_sketch, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
               
                # Resize to a standard size for comparison
                uploaded_sketch = cv2.resize(uploaded_sketch, (256, 256))
               
                # Clear previous results if any
                try:
                    if hasattr(self, 'results_frame'):
                        for widget in self.results_frame.winfo_children():
                            widget.destroy()
                except Exception:
                    pass
               
                # Compare with saved sketches if using upload window
                try:
                    if hasattr(self, 'results_frame'):
                        self.compare_sketches(uploaded_sketch)
                except Exception:
                    # ignore if not in upload window
                    pass
               
                # Update current sketch for main app
                self.current_sketch = uploaded_sketch
               
                # Display the uploaded sketch in preview (if label exists)
                sketch_img = Image.open(file_path)
                sketch_img.thumbnail((300, 300))
                sketch_photo = ImageTk.PhotoImage(sketch_img)
                try:
                    if hasattr(self, 'preview_label'):
                        self.preview_label.configure(image=sketch_photo)
                        self.preview_label.image = sketch_photo
                except Exception:
                    # fallback: if main application labels exist, show there
                    if hasattr(self, 'sketch_label') and self.sketch_label:
                        self.sketch_label.configure(image=sketch_photo)
                        self.sketch_label.image = sketch_photo
                       
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process sketch: {str(e)}")
   
    def compare_sketches(self, uploaded_sketch):
        results = []
        dataset_dir = os.path.join(self.data_dir, "dataset")
       
        # Get selected gender filter
        gender_filter = getattr(self, 'gender_var', tk.StringVar(value="all")).get()
       
        # Clear previous results
        try:
            if hasattr(self, 'results_frame'):
                for widget in self.results_frame.winfo_children():
                    widget.destroy()
        except Exception:
            pass
           
        if not os.path.exists(dataset_dir):
            try:
                ttk.Label(
                    self.results_frame,
                    text="Dataset not found. Please run setup_dataset.py first.",
                    font=('Helvetica', 12)
                ).pack(pady=20)
            except Exception:
                messagebox.showinfo("Info", "Dataset not found. Please run setup_dataset.py first.")
            return
           
        # Extract features from uploaded sketch
        uploaded_features = self.extract_sketch_features(uploaded_sketch)
       
        # Compare with sketches in dataset
        genders = ['male', 'female'] if gender_filter == 'all' else [gender_filter]
       
        for gender in genders:
            sketches_dir = os.path.join(dataset_dir, gender, 'sketches')
            photos_dir = os.path.join(dataset_dir, gender, 'photos')
           
            if not os.path.exists(sketches_dir) or not os.path.exists(photos_dir):
                continue
               
            for sketch_file in os.listdir(sketches_dir):
                if not sketch_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    continue
                   
                # Load and process sketch
                sketch_path = os.path.join(sketches_dir, sketch_file)
                saved_sketch = cv2.imread(sketch_path, cv2.IMREAD_GRAYSCALE)
                if saved_sketch is None:
                    continue
                   
                saved_sketch = cv2.resize(saved_sketch, (256, 256))
                saved_features = self.extract_sketch_features(saved_sketch)
               
                # Calculate similarity
                score = self.calculate_similarity(uploaded_features, saved_features)
               
                # Find corresponding photo
                photo_file = sketch_file.replace('-sz1', '') # Remove sketch suffix
                photo_path = os.path.join(photos_dir, photo_file)
               
                if os.path.exists(photo_path):
                    results.append({
                        'sketch_path': sketch_path,
                        'photo_path': photo_path,
                        'score': score,
                        'gender': gender
                    })
       
        # Sort results by similarity score
        results.sort(key=lambda x: x['score'], reverse=True)
       
        if not results:
            try:
                ttk.Label(
                    self.results_frame,
                    text="No matches found. Try adjusting the gender filter.",
                    font=('Helvetica', 12)
                ).pack(pady=20)
            except Exception:
                messagebox.showinfo("No matches", "No matches found. Try adjusting the gender filter.")
            return
           
        # Display results
        try:
            ttk.Label(
                self.results_frame,
                text=f"Found {len(results)} matches (showing top 10):",
                font=('Helvetica', 14, 'bold')
            ).pack(pady=10)
        except Exception:
            pass
       
        # Create a frame for holding all result rows
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True)
       
        # Show top 10 matches
        for i, result in enumerate(results[:10], 1):
            try:
                result_frame = ttk.Frame(results_container)
                result_frame.pack(pady=10, padx=10, fill='x')
               
                # Load and resize sketch image
                sketch_img = Image.open(result['sketch_path'])
                sketch_img = sketch_img.convert('RGB') # Convert to RGB mode
                sketch_img.thumbnail((100, 100))
                sketch_photo = ImageTk.PhotoImage(sketch_img)
               
                # Load and resize photo image
                photo_img = Image.open(result['photo_path'])
                photo_img = photo_img.convert('RGB') # Convert to RGB mode
                photo_img.thumbnail((100, 100))
                photo_photo = ImageTk.PhotoImage(photo_img)
               
                # Keep references to prevent garbage collection
                result_frame.sketch_photo = sketch_photo
                result_frame.photo_photo = photo_photo
               
                # Create image labels
                sketch_label = ttk.Label(result_frame, image=sketch_photo)
                sketch_label.pack(side='left', padx=5)
               
                photo_label = ttk.Label(result_frame, image=photo_photo)
                photo_label.pack(side='left', padx=5)
               
                # Create info label
                info_frame = ttk.Frame(result_frame)
                info_frame.pack(side='left', padx=10, fill='x', expand=True)
               
                ttk.Label(
                    info_frame,
                    text=f"Match #{i} ({result['gender'].title()})",
                    font=('Helvetica', 12, 'bold')
                ).pack(anchor='w')
               
                ttk.Label(
                    info_frame,
                    text=f"Similarity: {result['score']:.1%}",
                    font=('Helvetica', 12)
                ).pack(anchor='w')
               
                # Add filename information
                ttk.Label(
                    info_frame,
                    text=f"File: {os.path.basename(result['photo_path'])}",
                    font=('Helvetica', 10)
                ).pack(anchor='w')
               
            except Exception as e:
                print(f"Error displaying result {i}: {str(e)}")
                continue
       
        # Update the canvas scroll region
        try:
            self.results_canvas.update_idletasks()
            self.results_canvas.configure(scrollregion=self.results_canvas.bbox('all'))
        except Exception:
            pass
       
    def extract_sketch_features(self, sketch):
        """Extract multiple features from a sketch for robust matching."""
        features = {}
       
        # 1. Edge features using multi-scale Canny edge detection
        edges_fine = cv2.Canny(sketch, 30, 100) # Fine details
        edges_coarse = cv2.Canny(sketch, 100, 200) # Coarse details
        features['edges_fine'] = edges_fine
        features['edges_coarse'] = edges_coarse
       
        # 2. Local Binary Patterns for texture analysis with multiple scales
        features['lbp'] = {}
        for radius in [1, 2, 3]: # Multiple scales for better texture capture
            n_points = 8 * radius
            lbp = local_binary_pattern(sketch, n_points, radius, method='uniform')
            features['lbp'][f'radius_{radius}'] = lbp
       
        # 3. Enhanced HOG features for better shape analysis
        win_size = (256, 256)
        cell_size = (8, 8)
        block_size = (16, 16)
        hog = cv2.HOGDescriptor(win_size, block_size, cell_size, cell_size, 9)
        features['hog'] = hog.compute(sketch)
       
        # 4. Region-based features with facial landmarks
        regions = self.extract_facial_regions(sketch)
        features['regions'] = regions
       
        # 5. Global intensity statistics
        features['global_stats'] = {
            'mean': np.mean(sketch),
            'std': np.std(sketch),
            'median': np.median(sketch),
        }
       
        return features
       
    def extract_facial_regions(self, sketch):
        """Extract features from specific facial regions with gender-specific considerations."""
        height, width = sketch.shape
        regions = {}
       
        # Define regions of interest (ROIs) with more precise facial areas
        rois = {
            'forehead': (0, height//4, width//4, 3*width//4),
            'eyes': (height//4, height//2, width//4, 3*width//4),
            'nose': (height//3, 2*height//3, width//3, 2*width//3),
            'mouth': (height//2, 3*height//4, width//4, 3*width//4),
            'jaw': (3*height//4, height, width//4, 3*width//4),
            'left_cheek': (height//3, 2*height//3, 0, width//3),
            'right_cheek': (height//3, 2*height//3, 2*width//3, width),
            'left_eye': (height//4, height//2, width//4, width//2),
            'right_eye': (height//4, height//2, width//2, 3*width//4)
        }
       
        for region_name, (y1, y2, x1, x2) in rois.items():
            roi = sketch[y1:y2, x1:x2]
            if roi.size == 0: # Skip empty regions
                continue
               
            # Extract comprehensive features for each region
            regions[region_name] = {
                'intensity': np.mean(roi),
                'variance': np.var(roi),
                'edges': cv2.Canny(roi, 50, 150),
                'gradient': np.gradient(roi),
                'histogram': np.histogram(roi, bins=32, range=(0, 256))[0]
            }
           
        return regions
       
    def calculate_similarity(self, features1, features2):
        """Calculate weighted similarity score between two sets of features with gender-specific considerations."""
        weights = {
            'edges_fine': 0.2, # Fine details like wrinkles, hair
            'edges_coarse': 0.15, # Coarse details like face shape
            'lbp': 0.15, # Texture features
            'hog': 0.2, # Overall shape features
            'regions': 0.25, # Specific facial regions
            'global_stats': 0.05 # Global image statistics
        }
       
        total_score = 0
       
        # Compare edge features at both scales
        edge_fine_sim = ssim(features1['edges_fine'], features2['edges_fine'], data_range=255, win_size=3)
        edge_coarse_sim = ssim(features1['edges_coarse'], features2['edges_coarse'], data_range=255, win_size=3)
        total_score += weights['edges_fine'] * edge_fine_sim
        total_score += weights['edges_coarse'] * edge_coarse_sim
       
        # Compare LBP features at multiple scales
        lbp_sim = 0
        for radius in [1, 2, 3]:
            key = f'radius_{radius}'
            if key in features1['lbp'] and key in features2['lbp']:
                sim = ssim(features1['lbp'][key], features2['lbp'][key],
                          data_range=features1['lbp'][key].max() - features1['lbp'][key].min(),
                          win_size=3)
                lbp_sim += sim / 3 # Average over scales
        total_score += weights['lbp'] * lbp_sim
       
        # Compare HOG features with L2 normalization
        hog1_norm = features1['hog'] / (np.linalg.norm(features1['hog']) + 1e-6)
        hog2_norm = features2['hog'] / (np.linalg.norm(features2['hog']) + 1e-6)
        hog_sim = 1 - np.linalg.norm(hog1_norm - hog2_norm) / 2
        total_score += weights['hog'] * hog_sim
       
        # Compare region features with weighted importance
        region_weights = {
            'forehead': 0.1,
            'eyes': 0.2,
            'nose': 0.15,
            'mouth': 0.15,
            'jaw': 0.1,
            'left_cheek': 0.1,
            'right_cheek': 0.1,
            'left_eye': 0.05,
            'right_eye': 0.05
        }
       
        region_sim = 0
        total_weight = 0
        common_regions = set(features1['regions'].keys()) & set(features2['regions'].keys())
       
        if common_regions:
            for region in common_regions:
                weight = region_weights.get(region, 0.1)
                region_score = self.compare_regions(
                    features1['regions'][region],
                    features2['regions'][region]
                )
                region_sim += weight * region_score
                total_weight += weight
               
            if total_weight > 0:
                region_sim /= total_weight
                total_score += weights['regions'] * region_sim
       
        # Compare global statistics
        stats1 = features1['global_stats']
        stats2 = features2['global_stats']
        stats_sim = 1 - (
            abs(stats1['mean'] - stats2['mean']) / 255 +
            abs(stats1['std'] - stats2['std']) / (stats1['std'] + stats2['std'] + 1e-6) +
            abs(stats1['median'] - stats2['median']) / 255
        ) / 3
        total_score += weights['global_stats'] * stats_sim
       
        return total_score
       
    def compare_regions(self, region1, region2):
        """Compare features of specific facial regions with enhanced metrics."""
        # Compare intensity and variance with normalization
        intensity_sim = 1 - abs(region1['intensity'] - region2['intensity']) / 255
        variance_sim = 1 - abs(region1['variance'] - region2['variance']) / (region1['variance'] + region2['variance'] + 1e-6)
       
        # Compare edge patterns with SSIM
        edge_sim = ssim(region1['edges'], region2['edges'], data_range=255)
       
        # Compare gradients
        grad_sim = 1 - np.mean(np.abs(np.array(region1['gradient']) - np.array(region2['gradient']))) / 255
       
        # Compare histograms using correlation
        hist_sim = 1 - np.mean(np.abs(region1['histogram'] - region2['histogram'])) / np.sum(region1['histogram'])
       
        # Weighted combination of regional features
        weights = {
            'intensity': 0.2,
            'variance': 0.2,
            'edges': 0.3,
            'gradient': 0.2,
            'histogram': 0.1
        }
       
        total_sim = (
            weights['intensity'] * intensity_sim +
            weights['variance'] * variance_sim +
            weights['edges'] * edge_sim +
            weights['gradient'] * grad_sim +
            weights['histogram'] * hist_sim
        )
       
        return total_sim
       
    def show_main_application(self):
        # Clear any existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
           
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
       
        # Create image frames container
        images_frame = ttk.Frame(main_frame)
        images_frame.pack(fill='x', pady=10)
       
        # Similarity label (initially hidden)
        self.similarity_label = ttk.Label(
            main_frame,
            text="",
            font=('Helvetica', 16, 'bold'),
            foreground='green'
        )
        self.similarity_label.pack(pady=5)
       
        # Create two image panels
        self.sketch_frame = ttk.Frame(images_frame, borderwidth=1, relief='solid', width=300, height=300)
        self.sketch_frame.pack_propagate(False)
        self.sketch_frame.pack(side='left', padx=10, pady=10)
       
        self.result_frame = ttk.Frame(images_frame, borderwidth=1, relief='solid', width=300, height=300)
        self.result_frame.pack_propagate(False)
        self.result_frame.pack(side='left', padx=10, pady=10)
       
        # Create empty labels for images (300x300 pixels)
        empty_img = Image.new('RGB', (300, 300), 'white')
        empty_photo = ImageTk.PhotoImage(empty_img)
       
        self.sketch_label = ttk.Label(self.sketch_frame, image=empty_photo)
        self.sketch_label.image = empty_photo
        self.sketch_label.pack(expand=True, fill='both')
       
        self.result_label = ttk.Label(self.result_frame, image=empty_photo)
        self.result_label.image = empty_photo
        self.result_label.pack(expand=True, fill='both')
       
        # Result info frame
        self.result_info_frame = ttk.Frame(main_frame)
        self.result_info_frame.pack(fill='x', pady=10)
       
        # Create buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
       
        # Add buttons with consistent size
        button_style = {'width': 15, 'style': 'Custom.TButton'}
       
        ttk.Button(
            buttons_frame,
            text="OPEN SKETCH",
            command=self.open_sketch,
            **button_style
        ).pack(side='left', padx=10)
       
        ttk.Button(
            buttons_frame,
            text="UPLOAD SKETCH",
            command=self.upload_sketch,
            **button_style
        ).pack(side='left', padx=10)
       
        ttk.Button(
            buttons_frame,
            text="FIND MATCH",
            command=self.find_match,
            **button_style
        ).pack(side='left', padx=10)
       
    def open_sketch(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            try:
                # Load and display the sketch
                sketch_img = Image.open(file_path)
                sketch_img.thumbnail((300, 300))
                sketch_photo = ImageTk.PhotoImage(sketch_img)
                self.sketch_label.configure(image=sketch_photo)
                self.sketch_label.image = sketch_photo
               
                # Update the current sketch
                self.current_sketch = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
               
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load sketch: {str(e)}")
               
    def find_match(self):
        if self.current_sketch is None:
            messagebox.showerror("Error", "Please load or upload a sketch first")
            return
       
        # Extract features from the current sketch
        sketch_features = self.extract_sketch_features(self.current_sketch)
       
        # Compare with saved sketches
        results = []
        dataset_dir = os.path.join(self.data_dir, "dataset")
       
        if not os.path.exists(dataset_dir):
            messagebox.showerror("Error", "Dataset not found. Please run setup_dataset.py first.")
            return
           
        # Compare with sketches in dataset
        for gender in ['male', 'female']:
            sketches_dir = os.path.join(dataset_dir, gender, 'sketches')
            photos_dir = os.path.join(dataset_dir, gender, 'photos')
           
            if not os.path.exists(sketches_dir) or not os.path.exists(photos_dir):
                continue
               
            for sketch_file in os.listdir(sketches_dir):
                if not sketch_file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    continue
                   
                # Load and process sketch
                sketch_path = os.path.join(sketches_dir, sketch_file)
                saved_sketch = cv2.imread(sketch_path, cv2.IMREAD_GRAYSCALE)
                if saved_sketch is None:
                    continue
                   
                saved_sketch = cv2.resize(saved_sketch, (256, 256))
                saved_features = self.extract_sketch_features(saved_sketch)
               
                # Calculate similarity
                score = self.calculate_similarity(sketch_features, saved_features)
               
                # Find corresponding photo
                photo_file = sketch_file.replace('-sz1', '') # Remove sketch suffix
                photo_path = os.path.join(photos_dir, photo_file)
               
                if os.path.exists(photo_path):
                    results.append({
                        'sketch_path': sketch_path,
                        'photo_path': photo_path,
                        'score': score,
                        'gender': gender
                    })
       
        # Sort results by similarity score
        results.sort(key=lambda x: x['score'], reverse=True)
       
        if not results:
            messagebox.showerror("Error", "No matches found")
            return
           
        # Display the top match
        top_match = results[0]
        self.similarity_label.config(text=f"Similarity: {top_match['score']:.1%}")
       
        # Display the matched sketch and photo
        matched_sketch_img = Image.open(top_match['sketch_path'])
        matched_sketch_img.thumbnail((300, 300))
        matched_sketch_photo = ImageTk.PhotoImage(matched_sketch_img)
        self.sketch_label.configure(image=matched_sketch_photo)
        self.sketch_label.image = matched_sketch_photo
       
        matched_photo_img = Image.open(top_match['photo_path'])
        matched_photo_img.thumbnail((300, 300))
        matched_photo_photo = ImageTk.PhotoImage(matched_photo_img)
        self.result_label.configure(image=matched_photo_photo)
        self.result_label.image = matched_photo_photo
       
    def logout(self):
        self.create_login_frame()
       
    def show_sketch_creation(self):
        # Clear any existing frames
        for widget in self.root.winfo_children():
            widget.destroy()
           
        # Create main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both')
       
        # Initialize sketch canvas with the app reference
        self.sketch_canvas = FaceSketchCanvas(main_frame, self)
       
        # Add back button at the bottom
        back_btn = ttk.Button(
            main_frame,
            text="Back to Menu",
            style='Custom.TButton',
            command=self.create_main_menu
        )
        back_btn.pack(pady=10)
       
    def run(self):
        self.root.mainloop()
if _name_ == "_main_":
    app = FaceSketchApp()
    app.run()