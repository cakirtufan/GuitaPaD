"""Real-time audio engine independent of the audio-device backend."""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from guitapad.audio.config import AudioConfig
from guitapad.audio.metrics import CallbackMetrics
from guitapad.dsp.chain import EffectChain


class AudioEngine:
    """Route the guitar input through an in-place DSP chain."""

    def __init__(
        self,
        config: AudioConfig,
        effect_chain: EffectChain,
    ) -> None:
        self.config = config
        self.effect_chain = effect_chain
        self.metrics = CallbackMetrics()

        # Allocated once before the audio stream begins.
        self._mono_buffer = np.zeros(
            (config.block_size, 1),
            dtype=np.float32,
        )

        # Reused for absolute-value peak calculations.
        self._meter_scratch = np.empty(
            config.block_size,
            dtype=np.float32,
        )

        # Approximately 300 ms meter release time.
        self._meter_decay = math.exp(
            -config.block_size
            / (config.sample_rate * 0.30)
        )

        self.effect_chain.prepare(
            sample_rate=config.sample_rate,
            block_size=config.block_size,
            channels=1,
        )

    def audio_callback(
        self,
        indata: np.ndarray,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: Any,
    ) -> None:
        """PortAudio callback: no printing, files or GUI work."""

        del time_info

        callback_start = time.perf_counter()

        try:
            if status:
                self.metrics.stream_status_message = str(status)

            outdata.fill(0.0)

            if frames != self.config.block_size:
                self.metrics.block_size_mismatch_count += 1
                return

            np.copyto(
                self._mono_buffer[:, 0],
                indata[:, self.config.guitar_input_index],
                casting="no",
            )

            mono_signal = self._mono_buffer[:, 0]

            # Input meter: before processing.
            np.abs(
                mono_signal,
                out=self._meter_scratch,
            )
            input_peak = float(
                np.max(self._meter_scratch)
            )

            if input_peak >= 0.999:
                self.metrics.input_clip_detected = True

            self.metrics.input_peak_linear = max(
                input_peak,
                self.metrics.input_peak_linear
                * self._meter_decay,
            )

            self.effect_chain.process(
                self._mono_buffer
            )

            # Output meter: after gain and limiter.
            np.abs(
                mono_signal,
                out=self._meter_scratch,
            )
            output_peak = float(
                np.max(self._meter_scratch)
            )

            self.metrics.output_peak_linear = max(
                output_peak,
                self.metrics.output_peak_linear
                * self._meter_decay,
            )

            outdata[
                :,
                self.config.left_output_index,
            ] = mono_signal

            outdata[
                :,
                self.config.right_output_index,
            ] = mono_signal

        except Exception as error:
            outdata.fill(0.0)

            self.metrics.callback_error_count += 1
            self.metrics.last_callback_error = repr(error)

        finally:
            elapsed = (
                time.perf_counter()
                - callback_start
            )

            self.metrics.callback_count += 1

            if elapsed > self.metrics.maximum_callback_seconds:
                self.metrics.maximum_callback_seconds = elapsed

    def reset(self) -> None:
        self._mono_buffer.fill(0.0)
        self._meter_scratch.fill(0.0)

        self.metrics.input_peak_linear = 0.0
        self.metrics.output_peak_linear = 0.0
        self.metrics.input_clip_detected = False

        self.effect_chain.reset()
