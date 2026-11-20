# Verification — Mulec 0.1.0

## Arrangement readability (2026-11-20)

Passed 84 Python tests, 3 TypeScript tests, all 6 browser scenarios, Ruff, and the production build/type check. The new browser scenario verifies aligned staves beside long cues, additional width for dense harmony, lone offbeat chord labels, and no page or harmony overflow at 1440, 900 and 390 pixels. Desktop and mobile screenshots were visually inspected.

The condensed PDF regression verifies repeated section headings on continuation pages, retained final cues, and lone offbeat entrances on Letter and A4. All nine current local charts were regenerated: eight remain two pages and the longest chart remains three. All three the longest chart pages and a continuation fixture were visually checked. These are layout checks, not a transcription-accuracy benchmark.

## Condense spacing correction (2026-11-19)

Condense now retains musical staves and rhythm slashes in browser and PDF, with shorter measures instead of a staff-free shorthand layout. Browser acceptance verifies that staves stay visible and measures are narrower than the regular arrangement. The chord font size is retained, with responsive six/four/two-column layouts. PDF pages were visually inspected; current songs fit two pages except the longest 163-bar chart, which needs three to retain readable musical bars. The earlier all-songs/two-page result below describes the superseded staff-free layout.

Checks passed: 83 Python tests, all 5 browser scenarios, Ruff and production build/type checking. The live browser was refreshed with Condense enabled and five visible staff lines verified.

## Condense overview milestone (2026-11-19)

Local checks passed: 83 Python tests, 3 TypeScript tests, Ruff, frontend build/type checking, and all 5 browser acceptance scenarios. Condense is a reversible view preference, separate from the saved project. The browser regression verifies switching both directions, exact phrase references, hidden staff lines, persisted preference, matching PDF download, mobile overflow, and unchanged source measures.

New arrangement regressions cover cross-name phrase references, retained changed chords/cues/meter, repeat counts, and direct references to physically printed music rather than reference chains. A 160-bar print fixture fits two pages on Letter and A4 with its final cue intact. All nine newly uploaded local songs render on 1–2 pages; the longest 163-bar chart renders on two. Representative pages were rendered and visually checked. These are layout and data-preservation checks, not harmony-accuracy claims.

## Bulk upload milestone (2026-11-19)

The browser suite now has four passing scenarios. The new real-audio scenario drops multiple files globally from Library, rejects a text file without losing accepted audio, processes valid recordings around a corrupt WAV, appends another recording while the queue is active, verifies all three completed charts are saved, and clears finished queue rows. Multi-selection, duplicate/size/format filtering, production build/type checking, and three TypeScript tests also pass. Other chart acceptance scenarios remain green. Backend analysis logic is unchanged.

The requested fresh library reset moved the previous 12 projects and 10 audio files to an ignored local backup before creating a new empty database. The production browser was refreshed and left on the multiple-recording import form.

## Handwritten rhythm-chart print milestone (2026-11-19)

The reference PDF was inspected visually and its embedded font names identified as Inkpen2. Mulec now bundles an OFL-licensed MuseJazz-derived TrueType font, including provenance and conversion script, for a similar handwritten style across browser and PDF. Exact Inkpen2 typography is not claimed.

Compact PDFs render rhythm staves/slashes, repeat barlines and total-pass counts, short jazz chord symbols, and explicit changed-ending directions. Redundant inferred chord carries are hidden; manual events and unresolved harmony remain visible. A page-fit pass targets two, three or four pages according to written length, with a 12-point chord-text lower bound and wrapping for dense changes. Exceptionally long scores can exceed the target without losing music.

The actual local representative arrangement renders on 2 pages and the longest chart on 4 pages. All pages were rendered and inspected for spacing and glyphs. Engineering coverage checks shorthand quality/slash bass, offbeat and compound-meter beat labels, retained manual changes, an end cue on a rehearsal-length PDF, embedded font resources, browser font loading and visible rhythm rows. This validates printing behavior, not harmonic accuracy.

Latest local checks passed: 80 Python tests, 2 TypeScript tests, Ruff, production frontend build/type checking, and all 3 browser acceptance scenarios.

## Compact arrangement milestone (2026-11-19)

