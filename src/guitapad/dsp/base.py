"""Base interface for all GuitaPaD effects."""

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


AudioBlock = NDArray[np.float32]


class Effect(ABC):
    """JUCE-like lifecycle shared by every DSP module."""

    @abstractmethod
    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        """Prepare internal state before real-time processing begins."""

    @abstractmethod
    def process(self, audio_block: AudioBlock) -> None:
        """Process an audio block in place."""

    @abstractmethod
    def reset(self) -> None:
        """Clear all state accumulated by the effect."""
