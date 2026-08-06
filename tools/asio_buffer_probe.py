"""Measure native callback sizes delivered by the Audient ASIO driver."""

from __future__ import annotations

import os
import time
from typing import Any

os.environ.setdefault("SD_ENABLE_ASIO", "1")

import sounddevice as sd


SAMPLE_RATE = 48_000
INPUT_CHANNELS = 4
OUTPUT_CHANNELS = 4

callback_count = 0
last_frames = 0
minimum_frames = 1_000_000
maximum_frames = 0
frame_size_change_count = 0
status_message = ""

TARGET_BUFFER_SIZE = 128
TARGET_LATENCY = TARGET_BUFFER_SIZE / SAMPLE_RATE


def find_audient_asio_device() -> int:
    host_apis = sd.query_hostapis()

    for index, device in enumerate(sd.query_devices()):
        host_api_name = host_apis[device["hostapi"]]["name"]

        if (
            host_api_name.upper() == "ASIO"
            and "AUDIENT" in device["name"].upper()
        ):
            return index

    raise RuntimeError("Audient ASIO device not found.")


def callback(
    indata: Any,
    outdata: Any,
    frames: int,
    time_info: Any,
    status: sd.CallbackFlags,
) -> None:
    del indata, time_info

    global callback_count
    global last_frames
    global minimum_frames
    global maximum_frames
    global frame_size_change_count
    global status_message

    # Safety: no input signal is sent to the outputs.
    outdata.fill(0.0)

    if status:
        status_message = str(status)

    if last_frames and frames != last_frames:
        frame_size_change_count += 1

    last_frames = frames
    minimum_frames = min(minimum_frames, frames)
    maximum_frames = max(maximum_frames, frames)
    callback_count += 1


def main() -> None:
    device_index = find_audient_asio_device()
    device = sd.query_devices(device_index)

    print("GuitaPaD — Native ASIO Buffer Probe")
    print(f"Device: {device['name']}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print("Python blocksize: 0 — ASIO/PortAudio decides")
    print("No audio will be sent to the outputs.")
    print("Press Ctrl+C to stop.\n")

    try:
        with sd.Stream(
            device=device_index,
            samplerate=SAMPLE_RATE,
            blocksize=0,
            channels=(INPUT_CHANNELS, OUTPUT_CHANNELS),
            dtype="float32",
            latency=(0.0, 0.0),
            callback=callback,
        ) as stream:
            input_latency, output_latency = stream.latency

            print(f"Stream blocksize property: {stream.blocksize}")
            print(
                "Reported latency: "
                f"input={input_latency * 1000:.2f} ms, "
                f"output={output_latency * 1000:.2f} ms, "
                f"total={(input_latency + output_latency) * 1000:.2f} ms"
            )
            print()

            while True:
                time.sleep(1.0)

                print(
                    f"\rCallbacks: {callback_count:<8} "
                    f"Last frames: {last_frames:<5} "
                    f"Min: {minimum_frames:<5} "
                    f"Max: {maximum_frames:<5} "
                    f"Changes: {frame_size_change_count:<5} "
                    f"Status: {status_message or 'OK':<20}",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        print("\n\nProbe stopped.")


if __name__ == "__main__":
    main()
