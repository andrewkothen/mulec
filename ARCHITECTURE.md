# Mulec architecture

## Decisions

The complete MVP is one local service: **FastAPI** serves both `/api` and the static **Next.js / React / TypeScript** frontend. Production needs no Node server. This eliminates cross-origin setup and keeps the installed app usable without internet. Custom CSS provides the responsive design without adding a separate CSS toolchain; no external font resources are loaded.

**librosa, NumPy, SciPy and soundfile** implement a genuine deterministic DSP pipeline. No pretrained weights or hosted inference are required. `imageio-ffmpeg` supplies a local decoder for common formats. **music21** validates harmony and generates MusicXML/MIDI. **ReportLab** creates print-ready chord charts. **WaveSurfer** handles waveform playback, seeking and speed; **OpenSheetMusicDisplay** renders portable notation. **SQLite** plus ordinary audio files provide local persistence.

## Canonical data and invariants

`backend/models.py` is the authoritative versioned Pydantic schema; `frontend/lib/model.ts` mirrors it. Schema version 1 includes metadata, source references, nominal tempo/map, key, meter, beat times, measure boundaries, chord events, monophonic note events, sections/cues/repeats, confidence and manual-origin flags. Instrument part, display mode, theme and paper are view preferences rather than destructive project transformations.

- All absolute times are **seconds from the original recording**, including region analysis.
- All musical offsets/durations are **quarter-note units**. A 6/8 measure contains 3 quarter notes; UI beat positions are one-based quarter-note positions.
- A measure owns `[start,end)` audio time and its own meter. Musical offsets are mapped linearly within that interval. A partial last audio measure still has the chosen meter; review/trim that bar manually.
- Chord starts are unique and within their measure. Monophonic notes cannot overlap or extend past a bar. Gaps become rests during export.
- Inference confidence is a heuristic score, not a calibrated probability. Manual edits have a separate flag.
- IDs identify projects and events; revisions guard concurrent saves. Export derives transposed copies and does not mutate concert data.

## Processing boundaries

1. **Ingestion (`api/app.py`):** streams uploads with a 150 MB cap to generated filenames. Only two analysis jobs can be queued/running, with one worker. YouTube/Bandcamp references are validated and never fetched. Each analysis creates a fresh project.
2. **Decode (`analysis/audio.py`):** FFmpeg subprocess with no shell, local-only input protocols, timeout and duration cap. Downmix to mono/22,050 Hz; reject silent/invalid/short audio; normalize and generate waveform peaks. Save a browser-compatible WAV.
3. **Rhythm (`analysis/rhythm.py`):** onset strength → dynamic-programming beat tracker → measured beat intervals and provisional measure boundaries. The user may override BPM/meter; uncertainty and fallback assumptions are explicit.
4. **Harmony (`analysis/harmony.py`):** harmonic separation → CQT chroma → key-profile correlation → overlapping half-beat chord-template matching → Viterbi smoothing across the chart. A known key overrides the inferred tonal center and supplies only a weak ranking prior; clearly supported borrowed chords remain possible. Sustained candidates need evidence for their constituent tones. Unsupported harmony becomes `?`; actual silence becomes N.C. Genre-specific progressions are not imposed. These heuristic changes still require real-recording evaluation.
5. **Optional melody (`analysis/melody.py`):** pYIN at 8 kHz → voiced-frame confidence filtering → pitch segmentation → half-quarter quantization and bar splitting. This is monophonic pitch tracking, not source separation.
6. **Assembly (`analysis/pipeline.py`):** collect structured results, warnings and evidence-based repeated-phrase suggestions; validate and save the new project.

Each stage exposes typed inputs/results or a canonical model. DSP is isolated from editor transformations and storage. Exceptions become actionable job errors; traceback details stay in local logs. Jobs interrupted by process restart are explicitly marked failed.

## Editor and exports

Immutable frontend snapshots implement undo/redo. Saving uses an independent revision reference so history navigation does not create false save conflicts. Timing/grid correction never runs inference; changing meter is rejected if it would discard musical events. Splitting carries harmony into the second bar and splits crossing melody durations.

The server validates chord syntax, key names, bounds and timelines before persistence/export. Editing transposed views uses concert pitches in the inspector with an explicit notice. Export endpoints accept the current project snapshot so unsaved corrections are included.

MusicXML/MIDI are generated from a music21 Score. ReportLab chord PDFs lay out bounded rows with bar numbers, chord beat positions, cues, section labels, repeats and page numbering. Melody engraving is delegated to OSMD/MusicXML; the MVP's PDF route is explicitly labeled a chord chart.

## Safety and resource boundaries

Loopback binding, Host checks and Origin checks protect against casual cross-site access. No URL fetch endpoint or third-party telemetry exists. Uploaded filenames never become server paths. JSON imports are capped at 10 MB and validated. SQLite serializes writes; optimistic revision checks prevent silent multi-tab overwrites. A data-folder backup is sufficient to restore the local library.

The intended user is a musician operating their own localhost instance; this is not a multiuser internet server. Do not expose the service on public interfaces.

## Extension points

`Source` can gain explicit authorized adapters; `AnalysisOptions` and independent stage modules can accept local transcription backends; tempo maps and per-measure meters allow future nonuniform grid tools; the canonical project can gain endings/hits/cues and instrument parts via a schema migration. Version 1 currently stores nominal tempo points, not automatic tempo-map inference. See the roadmap for the implementation order.
