"""Compare native and forced PortAudio callback block sizes."""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

os.environ.setdefault("SD_ENABLE_ASIO", "1")

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 48_000
INPUT_CHANNELS = 4
OUTPUT_CHANNELS = 4
GUITAR_INPUT_INDEX = 0
OUTPUT_GAIN = 0.05
OUTPUT_LIMIT = 0.80


@dataclass(slots=True)
class TestStats:
    callback_count: int = 0
    frame_sizes: Counter[int] = field(default_factory=Counter)
    maximum_callback_seconds: float = 0.0
    status_message: str = ""


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


def make_callback(stats: TestStats):
    def callback(
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        del time_info

        start = time.perf_counter()

        outdata.fill(0.0)

        if status:
            stats.status_message = str(status)

        # Input 1 → output 1
        np.multiply(
            indata[:, GUITAR_INPUT_INDEX],
            OUTPUT_GAIN,
            out=outdata[:, 0],
        )

        # Output 1 → output 2
        np.copyto(outdata[:, 1], outdata[:, 0])

        # Temporary output safety clamp
        np.clip(
            outdata[:, :2],
            -OUTPUT_LIMIT,
            OUTPUT_LIMIT,
            out=outdata[:, :2],
        )

        stats.callback_count += 1
        stats.frame_sizes[frames] += 1

        elapsed = time.perf_counter() - start

        if elapsed > stats.maximum_callback_seconds:
            stats.maximum_callback_seconds = elapsed

    return callback


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode",
        choices=("auto", "128"),
        help="'auto' uses blocksize=0; '128' forces 128-frame callbacks.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    requested_block_size = 0 if args.mode == "auto" else 128
    device_index = find_audient_asio_device()
    device = sd.query_devices(device_index)
    stats = TestStats()

    print("GuitaPaD — Block Mode Comparison")
    print(f"Mode: {args.mode}")
    print(f"Device: {device['name']}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"Requested block size: {requested_block_size}")
    print(f"Output gain: {OUTPUT_GAIN}")
    print()
    print("Keep the Audient panel at 48 kHz / 128 samples.")
    print("Turn the EVO output down and disable direct monitoring.")
    print("Press Enter to start. Press Ctrl+C to stop.")
    input()

    try:
        with sd.Stream(
            device=device_index,
            samplerate=SAMPLE_RATE,
            blocksize=requested_block_size,
            channels=(INPUT_CHANNELS, OUTPUT_CHANNELS),
            dtype="float32",
            latency="low",
            callback=make_callback(stats),
        ) as stream:
            input_latency, output_latency = stream.latency

            print("\nStream started.")
            print(f"Stream blocksize property: {stream.blocksize}")
            print(
                "Reported latency: "
                f"input={input_latency * 1_000:.2f} ms, "
                f"output={output_latency * 1_000:.2f} ms, "
                f"total={(input_latency + output_latency) * 1_000:.2f} ms"
            )

            while True:
                time.sleep(1.0)

                frame_summary = ", ".join(
                    f"{frames}:{count}"
                    for frames, count in sorted(stats.frame_sizes.items())
                )

                print(
                    f"\rCallbacks: {stats.callback_count:<8} "
                    f"Frames: {frame_summary:<24} "
                    f"Max callback: "
                    f"{stats.maximum_callback_seconds * 1_000:7.3f} ms "
                    f"Status: {stats.status_message or 'OK':<20}",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        print("\n\nTest stopped.")

    print("\n=== Final result ===")
    print(f"Mode: {args.mode}")
    print(f"Requested block size: {requested_block_size}")
    print(f"Observed callback frame sizes: {dict(stats.frame_sizes)}")
    print(
        f"Maximum callback: "
        f"{stats.maximum_callback_seconds * 1_000:.3f} ms"
    )
    print(f"Status: {stats.status_message or 'OK'}")


if __name__ == "__main__":
    main()
