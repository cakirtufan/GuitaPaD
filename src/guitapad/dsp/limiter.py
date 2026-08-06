"""Temporary output safety limiter."""

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect


class HardLimiter(Effect):
    """Clamp samples to a fixed safety range.

    This is not intended to be the final musical limiter. It exists only
    to prevent unexpectedly large output values during early development.
    """

    def __init__(self, limit: float = 0.80) -> None:
        limit = float(limit)

        if not 0.0 < limit <= 1.0:
            raise ValueError("Limiter threshold must be between 0 and 1.")

        self._limit = limit

    @property
    def limit(self) -> float:
        return self._limit

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        del sample_rate, block_size, channels

    def process(self, audio_block: AudioBlock) -> None:
        np.clip(
            audio_block,
            -self._limit,
            self._limit,
            out=audio_block,
        )

    def reset(self) -> None:
        pass
