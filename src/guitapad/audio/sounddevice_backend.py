"""PortAudio/sounddevice implementation of the audio backend."""

from __future__ import annotations

import os

# Must be set before importing sounddevice.
os.environ.setdefault("SD_ENABLE_ASIO", "1")

import sounddevice as sd

from guitapad.audio.backend import AudioBackend, StreamInfo
from guitapad.audio.config import AudioConfig
from guitapad.audio.engine import AudioEngine


class SoundDeviceBackend(AudioBackend):
    """Run AudioEngine through the Audient ASIO driver."""

    def __init__(
        self,
        config: AudioConfig,
        engine: AudioEngine,
    ) -> None:
        self.config = config
        self.engine = engine

        self._device_index = self._find_audient_asio_device()
        self._device = sd.query_devices(self._device_index)
        self._stream: sd.Stream | None = None

        self._validate_settings()

    @staticmethod
    def _find_audient_asio_device() -> int:
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
            "Check the EVO 4 connection and driver."
        )

    def _validate_settings(self) -> None:
        sd.check_input_settings(
            device=self._device_index,
            channels=self.config.input_channels,
            dtype="float32",
            samplerate=self.config.sample_rate,
        )

        sd.check_output_settings(
            device=self._device_index,
            channels=self.config.output_channels,
            dtype="float32",
            samplerate=self.config.sample_rate,
        )

    def start(self) -> None:
        if self._stream is not None:
            return

        target_latency_seconds = (
            self.config.block_size - 1
        ) / self.config.sample_rate

        self._stream = sd.Stream(
            device=self._device_index,
            samplerate=self.config.sample_rate,

            # Do not force PortAudio callback adaptation.
            blocksize=0,

            channels=(
                self.config.input_channels,
                self.config.output_channels,
            ),
            dtype="float32",

            # Request just below the desired native ASIO buffer.
            latency=(
                target_latency_seconds,
                target_latency_seconds,
            ),

            callback=self.engine.audio_callback,
        )

        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return

        self._stream.stop()
        self._stream.close()
        self._stream = None
        self.engine.reset()

    @property
    def is_running(self) -> bool:
        return bool(
            self._stream is not None
            and self._stream.active
        )

    @property
    def stream_info(self) -> StreamInfo:
        if self._stream is None:
            raise RuntimeError("Audio stream has not been started.")

        input_latency, output_latency = self._stream.latency

        return StreamInfo(
            device_name=str(self._device["name"]),
            requested_block_size=self.config.block_size,
            actual_block_size=self._stream.blocksize,
            input_latency_seconds=float(input_latency),
            output_latency_seconds=float(output_latency),
        )
