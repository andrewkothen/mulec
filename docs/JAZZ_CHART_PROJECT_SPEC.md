# Historical specification

This is the original project brief. The owner subsequently renamed the application Mulec and authorized public source publication. Those later decisions supersede the private-repository requirements below. User recordings and project data remain local and excluded from Git.

# Project: Jazz Chart — Local-First Audio-to-Jazz-Notation Application

You are a senior software architect, audio DSP engineer, music-information-retrieval specialist, and full-stack developer.

Build a functional, production-quality foundation for a completely independent, self-hosted browser application that converts audio recordings into professional jazz charts for musicians.

**Do not stop at planning, scaffolding, or writing documentation. Implement and test a working MVP.**

## 1. Product vision

I am a musician building this tool for personal use and for preparing charts for band rehearsals and performances.

The application must accept audio from:

- Local uploads (WAV, MP3, FLAC, M4A where supported).
- YouTube links.
- Bandcamp links.
- Future audio sources through a modular ingestion system.

For YouTube and Bandcamp, implement a compliant, clearly separated source workflow. Support authorized downloading where permitted, and otherwise provide playback/reference links with local-file import. Do not circumvent DRM, authentication, access controls, or platform restrictions.

The system should analyze the music and generate editable, musician-readable jazz charts.

The primary output is **a practical jazz lead sheet or rhythm-section chart, not a literal orchestral transcription of every instrument**.

## 2. Non-negotiable requirements

- No OpenAI, Anthropic, or other hosted AI APIs.
- No paid APIs, subscriptions, or cloud processing required.
- All audio processing must execute locally.
- Pretrained, freely redistributable local transcription models are allowed, but no model training or hosted inference may be required.
- The application must work offline after dependencies and model assets are installed, for supported local files.
- No authentication, cloud database, telemetry, or external runtime infrastructure.
- Run on localhost from a browser.
- Cross-platform architecture, prioritizing macOS development.
- Open-source libraries with compatible licensing.
- Maintainable, modular, documented code.
- Persist user projects locally.

## 3. Preferred technology stack

Frontend:
- Next.js with React and TypeScript.
- Tailwind CSS.
- Clean, responsive, professional UI.
- Web Audio API for playback and interaction.
- Wavesurfer.js for waveform visualization.
- OpenSheetMusicDisplay or Verovio for MusicXML rendering.
- A structured, editable notation model.

Backend:
- Python 3.12+.
- FastAPI.
- librosa, NumPy, SciPy, soundfile.
- FFmpeg for supported audio decoding.
- music21 for musical analysis and MusicXML generation.
- Optional madmom, Essentia, or other established MIR libraries if compatible.
- Basic Pitch or another locally executable transcription model where beneficial.
- SQLite for project metadata, with audio files stored locally.

Use the best appropriate alternatives where technical limitations or licensing make them preferable. Document architectural decisions.

Package everything into a straightforward local development workflow, ideally with a single startup command.

## 4. Music-analysis pipeline

Implement a modular pipeline with these components:

A. Audio preprocessing
- Decode and normalize supported formats.
- Downmix or select channels where appropriate.
- Resample audio.
- Create waveform data.
- Detect silence.
- Support selecting a time region for analysis.

B. Tempo and rhythmic analysis
- Estimate BPM.
- Detect beats and downbeats.
- Infer time signatures with confidence scoring.
- Support swing and straight eighth-note interpretation.
- Allow user-defined tempo and beat-grid correction.
- Quantize note events to musically meaningful subdivisions.

