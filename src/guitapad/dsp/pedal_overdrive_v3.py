"""Frequency-selective pedal-style overdrive."""

from __future__ import annotations

import math

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect
from guitapad.dsp.highpass import OnePoleHighPass


class PedalOverdriveV3(Effect):
    """Frequency-selective asymmetric overdrive.

    Instead of boosting the complete guitar signal:

        driven = dry + (gain - 1) * high_pass(dry)

    Low frequencies therefore remain close to unity gain while
    mids/highs receive progressively more drive.
    """

    def __init__(
        self,
        drive_db: float = 12.0,
        level: float = 0.55,
        smoothing_time_seconds: float = 0.020,
    ) -> None:
        self._drive_db = float(drive_db)
        self._level = float(level)
        self._enabled = True

        self._positive_shape = 1.8
        self._negative_shape = 2.8

        self._positive_norm = (
            1.0 / math.tanh(self._positive_shape)
        )
        self._negative_norm = (
            1.0 / math.tanh(self._negative_shape)
        )

        self._target_gain = self._db_to_gain(
            self._drive_db
        )
        self._current_gain = self._target_gain
        self._active_gain = self._target_gain

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

        self._dry = np.empty(
            (0, 0),
            dtype=np.float32,
        )
        self._drive_band = np.empty(
            (0, 0),
            dtype=np.float32,
        )
        self._positive = np.empty(
            (0, 0),
            dtype=np.float32,
        )
        self._negative = np.empty(
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

        # Only this part receives the additional drive.
        self._drive_high_pass = OnePoleHighPass(
            cutoff_hz=700.0,
        )

        # Remove DC produced by asymmetric clipping.
        self._dc_blocker = OnePoleHighPass(
            cutoff_hz=20.0,
        )

    @staticmethod
    def _db_to_gain(value: float) -> float:
        return math.pow(
            10.0,
            value / 20.0,
        )

    @property
    def drive_db(self) -> float:
        return self._drive_db

    @drive_db.setter
    def drive_db(self, value: float) -> None:
        value = max(
            0.0,
            min(36.0, float(value)),
        )

        self._drive_db = value
        self._target_gain = self._db_to_gain(
            value
        )

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, value: float) -> None:
        self._level = max(
            0.0,
            float(value),
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
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

        self._dry = np.empty(
            shape,
            dtype=np.float32,
        )
        self._drive_band = np.empty(
            shape,
            dtype=np.float32,
        )
        self._positive = np.empty(
            shape,
            dtype=np.float32,
        )
        self._negative = np.empty(
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

        self._drive_high_pass.prepare(
            sample_rate,
            block_size,
            channels,
        )

        self._dc_blocker.prepare(
            sample_rate,
            block_size,
            channels,
        )

        self._current_gain = self._target_gain
        self._active_gain = self._target_gain
        self._drive_samples_remaining = 0

        target_mix = (
            1.0 if self._enabled else 0.0
        )

        self._current_mix = target_mix
        self._active_target_mix = target_mix
        self._bypass_samples_remaining = 0

    def _apply_frequency_selective_drive(
        self,
        audio_block: AudioBlock,
        dry: AudioBlock,
    ) -> None:
        frames = audio_block.shape[0]

        band = self._drive_band[:frames]

        np.copyto(
            band,
            dry,
        )

        self._drive_high_pass.process(
            band
        )

        target = self._target_gain

        if target != self._active_gain:
            self._active_gain = target
            self._drive_samples_remaining = (
                self._smoothing_samples
            )

        if self._drive_samples_remaining <= 0:
            self._current_gain = target

            np.multiply(
                band,
                target - 1.0,
                out=band,
            )

            np.copyto(
                audio_block,
                dry,
            )

            np.add(
                audio_block,
                band,
                out=audio_block,
            )
            return

        ramp_frames = min(
            frames,
            self._drive_samples_remaining,
        )

        step = (
            target - self._current_gain
        ) / self._drive_samples_remaining

        np.multiply(
            self._ramp_positions[:ramp_frames],
            step,
            out=self._drive_ramp[:ramp_frames],
        )

        np.add(
            self._drive_ramp[:ramp_frames],
            self._current_gain,
            out=self._drive_ramp[:ramp_frames],
        )

        self._current_gain = float(
            self._drive_ramp[ramp_frames - 1]
        )

        # Convert total gain to EXTRA high-band gain.
        np.subtract(
            self._drive_ramp[:ramp_frames],
            1.0,
            out=self._drive_ramp[:ramp_frames],
        )

        np.multiply(
            band[:ramp_frames],
            self._drive_ramp[
                :ramp_frames,
                np.newaxis,
            ],
            out=band[:ramp_frames],
        )

        if ramp_frames < frames:
            np.multiply(
                band[ramp_frames:],
                target - 1.0,
                out=band[ramp_frames:],
            )

        np.copyto(
            audio_block,
            dry,
        )

        np.add(
            audio_block,
            band,
            out=audio_block,
        )

        self._drive_samples_remaining -= (
            ramp_frames
        )

        if self._drive_samples_remaining <= 0:
            self._current_gain = target

    def _clip(
        self,
        audio_block: AudioBlock,
    ) -> None:
        frames = audio_block.shape[0]

        positive = self._positive[:frames]
        negative = self._negative[:frames]

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
                "Audio channel count changed."
            )

        dry = self._dry[:frames]

        np.copyto(
            dry,
            audio_block,
        )

        self._apply_frequency_selective_drive(
            audio_block,
            dry,
        )

        self._clip(
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

        target_mix = (
            1.0 if self._enabled else 0.0
        )

        if target_mix != self._active_target_mix:
            self._active_target_mix = target_mix
            self._bypass_samples_remaining = (
                self._smoothing_samples
            )

        if self._bypass_samples_remaining <= 0:
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
        self._drive_high_pass.reset()
        self._dc_blocker.reset()

        self._current_gain = self._target_gain
        self._active_gain = self._target_gain

        self._drive_samples_remaining = 0
        self._bypass_samples_remaining = 0

        target_mix = (
            1.0 if self._enabled else 0.0
        )

        self._current_mix = target_mix
        self._active_target_mix = target_mix
