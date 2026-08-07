# GuitaPaD

**GuitaPaD** is an open-source adaptive guitar tone platform built with Python, real-time DSP, and machine learning.

The long-term goal is not just to provide a collection of guitar effects. GuitaPaD aims to **listen to a reference guitar tone, analyse its character, and automatically adapt an interpretable DSP signal chain to move the player's own guitar toward that target tone**.

A typical future workflow could look like this:

```text
Reference guitar tone
        |
        v
Tone analysis / ML representation
        |
        v
Target tone
        ^
        |
Your guitar DI
        |
        v
GuitaPaD DSP chain
        |
        v
Rendered tone
        |
        v
Compare -> optimise -> refine
```

Instead of a fixed preset saying "these are the settings for this song", the idea is:

> **Given your guitar and your audio interface, find the DSP settings that best reproduce the character of a chosen reference tone.**

The project is currently developed and tested with an **Audient EVO 4** on Windows using **ASIO**, but the architecture is intended to support other interfaces and platforms.

> GuitaPaD is still experimental. The real-time engine is working, while the adaptive tone-matching system is the main development direction.

---

## Why GuitaPaD?

Most guitar software offers fixed effects, amp models, or presets.

GuitaPaD is being designed around a different question:

> Can we build an open system that understands a reference tone and adapts itself to the player's actual input signal?

That turns guitar tone matching into a hybrid **DSP + optimisation + machine-learning problem**.

The DSP chain remains explicit and inspectable. Machine learning is used to analyse tones, estimate useful starting parameters, and guide the search for a better match.

The aim is not to hide everything inside a black-box neural network.

---

## Project philosophy

GuitaPaD follows a few core principles:

- **Interpretable DSP first**  
  Effects, amp stages, tone shaping, cabinets, and other processing blocks should remain understandable and measurable.

- **Machine learning where it adds value**  
  ML should help analyse reference tones, estimate parameters, build perceptual representations, and accelerate optimisation.

- **Measure before optimising**  
  Latency, callback time, signal levels, spectral behaviour, and listening results are measured rather than assumed.

- **Python first**  
  Python is used for readability, experimentation, DSP research, data analysis, and ML development.

- **Native code only when justified**  
  C++/JUCE or another lower-level implementation should be introduced only when profiling shows a real need.

- **Community-friendly tone recipes**  
  Tone configurations should eventually be shareable as open parameter files rather than opaque proprietary presets.

---

## Current status

The real-time foundation is already working.

Current features include:

- Real-time guitar input and output
- ASIO audio backend
- 48 kHz processing
- 128-sample target callback
- Modular in-place DSP chain
- 35 Hz high-pass filter
- Master gain
- Safety limiter
- Experimental overdrive models
- PySide6 desktop GUI
- Input/output metering
- Callback timing and deadline monitoring
- Raw DI recording
- 24-bit mono WAV export
- Offline DSP analysis tools

The current Audient EVO 4 setup reports approximately:

```text
Sample rate       48,000 Hz
Callback          128 samples
Total I/O latency ~9.79 ms
```

During recent DSP + DI-recording tests, maximum callback time remained around 20% of the available callback deadline.

This means the immediate bottleneck is currently **tone modelling**, not Python callback performance.

---

## Where the project is going

The intended tone engine is larger than a single distortion effect.

A future signal path may look roughly like this:

```text
Guitar DI
   |
Input calibration
   |
Gate
   |
Pre-EQ / tightening
   |
Nonlinear amp stages
   |
Tone stack
   |
Power-amp shaping
   |
Cabinet
   |
Microphone / spatial shaping
   |
Post-EQ
   |
Output
```

The tone matcher will control parameters across this chain.

Conceptually:

```text
y = DSP(x, theta)
```

where:

- `x` is the player's DI guitar signal
- `theta` contains controllable DSP parameters
- `y` is the rendered output

A reference tone is converted into a target representation:

```text
z_target = Analyse(reference)
```

The rendered tone is analysed using the same representation:

```text
z_current = Analyse(DSP(x, theta))
```

The system then searches for parameters that reduce the perceptual difference:

```text
theta* = argmin Distance(z_current, z_target)
```

Later, ML models may predict a strong initial `theta` so optimisation does not have to start from scratch.

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/roadmap.md`](docs/roadmap.md)
- [`docs/decisions.md`](docs/decisions.md)

---

## Reference-tone matching

A future example could be:

```text
Reference:
Metallica - Enter Sandman-like rhythm character

Your input:
Your own guitar -> your own pickup -> your own audio interface

