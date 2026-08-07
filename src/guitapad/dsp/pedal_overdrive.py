"""Pedal-style asymmetric overdrive."""

from __future__ import annotations

import math

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect
from guitapad.dsp.highpass import OnePoleHighPass


class PedalOverdriveV2(Effect):
    """Asymmetric soft-clipping pedal-style overdrive.

    Wet path:

        Drive
        -> asymmetric clipping
        -> DC blocker
        -> Level

    Positive and negative half-cycles saturate differently,
    generating both even and odd harmonics.
    """

    def __init__(
        self,
        drive_db: float = 12.0,
        level: float = 0.55,
        smoothing_time_seconds: float = 0.020,
    ) -> None:
        if smoothing_time_seconds < 0.0:
            raise ValueError(
                "smoothing_time_seconds cannot be negative."
            )

        if level < 0.0:
            raise ValueError(
                "level cannot be negative."
            )

        self._drive_db = float(drive_db)
        self._level = float(level)

        self._positive_shape = 1.8
        self._negative_shape = 2.8

        self._positive_norm = (
            1.0 / math.tanh(self._positive_shape)
        )
        self._negative_norm = (
            1.0 / math.tanh(self._negative_shape)
        )

        self._target_pre_gain = self._db_to_gain(
            self._drive_db
        )
        self._current_pre_gain = (
            self._target_pre_gain
        )
        self._active_pre_gain = (
            self._target_pre_gain
        )

        self._enabled = True

        self._current_mix = 1.0
        self._active_target_mix = 1.0

        self._smoothing_time_seconds = float(
            smoothing_time_seconds
        )

        self._smoothing_samples = 0
        self._drive_samples_remaining = 0
        self._bypass_samples_remaining = 0

        self._block_size = 0
        self._channels = 0

        self._dry_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )

        self._positive_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )

        self._negative_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )

        self._ramp_positions = np.empty(
            0,
            dtype=np.float32,
        )

        self._drive_ramp = np.empty(
            0,
            dtype=np.float32,
        )

        self._mix_ramp = np.empty(
            0,
            dtype=np.float32,
        )

        # Asymmetric clipping creates a small DC component.
        self._dc_blocker = OnePoleHighPass(
            cutoff_hz=20.0,
        )

    @staticmethod
    def _db_to_gain(
        value: float,
    ) -> float:
        return math.pow(
            10.0,
            value / 20.0,
        )

    @property
    def drive_db(self) -> float:
        return self._drive_db

    @drive_db.setter
    def drive_db(
        self,
        value: float,
    ) -> None:
        value = max(
            0.0,
            min(36.0, float(value)),
        )

        self._drive_db = value
        self._target_pre_gain = self._db_to_gain(
            value
        )

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(
        self,
        value: float,
    ) -> None:
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
    def enabled(
        self,
        value: bool,
    ) -> None:
        self._enabled = bool(value)

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
            * self._smoothing_time_seconds
        )

        shape = (
            block_size,
            channels,
        )

        self._dry_scratch = np.empty(
            shape,
            dtype=np.float32,
        )

        self._positive_scratch = np.empty(
            shape,
            dtype=np.float32,
        )

        self._negative_scratch = np.empty(
            shape,
            dtype=np.float32,
        )

        self._ramp_positions = np.arange(
            1,
            block_size + 1,
            dtype=np.float32,
        )

        self._drive_ramp = np.empty(
            block_size,
            dtype=np.float32,
        )

        self._mix_ramp = np.empty(
            block_size,
            dtype=np.float32,
        )

        self._dc_blocker.prepare(
            sample_rate=sample_rate,
            block_size=block_size,
            channels=channels,
        )

        self._current_pre_gain = (
            self._target_pre_gain
        )
        self._active_pre_gain = (
            self._target_pre_gain
        )
        self._drive_samples_remaining = 0

        target_mix = (
            1.0
            if self._enabled
            else 0.0
        )

        self._current_mix = target_mix
        self._active_target_mix = target_mix
        self._bypass_samples_remaining = 0

    def _apply_drive(
        self,
        audio_block: AudioBlock,
    ) -> None:
        frames = audio_block.shape[0]
        target = self._target_pre_gain

        if target != self._active_pre_gain:
            self._active_pre_gain = target
            self._drive_samples_remaining = (
                self._smoothing_samples
            )

        if (
            self._drive_samples_remaining <= 0
            or self._smoothing_samples == 0
        ):
            self._current_pre_gain = target

            np.multiply(
                audio_block,
                target,
                out=audio_block,
            )
            return

        ramp_frames = min(
            frames,
            self._drive_samples_remaining,
        )

        step = (
            target - self._current_pre_gain
        ) / self._drive_samples_remaining

        np.multiply(
            self._ramp_positions[:ramp_frames],
            step,
            out=self._drive_ramp[:ramp_frames],
        )

        np.add(
            self._drive_ramp[:ramp_frames],
            self._current_pre_gain,
            out=self._drive_ramp[:ramp_frames],
        )

        np.multiply(
            audio_block[:ramp_frames],
            self._drive_ramp[
                :ramp_frames,
                np.newaxis,
            ],
            out=audio_block[:ramp_frames],
        )

        self._current_pre_gain = float(
            self._drive_ramp[ramp_frames - 1]
        )

        self._drive_samples_remaining -= (
            ramp_frames
        )

        if self._drive_samples_remaining <= 0:
            self._current_pre_gain = target

        if ramp_frames < frames:
            np.multiply(
                audio_block[ramp_frames:],
                target,
                out=audio_block[ramp_frames:],
            )

    def _apply_asymmetric_clip(
        self,
        audio_block: AudioBlock,
    ) -> None:
        frames = audio_block.shape[0]

        positive = self._positive_scratch[:frames]
        negative = self._negative_scratch[:frames]

        # Positive half-cycle.
        np.maximum(
            audio_block,
            0.0,
            out=positive,
        )

        np.multiply(
            positive,
            self._positive_shape,
            out=positive,
        )

        np.tanh(
            positive,
            out=positive,
        )

        np.multiply(
            positive,
            self._positive_norm,
            out=positive,
        )

        # Negative half-cycle.
        np.minimum(
            audio_block,
            0.0,
            out=negative,
        )

        np.multiply(
            negative,
            self._negative_shape,
            out=negative,
        )

        np.tanh(
            negative,
            out=negative,
        )

        np.multiply(
            negative,
            self._negative_norm,
            out=negative,
        )

        np.add(
            positive,
            negative,
            out=audio_block,
        )

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

        # Wet path.
        self._apply_drive(
            audio_block
        )

        self._apply_asymmetric_clip(
            audio_block
        )

        self._dc_blocker.process(
            audio_block
        )

        np.multiply(
            audio_block,
            self._level,
            out=audio_block,
        )

        # Smooth wet/dry bypass.
        target_mix = (
            1.0
            if self._enabled
            else 0.0
        )

        if target_mix != self._active_target_mix:
            self._active_target_mix = target_mix
            self._bypass_samples_remaining = (
                self._smoothing_samples
            )

        if (
            self._bypass_samples_remaining <= 0
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
            self._bypass_samples_remaining,
        )

        step = (
            target_mix - self._current_mix
        ) / self._bypass_samples_remaining

        np.multiply(
            self._ramp_positions[:ramp_frames],
            step,
            out=self._mix_ramp[:ramp_frames],
        )

        np.add(
            self._mix_ramp[:ramp_frames],
            self._current_mix,
            out=self._mix_ramp[:ramp_frames],
        )

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

        self._bypass_samples_remaining -= (
            ramp_frames
        )

        if self._bypass_samples_remaining <= 0:
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
        self._dc_blocker.reset()

        self._current_pre_gain = (
            self._target_pre_gain
        )
        self._active_pre_gain = (
            self._target_pre_gain
        )
        self._drive_samples_remaining = 0

        target_mix = (
            1.0
            if self._enabled
            else 0.0
        )

        self._current_mix = target_mix
        self._active_target_mix = target_mix
        self._bypass_samples_remaining = 0

        if self._dry_scratch.size:
            self._dry_scratch.fill(0.0)

        if self._positive_scratch.size:
            self._positive_scratch.fill(0.0)

        if self._negative_scratch.size:
            self._negative_scratch.fill(0.0)
