import numpy as np
import pyaudio
import math
import state

SAMPLE_RATE = 44100
BUFFER_SIZE = 256

class AudioEngine:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=2,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=BUFFER_SIZE,
            stream_callback=self.callback
        )
        self.stream.start_stream()
        
        self.phase = 0.0
        
        # --- STATE ---
        self.curr_freq = 110.0
        self.curr_vol = 0.0
        self.curr_pan = 0.0
        self.curr_timbre = 0.0
        
        self.target_freq = 110.0
        self.target_vol = 0.0
        self.target_pan = 0.0
        self.target_timbre = 0.0
        
        self.last_samples = np.zeros(BUFFER_SIZE)

    def update_params(self, x, y):
        s = state.shared
        speed = math.sqrt(x**2 + y**2)
        
        # 1. Calculate Targets
        if speed > 0:
            self.target_vol = min(s.gain, (math.log(speed + 1) / 4.0) * s.gain)
        else:
            self.target_vol = 0.0

        self.target_freq = s.base_freq + (speed * s.pitch_scale)
        self.target_pan = max(-1.0, min(1.0, x / 60.0))
        self.target_timbre = min(1.0, abs(y) / 50.0)

    def decay(self):
        self.target_vol = 0.0

    def callback(self, in_data, frame_count, time_info, status):
        s = state.shared
        
        # --- SMOOTHING LOGIC ---
        alpha = (1.0 - s.smoothing) * 0.5
        
        # Exponential Moving Average
        self.curr_freq = (self.target_freq * alpha) + (self.curr_freq * (1 - alpha))
        self.curr_vol  = (self.target_vol * alpha)  + (self.curr_vol * (1 - alpha))
        self.curr_pan  = (self.target_pan * alpha)  + (self.curr_pan * (1 - alpha))
        self.curr_timbre = (self.target_timbre * alpha) + (self.curr_timbre * (1 - alpha))

        # --- SYNTHESIS ---
        # Calculate Phase Vector
        phase_inc = 2 * np.pi * self.curr_freq / SAMPLE_RATE
        phases = self.phase + np.arange(frame_count) * phase_inc
        
        # FIX: phase_inc is a float, so we just use it directly (no [-1])
        self.phase = (self.phase + frame_count * phase_inc) % (2 * np.pi)
        
        # Generate Waves
        wave_pure = np.sin(phases)
        wave_grit = np.sin(phases * 2.5) * self.curr_timbre
        
        mono = (wave_pure + wave_grit) * self.curr_vol * 0.5
        
        # Save for Visuals
        self.last_samples = mono
        
        # Stereo Panning
        norm_pan = (self.curr_pan + 1) / 2.0
        angle = norm_pan * (np.pi / 2)
        
        stereo = np.zeros(frame_count * 2, dtype=np.float32)
        stereo[0::2] = mono * np.cos(angle)
        stereo[1::2] = mono * np.sin(angle)
        
        return (stereo.tobytes(), pyaudio.paContinue)
    
    def shutdown(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
