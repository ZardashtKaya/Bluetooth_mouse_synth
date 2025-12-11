# Mouse Sonifier & Waterfall Visualizer

A real-time Bluetooth packet analyzer that transforms your mouse movements into a smooth, sci-fi synth soundtrack and a live FFT waterfall spectrogram.

This tool captures raw Bluetooth HID packets directly from the macOS kernel, decodes the 16-bit movement data, and maps velocity to pitch and amplitude using additive synthesis.


## 🚀 Features

* **Real-Time Sonification:** Converts mouse velocity into audio pitch and volume instantly.
* **Glitch-Free Audio Engine:** Uses **per-sample interpolation** to eliminate "zipper noise" (audio stepping artifacts) during fast movements.
* **Additive Synthesis:** Generates rich audio by combining a fundamental sine wave with a detuned harmonic.
* **Waterfall Spectrogram:** Visualizes the frequency content of your hand movements over time (FFT-based).
* **Live Oscilloscope:** See the raw magnitude signal of your mouse strokes.
* **Packet Logger:** Displays the raw Hexadecimal payload and decoded X/Y deltas in real-time.

## 🛠 Prerequisites

* **OS:** macOS (Required for `packetlogger`) can be obtained from older versions of Additional Tools from Apple's Developer website
* **Python:** 3.x
* **Hardware:** A Bluetooth Mouse (Magic Mouse, Logitech MX, etc.)

### Dependencies
You need `numpy` for the math and `pyaudio` for the sound engine.

```bash
pip install numpy pyaudio
