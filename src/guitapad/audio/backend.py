"""Abstract audio backend contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StreamInfo:
    device_name: str
    requested_block_size: int
    actual_block_size: int
    input_latency_seconds: float
    output_latency_seconds: float


class AudioBackend(ABC):
    """Interface implemented by the current sounddevice backend."""

    @abstractmethod
    def start(self) -> None:
        """Open and start the audio stream."""

    @abstractmethod
    def stop(self) -> None:
        """Stop and close the audio stream."""

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return whether the stream is active."""

    @property
    @abstractmethod
    def stream_info(self) -> StreamInfo:
        """Return information reported by the active stream."""