C. Harmonic analysis
- Estimate key and tonal center.
- Extract chroma features.
- Segment harmonic changes.
- Estimate chord roots, qualities, and bass notes.
- Support jazz harmony, including:
  - Major 7, minor 7, dominant 7.
  - Half-diminished and diminished.
  - Augmented chords.
  - Sus chords.
  - Extensions (9, 11, 13).
  - Alterations (b9, #9, #11, b13).
  - Slash chords.
- Prefer conventional, readable jazz chord symbols.
- Implement harmonic smoothing and contextual ranking.
- Do not invent harmonic detail when the recording does not support it.
- Allow corrections to all estimated chords.

D. Melody transcription
- Extract primary melodic pitch events.
- Detect note onsets and durations.
- Convert pitches into conventional notation.
- Handle rests, ties, accidentals, and rhythmic quantization.
- Avoid over-quantization and excessive notation clutter.
- Allow configurable transcription sensitivity.
- Represent uncertain pitches separately from confirmed notes.

E. Musical form analysis
- Estimate phrase and section boundaries.
- Suggest common jazz forms such as 12-bar blues, 16-bar forms, AABA, and ABAC.
- Detect potentially repeated sections.
- Generate measures with bar numbers.
- Allow manual control of sections and rehearsal markers.
- Never label a form as certain without supporting evidence.

Each pipeline stage must have a clearly defined data interface and be independently testable.

## 5. Jazz chart generation

Provide three chart modes:

**Mode 1: Chord Chart**
- Chord symbols placed in measures.
- One or more harmonic changes per measure.
- Section labels.
- Repeats and endings.
- Compact layout suitable for rhythm-section players.

**Mode 2: Lead Sheet**
- Single-staff melody notation.
- Chord symbols above the staff.
- Key signature and time signature.
- Proper rhythmic notation.
- Rehearsal marks and repeats.

**Mode 3: Form Chart**
- Section structure and measure counts.
- Harmony organized into clear phrases.
- Rehearsal-oriented roadmap.

Design for common professional jazz notation conventions, including the visual density and readability associated with Real Book-style charts, without copying copyrighted chart material.

Use MusicXML as the primary portable notation format.

## 6. Interactive notation editor

The generated chart must be editable.

Implement:
- Click a chord to change its root, quality, extensions, or alterations.
- Add and remove chord changes within measures.
- Set key signature and time signature.
- Change BPM.
- Add, delete, and split measures.
- Edit section names.
- Set rehearsal marks.
- Edit melody pitches and durations through an accessible initial interface.
- Undo and redo.
- Save project.
- Load project.
- Transpose the chart to any key.
- Generate B-flat and E-flat transposed parts.
- Toggle between concert pitch and transposed notation.

The chart must not merely be a static image or PDF preview.

## 7. Audio synchronization

Create a split-screen workspace:

Left panel:
- Audio player.
- Waveform.
- Play/pause.
- Scrubbing.
- Loop selected section.
- Playback speed.
- Time-region selection.

Right panel:
- Editable jazz chart.
- Measure highlighting synchronized to playback.
- Click a measure to jump to its approximate audio position.
- Indicate transcription confidence when useful.

Provide visual feedback during processing and meaningful errors when analysis fails.

## 8. Exports

Implement:
- PDF, optimized for printing on US Letter and A4.
- MusicXML.
- MIDI when melody data is present.
- JSON project format.

A printed lead sheet must show:
- Song title.
- Composer or source metadata, if provided.
- Key and time signature.
- Tempo marking.
- Chord symbols.
- Melody when available.
- Bar lines and measure spacing.
- Section markers and repeats.

Prioritize readability over excessive detail.

## 9. UX and interface direction

Build a polished desktop-first application inspired by professional music software, but significantly simpler to operate.

Main navigation:
- Library
- New Transcription
- Chart Editor
- Settings

Primary workflow:

Import Audio → Analyze → Review Chart → Edit → Export

Use restrained, accessible UI design. Avoid unnecessary animation.

The main chart workspace should be the product's centerpiece.

Provide a useful light theme optimized for reading sheet music, plus optional dark UI chrome.

## 10. Accuracy and limitations

This is critical.

Mixed, mastered recordings are substantially harder to analyze than isolated instruments.

Do not misrepresent the system as capable of perfectly identifying every chord or melody from every recording.

Implement a genuine working audio analysis pipeline, not mock data.

Use confidence values, explicit uncertainty, and manual correction workflows.

Prioritize:

1. Reliable audio loading and playback.
2. Tempo and beat estimation.
3. Usable chord estimates.
4. Measure-based jazz chart generation.
5. Editing and correcting the output.
6. Printable PDF and MusicXML export.
7. Melody transcription improvements.
8. Advanced form analysis.

If necessary, simplify the first version to deliver a genuinely functional chord-chart generator before attempting advanced lead-sheet transcription.

## 11. Architecture and project structure

Use a monorepo with separate frontend and backend directories.

Define a canonical internal data structure covering:
- Project metadata.
- Audio source references.
- Tempo maps.
- Beat and measure boundaries.
- Time signatures.
- Tonal centers.
- Chord events.
- Melody note events.
- Sections and form.
- Confidence values.
- Manual edits.
- Export settings.

Store all timing references consistently and support conversion between seconds, beats, and measures.

Ensure editing logic is independent of inference logic so manual changes are not unintentionally overwritten.

Create unit tests for music theory transformations, timing, quantization, chord serialization, and transposition.

## 12. Initial deliverables

Work autonomously through the following phases.

Phase 1: Architecture
- Inspect the repository.
- Create a technical implementation plan.
- Select and justify libraries.
- Identify licensing and runtime limitations.
- Define the data model.

Phase 2: Working application
- Scaffold the frontend and backend.
- Implement audio upload and playback.
- Implement actual beat, tempo, key, and chord analysis.
- Build a measure-based editable chord chart.
- Persist projects.
- Implement MusicXML and PDF export.

Phase 3: Enrichment
- Add melody transcription.
- Improve chord recognition.
- Add waveform/chart synchronization.
- Add transposition and instrument-specific exports.
- Add section detection and form suggestions.

Phase 4: Verification
- Create and run automated tests.
- Include original or openly licensed test audio fixtures.
- Verify the complete import-to-export process.
- Fix build and runtime errors.
- Document known limitations with reproducible examples.

## 13. Execution instructions

Start implementing immediately.

Make reasonable engineering decisions without asking routine questions.

Do not silently replace real functionality with hardcoded placeholder results.

When a feature is too large for the initial implementation, document it, preserve a clean extension point, and continue developing functional core features.

Use available tooling to install dependencies, run builds, test endpoints, and verify outputs.

Create:
- README.md
- ARCHITECTURE.md
- ROADMAP.md
- Local startup scripts
- Example test fixture
- Tests for major processing modules

If Git is available, initialize version control if necessary and make meaningful commits at major stable milestones.

Do not deploy to a hosting provider, use paid services, or publish the repository.

**Success criterion:** I can launch the application on my computer, upload a real audio recording, obtain an automatically generated jazz chord chart, correct the harmony in a browser editor, and export a printable chart.

Begin with that complete vertical slice. Then improve the product toward the full specification using the remaining available execution time and resources.

## 14. GitHub Repository and Version Control

Use my connected GitHub account for source control and project versioning, if authenticated access is available.

- Create a **new private GitHub repository** named `jazz-chart`. Never make it public.
- Initialize Git with a clean `main` branch.
- Use a `develop` branch for active development.
- Create feature branches for major components when appropriate.
- Make descriptive, atomic commits as functionality is completed.
- Push working changes to GitHub regularly.
- Use GitHub Issues to track future features, bugs, and technical debt.
- Maintain a CHANGELOG.md documenting meaningful milestones.
- Add a comprehensive `.gitignore` excluding uploaded audio, local databases, secrets, virtual environments, model weights, and build artifacts.
- Never commit credentials, personal recordings, or copyrighted audio.
- Add GitHub Actions for automated linting, tests, and build validation, using free tooling where available.
- Keep `main` stable and usable. Merge only after relevant tests pass.
- Do not deploy or publish the application.

**Autonomous execution:** Continue implementation through meaningful milestones, committing and pushing tested work as you go. If GitHub authentication or permissions are unavailable, complete local Git setup and report the exact authentication step required.

The repository must remain private, and the entire application must continue to function locally without relying on GitHub or any external runtime service.

Suggested repository structure:

```text
jazz-chart/
├── frontend/             # Next.js / TypeScript
├── backend/              # Python / FastAPI
│   ├── analysis/         # Audio DSP and transcription
│   ├── music/            # Harmony, rhythm, notation
│   └── api/              # Application endpoints
├── tests/
├── scripts/
├── docs/
├── .github/
│   └── workflows/       # CI
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
└── CHANGELOG.md
```

## 15. Musical Context: Indie / Jazz Hybrid Recordings

The target recordings are primarily original indie, alternative, and jazz-influenced songs—not necessarily traditional jazz standards.

Build a genre-agnostic transcription engine that produces professional, jazz-standard notation suitable for a contemporary live band.

Important adjustments:

- Do not assume traditional jazz harmony, swing, or standard jazz forms.
- Recognize indie/alternative harmonic vocabulary: add9, sus2, sus4, maj7, m7, slash chords, pedal tones, modal harmony, and extended or altered chords.
- Support straight, swung, syncopated, and irregular rhythms.
- Detect variable harmonic rhythm, including chord changes occurring between beats.
- Support nontraditional forms, irregular phrase lengths, intros, outros, instrumental sections, and transitions.
- Allow tempo maps, meter changes, and manual beat-grid corrections.
- Preserve musically important rhythmic hits, stops, breaks, and sustained chords.
- Support common band instruments including vocals, guitar, bass, keyboards, drums, and horns.
- Distinguish melody, chord progression, bass movement, and arrangement cues where analysis permits.
- Avoid forcing ambiguous chords into unnecessarily complex jazz symbols.
- Prefer the simplest accurate chord symbol that communicates the musical intent.

### Chart types

1. **Lead Sheet:** Vocal or instrumental melody, chord symbols, and song structure.
2. **Rhythm Section Chart:** Chords, measures, rhythmic hits, stops, breaks, and rehearsal markers.
3. **Chord / Form Chart:** Compact roadmap suitable for rehearsal.
4. **Instrument Parts (future):** Individual transposed parts and arrangement-specific cues.

The fundamental goal is not an academically perfect transcription. It is a musically accurate, legible, editable chart that allows competent musicians to rehearse and perform an original song with minimal explanation.

Prioritize correct form, harmonic rhythm, clear chord symbols, and useful rehearsal cues over unnecessarily detailed transcription.

## 16. Final Implementation Directive

You have full discretion to make reasonable technical and architectural decisions to accomplish this project.

Prioritize delivering working software over exhaustive planning.

Start with a functional end-to-end MVP that takes an uploaded audio file, analyzes its tempo and harmony, generates an editable chord chart, and exports a printable PDF.

After completing the MVP, continue implementing the remaining features in order of technical feasibility and musical usefulness.

Use GitHub for incremental, tested commits, keeping the repository private.

Do not stop after scaffolding, generating documentation, or creating placeholder interfaces. Build and verify actual functionality.

When execution limits are reached, commit all completed, tested work and document the exact next implementation steps.
