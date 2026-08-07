# GuitaPaD - Reference Audio Legal & Privacy Design Note

**Status:** Project design note  
**Scope:** Reference-audio capture and tone analysis  
**Primary legal context considered:** Germany / EU copyright framework  
**Purpose:** Preserve the current design decision so the project does not drift toward unnecessary storage, downloading, or redistribution of copyrighted audio.

> This document is a technical/project risk note, not legal advice. If GuitaPaD later becomes a commercial service, stores user audio, operates a server-side reference library, or is distributed at scale, the legal position should be reviewed professionally.

---

## 1. The problem

GuitaPaD should eventually allow a user to play a reference tone from another application and ask the system to match that tone with the user's own guitar.

A realistic workflow could be:

```text
User plays a reference
in browser / media player / streaming app
        |
        v
GuitaPaD captures a short system-audio sample
        |
        v
Tone analysis
        |
        v
Numerical tone representation
        |
        v
Temporary raw audio is destroyed
        |
        v
DSP / ML tone matching
        |
        v
Tone recipe
```

The project should **not depend on users owning MP3/WAV files** and should **not implement service-specific downloaders**.

---

## 2. Core design decision

GuitaPaD will treat reference audio as **temporary analysis input**, not as project content.

The normal product path should be:

```text
CAPTURE
   |
   v
temporary in-memory audio buffer
   |
   v
ANALYSE
   |
   v
extract numerical representation
   |
   v
DISCARD RAW AUDIO
```

Only derived information required for tone matching should remain.

Examples:

```text
spectral representation
transient descriptors
dynamic descriptors
harmonic descriptors
learned tone embedding
final DSP parameters / tone recipe
```

The original reference recording should not be retained by default.

---

## 3. Storage policy

### Normal user mode

Reference audio should:

- be captured only temporarily;
- remain in memory where practical;
- not be written to the project directory;
- not be uploaded to a GuitaPaD server;
- not be included in telemetry;
- not be added to Git;
- not be shared with the community;
- be discarded immediately after the required numerical representation is extracted.

The UI should make this behaviour visible.

Example:

```text
CAPTURE REFERENCE
10.0 s

Analysing...
Target extracted
Temporary audio discarded
```

### Development mode

Saving a reference recording for debugging should be a separate explicit developer feature, disabled in normal use.

Development recordings must not be committed to the public repository unless the developer has the necessary rights to distribute them.

---

## 4. GuitaPaD should remain source-agnostic

GuitaPaD should provide a generic **system-audio capture** function.

It should not contain features marketed as:

```text
Download from YouTube
Capture Spotify
Rip streaming service
Download song
```

Instead:

```text
Capture reference audio
```

The application does not need to know whether the source is:

- a browser,
- a DAW,
- a media player,
- a user's own recording,
- licensed audio,
- Creative Commons material,
- or another lawful source.

This keeps the technical feature general and avoids tying GuitaPaD to a specific content platform.

---

## 5. No DRM circumvention

GuitaPaD must not be designed to:

- decrypt protected media;
- bypass DRM;
- defeat copy-protection systems;
- intercept protected content before normal playback;
- modify another application's protection mechanisms;
- advertise itself as a way to circumvent technical restrictions.

German Copyright Act §95a protects effective technological protection measures and restricts circumvention of such measures.

GuitaPaD should only analyse audio that is already being rendered normally by the user's system.

---

## 6. No copyrighted reference library

The repository should never contain a library such as:

```text
references/
    metallica_enter_sandman.wav
    nirvana_smells_like_teen_spirit.wav
    ...
```

Community sharing should contain only material produced by GuitaPaD or otherwise legally distributable.

For example:

```json
{
  "name": "Enter Sandman-inspired rhythm tone",
  "engine_version": "0.x",
  "input_profile": {},
  "amp": {},
  "cabinet": {},
  "post_eq": {},
  "matching_metadata": {}
}
```

The shared object is the **tone recipe**, not the copyrighted recording used as a reference.

Artist/song names may be used descriptively to communicate the intended tone character, without claiming affiliation or endorsement.

---

## 7. User responsibility

GuitaPaD cannot determine the legal status of every audio source selected by every user.

The application and README should therefore state clearly that:

> Users are responsible for ensuring that they have the necessary rights or legal basis to use any reference audio submitted to GuitaPaD.

This disclaimer is useful, but it is **not the main legal protection**.

The stronger protection is architectural:

```text
no supplied copyrighted content
+
no downloader
+
no DRM bypass
+
temporary processing
+
no permanent raw-audio storage
+
no redistribution
```

The software should behave consistently with the disclaimer.

---

## 8. Suggested public-facing wording

A concise README / application notice can use:

> **Reference Audio**  
> GuitaPaD does not provide, distribute, or permanently store reference recordings. Reference audio is processed temporarily for tone analysis and discarded after the required numerical representation has been extracted. Users are responsible for ensuring that they have the necessary rights or legal basis to use their chosen reference material. GuitaPaD does not circumvent DRM or other technological protection measures.

A slightly shorter UI version:

> Reference audio is processed temporarily and is not stored by GuitaPaD. Use only material that you are legally entitled to analyse.

---

## 9. Why temporary processing matters

German Copyright Act §44b defines text and data mining broadly as automated analysis of digital or digitised works in order to obtain information such as patterns, trends, and correlations.

