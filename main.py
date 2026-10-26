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

        self.title("VRChat Battery OSC Bridge")
        self.geometry("950x540")
        self.minsize(800, 500)

        self.osc_client = udp_client.SimpleUDPClient("127.0.0.1", 9000)
        self.is_running = True

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=70, corner_radius=0, fg_color="#181818")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.home_btn = ctk.CTkButton(self.sidebar_frame, text="🏠", width=40, height=40, fg_color="#2b2b2b", font=("Arial", 16))
        self.home_btn.grid(row=0, column=0, padx=15, pady=(20, 10))

        # Main Content
        self.main_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Home", font=("Segoe UI", 24, "bold"), text_color="#ffffff")
        self.title_label.grid(row=0, column=0, sticky="w", padx=30, pady=(25, 15))

        # Status Card
        self.card_init = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_init.grid(row=1, column=0, sticky="ew", padx=30, pady=8)
        self.card_init.grid_columnconfigure(0, weight=1)

        self.init_label = ctk.CTkLabel(self.card_init, text="Battery Module Active", font=("Segoe UI", 16), text_color="#ffffff")
        self.init_label.grid(row=0, column=0, sticky="w", padx=25, pady=22)

        # OSC Info Card
        self.card_osc = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_osc.grid(row=2, column=0, sticky="ew", padx=30, pady=8)
        self.card_osc.grid_columnconfigure(0, weight=1)

        self.osc_title = ctk.CTkLabel(self.card_osc, text="📡  OSC Status", font=("Segoe UI", 14, "bold"), text_color="#ffffff")
        self.osc_title.grid(row=0, column=0, sticky="w", padx=25, pady=(18, 4))

        self.osc_details = ctk.CTkLabel(self.card_osc, text="Target: 127.0.0.1:9000 (/avatar/parameters/BatteryLevel)", font=("Segoe UI", 12), text_color="#a0a0a0")
        self.osc_details.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 18))

        # Battery Info Card
        self.card_avatar = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e", corner_radius=10)
        self.card_avatar.grid(row=3, column=0, sticky="ew", padx=30, pady=8)
        self.card_avatar.grid_columnconfigure(0, weight=1)

        self.avatar_title = ctk.CTkLabel(self.card_avatar, text="🔋  Battery Status", font=("Segoe UI", 14, "bold"), text_color="#ffffff")
        self.avatar_title.grid(row=0, column=0, sticky="w", padx=25, pady=(18, 4))

        self.battery_status_label = ctk.CTkLabel(self.card_avatar, text="Reading battery...", font=("Segoe UI", 12), text_color="#a0a0a0", justify="left")
        self.battery_status_label.grid(row=1, column=0, sticky="w", padx=25, pady=(0, 18))

        # Start background polling thread
        self.poll_thread = threading.Thread(target=self.poll_battery_loop, daemon=True)
        self.poll_thread.start()

    def poll_battery_loop(self):
        while self.is_running:
            battery = psutil.sensors_battery()
            if battery:
                val = round(battery.percent / 100.0, 2)
                plugged = "Plugged In" if battery.power_plugged else "Discharging"
                
                # Send OSC
                self.osc_client.send_message("/avatar/parameters/BatteryLevel", val)
                
                # Update UI
                self.battery_status_label.configure(
                    text=f"Battery: {battery.percent}% ({plugged})\nOSC Sent Float: {val}"
                )
            else:
                self.battery_status_label.configure(text="No battery detected on system.")
            time.sleep(5)

if __name__ == "__main__":
    app = BatteryOSCApp()
    app.mainloop()
