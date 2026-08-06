"""Lightweight real-time callback metrics."""

from dataclasses import dataclass


@dataclass(slots=True)
class CallbackMetrics:
    callback_count: int = 0
    maximum_callback_seconds: float = 0.0
    stream_status_message: str = ""

    block_size_mismatch_count: int = 0
    callback_error_count: int = 0
    last_callback_error: str = ""

    # Decaying peak levels used by GUI meters.
    input_peak_linear: float = 0.0
    output_peak_linear: float = 0.0
