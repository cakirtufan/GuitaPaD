"""Small WAV helpers for offline recordings."""

from __future__ import annotations

from pathlib import Path
import wave

import numpy as np


def write_pcm24_mono(
    path: Path,
    samples: np.ndarray,
    sample_rate: int,
) -> None:
    """Write mono float32 samples as 24-bit PCM WAV."""

    samples = np.asarray(
        samples,
        dtype=np.float32,
    )

    clipped = np.clip(
        samples,
        -1.0,
        1.0,
    )

    integers = np.rint(
        clipped * 8_388_607.0
    ).astype(
        np.int32,
        copy=False,
    )

    packed = np.empty(
        integers.size * 3,
        dtype=np.uint8,
    )

    packed[0::3] = (
        integers & 0xFF
    ).astype(
        np.uint8,
        copy=False,
    )

    packed[1::3] = (
        (integers >> 8) & 0xFF
    ).astype(
        np.uint8,
        copy=False,
    )

    packed[2::3] = (
        (integers >> 16) & 0xFF
    ).astype(
        np.uint8,
        copy=False,
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with wave.open(
        str(path),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(3)
        wav_file.setframerate(
            sample_rate
        )
        wav_file.writeframes(
            packed.tobytes()
        )
