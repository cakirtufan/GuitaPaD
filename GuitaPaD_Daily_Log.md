# GuitaPaD Daily Log

Development journal for experiments, measurements, decisions and lessons
learned during the GuitaPaD project.

---

## 2026-08-07 - DI capture, overdrive experiments and DSP diagnosis

### Real-time DSP baseline

The real-time audio pipeline remained stable throughout the experiments.

Current hardware/runtime baseline:

- Audient EVO 4
- ASIO
- 48 kHz
- 128-sample callback blocks
- Total measured I/O latency: approximately 9.79 ms
- Callback deadline: approximately 2.67 ms

The 35 Hz first-order high-pass filter remained stable and transparent.

After optimizing the GUI so that button styling is not changed dynamically
during refreshes, the HPF version reached approximately:

- Max callback: 0.225 ms
- Deadline load: 8.4 %

This confirmed that the basic Python/NumPy real-time architecture still has
substantial CPU headroom.

### GUI cleanup

Several corrupted Unicode characters were found in the GUI, for example:

- signal-chain arrows displayed as `?`
- `OUTPUT 1?2`
- subtitle separators displayed as `?`
- `-? dB`
- unknown latency displayed as `?`
- callback-error separator displayed as `?`

The affected UI strings were converted to ASCII-safe representations such as:

- `->`
- `|`
- `/`
- `-inf dB`
- `--`

This removed the encoding-related display problems.

### Overdrive V1

A simple full-band pre-gain followed by symmetric `tanh` saturation was tested.

The implementation behaved correctly mathematically:

- symmetric transfer function
- primarily odd harmonics
- smooth bypass
- smooth Drive parameter changes

Real-time performance was good:

- approximately 0.280 ms max callback
- approximately 10.5 % deadline load

Subjective result:

- sounded more like an overdriven clean signal than a useful distortion
- increasing Drive mainly made the sound more compressed and muddy

Conclusion:

A simple full-band gain -> static waveshaper structure did not produce the
desired pedal character.

### Overdrive V1 with pre-clipping low cut

A 150 Hz high-pass filter was inserted before the V1 clipping stage.

Subjective result:

- low-end reduction did not solve the character problem
- sound was described as similar to a cheap amplifier distortion

Performance remained good:

- approximately 0.270 ms
- approximately 10 % deadline load

Conclusion:

Randomly adjusting the clipping-band cutoff was not a productive direction.

### Overdrive V2

An asymmetric nonlinear transfer function was introduced to generate both even
and odd harmonics.

Offline FFT verification confirmed richer harmonic generation.

Live implementation also included a 20 Hz DC blocker after clipping.

Performance:

- Max callback: approximately 0.409 ms
- Deadline load: approximately 15.3 %

Subjective result:

- still muddy / cheap sounding

Conclusion:

Adding asymmetric harmonics alone did not solve the perceived tone problem.

### Overdrive V3

A frequency-selective Drive stage was tested.

Structure:

`dry + boosted high-pass band -> asymmetric clipping`

The internal Drive high-pass corner was approximately 700 Hz.

Performance:

- Max callback: approximately 0.501 ms
- Deadline load: approximately 18.8 %

Subjective result:

- still sounded like a cheap amplifier distortion

Conclusion:

V1, V2 and V3 all demonstrated that continuing to tune arbitrary static
waveshapers was unlikely to solve the problem.

The project direction was therefore changed from waveshaper tuning toward
physically motivated distortion/circuit modelling.

### Raw DI recorder

A real-time-safe DI recorder was added.

Important architecture:

`Audient Input 1 -> preallocated RAM buffer`

The recording is captured before the DSP chain.

No disk I/O is performed inside the audio callback.

After recording stops, the buffer is written outside the callback as:

- mono
- 48 kHz
- 24-bit PCM WAV

Recordings are stored under:

`recordings/`

The directory is ignored by Git so test audio is not committed accidentally.

A roughly 10-second real guitar DI recording was successfully captured.