GuitaPaD:
Analyse target
-> analyse your DI
-> configure DSP
-> render
-> compare
-> refine
```

The important distinction is that GuitaPaD should not merely load a universal fixed preset.

The target is **adaptive matching**:

```text
target tone + your guitar -> personalised DSP parameters
```

Artist and song names can be useful descriptions of user-provided references, but GuitaPaD is not affiliated with those artists and does not distribute copyrighted reference recordings.

Users should provide reference audio they are legally entitled to use.

---

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

Install the project with GUI dependencies:

```bash
pip install -e ".[gui]"
```

Run the GUI:

```bash
python tools/gui.py
```

---

## Using another audio interface

The current backend was built and validated with an **Audient EVO 4**.

Other audio interfaces should be possible, but device selection is not yet exposed through the GUI.

First install the manufacturer's low-latency driver. On Windows, ASIO is strongly recommended.

List the devices visible to Python:

```bash
python -c "import sounddevice as sd; print(sd.query_devices()); print(sd.query_hostapis())"
```

### Device selection

The current device-selection logic lives in:

```text
src/guitapad/audio/sounddevice_backend.py
```

At present, the backend searches the available ASIO devices for an Audient device.

Until device selection is generalised, users of another interface can adapt the matching logic to the device name reported by `sounddevice`.

For example:

```python
if (
    host_api_name.upper() == "ASIO"
    and "FOCUSRITE" in device_name.upper()
):
    return device_index
```

Automatic/configurable device selection is on the roadmap.

### Channel mapping

Audio-channel configuration lives in:

```text
src/guitapad/audio/config.py
```

The current development setup uses zero-based Python channel indexes.

For example:

```python
guitar_input_index = 0
left_output_index = 0
right_output_index = 1
```

If your guitar is connected to another input, change the input index accordingly.

The configured input/output channel count must also be supported by the selected interface and driver.

### Buffer size

Current development settings:

```text
Sample rate  48,000 Hz
Target       128 samples
```

If a different interface produces dropouts or stream errors, start with a larger hardware buffer and reduce it gradually.

The GUI exposes callback timing and stream diagnostics to help test new hardware.

---

## Raw DI recording

GuitaPaD can capture the raw guitar input before the effect chain.

Current recording format:

```text
48 kHz
mono
24-bit PCM WAV
```

The real-time callback only copies samples into a preallocated RAM buffer.

File writing happens after recording stops.

This is important for tone research because the **same performance** can be rendered repeatedly through different DSP chains and parameter configurations.

---

## Tone recipes

A future tone recipe may be represented as a readable configuration rather than a proprietary preset:

```json
{
  "name": "High-gain rhythm reference",
  "input": {
    "trim_db": -4.8
  },
  "pre_eq": {
    "low_cut_hz": 78
  },
  "amp": {
    "gain": 0.63,
    "bias": 0.47
  },
  "cabinet": {
    "model": "4x12_a"
  },
  "post_eq": {
    "presence_db": 2.4
  }
}
```

Eventually, community members should be able to share:

- tone recipes
- hardware-specific adaptations
- measurements
- DSP modules
- cabinet models
- ML experiments
- reference-matching strategies

without requiring everyone to use the same guitar or audio interface.

---

## Contributing

GuitaPaD is intended to grow as an open technical project.

Useful contribution areas include:

- support for additional audio interfaces
- GUI audio-device selection
- Linux and macOS audio backends
- DSP effects
- virtual-analog circuit modelling
- amp modelling
- cabinet and microphone modelling
- anti-aliasing and oversampling
- perceptual audio features
- tone-matching loss functions
- optimisation algorithms
- ML parameter estimators
- source separation for full-mix references
- MIDI controller support
- preset / tone-recipe formats
- profiling
- hardware testing

If you test GuitaPaD with another interface, useful issue information includes:

- operating system
- interface model
- driver/backend
- sample rate
- buffer size
- measured latency
- callback load
- input/output channel mapping
- stream errors or block mismatches

---

## Development notes

The development journal is stored in:

```text
GuitaPaD_Daily_Log.md
```

Longer project notes are kept under:

```text
docs/
```

---

## Disclaimer

GuitaPaD is an independent open-source project.

Artist, band, song, amplifier, pedal, and product names may be used descriptively when discussing user-provided reference tones or compatibility. Such references do not imply endorsement or affiliation.

Copyrighted recordings are not intended to be distributed as part of the repository.

---

Built one block, one measurement, and one questionable distortion experiment at a time.
