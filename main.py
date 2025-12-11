import dearpygui.dearpygui as dpg
import numpy as np
import threading
import queue
import time
import state
from packet_reader import PacketReader
from audio_engine import AudioEngine, SAMPLE_RATE, BUFFER_SIZE

# --- SETTINGS ---
W_WIDTH = 1200
W_HEIGHT = 900
SPECTRO_WIDTH = 600
SPECTRO_HEIGHT = 256  # Height of waterfall texture

# Data Exchange
data_queue = queue.Queue()
audio = AudioEngine()
reader = PacketReader(data_queue)

# --- VISUALIZATION BUFFERS ---
# Texture buffer: [Height, Width, 4(RGBA)] flattened
# We use floats 0.0-1.0 for texture data in DPG
texture_data = np.zeros((SPECTRO_HEIGHT, SPECTRO_WIDTH, 4), dtype=np.float32)
texture_data[:, :, 3] = 1.0  # Set Alpha channel to full opacity

def update_loop_fixed():
    last_packet_time = time.time()
    
    while state.shared.running:
        # 1. READ PACKETS
        try:
            while True:
                # Non-blocking get
                pkt = data_queue.get_nowait()
                
                if pkt == "ERROR_CMD":
                    print("Error: PacketLogger command failed.")
                    return
                
                # We got movement! Update Audio & Time
                audio.update_params(pkt['x'], pkt['y'])
                last_packet_time = time.time()
                
                # Update Log Table
                if dpg.does_item_exist("log_table"):
                    # Add a new row to the table
                    with dpg.table_row(parent="log_table"):
                        dpg.add_text(pkt["time"])
                        dpg.add_text(pkt["hex"])
                        dpg.add_text(f"{pkt['x']}, {pkt['y']}")

        except queue.Empty:
            pass
        
        # 2. SILENCE DETECTION (The "Stuck Note" Fix)
        # If no packet for 50ms, tell audio engine to decay volume
        if time.time() - last_packet_time > 0.05:
            audio.decay()

        # 3. DRAW VISUALS
        if dpg.is_dearpygui_running():
            signal = audio.last_samples
            
            # --- OSCILLOSCOPE ---
            # X axis = 0..1024, Y axis = signal array
            x_data = np.arange(len(signal))
            dpg.set_value("scope_series", [x_data, signal])
            
            # --- SPECTROGRAM (WATERFALL) ---
            # 1. Compute FFT
            fft_data = np.abs(np.fft.rfft(signal))
            
            # 2. Slice 0Hz to MaxFreqView
            freq_res = SAMPLE_RATE / BUFFER_SIZE
            target_bins = int(state.shared.max_freq_view / freq_res)
            fft_slice = fft_data[:target_bins]
            
            if len(fft_slice) > 0:
                # Normalize values for visualization
                fft_slice = fft_slice / (np.max(fft_slice) + 0.001)
                fft_slice *= state.shared.contrast
                
                # Resize array to fit texture width (Interpolation)
                row_data = np.interp(
                    np.linspace(0, len(fft_slice), SPECTRO_WIDTH),
                    np.arange(len(fft_slice)),
                    fft_slice
                )
                
                # Shift Texture Down (Scroll Effect)
                global texture_data
                speed = int(state.shared.waterfall_speed)
                # Roll data downwards
                texture_data = np.roll(texture_data, speed, axis=0)
                
                # Create the new top row(s)
                new_rows = np.zeros((speed, SPECTRO_WIDTH, 4), dtype=np.float32)
                
                # Color Mapping (Blue -> Purple -> White)
                new_rows[:, :, 0] = row_data * 0.5   # Red
                new_rows[:, :, 1] = row_data * 0.2   # Green
                new_rows[:, :, 2] = row_data * 1.0   # Blue
                new_rows[:, :, 3] = 1.0              # Alpha
                
                # Apply new rows to top of texture
                texture_data[:speed, :] = new_rows
                
                # Upload to GPU
                dpg.set_value("spectro_texture", texture_data.flatten())
                
        # Sleep briefly to spare CPU cycles (approx 60 FPS update rate)
        time.sleep(0.016)

