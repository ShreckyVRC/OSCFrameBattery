import customtkinter as ctk
import psutil
from pythonosc import udp_client
import threading
import time
import openvr

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Theme Color Palettes (Background base + cohesive overlay shades)
THEMES = {
    "Midnight Navy": {
        "bg": "#0a0f1d", "sidebar": "#070a13", "card": "#111827", 
        "border": "#1f2937", "text": "#f8fafc", "subtext": "#94a3b8", 
        "accent": "#38bdf8", "log_bg": "#070a13", "log_text": "#38bdf8"
    },
    "Clean Grey": {
        "bg": "#121212", "sidebar": "#181818", "card": "#1e1e1e", 
        "border": "#2b2b2b", "text": "#ffffff", "subtext": "#a0a0a0", 
        "accent": "#00ffcc", "log_bg": "#141414", "log_text": "#00ffcc"
    },
    "Orange & White": {
        "bg": "#ffffff", "sidebar": "#f1f5f9", "card": "#fff7ed", 
        "border": "#fed7aa", "text": "#1c1917", "subtext": "#78716c", 
        "accent": "#ea580c", "log_bg": "#fffbeb", "log_text": "#c2410c"
    },
    "Red & Black": {
        "bg": "#09090b", "sidebar": "#000000", "card": "#18181b", 
        "border": "#27272a", "text": "#fef2f2", "subtext": "#fca5a5", 
        "accent": "#ef4444", "log_bg": "#000000", "log_text": "#f87171"
    },
    "Purple & Orange": {
        "bg": "#1e1b4b", "sidebar": "#0f0c29", "card": "#2e1065", 
        "border": "#581c87", "text": "#faf5ff", "subtext": "#d8b4fe", 
        "accent": "#f97316", "log_bg": "#0f0c29", "log_text": "#fb923c"
    }
}

class BatteryOSCApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.initialized = False  # Guard flag to prevent startup callback crashes

        self.title("VRChat Battery OSC Bridge - Steam Frame Edition")
        self.geometry("980x820")
        self.minsize(850, 700)

        self.is_running = False
        self.osc_client = None
        self.poll_interval = 3.0  # Default polling frequency (min 1.0s)
        self.current_theme_name = "Midnight Navy"
        self.palette = THEMES[self.current_theme_name]
        
        # Animation spinner frames
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        # Main window layout (Sidebar column 0, Content column 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. Left Navigation Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=75, corner_radius=0, fg_color=self.palette["sidebar"])
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.home_btn = ctk.CTkButton(self.sidebar_frame, text="🏠", width=45, height=45, fg_color=self.palette["card"], hover_color=self.palette["border"], font=("Arial", 18), command=self.show_home_view)
        self.home_btn.grid(row=0, column=0, padx=15, pady=(25, 10))

        self.settings_btn = ctk.CTkButton(self.sidebar_frame, text="⚙️", width=45, height=45, fg_color="transparent", hover_color=self.palette["border"], font=("Arial", 18), command=self.show_settings_view)
        self.settings_btn.grid(row=1, column=0, padx=15, pady=10)

        # --- 2. Main Content Container ---
        self.right_container = ctk.CTkFrame(self, fg_color=self.palette["bg"], corner_radius=0)
        self.right_container.grid(row=0, column=1, sticky="nsew")
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(0, weight=1)  # Views take upper space
        self.right_container.grid_rowconfigure(1, weight=0)  # Persistent Log pinned at bottom

        # Views Container Frame
        self.views_container = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.views_container.grid(row=0, column=0, sticky="nsew")
        self.views_container.grid_columnconfigure(0, weight=1)
        self.views_container.grid_rowconfigure(0, weight=1)

        # --- 3. Persistent Debug Log (Created FIRST so it exists for startup events) ---
        self.card_log = ctk.CTkFrame(self.right_container, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_log.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 20))
        self.card_log.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(self.card_log, text="📜  Live Event & Debug Log (Persistent)", font=("Segoe UI", 13, "bold"), text_color=self.palette["text"])
        self.log_title.grid(row=0, column=0, sticky="w", padx=20, pady=(12, 4))

        self.log_textbox = ctk.CTkTextbox(self.card_log, height=120, fg_color=self.palette["log_bg"], border_color=self.palette["border"], border_width=1, text_color=self.palette["log_text"], font=("Consolas", 11))
        self.log_textbox.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        self.log_textbox.configure(state="disabled")

        # Build Views
        self.setup_home_view()
        self.setup_settings_view()

        # Show Home by default
        self.show_home_view()

        # Mark initialization complete
        self.initialized = True

        # Start background polling thread & UI animation loop
        self.poll_thread = threading.Thread(target=self.poll_battery_loop, daemon=True)
        self.poll_thread.start()
        
        self.animate_ui()
        self.log_event("Application initialized successfully. Persistent debug log active.")

    def setup_home_view(self):
        """Builds the main dashboard view, including the polling frequency slider."""
        self.home_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.home_frame.grid_columnconfigure(0, weight=1)

        # Page Header
        self.title_label = ctk.CTkLabel(self.home_frame, text="Home - Hardware Bridge", font=("Segoe UI", 24, "bold"), text_color=self.palette["text"])
        self.title_label.grid(row=0, column=0, sticky="w", padx=30, pady=(20, 10))

        # Card 1: Module Control & Toggle
        self.card_init = ctk.CTkFrame(self.home_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_init.grid(row=1, column=0, sticky="ew", padx=30, pady=6)
        self.card_init.grid_columnconfigure(0, weight=1)

        self.init_label = ctk.CTkLabel(self.card_init, text="⠋ Steam Frame Battery Module Ready", font=("Segoe UI", 15), text_color=self.palette["text"])
        self.init_label.grid(row=0, column=0, sticky="w", padx=25, pady=18)

        self.toggle_tracking = ctk.CTkSwitch(self.card_init, text="Toggle Tracking", font=("Segoe UI", 12), command=self.toggle_bridge_state, progress_color=self.palette["accent"])
        self.toggle_tracking.grid(row=0, column=1, sticky="e", padx=25, pady=18)

        # Card 2: Device Selection & OSC Target Settings
        self.card_settings = ctk.CTkFrame(self.home_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_settings.grid(row=2, column=0, sticky="ew", padx=30, pady=6)
        self.card_settings.grid_columnconfigure(0, weight=1)

        self.settings_title = ctk.CTkLabel(self.card_settings, text="⚙️  Target Configuration & Device Discovery", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"])
        self.settings_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=25, pady=(15, 8))

        self.device_label = ctk.CTkLabel(self.card_settings, text="Target Device:", font=("Segoe UI", 12), text_color=self.palette["subtext"])
        self.device_label.grid(row=1, column=0, sticky="w", padx=25, pady=5)
        
        self.device_dropdown = ctk.CTkComboBox(self.card_settings, values=["Steam Frame (OpenVR / Headset)", "Local Host System Battery"], width=280, command=self.on_device_change, fg_color=self.palette["border"], border_color=self.palette["border"], text_color=self.palette["text"])
        self.device_dropdown.set("Steam Frame (OpenVR / Headset)")
        self.device_dropdown.grid(row=1, column=1, sticky="e", padx=25, pady=5)

        self.target_label = ctk.CTkLabel(self.card_settings, text="OSC Address & Port:", font=("Segoe UI", 12), text_color=self.palette["subtext"])
        self.target_label.grid(row=2, column=0, sticky="w", padx=25, pady=(5, 15))

        self.ip_entry = ctk.CTkEntry(self.card_settings, width=130, fg_color=self.palette["border"], border_color=self.palette["border"], text_color=self.palette["text"])
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=2, column=1, sticky="e", padx=(0, 140), pady=(5, 15))

        self.port_entry = ctk.CTkEntry(self.card_settings, width=90, fg_color=self.palette["border"], border_color=self.palette["border"], text_color=self.palette["text"])
        self.port_entry.insert(0, "9000")
        self.port_entry.grid(row=2, column=1, sticky="e", padx=25, pady=(5, 15))

        # Card 3: Polling Frequency Decimal Slider (1.0s to 10.0s)
        self.card_poll = ctk.CTkFrame(self.home_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_poll.grid(row=3, column=0, sticky="ew", padx=30, pady=6)
        self.card_poll.grid_columnconfigure(0, weight=1)

        self.poll_label_title = ctk.CTkLabel(self.card_poll, text="⏱️ Polling Frequency (1.0s - 10.0s)", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"])
        self.poll_label_title.grid(row=0, column=0, sticky="w", padx=25, pady=(15, 4))

        self.poll_desc = ctk.CTkLabel(self.card_poll, text="Fine-tune update rate for hardware telemetry.", font=("Segoe UI", 12), text_color=self.palette["subtext"])
        self.poll_desc.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 5))

        self.poll_slider = ctk.CTkSlider(self.card_poll, from_=1.0, to=10.0, number_of_steps=90, command=self.on_slider_change, progress_color=self.palette["accent"])
        self.poll_slider.set(self.poll_interval)
        self.poll_slider.grid(row=2, column=0, sticky="ew", padx=25, pady=(5, 15))

        self.poll_val_label = ctk.CTkLabel(self.card_poll, text=f"{self.poll_interval:.1f}s", font=("Segoe UI", 14, "bold"), text_color=self.palette["accent"])
        self.poll_val_label.grid(row=2, column=1, sticky="e", padx=25, pady=(5, 15))

        # Card 4: Live Status & Metrics
        self.card_avatar = ctk.CTkFrame(self.home_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_avatar.grid(row=4, column=0, sticky="ew", padx=30, pady=6)
        self.card_avatar.grid_columnconfigure(0, weight=1)

        self.avatar_title = ctk.CTkLabel(self.card_avatar, text="🔋  Live Stream Status", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"])
        self.avatar_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=25, pady=(15, 4))

        self.battery_status_label = ctk.CTkLabel(self.card_avatar, text="Bridge Offline. Toggle tracking above to begin.", font=("Segoe UI", 12), text_color=self.palette["subtext"], justify="left")
        self.battery_status_label.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 15))

        self.battery_badge = ctk.CTkLabel(self.card_avatar, text="🔋 --%", font=("Segoe UI", 16, "bold"), text_color=self.palette["subtext"])
        self.battery_badge.grid(row=1, column=1, sticky="e", padx=25, pady=(0, 15))

    def setup_settings_view(self):
        """Builds the dedicated QoL Settings view."""
        self.settings_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.settings_frame.grid_columnconfigure(0, weight=1)

        # Page Header
        self.settings_header = ctk.CTkLabel(self.settings_frame, text="Preferences & QoL Settings", font=("Segoe UI", 24, "bold"), text_color=self.palette["text"])
        self.settings_header.grid(row=0, column=0, sticky="w", padx=30, pady=(20, 10))

        # Theme Selector Card
        self.card_pref_theme = ctk.CTkFrame(self.settings_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_pref_theme.grid(row=1, column=0, sticky="ew", padx=30, pady=6)
        self.card_pref_theme.grid_columnconfigure(0, weight=1)

        self.theme_title = ctk.CTkLabel(self.card_pref_theme, text="🎨 Interface Aesthetic & Color Theme", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"])
        self.theme_title.grid(row=0, column=0, sticky="w", padx=25, pady=(15, 4))

        self.theme_desc = ctk.CTkLabel(self.card_pref_theme, text="Select your preferred UI color scheme.", font=("Segoe UI", 12), text_color=self.palette["subtext"])
        self.theme_desc.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 10))

        self.theme_dropdown = ctk.CTkComboBox(self.card_pref_theme, values=list(THEMES.keys()), width=280, command=self.on_theme_change, fg_color=self.palette["border"], border_color=self.palette["border"], text_color=self.palette["text"])
        self.theme_dropdown.set(self.current_theme_name)
        self.theme_dropdown.grid(row=1, column=1, sticky="e", padx=25, pady=(0, 15))

        # App Info Card
        self.card_pref_info = ctk.CTkFrame(self.settings_frame, fg_color=self.palette["card"], border_color=self.palette["border"], border_width=1, corner_radius=10)
        self.card_pref_info.grid(row=2, column=0, sticky="ew", padx=30, pady=6)
        self.card_pref_info.grid_columnconfigure(0, weight=1)

        self.info_title = ctk.CTkLabel(self.card_pref_info, text="ℹ️ About VRChat Battery Bridge", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"])
        self.info_title.grid(row=0, column=0, sticky="w", padx=25, pady=(15, 4))

        self.info_body = ctk.CTkLabel(self.card_pref_info, text="Version 1.4.1 (Startup Guard & Fixed Theme Edition)\nDesigned for custom Poiyomi avatar parameter shaders.", font=("Segoe UI", 12), text_color=self.palette["subtext"], justify="left")
        self.info_body.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 15))

    def show_home_view(self):
        self.settings_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.home_btn.configure(fg_color=self.palette["card"])
        self.settings_btn.configure(fg_color="transparent")

    def show_settings_view(self):
        self.home_frame.grid_forget()
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.settings_btn.configure(fg_color=self.palette["card"])
        self.home_btn.configure(fg_color="transparent")
        self.log_event("Navigated to QoL Settings Menu.")

    def on_slider_change(self, value):
        if not getattr(self, 'initialized', False):
            return
        self.poll_interval = max(1.0, round(float(value), 1))
        if hasattr(self, 'poll_val_label'):
            self.poll_val_label.configure(text=f"{self.poll_interval:.1f}s")
        self.log_event(f"Option Changed -> Polling frequency set to {self.poll_interval}s")

    def on_theme_change(self, theme_choice):
        if not getattr(self, 'initialized', False):
            return
        self.current_theme_name = theme_choice
        self.palette = THEMES[theme_choice]
        self.log_event(f"Option Changed -> Interface Theme updated to '{theme_choice}'")
        
        # Apply theme colors across window containers instantly
        self.sidebar_frame.configure(fg_color=self.palette["sidebar"])
        self.right_container.configure(fg_color=self.palette["bg"])
        self.card_log.configure(fg_color=self.palette["card"], border_color=self.palette["border"])
        self.log_textbox.configure(fg_color=self.palette["log_bg"], border_color=self.palette["border"], text_color=self.palette["log_text"])
        self.log_title.configure(text_color=self.palette["text"])
        
        # Rebuild views to update dynamic color bindings
        current_view = "home" if self.home_frame.winfo_ismapped() else "settings"
        self.setup_home_view()
        self.setup_settings_view()
        if current_view == "home":
            self.show_home_view()
        else:
            self.show_settings_view()

    def log_event(self, message):
        timestamp = time.strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}\n"
        
        def _insert():
            if hasattr(self, 'log_textbox') and self.log_textbox.winfo_exists():
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", full_msg)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")

        if threading.current_thread() is threading.main_thread():
            _insert()
        else:
            self.after(0, _insert)

    def animate_ui(self):
        current_spinner = self.spinner_frames[self.spinner_index]
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)

        if hasattr(self, 'init_label') and self.init_label.winfo_exists():
            if self.is_running:
                self.init_label.configure(text=f"{current_spinner} Steam Frame Battery Module Active (Streaming)")
            else:
                self.init_label.configure(text=f"{current_spinner} Steam Frame Battery Module Ready (Standby)")

        self.after(120, self.animate_ui)

    def on_device_change(self, choice):
        if not getattr(self, 'initialized', False):
            return
        self.log_event(f"Option Changed -> Target Device set to: {choice}")

    def toggle_bridge_state(self):
        if self.toggle_tracking.get() == 1:
            try:
                ip = self.ip_entry.get()
                port = int(self.port_entry.get())
                self.osc_client = udp_client.SimpleUDPClient(ip, port)
                self.is_running = True
                self.log_event(f"Tracking STARTED. Target OSC Endpoint -> {ip}:{port}")
            except Exception as e:
                self.log_event(f"ERROR: Failed to start tracking -> {e}")
                self.battery_status_label.configure(text=f"Configuration Error: {e}")
                self.toggle_tracking.deselect()
                self.is_running = False
        else:
            self.is_running = False
            self.log_event("Tracking STOPPED by user.")
            self.battery_status_label.configure(text="Bridge Offline.")
            self.battery_badge.configure(text="🔋 --%", text_color=self.palette["subtext"])

    def get_openvr_battery(self):
        try:
            vrmeters = openvr.init(openvr.VRApplication_Background)
            hmd_found = False
            for i in range(openvr.k_unMaxTrackedDeviceCount):
                device_class = vrmeters.getTrackedDeviceClass(i)
                if device_class == openvr.TrackedDeviceClass_HMD:
                    hmd_found = True
                    battery_pct = vrmeters.getFloatTrackedDeviceProperty(
                        i, openvr.Prop_DeviceBatteryPercentage_Float
                    )
                    openvr.shutdown()
                    
                    if battery_pct >= 0.0:
                        return int(battery_pct * 100.0)
            openvr.shutdown()
            if not hmd_found:
                return "No HMD Found in OpenVR"
        except Exception as err:
            return f"OpenVR Init Error: {err}"
        return "Battery Property N/A"

    def poll_battery_loop(self):
        while True:
            if self.is_running and self.osc_client:
                try:
                    selected_target = self.device_dropdown.get()
                    battery_val = None
                    plugged_status = "Unknown"
                    
                    if "OpenVR" in selected_target:
                        result = self.get_openvr_battery()
                        if isinstance(result, int):
                            battery_val = result
                            plugged_status = "Headset Active"
                        else:
                            self.log_event(f"OpenVR warning: {result}")
                            if hasattr(self, 'battery_status_label') and self.battery_status_label.winfo_exists():
                                self.battery_status_label.configure(text=f"OpenVR Status: {result}")
                                self.battery_badge.configure(text="🔋 N/A", text_color="#f59e0b")
                            time.sleep(max(self.poll_interval, 1.0))
                            continue
                    else:
                        # Local Host System Battery check with desktop fallback
                        batt = psutil.sensors_battery()
                        if batt is not None:
                            battery_val = batt.percent
                            plugged_status = "Plugged In" if batt.power_plugged else "Discharging"
                        else:
                            battery_val = 100
                            plugged_status = "AC Powered / Wall Connected (Desktop)"

                    if battery_val is not None:
                        val_float = round(float(battery_val) / 100.0, 2)
                        
                        # Send data transfer via OSC
                        self.osc_client.send_message("/avatar/parameters/BatteryLevel", val_float)
                        
                        # Log data transfer & UI update
                        self.log_event(f"Data Transfer -> Sent OSC '/avatar/parameters/BatteryLevel' = {val_float} ({battery_val}% - {plugged_status})")
                        
                        if hasattr(self, 'battery_status_label') and self.battery_status_label.winfo_exists():
                            self.battery_status_label.configure(
                                text=f"Connected Source: {selected_target}\nStatus: {plugged_status} | Battery: {battery_val}%\nOSC Float Sent: {val_float}"
                            )
                            self.battery_badge.configure(text=f"🔋 {battery_val}%", text_color=self.palette["accent"])
                except Exception as ex:
                    self.log_event(f"CRITICAL EXCEPTION in poll loop: {ex}")
                    if hasattr(self, 'battery_status_label') and self.battery_status_label.winfo_exists():
                        self.battery_status_label.configure(text=f"Bridge Exception: {ex}")
            time.sleep(max(self.poll_interval, 1.0))

if __name__ == "__main__":
    app = BatteryOSCApp()
    app.mainloop()
