"""Offline profiling and preset comparison dashboard."""

from __future__ import annotations

import math
import time

import numpy as np
import pandas as pd
import streamlit as st

from guitapad.dsp.chain import EffectChain
from guitapad.dsp.gain import Gain
from guitapad.dsp.limiter import HardLimiter


SAMPLE_RATE = 48_000


def linear_to_db(value: float) -> float:
    """Convert linear amplitude to decibels."""

    if value <= 0.0:
        return -90.0

    return 20.0 * math.log10(value)


def build_chain(
    *,
    gain: float,
    limiter: float,
    block_size: int,
) -> EffectChain:
    """Build the current minimal GuitaPaD DSP chain."""

    chain = EffectChain(
        [
            Gain(
                linear_gain=gain,
                smoothing_time_seconds=0.020,
            ),
            HardLimiter(limit=limiter),
        ]
    )

    chain.prepare(
        sample_rate=SAMPLE_RATE,
        block_size=block_size,
        channels=1,
    )

    return chain


def benchmark_chain(
    *,
    gain: float,
    limiter: float,
    block_size: int,
    iterations: int,
) -> dict[str, float | int]:
    """Measure offline DSP processing time for one block size."""

    chain = build_chain(
        gain=gain,
        limiter=limiter,
        block_size=block_size,
    )

    rng = np.random.default_rng(42)

    source = rng.uniform(
        low=-0.5,
        high=0.5,
        size=(block_size, 1),
    ).astype(np.float32)

    work = np.empty_like(source)

    # Warm up Python, NumPy and processor caches.
    for _ in range(100):
        np.copyto(work, source)
        chain.process(work)

    timings_us = np.empty(
        iterations,
        dtype=np.float64,
    )

    for index in range(iterations):
        np.copyto(work, source)

        start_ns = time.perf_counter_ns()
        chain.process(work)
        end_ns = time.perf_counter_ns()

        timings_us[index] = (
            end_ns - start_ns
        ) / 1_000.0

    deadline_us = (
        block_size
        / SAMPLE_RATE
        * 1_000_000.0
    )

    maximum_us = float(
        np.max(timings_us)
    )

    return {
        "Block size": block_size,
        "Deadline (?s)": deadline_us,
        "Mean DSP (?s)": float(
            np.mean(timings_us)
        ),
        "P95 DSP (?s)": float(
            np.percentile(timings_us, 95)
        ),
        "Maximum DSP (?s)": maximum_us,
        "Maximum load (%)": (
            maximum_us
            / deadline_us
            * 100.0
        ),
        "Iterations": iterations,
    }


