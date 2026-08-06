"""GuitaPaD command-line passthrough application."""

import time

from guitapad.audio.config import AudioConfig
from guitapad.audio.engine import AudioEngine
from guitapad.audio.sounddevice_backend import SoundDeviceBackend
from guitapad.dsp.chain import EffectChain
from guitapad.dsp.gain import Gain
from guitapad.dsp.limiter import HardLimiter


def choose_output_profile() -> tuple[str, float]:
    """Choose a safe initial gain for the physical listening setup."""

    print("Select listening profile:")
    print("1 — Headphones")
    print("2 — Left/right monitor outputs")

    while True:
        selection = input("\nSelection [1/2]: ").strip()

        if selection == "1":
            return "Headphones", 0.60

        if selection == "2":
            return "Left/right monitors", 0.60

        print("Enter either 1 or 2.")


def main() -> None:
    profile_name, initial_gain = choose_output_profile()

    config = AudioConfig(
        sample_rate=48_000,
        block_size=128,
    )

    effect_chain = EffectChain(
        [
            Gain(linear_gain=initial_gain),
            HardLimiter(limit=0.80),
        ]
    )

    engine = AudioEngine(
        config=config,
        effect_chain=effect_chain,
    )

    backend = SoundDeviceBackend(
        config=config,
        engine=engine,
    )

    print("\nGuitaPaD — Modular Passthrough")
    print(f"Listening profile: {profile_name}")
    print(f"Initial linear gain: {initial_gain:.2f}")
    print("ASIO input 1 → outputs 1 and 2")
    print()
    print("Turn the EVO output down and disable direct monitoring.")
    print("Press Enter to start. Press Ctrl+C to stop.")
    input()

    try:
        backend.start()

        info = backend.stream_info

        print("\nAudio stream started.")
        print(f"Device: {info.device_name}")
        print(
            f"Block size: requested={info.requested_block_size}, "
            f"actual={info.actual_block_size}"
        )
        print(
            f"Reported latency: "
            f"input={info.input_latency_seconds * 1_000:.2f} ms, "
            f"output={info.output_latency_seconds * 1_000:.2f} ms, "
            f"total="
            f"{(
                info.input_latency_seconds
                + info.output_latency_seconds
            ) * 1_000:.2f} ms"
        )

        while True:
            time.sleep(1.0)

            metrics = engine.metrics
            deadline = config.block_deadline_seconds
            callback_load = (
                metrics.maximum_callback_seconds
                / deadline
                * 100.0
            )

            status_text = (
                metrics.stream_status_message
                or "OK"
            )

            if metrics.callback_error_count:
                status_text = (
                    f"ERROR: {metrics.last_callback_error}"
                )

            print(
                f"\rCallbacks: {metrics.callback_count:<10} "
                f"Max callback: "
                f"{metrics.maximum_callback_seconds * 1_000:7.3f} ms "
                f"({callback_load:6.1f}% of deadline) "
                f"Status: {status_text:<30}",
                end="",
                flush=True,
            )

    except KeyboardInterrupt:
        print("\n\nStopping GuitaPaD.")

    finally:
        backend.stop()


if __name__ == "__main__":
    main()
