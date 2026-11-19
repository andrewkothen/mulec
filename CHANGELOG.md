# Changelog

## Handwritten rehearsal style — 2026-11-19

- Styled compact arrangements after the supplied reference: rhythm staves/slashes, repeat barlines/counts, short jazz chord symbols and a centered title.
- Bundled an OFL-licensed MuseJazz-derived font for consistent offline typography in the browser and PDFs; notation text and the editable chord chart use it too.
- Added a four-page print target with bounded spacing/type-size adjustments. Dense changes wrap before chord text falls below 12 points; music is retained when the target cannot be met.

## Compact arrangements — 2026-11-19

- Form defaults to a compact arrangement: playback order above unique parts, exact pattern repeat counts, and separately identified variations or changed endings.
- Recurring-part matching compares harmonic contours across phrases of different lengths and can regroup an existing section map.
- Added group-name suggestions, a manual “Same part as” control, and compact PDF export while retaining the full playback timeline and engraved rhythm-chart views.
- Verified persistence, merging, renaming and PDF download in the browser regression suite.

## Rhythm and number charts — 2026-11-16

- Form now engraves chord changes above beat slashes, with a new staff line at named sections. The rhythm arrangement can be exported as MusicXML.
- Removed the single-staff part label from the lead sheet and MusicXML.
- Added a jazz-symbol and Nashville-number switch for the chord chart and its PDF.

## Local harmony models — 2026-11-16

- Added optional offline S-KEY key estimation and LV-Chordia chord recognition. Close key alternatives appear in the inspector, and estimated chord changes are aligned to the project's beat grid.
- Removed repeated uncertainty text from the lead sheet and MusicXML. The editable chord chart retains unresolved events.

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