def process_transfer_curve(
    *,
    gain: float,
    limiter: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate static gain and hard-limiter transfer curve."""

    input_signal = np.linspace(
        -1.0,
        1.0,
        1_001,
        dtype=np.float32,
    )

    output_signal = np.clip(
        input_signal * gain,
        -limiter,
        limiter,
    )

    return input_signal, output_signal


def clipping_threshold(
    *,
    gain: float,
    limiter: float,
) -> float | None:
    """Return input amplitude where limiting begins."""

    if gain <= 0.0:
        return None

    threshold = limiter / gain

    if threshold >= 1.0:
        return None

    return threshold


st.set_page_config(
    page_title="GuitaPaD Lab",
    page_icon="??",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(
                circle at top left,
                #24201a 0%,
                #111318 42%,
                #0d0f13 100%
            );
    }

    [data-testid="stMetric"] {
        background: #191e26;
        border: 1px solid #303844;
        border-radius: 14px;
        padding: 16px;
    }

    h1, h2, h3 {
        letter-spacing: 0.02em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("?? GuitaPaD Lab")
st.caption(
    "Offline DSP profiling and preset comparison ? "
    "no ASIO stream is opened."
)

profiling_tab, preset_tab = st.tabs(
    [
        "DSP Profiling",
        "Preset Comparison",
    ]
)


# ============================================================
# DSP profiling
# ============================================================

with profiling_tab:
    st.subheader("Current DSP chain")

    st.code(
        "Input ? Smoothed Gain ? Safety Limiter ? Output",
        language=None,
    )

    control_1, control_2, control_3 = st.columns(3)

    with control_1:
        benchmark_gain = st.slider(
            "Master gain",
            min_value=0.0,
            max_value=1.0,
            value=0.60,
            step=0.01,
            key="benchmark_gain",
        )

    with control_2:
        benchmark_limiter = st.slider(
            "Limiter threshold",
            min_value=0.10,
            max_value=1.00,
            value=0.80,
            step=0.01,
            key="benchmark_limiter",
        )

    with control_3:
        iterations = st.select_slider(
            "Iterations per block size",
            options=[
                1_000,
                2_500,
                5_000,
                10_000,
            ],
            value=5_000,
        )

    st.caption(
        "The benchmark measures DSP processing only. "
        "It does not include ASIO, PortAudio, input/output "
        "latency or GUI update time."
    )

    if st.button(
        "Run offline benchmark",
        type="primary",
    ):
        results: list[dict[str, float | int]] = []

        progress = st.progress(0)

        for index, block_size in enumerate(
            [64, 128, 256, 512],
            start=1,
        ):
            results.append(
                benchmark_chain(
                    gain=benchmark_gain,
                    limiter=benchmark_limiter,
                    block_size=block_size,
                    iterations=iterations,
                )
            )

            progress.progress(index / 4)

        result_frame = pd.DataFrame(results)

        st.session_state[
            "profiling_results"
        ] = result_frame

    profiling_results = st.session_state.get(
        "profiling_results"
    )

    if profiling_results is not None:
        result_128 = profiling_results.loc[
            profiling_results["Block size"] == 128
        ].iloc[0]

        metric_1, metric_2, metric_3, metric_4 = st.columns(4)

        metric_1.metric(
            "128 deadline",
            f"{result_128['Deadline (?s)']:.1f} ?s",
        )

        metric_2.metric(
            "Mean DSP",
            f"{result_128['Mean DSP (?s)']:.2f} ?s",
        )

        metric_3.metric(
            "Maximum DSP",
            f"{result_128['Maximum DSP (?s)']:.2f} ?s",
        )

        metric_4.metric(
            "Maximum deadline load",
            f"{result_128['Maximum load (%)']:.2f}%",
        )

        st.dataframe(
            profiling_results.style.format(
                {
                    "Deadline (?s)": "{:.2f}",
                    "Mean DSP (?s)": "{:.3f}",
                    "P95 DSP (?s)": "{:.3f}",
                    "Maximum DSP (?s)": "{:.3f}",
                    "Maximum load (%)": "{:.3f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        chart_frame = profiling_results[
            [
                "Block size",
                "Mean DSP (?s)",
                "P95 DSP (?s)",
                "Maximum DSP (?s)",
            ]
        ].set_index("Block size")

        st.subheader("DSP processing time")
        st.bar_chart(chart_frame)

        st.download_button(
            "Download profiling CSV",
            data=profiling_results.to_csv(
                index=False
            ),
            file_name="guitapad_profiling.csv",
            mime="text/csv",
        )


# ============================================================
# Preset comparison
# ============================================================

with preset_tab:
    st.subheader("Compare two static presets")

    preset_a_column, preset_b_column = st.columns(2)

    with preset_a_column:
        st.markdown("### Preset A")

        gain_a = st.slider(
            "Master gain A",
            min_value=0.0,
            max_value=2.0,
            value=0.60,
            step=0.01,
        )

        limiter_a = st.slider(
            "Limiter A",
            min_value=0.10,
            max_value=1.00,
            value=0.80,
            step=0.01,
        )

    with preset_b_column:
        st.markdown("### Preset B")

        gain_b = st.slider(
            "Master gain B",
            min_value=0.0,
            max_value=2.0,
            value=1.20,
            step=0.01,
        )

        limiter_b = st.slider(
            "Limiter B",
            min_value=0.10,
            max_value=1.00,
            value=0.80,
            step=0.01,
        )

    input_curve, output_a = process_transfer_curve(
        gain=gain_a,
        limiter=limiter_a,
    )

    _, output_b = process_transfer_curve(
        gain=gain_b,
        limiter=limiter_b,
    )

    transfer_frame = pd.DataFrame(
        {
            "Input": input_curve,
            "Preset A": output_a,
            "Preset B": output_b,
        }
    ).set_index("Input")

    st.subheader("Input/output transfer curve")
    st.line_chart(transfer_frame)

    threshold_a = clipping_threshold(
        gain=gain_a,
        limiter=limiter_a,
    )

    threshold_b = clipping_threshold(
        gain=gain_b,
        limiter=limiter_b,
    )

    summary_a, summary_b = st.columns(2)

    with summary_a:
        st.markdown("#### Preset A summary")

        a_metric_1, a_metric_2 = st.columns(2)

        a_metric_1.metric(
            "Linear gain",
            f"{gain_a:.2f}",
        )

        a_metric_2.metric(
            "Gain",
            f"{linear_to_db(gain_a):.1f} dB",
        )

        if threshold_a is None:
            st.success(
                "No hard limiting occurs for "
                "an input within ?1.0."
            )
        else:
            st.warning(
                "Hard limiting begins at input amplitude "
                f"?{threshold_a:.3f}."
            )

    with summary_b:
        st.markdown("#### Preset B summary")

        b_metric_1, b_metric_2 = st.columns(2)

        b_metric_1.metric(
            "Linear gain",
            f"{gain_b:.2f}",
        )

        b_metric_2.metric(
            "Gain",
            f"{linear_to_db(gain_b):.1f} dB",
        )

        if threshold_b is None:
            st.success(
                "No hard limiting occurs for "
                "an input within ?1.0."
            )
        else:
            st.warning(
                "Hard limiting begins at input amplitude "
                f"?{threshold_b:.3f}."
            )

    st.info(
        "This first preset comparison covers the current "
        "Gain + HardLimiter chain. Overdrive, tone, EQ and "
        "cabinet parameters will be added as those effects "
        "enter the project."
    )
