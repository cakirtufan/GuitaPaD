"""Query native ASIO buffer capabilities without opening an audio stream."""

from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path

os.environ.setdefault("SD_ENABLE_ASIO", "1")

import _sounddevice_data
import sounddevice as sd


def find_audient_asio_device() -> int:
    """Return the Audient device exposed through ASIO."""

    host_apis = sd.query_hostapis()

    for device_index, device in enumerate(sd.query_devices()):
        api_name = host_apis[device["hostapi"]]["name"]

        if (
            api_name.upper() == "ASIO"
            and "AUDIENT" in device["name"].upper()
        ):
            return device_index

    raise RuntimeError("Audient ASIO device not found.")


def locate_asio_portaudio_dll() -> Path:
    """Locate the ASIO-enabled DLL bundled with sounddevice."""

    architecture = platform.architecture()[0]
    filename = f"libportaudio{architecture}-asio.dll"

    package_root = Path(next(iter(_sounddevice_data.__path__)))
    dll_path = package_root / "portaudio-binaries" / filename

    if not dll_path.exists():
        raise FileNotFoundError(
            f"ASIO PortAudio DLL was not found: {dll_path}"
        )

    return dll_path


def main() -> None:
    device_index = find_audient_asio_device()
    device = sd.query_devices(device_index)
    dll_path = locate_asio_portaudio_dll()

    portaudio = ctypes.CDLL(str(dll_path))

    get_buffer_sizes = portaudio.PaAsio_GetAvailableBufferSizes
    get_buffer_sizes.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_long),
        ctypes.POINTER(ctypes.c_long),
        ctypes.POINTER(ctypes.c_long),
        ctypes.POINTER(ctypes.c_long),
    ]
    get_buffer_sizes.restype = ctypes.c_int

    get_error_text = portaudio.Pa_GetErrorText
    get_error_text.argtypes = [ctypes.c_int]
    get_error_text.restype = ctypes.c_char_p

    minimum = ctypes.c_long()
    maximum = ctypes.c_long()
    preferred = ctypes.c_long()
    granularity = ctypes.c_long()

    error_code = get_buffer_sizes(
        device_index,
        ctypes.byref(minimum),
        ctypes.byref(maximum),
        ctypes.byref(preferred),
        ctypes.byref(granularity),
    )

    if error_code != 0:
        error_text = get_error_text(error_code)
        decoded = (
            error_text.decode("utf-8", errors="replace")
            if error_text
            else "Unknown PortAudio error"
        )

        raise RuntimeError(
            f"PaAsio_GetAvailableBufferSizes failed: "
            f"{error_code}, {decoded}"
        )

    print("GuitaPaD — ASIO Buffer Capabilities")
    print(f"Device index: {device_index}")
    print(f"Device: {device['name']}")
    print(f"PortAudio DLL: {dll_path}")
    print()
    print(f"Minimum native buffer:   {minimum.value} frames")
    print(f"Maximum native buffer:   {maximum.value} frames")
    print(f"Preferred native buffer: {preferred.value} frames")
    print(f"Buffer granularity:      {granularity.value}")
    print()
    print(
        "Default low input latency:  "
        f"{device['default_low_input_latency'] * 1000:.2f} ms"
    )
    print(
        "Default low output latency: "
        f"{device['default_low_output_latency'] * 1000:.2f} ms"
    )

    if granularity.value == -1:
        print(
            "\nGranularity -1 means legal buffer sizes "
            "are powers of two."
        )


if __name__ == "__main__":
    main()
