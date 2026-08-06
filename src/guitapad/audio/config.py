"""Audio stream configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Immutable configuration shared by the audio backend and engine."""

    sample_rate: int = 48_000
    block_size: int = 128

    input_channels: int = 4
    output_channels: int = 4

    guitar_input_index: int = 0
    left_output_index: int = 0
    right_output_index: int = 1

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")

        if self.block_size <= 0:
            raise ValueError("block_size must be positive.")

        if not 0 <= self.guitar_input_index < self.input_channels:
            raise ValueError("Invalid guitar input channel index.")

        for output_index in (
            self.left_output_index,
            self.right_output_index,
        ):
            if not 0 <= output_index < self.output_channels:
                raise ValueError("Invalid output channel index.")

    @property
    def block_deadline_seconds(self) -> float:
        """Maximum processing time available for one audio block."""

        return self.block_size / self.sample_rate
