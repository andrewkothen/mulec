# Mulec roadmap

The first priority is a tested upload → genuine analysis → editable chart → local save → printable export workflow. That vertical slice is implemented.

## Implemented MVP

- [x] Local audio import/decoding, waveform playback, scrubbing, loop, speed and region analysis
- [x] Actual pulse, chroma, key and chord analysis with uncertainty and explicit meter assumptions
- [x] Editable measure-based harmony, section names, cues and repeats
- [x] Add/delete/split measures; manual timing/grid correction; undo/redo
- [x] SQLite project library and revision-safe saves
- [x] PDF chord charts (Letter/A4), MusicXML and project JSON
- [x] Concert/B-flat/E-flat views and exports; arbitrary semitone transposition
- [x] Optional monophonic melody guide, manual note editor, OSMD lead-sheet preview and MIDI export
- [x] Form view and conservative matching-phrase suggestions
- [x] Original synthetic fixture, API/music/DSP/editor tests, browser acceptance test, CI configuration
- [x] Source reference workflow for YouTube/Bandcamp with authorized local import

## Next tested milestones / future GitHub issues

Tracked privately: [beat-grid and meter support (#1)](https://github.com/andrewkothen/mulec/issues/1), [engraved lead-sheet PDF (#2)](https://github.com/andrewkothen/mulec/issues/2), and [mixed-recording accuracy benchmark (#3)](https://github.com/andrewkothen/mulec/issues/3).

1. **Beat-grid accuracy:** user draggable downbeats; pickup/partial-bar support; half/double tempo actions; a percussion/compound-meter test corpus. Retain both estimated and corrected grids.
2. **Tempo/meter maps:** segment actual tempo changes, edit tempo anchors and per-bar meter, export corresponding tempo/meter events. Verify sync on rubato recordings.
3. **Harmony quality:** multi-octave spectral whitening, bass-aware/slash-chord confidence, cross-bar context, adaptive change points and an original real-instrument benchmark. Do not claim improvements from synthetic fixtures alone.
4. **Notation printing:** engraved lead-sheet PDF, tie preservation across edited bars, triplets/swing subdivision choices, rhythmic slash/hit notation, alternate endings and engraving layout controls.
5. **Melody usefulness:** optional permissively licensed local source separation/transcription adapter, candidate notes versus confirmed notes, expressive onset/duration controls and selected-region reanalysis into a new version.
6. **Form evidence:** similarity matrix and user-reviewed section candidates, irregular phrases and explicit transitions; distinguish suggestions from committed form.
7. **Project lifecycle:** archive/delete with confirmation, audio relinking for JSON imports, portable project bundles, auto-save/recovery and schema migrations.
8. **Desktop experience:** validate Windows/Linux manually, package a signed local launcher if desired, monitor memory on 15-minute dense recordings, background cancellation/progress recovery.
9. **Private source control:** maintain the connected private `andrewkothen/mulec` repository, tested main/develop milestones and issues from this backlog. Never make it public or deploy automatically.

## Acceptance gates for further work

Preserve fully offline operation after installation; keep all audio out of version control; test transformations and API compatibility; run production build and browser import-to-export smoke test; visually inspect changed PDF layouts; document measured accuracy and uncertainty. No paid service is required.
