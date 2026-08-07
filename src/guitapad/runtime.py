"""Application runtime shared by CLI, GUI and future control surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import math

from guitapad.audio.backend import StreamInfo
from guitapad.audio.config import AudioConfig
from guitapad.audio.engine import AudioEngine
from guitapad.audio.wav_io import write_pcm24_mono
from guitapad.audio.sounddevice_backend import SoundDeviceBackend
from guitapad.dsp.chain import EffectChain
from guitapad.dsp.gain import Gain
from guitapad.dsp.highpass import OnePoleHighPass
from guitapad.dsp.pedal_overdrive_v3 import PedalOverdriveV3
from guitapad.dsp.limiter import HardLimiter


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Read-only application state for GUI and monitoring surfaces."""

    running: bool
    master_gain: float

    callback_count: int
    maximum_callback_ms: float
    callback_load_percent: float

    stream_status: str
    block_size_mismatch_count: int
    callback_error_count: int

    input_peak_dbfs: float
    output_peak_dbfs: float
    high_pass_enabled: bool
    overdrive_enabled: bool
    overdrive_drive_db: float
    input_clip_detected: bool

    input_latency_ms: float | None
    output_latency_ms: float | None
    total_latency_ms: float | None


def amplitude_to_dbfs(
    amplitude: float,
) -> float:
    """Convert linear full-scale amplitude to dBFS."""

    if amplitude <= 0.0:
        return -90.0

    return max(
        -90.0,
        20.0 * math.log10(amplitude),
    )


class GuitaPadRuntime:
    """Own the audio backend, audio engine and current DSP chain."""

    def __init__(
        self,
        *,
        initial_master_gain: float = 0.60,
    ) -> None:
        self.config = AudioConfig(
            sample_rate=48_000,
            block_size=128,
        )

        self.input_high_pass = OnePoleHighPass(
            cutoff_hz=35.0,
        )

        self.overdrive = PedalOverdriveV3(
            drive_db=12.0,
            level=0.55,
        )

        self.master_gain = Gain(
            linear_gain=initial_master_gain,
        )

        self.safety_limiter = HardLimiter(
            limit=0.80,
        )

        self.effect_chain = EffectChain(
            [
                self.input_high_pass,
                self.overdrive,
                self.master_gain,
                self.safety_limiter,
            ]
        )

        self.engine = AudioEngine(
            config=self.config,
            effect_chain=self.effect_chain,
        )

        self.backend = SoundDeviceBackend(
            config=self.config,
            engine=self.engine,
        )

        self._stream_info: StreamInfo | None = None

    @property
    def is_running(self) -> bool:
        return self.backend.is_running

    def start(self) -> None:
        if self.backend.is_running:
            return

        self.backend.start()
        self._stream_info = self.backend.stream_info

    def stop(self) -> None:
        self.engine.di_recorder.stop()
        self.backend.stop()
        self._stream_info = None

    def set_master_gain(self, value: float) -> None:
        """Update master gain outside the audio callback."""

        value = max(0.0, min(1.0, float(value)))
        self.master_gain.linear_gain = value

    def set_high_pass_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Enable or bypass the input high-pass filter."""

        self.input_high_pass.enabled = bool(enabled)

    def set_overdrive_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Enable or bypass the overdrive."""

        self.overdrive.enabled = bool(enabled)

    def set_overdrive_drive_db(
        self,
        value: float,
    ) -> None:
        """Set overdrive pre-gain in decibels."""

        self.overdrive.drive_db = value

    @property
    def is_di_recording(self) -> bool:
        return self.engine.di_recorder.is_recording

    @property
    def di_recorded_seconds(self) -> float:
        return self.engine.di_recorder.duration_seconds

    def start_di_recording(self) -> None:
        """Begin raw input capture."""

        if not self.backend.is_running:
            raise RuntimeError(
                "Audio engine must be running before recording."
            )

        self.engine.di_recorder.start()

    def stop_di_recording(self) -> None:
        """Stop raw input capture."""

        self.engine.di_recorder.stop()

    def save_di_recording(self) -> Path:
        """Save the current raw DI buffer as 24-bit WAV."""

        samples = (
            self.engine.di_recorder.copy_recorded()
        )

        if samples.size == 0:
            raise RuntimeError(
                "No DI samples have been recorded."
            )

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        recording_dir = (
            project_root
            / "recordings"
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        path = (
            recording_dir
            / f"di_{timestamp}.wav"
        )

        write_pcm24_mono(
            path=path,
            samples=samples,
            sample_rate=self.config.sample_rate,
        )

        return path

    def snapshot(self) -> RuntimeSnapshot:
        """Create a lightweight state snapshot for the GUI."""

        metrics = self.engine.metrics

        deadline_seconds = self.config.block_deadline_seconds

        callback_load = (
            metrics.maximum_callback_seconds
            / deadline_seconds
            * 100.0
        )

        input_latency_ms: float | None = None
        output_latency_ms: float | None = None
        total_latency_ms: float | None = None

        if self._stream_info is not None:
            input_latency_ms = (
                self._stream_info.input_latency_seconds
                * 1_000.0
            )

            output_latency_ms = (
                self._stream_info.output_latency_seconds
                * 1_000.0
            )

            total_latency_ms = (
                input_latency_ms
                + output_latency_ms
            )

        if metrics.callback_error_count:
            status = (
                f"ERROR: {metrics.last_callback_error}"
            )
        elif metrics.stream_status_message:
            status = metrics.stream_status_message
        elif metrics.input_clip_detected:
            status = "INPUT CLIP"
        elif self.backend.is_running:
            status = "OK"
        else:
            status = "STOPPED"

        return RuntimeSnapshot(
            running=self.backend.is_running,
            master_gain=self.master_gain.linear_gain,
            callback_count=metrics.callback_count,
            maximum_callback_ms=(
                metrics.maximum_callback_seconds
                * 1_000.0
            ),
            callback_load_percent=callback_load,
            stream_status=status,
            block_size_mismatch_count=(
                metrics.block_size_mismatch_count
            ),
            callback_error_count=(
                metrics.callback_error_count
            ),
            input_peak_dbfs=amplitude_to_dbfs(
                metrics.input_peak_linear
            ),
            output_peak_dbfs=amplitude_to_dbfs(
                metrics.output_peak_linear
            ),
            input_clip_detected=metrics.input_clip_detected,
            high_pass_enabled=self.input_high_pass.enabled,
            overdrive_enabled=self.overdrive.enabled,
            overdrive_drive_db=self.overdrive.drive_db,
            input_latency_ms=input_latency_ms,
            output_latency_ms=output_latency_ms,
            total_latency_ms=total_latency_ms,
        )
