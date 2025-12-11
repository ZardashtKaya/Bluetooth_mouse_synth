# state.py
class AppState:
    def __init__(self):
        # --- Audio Synthesis ---
        self.gain = 0.5          # Master Volume
        self.base_freq = 110.0   # Starting pitch
        self.pitch_scale = 15.0  # How much speed affects pitch
        self.smoothing = 0.3     # 0.01 (Slow) to 0.9 (Fast)
        
        # --- Visuals ---
        self.waterfall_speed = 2 # Pixels per frame
        self.contrast = 1.0      # Visual gain for spectrogram
        self.max_freq_view = 4000 # 0Hz to 4kHz range
        
        # --- Global Flags ---
        self.running = True

# Create a single shared instance
shared = AppState()
