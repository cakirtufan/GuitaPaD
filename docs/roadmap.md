# GuitaPaD Roadmap

This roadmap reflects the current project direction: **adaptive tone matching using interpretable DSP plus machine learning**.

It is intentionally staged so that the project does not jump directly into ML before the controllable tone engine is capable of producing useful sounds.

---

## Phase 0 - Real-time foundation

Status: **working / continuing validation**

Goals:

- stable low-latency audio I/O
- deterministic callback
- modular DSP lifecycle
- runtime/GUI separation
- live meters and diagnostics
- raw DI recording
- reproducible offline testing

Already demonstrated:

- Audient EVO 4 ASIO
- 48 kHz
- 128-frame callback
- approximately 9.79 ms reported total I/O latency
- real-time callback with substantial headroom
- 35 Hz HPF
- master gain
- safety limiter
- PySide6 GUI
- raw 24-bit DI recording

Remaining foundation work:

- general audio-device selection
- configurable channel mapping
- longer stability tests
- regression tests
- clearer runtime configuration files

---

## Phase 1 - Build a complete tone engine

Priority: **next major engineering milestone**

Do not optimise against reference tones until the DSP graph can generate a useful range of guitar sounds.

Target blocks:

1. input calibration
2. noise gate
3. pre-EQ / low-end tightening
4. nonlinear amp/preamp stages
5. tone stack
6. power-amp shaping
7. cabinet model
8. microphone / spatial model
9. post-EQ
10. output safety

Development rule:

> Every block must first be tested offline with fixed DI, then benchmarked before entering the live callback.

Important lesson from early overdrive experiments:

Static waveshaping by itself did not produce the desired high-quality pedal/amp character.

Future nonlinear work should consider:

- physically motivated circuit behaviour
- stateful nonlinear systems
- gain staging
- interaction with amp/cab filtering
- aliasing
- oversampling / antialiasing where needed

---

## Phase 2 - Define the tone representation

Goal:

Turn reference audio and rendered guitar audio into comparable feature representations.

Initial features to investigate:

- multi-resolution STFT magnitude
- spectral envelope
- band energies
- spectral centroid and slope
- transient/onset descriptors
- RMS envelope
- crest factor
- dynamic range
- harmonic distribution
- distortion-related high-frequency structure

Deliverable:

```text
Analyse(audio) -> feature vector / structured representation
```

Validation:

Two tones that listeners perceive as similar should generally have a smaller feature distance than clearly different tones.

---

## Phase 3 - Offline parameter optimisation

Goal:

Given:

```text
player DI
reference tone
DSP parameter space
```

automatically find a better tone recipe.

Loop:

```text
choose theta
-> render DI
-> analyse render
-> compare with target
-> update theta
```

Start with isolated or guitar-dominant reference audio.

Candidate optimisation approaches should be benchmarked rather than chosen by fashion.

Possible methods:

- coarse-to-fine search
- coordinate optimisation
- Bayesian optimisation
- evolutionary algorithms
- CMA-ES
- other derivative-free search

Deliverable:

```text
DI + reference -> optimised tone recipe
```

The output remains an interpretable DSP preset.

---

## Phase 4 - Tone-recipe format and reproducibility

Define a versioned recipe schema.

A recipe should record:

- DSP graph version
- parameters
- sample rate assumptions
- input calibration
- optional hardware profile
- matching metadata
- optional similarity score

Goals:

- deterministic rendering
- easy sharing
- diffable text files
- backwards-compatible schema migration

Suggested format:

```text
JSON
```

---

## Phase 5 - ML parameter estimator

Only after the optimiser has generated enough examples:

Train a model to estimate useful initial DSP parameters.

Input may include:

```text
reference features
+
player DI features
+
optional hardware/profile features
```

Output:

```text
initial theta
```

Then refine using the offline optimiser.

Target architecture:

```text
ML initializer
-> DSP render
-> loss
-> optimisation
-> final recipe
```

This should dramatically reduce search time if successful.

---

## Phase 6 - Perceptual learning

Goal:

Make the matching criterion better reflect human judgement.

Possible data:

- A/B listening preferences
- ranking of candidate tones
- user ratings
- accepted/rejected optimiser results

Possible models:

- learned tone embedding
- pairwise ranking model
- learned loss weighting
- preference model

Important constraint:

A learned perceptual model should guide the DSP parameters, not silently replace the entire audio engine.

---

## Phase 7 - Full-song reference support

Initial matching should not assume that a mastered song is an isolated guitar recording.

Later research:

- source separation
- guitar-stem extraction
- guitar-aware time-frequency masks
- multi-track / double-track analysis
- stereo reference analysis
- confidence scoring

Goal:

Allow a user to select a short section of a song and extract a useful guitar-tone target with minimal manual preparation.

---

## Phase 8 - Hardware adaptation

Generalise beyond the current Audient EVO 4 setup.

Goals:

- GUI device selector
- stored audio-interface profiles
- configurable input/output channel mapping
- input calibration
- automatic level test
- hardware-specific latency reports

Potential profile metadata:

```text
OS
driver/backend
interface
input channel
sample rate
buffer
measured latency
input gain/calibration
```

---

## Phase 9 - MIDI and performance workflow

Integrate physical control.

Initial target hardware:

- Behringer X-TOUCH MINI

Possible mappings:

- preset/tone-recipe selection
- gain
- tone controls
- wet/dry
- effect bypass
- scene changes

Live performance must use already-matched tone recipes.

Heavy optimisation remains offline.

---

## Phase 10 - Community tone library

Goal:

Create a community around open tone recipes and measurements.

Potential contribution types:

- tone recipes
- guitar/pickup adaptations
- interface profiles
- cabinet models
- DSP blocks
- ML models
- benchmark results
- tone-matching experiments

Artist/song names may be used descriptively for user-provided references, but copyrighted audio should not be distributed with the repository.

A community recipe should ideally state the environment in which it was created.

Example:

```text
Reference description
Guitar / pickup
Interface
Sample rate
Tone-engine version
Recipe
Match score
User rating
```

---

# Near-term priority

The immediate order should be:

```text
1. Preserve stable real-time engine
2. Build convincing amp + cab capable tone engine
3. Keep using fixed DI for repeatable experiments
4. Define tone-analysis features
5. Build offline matching loop
6. Add ML only after optimisation targets are meaningful
```

The project should resist the temptation to train a model before the DSP parameter space itself is capable of representing the target tones.
