"""Display real-time input levels from the Audient EVO ASIO device.

This diagnostic tool reads all EVO ASIO input channels but sends no audio
to the outputs. It is used to identify the physical guitar input channel.
"""

from __future__ import annotations

import math
import os
import time
from typing import Any

# Must be set before importing sounddevice.
os.environ.setdefault("SD_ENABLE_ASIO", "1")

import sounddevice as sd


SAMPLE_RATE = 48_000
BLOCK_SIZE = 256
INPUT_CHANNELS = 4
DISPLAY_INTERVAL_SECONDS = 0.10
DB_FLOOR = -90.0
BAR_WIDTH = 40


# These values are updated by the audio callback and read by the main thread.
# A production meter will later use a more formal thread-safe state layer.
latest_peaks = [0.0] * INPUT_CHANNELS
latest_rms = [0.0] * INPUT_CHANNELS
latest_status = ""


def find_audient_asio_device() -> int:
    """Return the device index of the Audient ASIO driver."""

    host_apis = sd.query_hostapis()

    for device_index, device in enumerate(sd.query_devices()):
        host_api_name = host_apis[device["hostapi"]]["name"]
        device_name = device["name"]

        if (
            host_api_name.upper() == "ASIO"
            and "AUDIENT" in device_name.upper()
        ):
            return device_index

    raise RuntimeError(
        "Audient ASIO device not found. "
        "Check the EVO 4 connection and Audient driver."
    )


def amplitude_to_dbfs(amplitude: float) -> float:
    """Convert a linear float amplitude to dBFS."""

    if amplitude <= 0.0:
        return DB_FLOOR

    return max(DB_FLOOR, 20.0 * math.log10(amplitude))


def make_bar(dbfs: float) -> str:
    """Create a text level bar between DB_FLOOR and 0 dBFS."""

    normalized = (dbfs - DB_FLOOR) / abs(DB_FLOOR)
    normalized = max(0.0, min(1.0, normalized))

    filled = round(normalized * BAR_WIDTH)
    return "#" * filled + "-" * (BAR_WIDTH - filled)


def audio_callback(
    indata: Any,
    frames: int,
    time_info: Any,
    status: sd.CallbackFlags,
) -> None:
    """Measure peak and RMS values without printing from the audio thread."""

    del time_info

    global latest_status

    if status:
        latest_status = str(status)

    # RawInputStream supplies interleaved float32 samples:
    # frame 0: CH1, CH2, CH3, CH4
    # frame 1: CH1, CH2, CH3, CH4
    samples = memoryview(indata).cast("f")

    peaks = [0.0] * INPUT_CHANNELS
    squared_sums = [0.0] * INPUT_CHANNELS

    for frame_index in range(frames):
        frame_offset = frame_index * INPUT_CHANNELS

        for channel in range(INPUT_CHANNELS):
            sample = float(samples[frame_offset + channel])
            absolute_sample = abs(sample)

            if absolute_sample > peaks[channel]:
                peaks[channel] = absolute_sample

            squared_sums[channel] += sample * sample

    for channel in range(INPUT_CHANNELS):
        latest_peaks[channel] = peaks[channel]
        latest_rms[channel] = math.sqrt(squared_sums[channel] / frames)


def draw_meter(device_name: str) -> None:
    """Render the latest meter values in the terminal."""

    # Move cursor to the top-left without clearing the scrollback.
    print("\x1b[H", end="")

    print("GuitaPaD — EVO 4 Input Meter")
    print(f"Device: {device_name}")
    print(
        f"Sample rate: {SAMPLE_RATE} Hz | "
        f"Block size: {BLOCK_SIZE} | "
        f"Input channels: {INPUT_CHANNELS}"
    )
    print("Play the guitar, then observe which channel responds.")
    print("Press Ctrl+C to stop.\n")

    for channel in range(INPUT_CHANNELS):
        peak_db = amplitude_to_dbfs(latest_peaks[channel])
        rms_db = amplitude_to_dbfs(latest_rms[channel])
        bar = make_bar(peak_db)

        clip_warning = " CLIP!" if latest_peaks[channel] >= 0.99 else ""

        print(
            f"CH {channel + 1} "
            f"|{bar}| "
            f"Peak {peak_db:6.1f} dBFS "
            f"RMS {rms_db:6.1f} dBFS"
            f"{clip_warning}       "
        )

    print()
    if latest_status:
        print(f"Stream status: {latest_status}                 ")
    else:
        print("Stream status: OK                              ")


def main() -> None:
    device_index = find_audient_asio_device()
    device = sd.query_devices(device_index)

    sd.check_input_settings(
        device=device_index,
        channels=INPUT_CHANNELS,
        dtype="float32",
        samplerate=SAMPLE_RATE,
    )

    print("\x1b[2J\x1b[H", end="")

    try:
        with sd.RawInputStream(
            device=device_index,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=INPUT_CHANNELS,
            dtype="float32",
            latency="low",
            callback=audio_callback,
        ):
            while True:
                draw_meter(device["name"])
                time.sleep(DISPLAY_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nInput meter stopped.")

    except sd.PortAudioError as error:
        raise RuntimeError(
            "Could not open the Audient ASIO input stream. "
            "Close other applications using the ASIO driver and try again."
        ) from error


if __name__ == "__main__":
    main()
