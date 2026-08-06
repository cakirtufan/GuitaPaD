"""Real-time audio engine independent of the audio-device backend."""

from __future__ import annotations

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

        # Preallocated once, before the stream starts.
        self._mono_buffer = np.zeros(
            (config.block_size, 1),
            dtype=np.float32,
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

            self.effect_chain.process(self._mono_buffer)

            mono_output = self._mono_buffer[:, 0]

            outdata[
                :,
                self.config.left_output_index,
            ] = mono_output

            outdata[
                :,
                self.config.right_output_index,
            ] = mono_output

        except Exception as error:
            # Never send undefined data to the physical outputs.
            outdata.fill(0.0)
            self.metrics.callback_error_count += 1
            self.metrics.last_callback_error = repr(error)

        finally:
            elapsed = time.perf_counter() - callback_start

            self.metrics.callback_count += 1

            if elapsed > self.metrics.maximum_callback_seconds:
                self.metrics.maximum_callback_seconds = elapsed

    def reset(self) -> None:
        self._mono_buffer.fill(0.0)
        self.effect_chain.reset()
