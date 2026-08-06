# Technical Decisions

## Audio device

- Interface: Audient EVO 4
- Driver: Audient USB Audio ASIO Driver
- PortAudio device index during initial setup: 26
- Sample rate target: 48 kHz
- Initial block size: 256 samples
- ASIO input channels: 4
- ASIO output channels: 4

## Input channel mapping

Tested with `tools/input_meter.py`.

- EVO 4 Instrument Input 1 corresponds to ASIO input channel 1.
- Python uses zero-based indexing, so the guitar signal is read from channel index 0.
- The remaining ASIO input channels did not respond during the guitar test.

## Initial validation

- Python version: 3.13.2
- sounddevice version: 0.5.5
- PortAudio: V19.7.0-devel
- ASIO host API detected successfully.
- 48 kHz mono input and stereo output configuration validated.