Local checks passed: 78 Python tests, 2 TypeScript transformation tests, Ruff, TypeScript type checking, production frontend build, and all 3 browser acceptance scenarios. The new browser scenario merges a returning F occurrence into A, renames the shared group, saves and reloads it, and downloads a compact PDF. Unit coverage retains changed endings, meter and melody differences, and distinguishes reversed harmonic contours from a returning phrase.

The local representative chart was regrouped and saved with a backup of its previous section labels. Its 107 performed bars compress to 52 written bars across two visually inspected PDF pages. This is evidence of the arrangement workflow, not a musical accuracy benchmark. Automatic grouping remains a suggestion; semantic Verse/Chorus/etc. names are assigned by the user.

## Key-signature regression fix (2026-11-16)

Db minor previously produced eight flats, causing OSMD/VexFlow to throw `BadKeySignature`. Export now writes the pitch-equivalent C# minor signature (four sharps). Regression coverage checks 38 tonic/mode combinations, unchanged note pitches, unknown harmony versus N.C., known-key overrides, and preservation of clearly evidenced borrowed chords. The real local project was also rendered successfully after its user-supplied key correction to E major. The chord guesses in existing projects were preserved; fixing the renderer does not certify their accuracy.

The conservative harmony update is evaluated on signal-path fixtures, not a validated real-recording accuracy benchmark. Do not use passing engineering tests as evidence that an arbitrary mixed recording has been correctly transcribed.

Verified on macOS arm64 with project-local Python 3.12 and Node 25. The application uses a static production build served on loopback.

## Reproducible evidence

The original synthetic fixture generated by `scripts/make_fixture.py` is eight bars at 120 BPM with Cmaj7 → Am7 → Dm7 → G7, repeated twice. It is not a recording of an existing song and is not hardcoded into analysis. The actual pipeline estimated **117.45 BPM** and returned **Cmaj7, Am7, Dm7, G7, Cmaj7, Am7, Dm7, G7** in eight measures. This verifies the working signal path, not accuracy on mastered recordings.

Automated coverage includes:

- Harmony parsing for sevenths, diminished/half-diminished, sus, add9, extensions/alterations and slash chords.
- Chord, bass and melody transposition without mutating the original.
- Quarter-note timing, compound meter, quantization and invalid/overlapping event rejection.
- Real FFmpeg decode, beat/chord inference, region analysis and BPM override.
- Silent/corrupt input rejection; localhost Host/Origin checks; reference URL validation.
- Upload → background job → save correction → reload → restart persistence.
- Revision conflicts, JSON import identity, unavailable imported audio and range playback.
- MusicXML harmony, melody, rests, repeat marks, metadata and bass spelling; MIDI signature.
- PDF content, Letter/A4 dimensions and multipage dense-chart layout.
- Editor bar splitting and safe grid correction.

The browser test adds real waveform playback, undo/redo, B-flat view, note editing, MusicXML SVG rendering, PDF download, viewport checks and a page reload. External runtime requests are blocked by the test.

## Manual QA

Inspect generated `tmp/library.png`, `tmp/workspace.png`, `tmp/lead-sheet.png`, `tmp/mobile.png` and rendered PDF pages. All are ignored by Git; generate them by running the browser test. Review PDF on both paper sizes after changes to its layout.

## Reproducible limitations

- A sustained drone/silent passage lacks reliable rhythmic evidence: pulse/grid may be provisional; silence is rejected for an entire file.
- Tempo estimates on a clean 120 BPM fixture differ slightly due to onset frame resolution. Correct BPM manually when rehearsal precision matters.
- Supply 6/8 to exercise compound meter; it is represented as three quarter notes per bar. Automatic compound/downbeat inference is not claimed.
- A monophonic sine melody can be tracked by optional pYIN; a full-band recording may follow accompaniment. The UI labels it experimental.
- Add melody and export PDF: the PDF intentionally remains a chord chart. Export MusicXML to carry melody notation.
- Import project JSON: notation survives but playback is unavailable because audio was not bundled.

Local checks passed: 28 Python tests, 2 TypeScript transformation tests, Ruff lint, TypeScript type checking, a production frontend build and one browser acceptance scenario. This includes extracting a 440 Hz monophonic melody from synthesized audio. The repository is connected; GitHub Actions results must be checked separately from these local results.
