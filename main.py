import customtkinter as ctk
import psutil
from pythonosc import udp_client
import threading
import time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class BatteryOSCApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VRChat Battery OSC Bridge - Steam Frame Edition")
        self.geometry("950x580")
        self.minsize(850, 520)

        self.is_running = False
        self.osc_client = None

        # Main window layout: Sidebar column (0) and Content column (1)
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

        self.init_label = ctk.CTkLabel(self.card_init, text="Steam Frame Battery Module Ready", font=("Segoe UI", 16), text_color="#ffffff")
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
        
        self.device_dropdown = ctk.CTkComboBox(self.card_settings, values=["Steam Frame (Default / OpenXR)", "Local Host System Battery"], width=280)
        self.device_dropdown.set("Steam Frame (Default / OpenXR)")
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
        self.avatar_title.grid(row=0, column=0, sticky="w", padx=25, pady=(18, 4))

        self.battery_status_label = ctk.CTkLabel(self.card_avatar, text="Bridge Offline. Toggle tracking above to begin.", font=("Segoe UI", 12), text_color="#a0a0a0", justify="left")
        self.battery_status_label.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 18))

        # Background Loop Threading
        self.poll_thread = threading.Thread(target=self.poll_battery_loop, daemon=True)
        self.poll_thread.start()

    def toggle_bridge_state(self):
        if self.toggle_tracking.get() == 1:
            try:
                ip = self.ip_entry.get()
                port = int(self.port_entry.get())
                self.osc_client = udp_client.SimpleUDPClient(ip, port)
                self.is_running = True
                self.init_label.configure(text="Steam Frame Battery Module Active")
            except Exception as e:
                self.battery_status_label.configure(text=f"Configuration Error: {e}")
                self.toggle_tracking.deselect()
                self.is_running = False
        else:
            self.is_running = False
            self.init_label.configure(text="Bridge Paused")
            self.battery_status_label.configure(text="Bridge Offline.")

    def poll_battery_loop(self):
        while True:
            if self.is_running and self.osc_client:
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        val = round(battery.percent / 100.0, 2)
                        plugged = "Plugged In" if battery.power_plugged else "Discharging"
                        
                        # Send to target OSC endpoint
                        self.osc_client.send_message("/avatar/parameters/BatteryLevel", val)
                        
                        self.battery_status_label.configure(
                            text=f"Connected Device: {self.device_dropdown.get()}\nBattery: {battery.percent}% ({plugged}) | OSC Float Sent: {val}"
                        )
                    else:
                        self.battery_status_label.configure(text="Searching for Steam Frame hardware link...")
                except Exception as ex:
                    self.battery_status_label.configure(text=f"Transmission Error: {ex}")
            time.sleep(5)

if __name__ == "__main__":
    app = BatteryOSCApp()
    app.mainloop()
