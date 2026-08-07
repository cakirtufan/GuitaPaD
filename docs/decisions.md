# Technical Decisions

This file records current architectural decisions for GuitaPaD.

Historical measurements remain documented in the project memory and daily log.

---

## 1. Project identity

GuitaPaD is no longer defined only as a digital pedalboard.

The primary long-term goal is:

> **An open-source adaptive guitar tone-matching platform combining interpretable DSP, optimisation, and machine learning.**

The system should be able to analyse a user-provided reference tone and adapt the DSP parameters to the user's own DI signal.

---

## 2. Hybrid ML + DSP architecture

Decision:

**The real-time audio path remains an explicit DSP graph.**

Machine learning will initially be used for:

- reference-tone analysis
- feature/embedding extraction
- parameter estimation
- optimisation initialisation
- perceptual similarity modelling
- hardware/input adaptation

Rejected as the first architecture:

```text
DI -> opaque neural network -> final audio
```

Reason:

The project values:

- interpretability
- debuggability
- parameter control
- reproducibility
- low-latency predictability
- learning the underlying DSP

End-to-end neural audio models may be researched later, but they are not the core architecture.

---

## 3. Offline matching, live rendering

Decision:

Tone matching and ML optimisation run outside the real-time callback.

Architecture:

```text
OFFLINE:
DI + reference
-> analysis
-> rendering
-> optimisation / ML
-> tone recipe

LIVE:
DI
-> DSP(tone recipe)
-> output
```

Reason:

Heavy optimisation and ML workloads must not threaten real-time callback stability.

---

## 4. Tone engine before ML

Decision:

Do not build a parameter-estimation ML system until the DSP tone engine can already generate convincing tones.

Reason:

A model cannot infer useful parameters if the target parameter space does not contain good solutions.

Immediate engineering priority:

- amp/nonlinear stages
- tone stack
- cabinet
- microphone/spatial shaping
- post EQ
- stable parameter interfaces

---

## 5. Static waveshaping is not the final distortion architecture

Several experimental overdrive approaches were tested:

- symmetric static clipping
- asymmetric clipping
- pre-clipping filtering
- frequency-selective drive
- input-trim variations
- simplified parallel nonlinear branch

These tests were useful but did not produce the desired tone quality.

Decision:

Do not continue endless arbitrary `tanh` parameter tuning.

Future distortion/amp work should investigate:

- stateful nonlinear stages
- physically motivated circuit behaviour
- complete amp + cabinet context
- nonlinear aliasing
- antialiasing / oversampling where justified

Experimental V1/V2/V3 implementations may remain as research history.

---

## 6. Reproducible DI is a core asset

Decision:

Raw DI recording is part of the architecture.

Reason:

A fixed DI allows controlled comparison of:

- DSP revisions
- parameter searches
- ML outputs
- feature extractors
- listening tests

Real-time recording rule:

The callback may copy audio into preallocated memory.

Disk I/O must remain outside the callback.

---

## 7. Reference audio policy

Decision:

The repository will not distribute copyrighted commercial recordings for tone matching.

Users may provide their own legally obtained reference audio.

Artist/song/product names may be used descriptively to identify a desired tone character, but this does not imply affiliation or endorsement.

Community tone recipes should store:

- parameters
- features/metadata where appropriate
- descriptive reference information

not copyrighted audio files.

---

## 8. Full mix is not the initial matching target

Decision:

Initial tone matching assumes:

- isolated guitar
or
- short guitar-dominant reference material

Reason:

A full commercial mix contains bass, drums, multiple guitars, mastering, and other components that can mislead the optimiser.

Source separation and full-mix support are later roadmap items.

---

## 9. Audio interface strategy

Current validated hardware:

- Audient EVO 4
- Audient USB Audio ASIO Driver
- Windows
- 48 kHz
- target 128-frame callback
- guitar input index 0
- dual-mono output 1/2

The current backend contains Audient-specific device detection.

Decision:

Keep the current validated backend stable while adding a later configurable device-selection layer.

The DSP modules themselves must remain independent of Audient hardware.

---

## 10. Current ASIO workaround

For the current Audient EVO 4 + PortAudio configuration:

```python
blocksize = 0
```

and a latency request just below the desired native 128-frame target is used.

This produced:

```text
callback frames   128
input latency     ~4.23 ms
output latency    ~5.56 ms
total latency     ~9.79 ms
```

Decision:

Preserve this workaround until a more general backend/configuration system is implemented and tested.

Do not assume the same negotiation method is correct for every interface.

---

## 11. Python-first strategy

Decision:

Continue in Python while measured callback performance remains acceptable.

Reasons:

- fast DSP experimentation
- readable algorithms
- direct integration with scientific Python
- ML ecosystem
- fast tooling/GUI iteration

Native migration criterion:

Move a specific component to C++/JUCE/native code only when profiling demonstrates that Python cannot satisfy latency, stability, or deployment needs.

Do not migrate pre-emptively.

---

## 12. GUI strategy

Live desktop control:

```text
PySide6
```

Offline analysis and experiment dashboards may use:

```text
Streamlit
```

The GUI does not own DSP logic.

Runtime state and DSP must remain reusable from:

- GUI
- CLI
- MIDI
- offline matching tools
- future services

Avoid dynamic stylesheet work in frequent refresh paths when it can cause timing spikes.

---

## 13. DSP lifecycle

Effects should use a small lifecycle similar to:

```text
prepare()
process()
reset()
```

DSP code must not depend directly on:

- sounddevice
- PySide6
- MIDI libraries

This keeps algorithms portable and testable.

---

## 14. Real-time callback rules

The audio callback must avoid:

- printing
- file operations
- network operations
- GUI calls
- blocking locks
- unbounded allocation
- ML training
- optimisation loops
- heavyweight dynamic setup

Any new DSP block must be benchmarked before being considered safe for live use.

---

## 15. Tone recipes

Decision:

Final matched tones should be stored as explicit versioned parameter recipes.

Preferred properties:

- text based
- human-readable
- diffable
- portable
- versioned
- reproducible

JSON is the current preferred candidate.

A recipe is not merely a song name.

It represents:

```text
tone-engine version
+ DSP graph
+ parameters
+ input calibration
+ optional hardware profile
+ matching metadata
```

---

## 16. Community direction

The project should make it easy for contributors to test and share:

- new audio interfaces
- DSP models
- cabinet models
- matching algorithms
- ML estimators
- tone recipes
- benchmarks

Hardware measurements should accompany hardware-specific recipes when possible.

The project should remain useful even for users who do not participate in ML development.

---

## 17. Evaluation principle

A numerical tone-match score is not sufficient by itself.

Every important modelling decision should consider:

- objective measurements
- controlled A/B renders
- repeatable DI
- listening judgement
- real-time performance

If an optimisation metric improves while listening quality gets worse, the metric must be questioned.
