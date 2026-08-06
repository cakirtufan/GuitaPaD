"""Open an ASIO stream without requesting block size or latency."""

from __future__ import annotations

import os
import time
from collections import Counter
from typing import Any

os.environ.setdefault("SD_ENABLE_ASIO", "1")

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 48_000
INPUT_CHANNELS = 4
OUTPUT_CHANNELS = 4

callback_count = 0
frame_sizes: Counter[int] = Counter()
maximum_callback_seconds = 0.0
status_message = ""


TARGET_HOST_BUFFER = 128
TARGET_LATENCY_FRAMES = TARGET_HOST_BUFFER - 1
TARGET_LATENCY_SECONDS = TARGET_LATENCY_FRAMES / SAMPLE_RATE


def find_audient_asio_device() -> int:
    host_apis = sd.query_hostapis()

    for index, device in enumerate(sd.query_devices()):
        api_name = host_apis[device["hostapi"]]["name"]

        if (
            api_name.upper() == "ASIO"
            and "AUDIENT" in device["name"].upper()
        ):
            return index

    raise RuntimeError("Audient ASIO device not found.")


def callback(
    indata: np.ndarray,
    outdata: np.ndarray,
    frames: int,
    time_info: Any,
    status: sd.CallbackFlags,
) -> None:
    del indata, time_info

    global callback_count
    global maximum_callback_seconds
    global status_message

    start = time.perf_counter()

    outdata.fill(0.0)

    if status:
        status_message = str(status)

    callback_count += 1
    frame_sizes[frames] += 1

    elapsed = time.perf_counter() - start

    if elapsed > maximum_callback_seconds:
        maximum_callback_seconds = elapsed


def main() -> None:
    # Remove any Python-side blocksize/latency defaults.

    device_index = find_audient_asio_device()
    device = sd.query_devices(device_index)

    print("GuitaPaD — Untouched ASIO Stream Probe")
    print(f"Device: {device['name']}")
    print(f"Sample rate: {SAMPLE_RATE}")
    print(f"sounddevice default blocksize: {sd.default.blocksize}")
    print(f"sounddevice default latency: {sd.default.latency}")
    print()
    print("No blocksize or latency argument will be sent.")
    print("No audio will be sent to the outputs.")
    print("Press Enter to start. Press Ctrl+C to stop.")
    input()

    try:
        with sd.Stream(
            device=device_index,
            samplerate=SAMPLE_RATE,
            blocksize=0,
            channels=(INPUT_CHANNELS, OUTPUT_CHANNELS),
            dtype="float32",
            latency=(
                TARGET_LATENCY_SECONDS,
                TARGET_LATENCY_SECONDS,
            ),
            callback=callback,
        ) as stream:
            input_latency, output_latency = stream.latency

            print("\nStream started.")
            print(f"Stream blocksize property: {stream.blocksize}")
            print(
                "Reported latency: "
                f"input={input_latency * 1000:.2f} ms, "
                f"output={output_latency * 1000:.2f} ms, "
                f"total={(input_latency + output_latency) * 1000:.2f} ms"
            )

            while True:
                time.sleep(1.0)

                frames_text = ", ".join(
                    f"{size}:{count}"
                    for size, count in sorted(frame_sizes.items())
                )

                print(
                    f"\rCallbacks: {callback_count:<8} "
                    f"Frames: {frames_text:<24} "
                    f"Max callback: "
                    f"{maximum_callback_seconds * 1000:7.3f} ms "
                    f"Status: {status_message or 'OK':<20}",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        print("\n\nProbe stopped.")


if __name__ == "__main__":
    main()
