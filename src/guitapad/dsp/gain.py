"""In-place gain processing."""

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect


class Gain(Effect):
    """Multiply every sample by a linear gain value."""

    def __init__(self, linear_gain: float = 1.0) -> None:
        self._linear_gain = 1.0
        self.linear_gain = linear_gain

    @property
    def linear_gain(self) -> float:
        return self._linear_gain

    @linear_gain.setter
    def linear_gain(self, value: float) -> None:
        value = float(value)

        if value < 0.0:
            raise ValueError("Gain cannot be negative.")

        self._linear_gain = value

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        del sample_rate, block_size, channels

    def process(self, audio_block: AudioBlock) -> None:
        np.multiply(
            audio_block,
            self._linear_gain,
            out=audio_block,
        )

    def reset(self) -> None:
        pass