The provision allows reproductions of **lawfully accessible** works for text and data mining, requires those copies to be deleted when they are no longer necessary for that purpose, and makes the exception subject to a possible reservation of rights by the rightholder.

This makes the following GuitaPaD architecture particularly sensible:

```text
reference audio
      |
      v
temporary copy
      |
      v
automated analysis
      |
      v
information about tone
      |
      v
temporary copy deleted
```

However, GuitaPaD should **not assume that §44b automatically authorises every possible reference source**. Lawful access and rights reservations still matter.

---

## 10. Temporary copies are not automatically unrestricted

German Copyright Act §44a also addresses temporary acts of reproduction that are transient or incidental and form an integral part of a technical process.

One of its conditions is that the temporary reproduction enables a **lawful use** and has no independent economic significance.

Therefore:

```text
"It exists only in RAM"
```

does **not** mean:

```text
"copyright rules no longer apply"
```

The temporary-buffer design reduces exposure and avoids unnecessary retention, but it should not be presented as a universal copyright exemption.

---

## 11. Open-source / non-commercial status

GuitaPaD is currently conceived as an open-source project without a commercial reference-audio service.

That is a favourable risk factor, but the project should **not document the assumption** that:

```text
open source + non-commercial = copyright does not apply
```

Instead the project position should remain:

```text
We minimise unnecessary copying and retention.
We do not distribute copyrighted reference material.
We do not circumvent protection systems.
The user chooses the reference.
The raw reference is temporary.
Only derived tone information and our DSP recipe remain.
```

If the project later changes into a hosted or commercial service, this note must be revisited.

---

## 12. Tone representation policy

After analysis, GuitaPaD may retain a numerical representation needed for matching.

Possible retained objects:

```text
spectral features
temporal features
tone embedding
normalisation parameters
matching score
DSP recipe
```

The design goal is that this representation describes the **tone characteristics required by the algorithm** rather than functioning as a reconstructable copy of the original recording.

This is also technically desirable: the community needs transferable tone information, not archived copyrighted recordings.

---

## 13. Community policy

Community contributions should be allowed to contain:

- GuitaPaD tone recipes;
- DSP parameter sets;
- legally distributable impulse responses;
- original recordings supplied under an appropriate licence;
- hardware profiles;
- benchmark results;
- tone embeddings/features where appropriate;
- matching scores;
- descriptions of reference tones.

Community contributions should not contain:

- copyrighted commercial song excerpts without permission;
- downloaded streaming audio;
- DRM-circumvention tools;
- credentials/tokens used to access media services;
- hidden caches of reference recordings.

---

## 14. Recommended implementation requirements

When reference capture is implemented, the following requirements should be treated as part of the feature specification:

1. **Generic system-audio capture**
   - No YouTube/Spotify/etc. integration is required.

2. **Short bounded buffer**
   - Initial target: approximately 5-10 seconds.
   - The exact duration is an engineering choice, not a legal safe-harbour number.

3. **RAM-first design**
   - Avoid creating temporary audio files unless technically necessary.

4. **Immediate analysis**
   - Extract the required tone representation as soon as capture stops.

5. **Explicit destruction**
   - Release/overwrite the raw reference buffer after analysis where practical.

6. **No automatic archival**
   - There should be no reference-audio history in normal mode.

7. **No cloud upload by default**
   - Matching should initially happen locally.

8. **No DRM bypass**
   - Only capture normally rendered system audio.

9. **Visible user notice**
   - Tell the user that they are responsible for the legal basis for the reference material.

10. **Recipe-only sharing**
    - Community/export features should operate on generated tone recipes and derived information, not the reference recording.

---

## 15. Current project position

The current intended workflow is:

```text
PLAY TARGET
    |
    v
CAPTURE ~10 s
    |
    v
ANALYSE
    |
    v
DELETE RAW REFERENCE
    |
    v
PLAY YOUR GUITAR
    |
    v
MATCH
    |
    v
SAVE TONE RECIPE
```

This is the design to preserve unless a later legal or technical review recommends otherwise.

---

## 16. Triggers for a new legal review

Revisit this decision before implementing any of the following:

- server-side reference-audio processing;
- permanent storage of user reference audio;
- public sharing of captured reference clips;
- a central reference-tone database built from commercial music;
- service-specific streaming integrations;
- automatic downloading of media;
- DRM-related functionality;
- commercial subscription features based on third-party reference recordings;
- training and distributing ML models whose dataset contains stored copyrighted recordings;
- reconstructable or near-reconstructable representations of copyrighted reference material.

---

## 17. Official German legal references

Checked on 2026-08-07:

- **UrhG §44a - Vorübergehende Vervielfältigungshandlungen**  
  https://www.gesetze-im-internet.de/urhg/BJNR012730965.html

- **UrhG §44b - Text und Data Mining**  
  https://www.gesetze-im-internet.de/urhg/__44b.html

- **UrhG §95a - Schutz technischer Maßnahmen**  
  https://www.gesetze-im-internet.de/urhg/__95a.html

These are official German federal-law sources.

---

## One-line project rule

> **GuitaPaD listens temporarily, learns the tone characteristics it needs, discards the reference audio, and keeps only the information required to reproduce the tone through its own DSP engine.**
