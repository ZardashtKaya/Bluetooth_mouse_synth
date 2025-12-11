# High-Performance Mouse Synth & Spectral Analyzer

A real-time, GPU-accelerated tool that transforms Bluetooth mouse movements into a responsive sci-fi soundscape. It features a modular architecture, low-latency audio synthesis, and a professional-grade 0–10kHz waterfall spectrogram.

## 🚀 Features

### 🔊 Modular Audio Engine
* **Spatial Audio:** X-Axis movement pans sound between Left/Right channels.
* **Dynamic Timbre:** Y-Axis movement introduces harmonic distortion ("grit").
* **Smart Smoothing:** Exponential Moving Average (EMA) filter eliminates mouse jitter while maintaining low latency.
* **Silence Detection:** Automatically decays volume when the mouse stops moving to prevent "stuck" notes.

### 📊 GPU-Accelerated Visuals
* **Powered by Dear PyGui:** Uses the GPU for rendering, allowing 60+ FPS performance without stalling the audio thread.
* **Dual Scope:** Real-time **Oscilloscope** (Time Domain) and **Waterfall Spectrogram** (Frequency Domain).
* **Wide-Band Analysis:** Visualizes the full harmonic series from 0Hz to 10kHz.
* **Auto-Contrast:** The spectrogram dynamically adjusts color intensity based on signal loudness.

### 🛠️ Live Controls
* Adjust **Gain**, **Smoothing**, **Base Frequency**, and **Pitch Sensitivity** in real-time.
* Toggle visual parameters like **Contrast** and **Scroll Speed**.
* View raw Hexadecimal packet logs live.

---

## 📦 Requirements

* **OS:** macOS (Required for `packetlogger` kernel tool).
* **Python:** 3.8+
* **Hardware:** Any Bluetooth Mouse (Magic Mouse, MX Master, etc.).

### Dependencies
Install the required Python libraries:

```bash
pip install dearpygui numpy pyaudio
````

*Note: On Apple Silicon (M1/M2/M3), if `pyaudio` fails to install, run `brew install portaudio` first.*

-----

## 📂 Project Structure

The project is split into 4 modular files for cleanliness and performance:

1.  **`main.py`**: The entry point. Handles the GPU GUI rendering (Dear PyGui), orchestrates threads, and manages the main event loop.
2.  **`audio_engine.py`**: Contains the `AudioEngine` class. Handles real-time synthesis, stereo panning, and the per-buffer smoothing mathematics.
3.  **`packet_reader.py`**: A dedicated thread that spawns the `sudo packetlogger` subprocess, parses raw Hex bytes, and pushes clean data to a queue.
4.  **`state.py`**: A shared state class that allows the GUI to update audio physics parameters instantly without complex thread locking.

-----

## ▶️ Usage

Because this tool taps directly into the macOS Bluetooth Packet Logger, it requires **root privileges**.

1.  Open your terminal in the project folder.
2.  Run the main script with `sudo`:

<!-- end list -->

```bash
sudo python3 main.py
```

3.  **Enter your password** to allow access to the Bluetooth stream.
4.  **Move your mouse:**
      * **Horizontal (X):** Pans audio Left \<-\> Right.
      * **Vertical (Y):** Adds "Grit" (Harmonic Distortion).
      * **Speed:** Increases Pitch and Volume.

-----

## 🎛️ Configuration Guide

Use the GUI sliders to tune the feel of the synth:

| Setting | Description | Recommended |
| :--- | :--- | :--- |
| **Smoothing** | Controls how "heavy" the mouse feels. Low = Slow/Cinematic. High = Fast/Twitchy. | `0.3` |
| **Pitch Scale** | How much the pitch rises with speed. | `15.0` |
| **Base Freq** | The pitch of the synth when moving slowly. | `110.0 Hz` |
| **Contrast** | Brightness of the Spectrogram colors. | `1.0` |

-----

## ⚠️ Troubleshooting

**`Error: PacketLogger command failed`**

  * Ensure you are running on **macOS**.
  * Ensure you used `sudo` to run the script.
  * If `packetlogger` is missing, install "Additional Tools for Xcode" from the [Apple Developer website](https://www.google.com/search?q=https://developer.apple.com/download/all/).

**`TypeError: 'float' object is not subscriptable`**

  * This was a known bug in older versions of `audio_engine.py`. Ensure you are using the latest version where `phase_inc` is treated as a float.

**Audio Glitches / Crackling**

  * If your CPU is under heavy load, open `audio_engine.py` and increase `BUFFER_SIZE` from `1024` to `2048`.

-----

## 📜 License

Open Source. feel free to fork, modify, and use in your own creative coding projects.
