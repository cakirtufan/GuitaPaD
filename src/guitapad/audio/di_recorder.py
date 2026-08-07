"""Preallocated raw DI capture buffer."""

from __future__ import annotations

import numpy as np


class DiRecorder:
    """Capture mono input into a preallocated float32 buffer.

    No file I/O occurs in the audio callback.
    """

    def __init__(
        self,
        sample_rate: int,
        max_seconds: float = 12.0,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError(
                "sample_rate must be positive."
            )

        if max_seconds <= 0.0:
            raise ValueError(
                "max_seconds must be positive."
            )

        self._sample_rate = int(sample_rate)

        self._max_samples = round(
            self._sample_rate * max_seconds
        )

        self._buffer = np.empty(
            self._max_samples,
            dtype=np.float32,
        )

        self._recording = False
        self._sample_count = 0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def duration_seconds(self) -> float:
        return (
            self._sample_count
            / self._sample_rate
        )

    def start(self) -> None:
        self._sample_count = 0
        self._recording = True

    def stop(self) -> None:
        self._recording = False

    def capture(
        self,
        mono_signal: np.ndarray,
    ) -> None:
        """Copy one callback block into the preallocated buffer."""

        if not self._recording:
            return

        remaining = (
            self._max_samples
            - self._sample_count
        )

        if remaining <= 0:
            self._recording = False
            return

        count = min(
            mono_signal.shape[0],
            remaining,
        )

        start = self._sample_count
        end = start + count

        np.copyto(
            self._buffer[start:end],
            mono_signal[:count],
            casting="no",
        )

        self._sample_count = end

        if self._sample_count >= self._max_samples:
            self._recording = False

    def copy_recorded(self) -> np.ndarray:
        """Return a safe copy outside the audio callback."""

        return self._buffer[
            :self._sample_count
        ].copy()
