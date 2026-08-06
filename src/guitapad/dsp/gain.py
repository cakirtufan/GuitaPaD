"""In-place gain processing with parameter smoothing."""

from __future__ import annotations

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect


class Gain(Effect):
    """Apply gain with a short click-free linear transition."""

    def __init__(
        self,
        linear_gain: float = 1.0,
        smoothing_time_seconds: float = 0.020,
    ) -> None:
        if smoothing_time_seconds < 0.0:
            raise ValueError(
                "Smoothing time cannot be negative."
            )

        self._target_gain = 1.0
        self._current_gain = 1.0
        self._active_target = 1.0

        self._smoothing_time_seconds = float(
            smoothing_time_seconds
        )

        self._smoothing_samples = 0
        self._samples_remaining = 0

        self._ramp_positions = np.empty(
            0,
            dtype=np.float32,
        )
        self._gain_ramp = np.empty(
            0,
            dtype=np.float32,
        )

        self.linear_gain = linear_gain
        self._current_gain = self._target_gain
        self._active_target = self._target_gain

    @property
    def linear_gain(self) -> float:
        """Return the requested target gain."""

        return self._target_gain

    @linear_gain.setter
    def linear_gain(self, value: float) -> None:
        value = float(value)

        if value < 0.0:
            raise ValueError(
                "Gain cannot be negative."
            )

        # GUI/control thread only changes this target value.
        # The audio thread performs the transition.
        self._target_gain = value

    @property
    def current_gain(self) -> float:
        """Return the gain currently reached by the smoother."""

        return self._current_gain

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        del channels

        if sample_rate <= 0.0:
            raise ValueError(
                "sample_rate must be positive."
            )

        if block_size <= 0:
            raise ValueError(
                "block_size must be positive."
            )

        self._smoothing_samples = round(
            sample_rate
            * self._smoothing_time_seconds
        )

        self._ramp_positions = np.arange(
            1,
            block_size + 1,
            dtype=np.float32,
        )

        self._gain_ramp = np.empty(
            block_size,
            dtype=np.float32,
        )

        self._current_gain = self._target_gain
        self._active_target = self._target_gain
        self._samples_remaining = 0

    def process(
        self,
        audio_block: AudioBlock,
    ) -> None:
        frames = audio_block.shape[0]

        if frames == 0:
            return

        target = self._target_gain

        # A new slider/MIDI target starts a fresh transition from the
        # gain value currently reached by the audio thread.
        if target != self._active_target:
            self._active_target = target
            self._samples_remaining = (
                self._smoothing_samples
            )

        if (
            self._samples_remaining <= 0
            or self._smoothing_samples == 0
        ):
            self._current_gain = target

            np.multiply(
                audio_block,
                target,
                out=audio_block,
            )
            return

        ramp_frames = min(
            frames,
            self._samples_remaining,
        )

        gain_step = (
            target - self._current_gain
        ) / self._samples_remaining

        np.multiply(
            self._ramp_positions[:ramp_frames],
            gain_step,
            out=self._gain_ramp[:ramp_frames],
        )

        np.add(
            self._gain_ramp[:ramp_frames],
            self._current_gain,
            out=self._gain_ramp[:ramp_frames],
        )

        np.multiply(
            audio_block[:ramp_frames],
            self._gain_ramp[
                :ramp_frames,
                np.newaxis,
            ],
            out=audio_block[:ramp_frames],
        )

        self._current_gain = float(
            self._gain_ramp[ramp_frames - 1]
        )
        self._samples_remaining -= ramp_frames

        if self._samples_remaining <= 0:
            self._current_gain = target

        # The transition can end partway through a block.
        if ramp_frames < frames:
            np.multiply(
                audio_block[ramp_frames:],
                target,
                out=audio_block[ramp_frames:],
            )

    def reset(self) -> None:
        self._current_gain = self._target_gain
        self._active_target = self._target_gain
        self._samples_remaining = 0

        if self._gain_ramp.size:
            self._gain_ramp.fill(
                self._target_gain
            )
