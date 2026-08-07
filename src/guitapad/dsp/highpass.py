"""First-order stateful high-pass filter."""

from __future__ import annotations

import math

import numpy as np

from guitapad.dsp.base import AudioBlock, Effect


class OnePoleHighPass(Effect):
    """First-order high-pass filter with click-reduced bypass.

    Filter recurrence:

        y[n] = alpha * (y[n-1] + x[n] - x[n-1])

    Bypass does not stop the filter state. The filter keeps running
    and the output crossfades between dry and filtered signals.
    """

    def __init__(
        self,
        cutoff_hz: float = 35.0,
        bypass_smoothing_time_seconds: float = 0.020,
    ) -> None:
        cutoff_hz = float(cutoff_hz)

        if cutoff_hz <= 0.0:
            raise ValueError("cutoff_hz must be positive.")

        if bypass_smoothing_time_seconds < 0.0:
            raise ValueError(
                "bypass_smoothing_time_seconds cannot be negative."
            )

        self._cutoff_hz = cutoff_hz
        self._alpha = 0.0

        self._enabled = True

        self._current_mix = 1.0
        self._active_target_mix = 1.0

        self._bypass_smoothing_time_seconds = float(
            bypass_smoothing_time_seconds
        )
        self._smoothing_samples = 0
        self._samples_remaining = 0

        self._channels = 0
        self._block_size = 0

        self._previous_input = np.empty(
            0,
            dtype=np.float32,
        )
        self._previous_output = np.empty(
            0,
            dtype=np.float32,
        )

        self._dry_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )
        self._filter_scratch = np.empty(
            (0, 0),
            dtype=np.float32,
        )

        self._alpha_powers = np.empty(
            (0, 1),
            dtype=np.float32,
        )
        self._inverse_alpha_powers = np.empty(
            (0, 1),
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
    def cutoff_hz(self) -> float:
        return self._cutoff_hz

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        # Control/GUI thread changes only the target state.
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

        if self._cutoff_hz >= sample_rate / 2.0:
            raise ValueError(
                "cutoff_hz must be below Nyquist."
            )

        dt = 1.0 / sample_rate
        rc = 1.0 / (
            2.0 * math.pi * self._cutoff_hz
        )

        self._alpha = rc / (rc + dt)

        self._channels = channels
        self._block_size = block_size

        self._smoothing_samples = round(
            sample_rate
            * self._bypass_smoothing_time_seconds
        )

        self._previous_input = np.zeros(
            channels,
            dtype=np.float32,
        )
        self._previous_output = np.zeros(
            channels,
            dtype=np.float32,
        )

        self._dry_scratch = np.empty(
            (block_size, channels),
            dtype=np.float32,
        )
        self._filter_scratch = np.empty(
            (block_size, channels),
            dtype=np.float32,
        )

        powers = np.arange(
            1,
            block_size + 1,
            dtype=np.float32,
        )

        self._alpha_powers = np.power(
            np.float32(self._alpha),
            powers,
        )[:, np.newaxis]

        self._inverse_alpha_powers = (
            1.0 / self._alpha_powers
        ).astype(
            np.float32,
            copy=False,
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

        target = 1.0 if self._enabled else 0.0
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
        filtered = self._filter_scratch[:frames]

        np.copyto(
            dry,
            audio_block,
        )

        # x[n] - x[n-1]
        np.subtract(
            dry[0],
            self._previous_input,
            out=filtered[0],
        )

        if frames > 1:
            np.subtract(
                dry[1:],
                dry[:-1],
                out=filtered[1:],
            )

        np.multiply(
            filtered,
            self._alpha,
            out=filtered,
        )

        np.multiply(
            filtered,
            self._inverse_alpha_powers[:frames],
            out=filtered,
        )

        np.cumsum(
            filtered,
            axis=0,
            out=filtered,
        )

        np.add(
            filtered,
            self._previous_output,
            out=filtered,
        )

        np.multiply(
            filtered,
            self._alpha_powers[:frames],
            out=filtered,
        )

        # Save filter state before filtered is reused for mixing.
        np.copyto(
            self._previous_input,
            dry[-1],
        )
        np.copyto(
            self._previous_output,
            filtered[-1],
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

            if target_mix >= 1.0:
                np.copyto(
                    audio_block,
                    filtered,
                )
            else:
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

        # dry + mix * (filtered - dry)
        np.subtract(
            filtered[:ramp_frames],
            dry[:ramp_frames],
            out=filtered[:ramp_frames],
        )

        np.multiply(
            filtered[:ramp_frames],
            self._mix_ramp[
                :ramp_frames,
                np.newaxis,
            ],
            out=filtered[:ramp_frames],
        )

        np.add(
            dry[:ramp_frames],
            filtered[:ramp_frames],
            out=audio_block[:ramp_frames],
        )

        self._current_mix = float(
            self._mix_ramp[ramp_frames - 1]
        )

        self._samples_remaining -= ramp_frames

        if self._samples_remaining <= 0:
            self._current_mix = target_mix

        if ramp_frames < frames:
            if target_mix >= 1.0:
                np.copyto(
                    audio_block[ramp_frames:],
                    filtered[ramp_frames:],
                )
            else:
                np.copyto(
                    audio_block[ramp_frames:],
                    dry[ramp_frames:],
                )

    def reset(self) -> None:
        if self._previous_input.size:
            self._previous_input.fill(0.0)

        if self._previous_output.size:
            self._previous_output.fill(0.0)

        target = 1.0 if self._enabled else 0.0

        self._current_mix = target
        self._active_target_mix = target
        self._samples_remaining = 0