# --- DPG GUI SETUP ---
dpg.create_context()

# Register the texture for the spectrogram
with dpg.texture_registry(show=False):
    dpg.add_raw_texture(
        width=SPECTRO_WIDTH, 
        height=SPECTRO_HEIGHT, 
        default_value=texture_data.flatten(), 
        format=dpg.mvFormat_Float_rgba, 
        tag="spectro_texture"
    )

with dpg.window(tag="Primary Window"):
    
    # Split Layout: Left (Controls) | Right (Visuals)
    with dpg.group(horizontal=True):
        
        # --- LEFT PANEL: CONFIGURATION ---
        with dpg.child_window(width=300):
            dpg.add_text("SYNTH SETTINGS", color=(0, 255, 204))
            dpg.add_separator()
            
            def update_config(sender, app_data, user_data):
                setattr(state.shared, user_data, app_data)

            dpg.add_slider_float(label="Master Gain", default_value=0.5, max_value=1.0, callback=update_config, user_data="gain")
            # Smoothing: 0.01 (Slow/Heavy) -> 0.95 (Fast/Responsive)
            dpg.add_slider_float(label="Smoothing", default_value=0.3, max_value=0.95, min_value=0.01, callback=update_config, user_data="smoothing")
            dpg.add_slider_float(label="Base Freq", default_value=110.0, max_value=500.0, min_value=50.0, callback=update_config, user_data="base_freq")
            dpg.add_slider_float(label="Pitch Scale", default_value=15.0, max_value=50.0, min_value=1.0, callback=update_config, user_data="pitch_scale")
            
            dpg.add_spacer(height=20)
            dpg.add_text("VISUAL SETTINGS", color=(0, 255, 204))
            dpg.add_separator()
            dpg.add_slider_float(label="Contrast", default_value=1.0, max_value=5.0, callback=update_config, user_data="contrast")
            dpg.add_slider_int(label="Waterfall Speed", default_value=2, max_value=10, min_value=0, callback=update_config, user_data="waterfall_speed")
            dpg.add_slider_int(label="Max Freq View", default_value=4000, max_value=10000, min_value=500, callback=update_config, user_data="max_freq_view")

            dpg.add_spacer(height=20)
            dpg.add_text("PACKET LOGS", color=(0, 255, 204))
            
            # Log Table
            with dpg.table(header_row=True, scrollY=True, height=-1, tag="log_table", policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(label="Time", width=70)
                dpg.add_table_column(label="Hex Payload", width=120)
                dpg.add_table_column(label="Delta", width=60)

        # --- RIGHT PANEL: VISUALS ---
        with dpg.child_window(width=-1):
            
            # Oscilloscope Plot
            dpg.add_text("Waveform (Time Domain)")
            with dpg.plot(height=150, width=-1, no_menus=True):
                # X Axis (No labels needed)
                dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True)
                
                # Y Axis - We capture the ID so we can parent the series to it
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Amp")
                
                # Line Series (Empty initially, updated in loop)
                dpg.add_line_series([], [], tag="scope_series", parent=y_axis)

            dpg.add_spacer(height=10)
            
            # Spectrogram Image
            dpg.add_text("Spectrogram (Frequency Domain)")
            dpg.add_image("spectro_texture", width=SPECTRO_WIDTH, height=SPECTRO_HEIGHT)

# --- STARTUP ---
reader.start()

# Start the Update Thread
render_thread = threading.Thread(target=update_loop_fixed, daemon=True)
render_thread.start()

# DPG Boilerplate
dpg.create_viewport(title="High-Performance Mouse Synth", width=W_WIDTH, height=W_HEIGHT)
dpg.setup_dearpygui()
dpg.set_primary_window("Primary Window", True)
dpg.show_viewport()
dpg.start_dearpygui()

# --- CLEANUP ---
state.shared.running = False
audio.shutdown()
dpg.destroy_context()
