"""Simple nonlinear soft-clipping overdrive."""

from __future__ import annotations

import math

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect


class SoftClipOverdrive(Effect):
    """Symmetric tanh soft clipping with click-reduced bypass."""

    def __init__(
        self,
        drive_db: float = 12.0,
        level: float = 0.60,
        bypass_smoothing_time_seconds: float = 0.020,
    ) -> None:
        self._drive_db = float(drive_db)
        self._level = float(level)

        if self._level < 0.0:
            raise ValueError(
                "level cannot be negative."
            )

        if bypass_smoothing_time_seconds < 0.0:
            raise ValueError(
                "bypass_smoothing_time_seconds cannot be negative."
            )

        self._pre_gain = 1.0
        self._update_pre_gain()

        self._enabled = True

        self._current_mix = 1.0
        self._active_target_mix = 1.0

        self._bypass_smoothing_time_seconds = float(
            bypass_smoothing_time_seconds
        )

        self._smoothing_samples = 0
        self._samples_remaining = 0
        self._block_size = 0
        self._channels = 0

        self._dry_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )

        self._ramp_positions = np.empty(
            0,
            dtype=np.float32,
        )

        self._mix_ramp = np.empty(
            0,
            dtype=np.float32,
        )

    @property
    def drive_db(self) -> float:
        return self._drive_db

    @drive_db.setter
    def drive_db(self, value: float) -> None:
        self._drive_db = float(value)
        self._update_pre_gain()

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, value: float) -> None:
        value = float(value)

        if value < 0.0:
            raise ValueError(
                "level cannot be negative."
            )

        self._level = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def _update_pre_gain(self) -> None:
        self._pre_gain = math.pow(
            10.0,
            self._drive_db / 20.0,
        )

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        if sample_rate <= 0.0:
            raise ValueError(
                "sample_rate must be positive."
            )

        if block_size <= 0:
            raise ValueError(
                "block_size must be positive."
            )

        if channels <= 0:
            raise ValueError(
                "channels must be positive."
            )

        self._block_size = block_size
        self._channels = channels

        self._smoothing_samples = round(
            sample_rate
            * self._bypass_smoothing_time_seconds
        )

        self._dry_scratch = np.empty(
            (block_size, channels),
            dtype=np.float32,
        )

        self._ramp_positions = np.arange(
            1,
            block_size + 1,
            dtype=np.float32,
        )

        self._mix_ramp = np.empty(
            block_size,
            dtype=np.float32,
        )

        target = (
            1.0
            if self._enabled
            else 0.0
        )

        self._current_mix = target
        self._active_target_mix = target
        self._samples_remaining = 0

    def process(
        self,
        audio_block: AudioBlock,
    ) -> None:
        frames, channels = audio_block.shape

        if frames == 0:
            return

        if channels != self._channels:
            raise RuntimeError(
                "Audio channel count changed after prepare()."
            )

        if frames > self._block_size:
            raise RuntimeError(
                "Audio block is larger than prepared block size."
            )

        dry = self._dry_scratch[:frames]

        np.copyto(
            dry,
            audio_block,
        )

        # Wet path:
        # input -> pre-gain -> tanh -> output level
        np.multiply(
            audio_block,
            self._pre_gain,
            out=audio_block,
        )

        np.tanh(
            audio_block,
            out=audio_block,
        )

        np.multiply(
            audio_block,
            self._level,
            out=audio_block,
        )

        target_mix = (
            1.0
            if self._enabled
            else 0.0
        )

        if target_mix != self._active_target_mix:
            self._active_target_mix = target_mix
            self._samples_remaining = (
                self._smoothing_samples
            )

        if (
            self._samples_remaining <= 0
            or self._smoothing_samples == 0
        ):
            self._current_mix = target_mix

            if target_mix <= 0.0:
                np.copyto(
                    audio_block,
                    dry,
                )

            return

        ramp_frames = min(
            frames,
            self._samples_remaining,
        )

        mix_step = (
            target_mix - self._current_mix
        ) / self._samples_remaining

        np.multiply(
            self._ramp_positions[:ramp_frames],
            mix_step,
            out=self._mix_ramp[:ramp_frames],
        )

        np.add(
            self._mix_ramp[:ramp_frames],
            self._current_mix,
            out=self._mix_ramp[:ramp_frames],
        )

        # dry + mix * (wet - dry)
        np.subtract(
            audio_block[:ramp_frames],
            dry[:ramp_frames],
            out=audio_block[:ramp_frames],
        )

        np.multiply(
            audio_block[:ramp_frames],
            self._mix_ramp[
                :ramp_frames,
                np.newaxis,
            ],
            out=audio_block[:ramp_frames],
        )

        np.add(
            audio_block[:ramp_frames],
            dry[:ramp_frames],
            out=audio_block[:ramp_frames],
        )

        self._current_mix = float(
            self._mix_ramp[ramp_frames - 1]
        )

        self._samples_remaining -= ramp_frames

        if self._samples_remaining <= 0:
            self._current_mix = target_mix

        if (
            ramp_frames < frames
            and target_mix <= 0.0
        ):
            np.copyto(
                audio_block[ramp_frames:],
                dry[ramp_frames:],
            )

    def reset(self) -> None:
        target = (
            1.0
            if self._enabled
            else 0.0
        )

        self._current_mix = target
        self._active_target_mix = target
        self._samples_remaining = 0

        if self._dry_scratch.size:
            self._dry_scratch.fill(0.0)
