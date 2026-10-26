import customtkinter as ctk
import psutil
from pythonosc import udp_client
import threading
import time
import openvr

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class BatteryOSCApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VRChat Battery OSC Bridge - Steam Frame Edition")
        self.geometry("950x720")
        self.minsize(850, 600)

        self.is_running = False
        self.osc_client = None
        
        # Animation spinner frames
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        # Main window layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. Left Navigation Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=70, corner_radius=0, fg_color="#181818")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.home_btn = ctk.CTkButton(self.sidebar_frame, text="🏠", width=40, height=40, fg_color="#2b2b2b", font=("Arial", 16))
        self.home_btn.grid(row=0, column=0, padx=15, pady=(20, 10))

        # --- 2. Main Content Area ---
        self.main_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Page Header
        self.title_label = ctk.CTkLabel(self.main_frame, text="Home - Hardware Bridge", font=("Segoe UI", 24, "bold"), text_color="#ffffff")
        self.title_label.grid(row=0, column=0, sticky="w", padx=30, pady=(25, 15))

        # --- Card 1: Module Control & Toggle ---
        self.card_init = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_init.grid(row=1, column=0, sticky="ew", padx=30, pady=8)
        self.card_init.grid_columnconfigure(0, weight=1)

        self.init_label = ctk.CTkLabel(self.card_init, text="⠋ Steam Frame Battery Module Ready", font=("Segoe UI", 16), text_color="#ffffff")
        self.init_label.grid(row=0, column=0, sticky="w", padx=25, pady=22)

        self.toggle_tracking = ctk.CTkSwitch(self.card_init, text="Toggle Tracking", font=("Segoe UI", 12), command=self.toggle_bridge_state)
        self.toggle_tracking.grid(row=0, column=1, sticky="e", padx=25, pady=22)

        # --- Card 2: Device Selection & OSC Target Settings ---
        self.card_settings = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_settings.grid(row=2, column=0, sticky="ew", padx=30, pady=8)
        self.card_settings.grid_columnconfigure(0, weight=1)

        self.settings_title = ctk.CTkLabel(self.card_settings, text="⚙️  Target Configuration & Device Discovery", font=("Segoe UI", 14, "bold"), text_color="#ffffff")
        self.settings_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=25, pady=(18, 10))

        # Device Dropdown
        self.device_label = ctk.CTkLabel(self.card_settings, text="Target Device:", font=("Segoe UI", 12), text_color="#a0a0a0")
        self.device_label.grid(row=1, column=0, sticky="w", padx=25, pady=5)
        
        self.device_dropdown = ctk.CTkComboBox(self.card_settings, values=["Steam Frame (OpenVR / Headset)", "Local Host System Battery"], width=280, command=self.on_device_change)
        self.device_dropdown.set("Steam Frame (OpenVR / Headset)")
        self.device_dropdown.grid(row=1, column=1, sticky="e", padx=25, pady=5)

        # IP & Port Inputs
        self.target_label = ctk.CTkLabel(self.card_settings, text="OSC Address & Port:", font=("Segoe UI", 12), text_color="#a0a0a0")
        self.target_label.grid(row=2, column=0, sticky="w", padx=25, pady=(5, 18))

        self.ip_entry = ctk.CTkEntry(self.card_settings, width=130)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=2, column=1, sticky="e", padx=(0, 140), pady=(5, 18))

        self.port_entry = ctk.CTkEntry(self.card_settings, width=90)
        self.port_entry.insert(0, "9000")
        self.port_entry.grid(row=2, column=1, sticky="e", padx=25, pady=(5, 18))

        # --- Card 3: Live Status & Metrics ---
        self.card_avatar = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_avatar.grid(row=3, column=0, sticky="ew", padx=30, pady=8)
        self.card_avatar.grid_columnconfigure(0, weight=1)

        self.avatar_title = ctk.CTkLabel(self.card_avatar, text="🔋  Live Stream Status", font=("Segoe UI", 14, "bold"), text_color="#ffffff")
        self.avatar_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=25, pady=(18, 4))

        self.battery_status_label = ctk.CTkLabel(self.card_avatar, text="Bridge Offline. Toggle tracking above to begin.", font=("Segoe UI", 12), text_color="#a0a0a0", justify="left")
        self.battery_status_label.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 18))

        # Right-side Battery Badge
        self.battery_badge = ctk.CTkLabel(self.card_avatar, text="🔋 --%", font=("Segoe UI", 16, "bold"), text_color="#a0a0a0")
        self.battery_badge.grid(row=1, column=1, sticky="e", padx=25, pady=(0, 18))

        # --- Card 4: Live Event & Debug Log ---
        self.card_log = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_log.grid(row=4, column=0, sticky="ew", padx=30, pady=8)
        self.card_log.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(self.card_log, text="📜  Live Event & Debug Log", font=("Segoe UI", 14, "bold"), text_color="#ffffff")
        self.log_title.grid(row=0, column=0, sticky="w", padx=25, pady=(18, 4))

        self.log_textbox = ctk.CTkTextbox(self.card_log, height=140, fg_color="#141414", text_color="#00ffcc", font=("Consolas", 11))
        self.log_textbox.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 18))
        self.log_textbox.configure(state="disabled")

        # Start background polling thread & UI animation loop
        self.poll_thread = threading.Thread(target=self.poll_battery_loop, daemon=True)
        self.poll_thread.start()
        
        self.animate_ui()
        self.log_event("Application initialized successfully. Ready.")

    def log_event(self, message):
        timestamp = time.strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}\n"
        
        def _insert():
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

        if self.is_running:
            self.init_label.configure(text=f"{current_spinner} Steam Frame Battery Module Active (Streaming)")
        else:
            self.init_label.configure(text=f"{current_spinner} Steam Frame Battery Module Ready (Standby)")

        self.after(120, self.animate_ui)

    def on_device_change(self, choice):
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
            self.battery_badge.configure(text="🔋 --%", text_color="#a0a0a0")

    def get_openvr_battery(self):
        try:
            vrmeters = openvr.init(openvr.VRApplication_Background)
            hmd_found = False
            for i in range(openvr.k_unMaxTrackedDeviceCount):
                # FIXED: Changed from getTrackedDeviceClassForIndex to getTrackedDeviceClass
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
                    
                    if "OpenVR" in selected_target:
                        result = self.get_openvr_battery()
                        if isinstance(result, int):
                            battery_val = result
                        else:
                            self.log_event(f"OpenVR warning: {result}")
                            self.battery_status_label.configure(text=f"OpenVR Status: {result}")
                            self.battery_badge.configure(text="🔋 N/A", text_color="#f29e4c")
                            time.sleep(3)
                            continue
                    else:
                        batt = psutil.sensors_battery()
                        if batt:
                            battery_val = batt.percent

                    if battery_val is not None:
                        val_float = round(float(battery_val) / 100.0, 2)
                        
                        # Send data transfer via OSC
                        self.osc_client.send_message("/avatar/parameters/BatteryLevel", val_float)
                        
                        # Log data transfer & UI update
                        self.log_event(f"Data Transfer -> Sent OSC '/avatar/parameters/BatteryLevel' = {val_float} ({battery_val}%)")
                        
                        self.battery_status_label.configure(
                            text=f"Connected Source: {selected_target}\nBattery Level: {battery_val}% | OSC Float Sent: {val_float}"
                        )
                        self.battery_badge.configure(text=f"🔋 {battery_val}%", text_color="#3fabf7")
                except Exception as ex:
                    self.log_event(f"CRITICAL EXCEPTION in poll loop: {ex}")
                    self.battery_status_label.configure(text=f"Bridge Exception: {ex}")
            time.sleep(3)

if __name__ == "__main__":
    app = BatteryOSCApp()
    app.mainloop()