Recording performance:

- Max callback: 0.532 ms
- Deadline load: approximately 20 %

Therefore even while copying raw DI into the recording buffer, the callback
remained comfortably below the 2.67 ms deadline.

### Real DI level analysis

The recorded DI showed:

- Peak: 0.62899
- Peak level: -4.03 dBFS
- RMS: 0.10735
- RMS level: -19.38 dBFS
- Crest factor: 15.36 dB
- Median active 50 ms RMS: approximately -19.58 dBFS

This revealed an important gain-staging fact.

The DI is already relatively hot.

Estimated peak after simple pre-gain:

- 0 dB: 0.629
- +6 dB: 1.255
- +12 dB: 2.504
- +18 dB: 4.996
- +24 dB: 9.969
- +30 dB: 19.891
- +36 dB: 39.687

Therefore the previous 24-36 dB Drive range was capable of driving the static
waveshapers extremely hard.

An offline trim experiment was performed at:

- 0 dB
- -6 dB
- -12 dB
- -18 dB

while keeping V3 Drive fixed.

Subjective result:

Even with corrected gain staging, the undesirable cheap-amplifier character
remained.

Conclusion:

Incorrect gain staging was not the primary cause of the unwanted distortion
character.

### Parallel clipping experiment

A second structural hypothesis was tested:

`dry + nonlinear high-frequency branch`

Only the filtered Drive branch was clipped, while the dry core remained intact.

Subjective result:

The resulting files were almost indistinguishable from the dry signal.

This was consistent with the measured DI spectrum: the signal contained
relatively little energy in the branch selected above approximately 700 Hz.

Conclusion:

This simplified parallel clipping architecture was also not sufficient.

### DI spectral investigation

Whole-recording analysis initially showed that most signal energy was below
700 Hz.

Because whole-file FFT energy can hide short pick transients, several attack
windows were then analysed separately.

After applying the same 35 Hz HPF used by the live runtime:

- raw peak: 0.62899
- post-HPF peak: 0.57181
- raw mean: approximately 0
- post-HPF mean: approximately 0

Representative attack spectral centroids ranged approximately from:

- 500 Hz
- to 1420 Hz

There was measurable content between 700 Hz and 3 kHz, while the 3-8 kHz band
was much weaker in the captured performance.

The analysis also showed why looking at only the maximum sample was not a
reliable way to identify a pick transient.

A multi-onset/spectral-flux method was used instead.

### Main lesson from today's experiments

The audio engine performance is not currently the limiting factor.

Even the most expensive live V3 + DI recording configuration remained around
20 % of the callback deadline.

The main unresolved problem is the distortion model itself.

The following hypotheses were tested and did not produce the desired result:

1. symmetric static clipping
2. asymmetric static clipping
3. pre-clipping low-frequency reduction
4. frequency-selective Drive
5. lower clipper input level
6. simplified parallel nonlinear branch

This is useful negative evidence.

Rather than continuing to change arbitrary `tanh` parameters or filter
frequencies, the next distortion stage should be based on the behaviour of a
physical nonlinear circuit.

### Next direction

Next session:

1. Keep the current real-time engine and DI recorder as the stable test base.
2. Use the same captured DI for deterministic offline A/B tests.
3. Implement a first nonlinear diode-limiter circuit model offline.
4. Start with a stateful RC + antiparallel-diode model rather than another
   memoryless waveshaper.
5. Verify the circuit numerically before moving it into the real-time callback.
6. Investigate oversampling / nonlinear aliasing only after the circuit model
   itself produces a promising tone.
7. Benchmark the final candidate against the 2.67 ms callback deadline before
   integrating it into the live chain.

### Current project status

Stable foundation:

`INPUT -> 35 Hz HPF -> DSP chain -> MASTER -> SAFETY LIMITER -> OUTPUT 1/2`

Raw DI capture is now available as a reproducible test source.

The V1/V2/V3 overdrive implementations should be treated as experiments rather
than the final distortion architecture.

