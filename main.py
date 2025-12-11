import sys
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import math
import struct
import random

# Check for libraries
try:
    import numpy as np
    import pyaudio
except ImportError:
    print("Error: This script requires 'numpy' and 'pyaudio'.")
    print("Install them with: pip install numpy pyaudio")
    sys.exit(1)

# --- CONFIGURATION ---
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 900
BG_COLOR = "#050505"
ACCENT_COLOR = "#00ffcc" # Cyan
WATERFALL_SPEED = 4       # Pixels per scroll
FFT_BINS = 40             # Number of frequency bands in waterfall
AUDIO_SAMPLE_RATE = 44100
BUFFER_SIZE = 1024        # Low latency (~23ms)

class AudioEngine:
    """Generates glitch-free, interpolated audio."""
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=AUDIO_SAMPLE_RATE,
            output=True,
            frames_per_buffer=BUFFER_SIZE,
            stream_callback=self.callback
        )
        self.stream.start_stream()
        
        # We track two phases independently to prevent clicking
        # when mixing different frequencies (Fundamental + Detuned Harmonic)
        self.phase1 = 0.0
        self.phase2 = 0.0
        
        self.current_freq = 110.0
        self.current_vol = 0.0
        
        self.target_freq = 110.0
        self.target_vol = 0.0

    def update_params(self, x_delta, y_delta):
        speed = math.sqrt(x_delta**2 + y_delta**2)
        
        # 1. Volume: Logarithmic curve
        if speed > 0:
            self.target_vol = min(0.6, (math.log(speed + 1) / 4))
        else:
            self.target_vol = 0.0

        # 2. Frequency: 110Hz -> 3000Hz
        self.target_freq = 110 + (speed * 20) 

    def callback(self, in_data, frame_count, time_info, status):
        # --- PER-SAMPLE INTERPOLATION (The Anti-Glitch Fix) ---
        
        # Create an array that smoothly slides from current_freq to target_freq
        # This eliminates the "stepping" sound (zipper noise)
        freqs = np.linspace(self.current_freq, self.target_freq, frame_count)
        vols = np.linspace(self.current_vol, self.target_vol, frame_count)
        
        # Update state for next buffer
        self.current_freq = self.target_freq
        self.current_vol = self.target_vol
        
        # --- ADDITIVE SYNTHESIS ---
        # Wave 1: Fundamental
        phase1_inc = 2 * np.pi * freqs / AUDIO_SAMPLE_RATE
        phases1 = self.phase1 + np.cumsum(phase1_inc)
        self.phase1 = phases1[-1] % (2 * np.pi) # Wrap safely
        wave1 = np.sin(phases1)
        
        # Wave 2: Second Harmonic (Octave + Detune)
        # We calculate this phase separately to avoid discontinuities/clicks
        # because 2.01 is not an integer multiple.
        phase2_inc = 2 * np.pi * (freqs * 2.01) / AUDIO_SAMPLE_RATE
        phases2 = self.phase2 + np.cumsum(phase2_inc)
        self.phase2 = phases2[-1] % (2 * np.pi)
        wave2 = np.sin(phases2) * 0.5

        # Mix and apply volume
        samples = (wave1 + wave2) * vols

        return (samples.astype(np.float32).tobytes(), pyaudio.paContinue)

class WaterfallApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Waterfall Spectrogram & Synth")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Signal Processing Buffers
        self.signal_buffer = np.zeros(128)
        
        self.audio = AudioEngine()
        self.setup_ui()
        self.start_logger_thread()

    def setup_ui(self):
        # 1. HEADER METRICS
        header = tk.Frame(self.root, bg=BG_COLOR, pady=15)
        header.pack(fill="x")
        
        self.lbl_freq = self.create_metric(header, "FREQUENCY", "0 Hz", ACCENT_COLOR)
        self.lbl_amp = self.create_metric(header, "AMPLITUDE", "0%", "white")

        # 2. WATERFALL SPECTROGRAM
        lbl_w = tk.Label(self.root, text="SPECTRAL WATERFALL (Time ↓  |  Freq →)", bg=BG_COLOR, fg="#666", font=("Arial", 10))
        lbl_w.pack(pady=(10,0))
        
        self.waterfall_height = 400
        self.waterfall = tk.Canvas(self.root, height=self.waterfall_height, bg="black", highlightthickness=0)
        self.waterfall.pack(fill="x", padx=20, pady=5)

        # 3. WAVEFORM (Oscilloscope)
        lbl_s = tk.Label(self.root, text="LIVE SIGNAL OSCILLOSCOPE", bg=BG_COLOR, fg="#666", font=("Arial", 10))
        lbl_s.pack(pady=(20,0))
        
        self.scope = tk.Canvas(self.root, height=120, bg="#111", highlightthickness=1, highlightbackground="#333")
        self.scope.pack(fill="x", padx=20, pady=5)
        
        # 4. LOGS
        log_frame = tk.Frame(self.root, bg=BG_COLOR, pady=10)
        log_frame.pack(fill="both", expand=True, padx=20)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#111", foreground="#ccc", fieldbackground="#111", font=("Menlo", 10), borderwidth=0)
        style.configure("Treeview.Heading", background="#222", foreground="white", relief="flat")
        
        self.tree = ttk.Treeview(log_frame, columns=("time", "hex", "val"), show="headings", height=6)
        self.tree.heading("time", text="TIME")
        self.tree.heading("hex", text="RAW HEX")
        self.tree.heading("val", text="DELTA")
        self.tree.column("time", width=100); self.tree.column("hex", width=200); self.tree.column("val", width=100)
        self.tree.pack(fill="both", expand=True)

    def create_metric(self, parent, title, val, color):
        f = tk.Frame(parent, bg=BG_COLOR, padx=40)
        f.pack(side="left", expand=True)
        tk.Label(f, text=title, bg=BG_COLOR, fg="#555", font=("Arial", 8)).pack()
        l = tk.Label(f, text=val, bg=BG_COLOR, fg=color, font=("Menlo", 24, "bold"))
        l.pack()
        return l

    def get_color(self, magnitude):
        """Maps magnitude (0-255) to a heatmap color (Black->Blue->Cyan->White)."""
        val = int(magnitude * 5) # Scale up visibility
        val = max(0, min(255, val))
        
        # Simple Heatmap Gradient
        if val < 50:
            return f"#{0:02x}{0:02x}{val*2:02x}" # Dark Blue
        elif val < 150:
            return f"#{0:02x}{val:02x}{255:02x}" # Cyan
        else:
            return f"#{val:02x}{255:02x}{255:02x}" # White-ish

    def update_visuals(self, x, y):
        # 1. Update Audio & Text
        mag = math.sqrt(x**2 + y**2)
        self.audio.update_params(x, y)
        self.lbl_freq.config(text=f"{int(self.audio.current_freq)} Hz")
        self.lbl_amp.config(text=f"{int(self.audio.current_vol * 100)}%")

        # 2. Update Buffer
        self.signal_buffer = np.roll(self.signal_buffer, -1)
        self.signal_buffer[-1] = mag

        # 3. DRAW SCOPE
        self.scope.delete("all")
        w = self.scope.winfo_width()
        h = self.scope.winfo_height()
        points = []
        for i, val in enumerate(self.signal_buffer):
            px = (i / len(self.signal_buffer)) * w
            py = h - min(h, val * 3) # Scale up
            points.append(px)
            points.append(py)
        if len(points) > 2:
            self.scope.create_line(points, fill=ACCENT_COLOR, width=2)

        # 4. DRAW WATERFALL
        self.waterfall.move("all", 0, WATERFALL_SPEED)
        
        # Calculate FFT
        fft_data = np.abs(np.fft.rfft(self.signal_buffer))
        bins = fft_data[:FFT_BINS]
        
        bin_w = self.waterfall.winfo_width() / len(bins)
        
        for i, b_mag in enumerate(bins):
            x1 = i * bin_w
            x2 = x1 + bin_w + 1
            color = self.get_color(b_mag)
            
            if b_mag > 2: 
                self.waterfall.create_rectangle(x1, 0, x2, WATERFALL_SPEED, fill=color, outline="")

    def start_logger_thread(self):
        t = threading.Thread(target=self.read_packet_logger)
        t.daemon = True
        t.start()
        self.root.after(10, self.process_queue)

    def read_packet_logger(self):
        cmd = ["sudo", "packetlogger", "convert", "-s", "-f", "mpr"]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
            for line in process.stdout:
                if self.stop_event.is_set(): break
                if "Receive" not in line: continue
                try:
                    hex_str = line.split("Receive")[1].strip()
                    parts = hex_str.split()
                    all_bytes = [int(p, 16) for p in parts]
                    if len(all_bytes) >= 17:
                        payload = all_bytes[11:17]
                        x = payload[1] | (payload[2] << 8)
                        if x > 32767: x -= 65536
                        y = payload[3] | (payload[4] << 8)
                        if y > 32767: y -= 65536

                        if x != 0 or y != 0:
                            self.data_queue.put({
                                "x": x, "y": y,
                                "hex": " ".join([f"{b:02X}" for b in payload]),
                                "time": datetime.datetime.now().strftime("%H:%M:%S")
                            })
                except Exception: continue
        except FileNotFoundError:
            self.data_queue.put("ERROR_CMD")

    def process_queue(self):
        try:
            while True:
                data = self.data_queue.get_nowait()
                if data == "ERROR_CMD":
                    messagebox.showerror("Error", "PacketLogger not found.")
                    return

                self.update_visuals(data['x'], data['y'])
                
                self.tree.insert("", 0, values=(data['time'], data['hex'], f"{data['x']}, {data['y']}"))
                if len(self.tree.get_children()) > 20:
                    self.tree.delete(self.tree.get_children()[-1])
        except queue.Empty:
            # Decay silence
            if self.audio.current_vol > 0.01:
                # Slowly lower target_vol if not already 0
                self.audio.target_vol = 0.0
                # But we must update current_vol manually here or in callback?
                # The callback handles the smoothing from current to target.
                # We just need to ensure the visuals scroll
                self.waterfall.move("all", 0, 1)
            else:
                pass
            pass
        
        self.root.after(20, self.process_queue)

if __name__ == "__main__":
    if len(sys.argv) == 1 and subprocess.run(["id", "-u"], capture_output=True).stdout.strip() != b'0':
        print("Please run with: sudo python3 mouse_waterfall_smooth.py")
        sys.exit(1)

    root = tk.Tk()
    app = WaterfallApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
