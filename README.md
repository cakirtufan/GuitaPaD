# GuitaPaD

**GuitaPaD** is an experimental real-time guitar effects processor written in Python.

The idea is simple: use a regular audio interface as the front end, build the DSP ourselves, and keep the system readable enough to understand what every stage is doing.

The project is currently developed and tested with an **Audient EVO 4** on Windows using **ASIO**, but the long-term goal is to make it easy to use with other audio interfaces as well.

> GuitaPaD is still under active development. Expect experiments, changing DSP models, and occasional rough edges.

## What works today

- Real-time guitar input/output
- Low-latency ASIO audio stream
- 48 kHz processing
- 128-sample target buffer
- Modular DSP effect chain
- 35 Hz high-pass filter
- Master gain and safety limiter
- Experimental overdrive models
- PySide6 desktop interface
- Input/output level metering
- Callback timing and deadline monitoring
- Raw DI recording to 24-bit WAV
- Offline DSP analysis tools

The current Python/NumPy implementation still has substantial real-time headroom on the development system.

## Requirements

- Python 3.12+
- An audio interface
- A low-latency audio driver
- Git

On Windows, **ASIO is strongly recommended**.

Main Python dependencies:

- NumPy
- sounddevice / PortAudio
- PySide6

## Installation

Clone the repository:

```bash
git clone https://github.com/cakirtufan/GuitaPaD.git
cd GuitaPaD
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install GuitaPaD with the GUI dependencies:

```bash
pip install -e ".[gui]"
```

Start the desktop interface:

```bash
python tools/gui.py
```

## Using another audio interface

GuitaPaD is currently configured around the **Audient EVO 4**, so another interface may require a small configuration change.

First, install the low-latency driver supplied by the manufacturer.

Then inspect the audio devices visible to Python:

```bash
python -c "import sounddevice as sd; print(sd.query_devices()); print(sd.query_hostapis())"
```

### 1. Select your interface

Device detection currently lives in:

```text
src/guitapad/audio/sounddevice_backend.py
```

At the moment, the backend looks for an ASIO device whose name contains:

```text
AUDIENT
```

If you use another interface, adapt the device-selection logic to match the name reported by `sounddevice.query_devices()`.

For example:

```python
if (
    host_api_name.upper() == "ASIO"
    and "FOCUSRITE" in device_name.upper()
):
    return device_index
```

A future version should make audio-device selection available directly from the GUI instead of requiring a source-code change.

### 2. Configure the channels

Audio channel settings are defined in:

```text
src/guitapad/audio/config.py
```

The current development configuration uses:

```python
input_channels = 4
output_channels = 4

guitar_input_index = 0
left_output_index = 0
right_output_index = 1
```

Channel indexes are zero-based.

If your guitar is connected to the second input, for example:

```python
guitar_input_index = 1
```

Make sure `input_channels` and `output_channels` are supported by your interface and driver.

### 3. Start conservatively

The current development settings are:

```text
Sample rate : 48,000 Hz
Buffer      : 128 samples
```

If your interface produces dropouts or callback errors, start with a larger hardware buffer and reduce it gradually.

The GUI reports useful real-time diagnostics including:

- maximum callback time
- callback deadline load
- stream errors
- block-size mismatches
- total reported I/O latency

These measurements are especially useful when testing GuitaPaD on a new device.

## Signal path

The project is built around a simple modular chain:

```text
Guitar
  |
Audio interface
  |
Raw input
  |
35 Hz HPF
  |
DSP effects
  |
Master gain
  |
Safety limiter
  |
Audio interface output
```

Effects share a small common DSP interface and are processed sequentially.

The real-time callback is intentionally kept predictable:

- no file I/O
- no GUI work
- no network access
- no printing/logging
- minimal allocation
- no blocking operations

## Raw DI recording

GuitaPaD can capture the raw guitar signal before the effect chain.

Recordings are stored as:

```text
48 kHz
mono
24-bit PCM WAV
```

During recording, the audio callback only copies samples into a preallocated RAM buffer.

The WAV file is written after recording stops, outside the real-time callback.

This gives us a reproducible source signal for controlled A/B comparisons: the exact same guitar performance can be passed through different DSP algorithms offline.

## Project status

The real-time engine, GUI, metering, HPF, recording system, and basic DSP architecture are working.

Distortion and overdrive modelling are still experimental.

Several simple static waveshaping approaches have already been tested and deliberately rejected because they did not produce the desired pedal-like response.

The next direction is physically motivated nonlinear circuit modelling, followed by controlled investigation of nonlinear aliasing and oversampling.

Development notes and measurements are kept in:

```text
GuitaPaD_Daily_Log.md
```

## Contributing

Contributions, experiments, measurements, and hardware reports are welcome.

Interesting areas include:

- support for additional audio interfaces
- device selection from the GUI
- Linux and macOS audio backends
- guitar DSP algorithms
- virtual-analog circuit modelling
- anti-aliasing and oversampling
- amp and cabinet processing
- MIDI controller support
- presets
- profiling and real-time optimisation
- testing on different hardware

If you try GuitaPaD with another interface, an issue containing the following information would be especially useful:

- operating system
- audio interface
- driver/backend
- sample rate
- buffer size
- measured latency
- callback load
- any stream errors or block-size mismatches

## Philosophy

GuitaPaD is intentionally built from the DSP level upward.

The goal is not simply to wrap existing guitar plugins. The goal is to understand, implement, measure, and improve the signal-processing stages directly.

Python is used first because readability and fast iteration matter.

If profiling eventually shows that a specific real-time component needs a lower-level implementation, that decision should be based on measurements rather than assumptions.

---

Built one block, one measurement, and one questionable distortion experiment at a time.
