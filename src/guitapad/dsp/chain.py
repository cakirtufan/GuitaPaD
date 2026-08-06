"""Ordered DSP effect chain."""

from collections.abc import Iterable

from guitapad.dsp.base import AudioBlock, Effect


class EffectChain:
    """Prepare and process effects in signal-flow order."""

    def __init__(self, effects: Iterable[Effect]) -> None:
        self._effects = tuple(effects)

    @property
    def effects(self) -> tuple[Effect, ...]:
        return self._effects

    def prepare(
        self,
        sample_rate: float,
        block_size: int,
        channels: int,
    ) -> None:
        for effect in self._effects:
            effect.prepare(
                sample_rate=sample_rate,
                block_size=block_size,
                channels=channels,
            )

    def process(self, audio_block: AudioBlock) -> None:
        for effect in self._effects:
            effect.process(audio_block)

    def reset(self) -> None:
        for effect in self._effects:
            effect.reset()
