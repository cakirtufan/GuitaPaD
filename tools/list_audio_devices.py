"""List available audio host APIs and devices."""

import os

# Must be set before importing sounddevice.
os.environ.setdefault("SD_ENABLE_ASIO", "1")

import sounddevice as sd


def main() -> None:
    host_apis = sd.query_hostapis()
    devices = sd.query_devices()

    print("=== PortAudio ===")
    print(sd.get_portaudio_version())

    print("\n=== Host APIs ===")
    for api_index, api in enumerate(host_apis):
        print(
            f"[{api_index}] {api['name']} | "
            f"devices={len(api['devices'])} | "
            f"default_input={api['default_input_device']} | "
            f"default_output={api['default_output_device']}"
        )

    print("\n=== Audio Devices ===")
    for device_index, device in enumerate(devices):
        api_name = host_apis[device["hostapi"]]["name"]

        print(
            f"\n[{device_index}] {device['name']}\n"
            f"    Host API: {api_name}\n"
            f"    Inputs: {device['max_input_channels']}\n"
            f"    Outputs: {device['max_output_channels']}\n"
            f"    Default sample rate: {device['default_samplerate']}\n"
            f"    Low input latency: {device['default_low_input_latency']:.6f} s\n"
            f"    Low output latency: {device['default_low_output_latency']:.6f} s"
        )


if __name__ == "__main__":
    main()
