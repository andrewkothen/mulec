# Changelog

## Key-signature and uncertainty fixes — 2026-11-16

- Fixed the lead-sheet crash caused by theoretical signatures such as Db minor (eight flats). MusicXML now uses an equivalent conventional signature without transposing pitches.
- Added a known-key override on import and a persisted manual-key flag; key corrections are displayed as user settings.
- Switched harmony features to harmonic CQT, added cross-bar smoothing and evidence gates. Unsupported harmony is marked `?`, distinct from silence/N.C. These changes do not establish accuracy on mixed recordings.
- Added a prominent warning for charts dominated by uncertain estimates. Existing saved chords are never silently replaced by new inference.
- Added export regressions across 38 tonic/mode combinations and a browser regression for Db minor rendering and E-major correction.

## 0.1.0 — 2026-11-15

- Renamed the product and intended private repository from Jazz Chart to **Mulec**; retained the full supplied specification.
- Implemented the working local audio-to-chord-chart vertical slice with real DSP and confidence reporting.
- Added browser playback, chart editing, revision-safe local persistence, undo/redo and print-ready exports.
- Added original demo synthesis, MusicXML notation preview, experimental monophonic melody, instrument transposition, form view and MIDI export.
- Added deterministic fixture tests, API persistence/export integration tests, browser acceptance coverage and GitHub Actions configuration.
- Installed and built the application locally, verified the browser workflow, and connected the private `andrewkothen/mulec` repository. Work continues on `develop`, with tested milestones retained on `main`.
