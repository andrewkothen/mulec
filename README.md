# Mulec

**From recording to rehearsal.** Mulec is a private, local-first browser application that turns an audio recording into an editable chord chart. It runs real signal analysis on your computer, saves projects locally, and exports printable PDF, MusicXML, MIDI melody and project JSON.

The application and intended private repository are named **Mulec / `mulec`**. The original supplied specification is preserved at [`docs/JAZZ_CHART_PROJECT_SPEC.md`](docs/JAZZ_CHART_PROJECT_SPEC.md); the user's subsequent naming decision overrides “Jazz Chart” and `jazz-chart` throughout that document.

## Run on this computer

Dependencies and a production frontend build have already been installed in this workspace:

```sh
python3 scripts/start.py
```

Open **http://127.0.0.1:8765**. On macOS you can also double-click **Launch Mulec.command**. Leave the terminal open while using the application; press Ctrl+C to stop it. If a server is already running, open the link without starting another.

After source changes, rebuild with `python3 scripts/start.py --build`.

## First installation on another machine

Requirements: Node.js 22+ with npm, an initial Python installation to run the setup script, and internet access for dependency installation. The backend runs with Python 3.12; setup installs it locally through uv. macOS is the verified platform. Linux is included in CI; Windows is architecturally supported but has not been manually verified.

```sh
python3 scripts/setup.py
python3 scripts/start.py
```

Or, with uv and Python 3.12 installed:

```sh
uv sync --locked --python 3.12
npm ci --prefix frontend
python3 scripts/start.py --build
```

Once installed and built, the application runs offline. There are no hosted AI calls, model downloads, account requirements, remote fonts, or runtime CDNs. Next.js telemetry is disabled by the provided scripts and CI. FFmpeg is supplied by the `imageio-ffmpeg` dependency.

## The working workflow

1. **New transcription:** select multiple WAV, FLAC, MP3, M4A, OGG or AIFF files, or drop them anywhere in Mulec. The limit is 150 MB / 15 minutes per recording. Batch chart titles come from filenames; composer and analysis options apply to the selected batch. YouTube/Bandcamp links are stored as single-song references; supply an authorized local file for analysis.
2. **Analyze:** local decoding, beat tracking, key estimation and chord recognition produce a measure-based chart. The progress indicator reports real processing stages.
3. **Review:** listen with the waveform, change playback speed, loop a region and select a bar to seek to it. Amber markers identify uncertain chord estimates.
4. **Edit:** change chord symbols and beat positions, add/remove changes, edit section labels and cues, add/delete/split bars, add melody notes, correct bar timing, or apply a uniform tempo/meter grid. Undo/redo retains up to 80 edits. Chord syntax includes `Cmaj7`, `Dm7`, `G7b9`, `Fm7b5`, `Bb/F` and `N.C.`.
5. **Save:** projects persist in SQLite; a revision check prevents overwriting a newer save from another tab. Analysis always creates a new project, so it cannot overwrite corrections.
6. **Export:** PDF chord charts on Letter/A4; MusicXML with melody/rests/harmony/repeats; MIDI when melody exists; JSON for notation backup. Exports use current edits, even before saving. Concert, B-flat (+2 semitones), and E-flat (+9 semitones) views/exports are available. The editor always edits concert pitches; transposed parts are derived views.

The **Try an original demo** action synthesizes original CC0 audio, then sends it through exactly the same analysis pipeline as an upload. It does not inject predetermined chord results.

The import queue uploads and analyzes one song at a time, shows per-song progress, and continues after a failed recording. Add further files while it runs, remove waiting songs, retry failures, or open completed charts from the queue or Library. Keep the window open until it finishes: files still waiting to upload are held by the browser and are not restored after a reload. Completed charts are saved locally as usual. Queuing imports preserves current editor changes.

**Form → Arrangement** is the rehearsal print view: handwritten jazz typography, rhythm slashes, repeat barlines/counts, compact chord symbols (△ major, - minor, ø half-diminished), and an arrangement roadmap. Browser and PDF use the same bundled MuseJazz-derived font. PDF layout targets four pages or fewer, with adaptive spacing and chord text kept at least 12 points; exceptionally long or dense charts can exceed that target rather than omit music. Short charts may fit one page. The font is an open-source alternative to the supplied reference's Inkpen2 typefaces, not an exact replacement.

Enable **Condense** in Form's Arrangement view for shorter musical measures: staff lines, rhythm slashes and chord lettering remain, with up to six bars per row where space permits. Dense measures have room for their changes. Exact repeats, changed endings, meter, beat cues, manual changes and uncertainty remain represented. The PDF follows the toggle and aims for fewer pages with a 12-point chord-text floor; long/dense charts can need more than two pages to remain readable. The preference survives reloads, and the underlying chart and recording timeline remain unchanged.

For stronger harmony analysis, run `python3 scripts/setup_harmony.py` after the regular setup. This installs [S-KEY](https://github.com/deezer/skey) for key estimation and [LV-Chordia](https://github.com/openmirlab/lv-chordia) for chord changes in separate local CPU environments. Deezer licenses the S-KEY weights for noncommercial research only. The download happens once. New imports use the models automatically and fall back to pitch profiles or chord templates if a model is unavailable. **Analysis notes** names the method used. Close key alternatives appear beside the estimated key.

If you know the song's key, choose **Analysis options → Known key** before importing. This overrides automatic key detection. Changing the signature under **Song & beat grid** applies to the notation. Theoretical signatures such as Db minor are respelled to their practical equivalent during notation export. Unresolved chord events appear as `?` in Chord chart and are omitted from the engraved staff and MusicXML.

## Honest MVP limits

- The engine estimates a starting chart, not a verified transcription. Mixed recordings, prominent bass lines, ambiguous voicings, distortion, drones and complex rhythm can produce wrong results.
- Meter is user-selected, with zero automatic confidence. The first detected beat is provisionally grouped as a downbeat. Tempo may be half/double time. Correct the beat grid before treating bar numbers as authoritative.
- Detected beat timing can reflect rubato, but automatic tempo-map segmentation and meter-change inference are not implemented. Applying a uniform grid replaces the timeline explicitly.
- LV-Chordia estimates chord qualities and inversions. The fallback uses triad, seventh, sus and add9 templates. Check chord voicings and extensions against the recording.
- Melody is optional, experimental monophonic pYIN, limited to a two-minute region. It cannot isolate vocals/instruments in a mastered mix. Half-beat quantization favors readability; swing changes the feel marking, not the transcription algorithm.
- Form compares harmonic contours across the recording to suggest recurring parts. **Arrangement** shows the playback order, writes identical returns once, compresses exact chord cycles with repeat counts, and retains changed endings. Export this view as a compact PDF. Use **Match recurring parts** to regroup existing sections, **Same part as** to merge an occurrence, or rename a group Verse, Chorus, Bridge, etc. Semantic section names are user assigned. By-section and full engraved rhythm charts remain available; MusicXML exports the full rhythm chart from Arrangement.
- Chord chart can switch between jazz chord symbols and Nashville numbers. The PDF uses the chosen style. Minor keys number from their relative major, and the chart shows which note is 1.
- **PDF is a chord chart**, not an engraved melody lead sheet. The browser renders MusicXML with OpenSheetMusicDisplay; export MusicXML to a notation application for engraved lead-sheet printing. Compact PDFs include separately labeled changed endings; formal MusicXML alternate-ending brackets are deferred.
- JSON does not embed audio. An imported JSON project opens without playback. For a complete backup, copy the entire `data/` directory while Mulec is stopped.
- No remote downloader is enabled. The source workflow supports YouTube/Bandcamp reference links with local import without circumventing platform restrictions.

## Storage and privacy

`data/mulec.sqlite3` holds project snapshots and analysis jobs; `data/audio/` holds normalized WAV playback files. Uploaded originals are removed after decoding/analysis. Set `MULEC_DATA_DIR` to choose another storage directory. The app binds to `127.0.0.1`, checks Host/Origin headers, accepts no remote audio URLs, and bounds upload size, decoded duration and analysis queue length.

Audio, databases, models, generated files, virtual environments and secrets are excluded from Git. The repository is intended to remain **private**. No deployment or publishing workflow exists.

## Development and verification

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check backend tests scripts
npm run typecheck --prefix frontend
npm test --prefix frontend
NEXT_TELEMETRY_DISABLED=1 npm run build --prefix frontend
```

Browser acceptance test (with dependencies/build installed):

```sh
.venv/bin/python scripts/make_fixture.py
cd frontend
npx playwright install chromium
npm run test:e2e
```

The browser test covers real upload → analysis → chord correction → save → undo/redo → B-flat preview → melody editing → playback → PDF download → MusicXML rendering → reload. It blocks external requests and checks mobile horizontal overflow. Artifacts stay in ignored `tmp/`.

For live frontend development, start the backend with `.venv/bin/python -m uvicorn backend.api.app:create_app --factory --host 127.0.0.1 --port 8765`, then run `NEXT_TELEMETRY_DISABLED=1 npm run dev --prefix frontend`. The Next development server proxies `/api` to the local backend.

See [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), [licensing notes](docs/DEPENDENCIES.md) and [verification evidence](docs/VERIFICATION.md).

## Private GitHub connection

The private repository is [andrewkothen/mulec](https://github.com/andrewkothen/mulec). This workspace is linked to it through the `origin` remote.

After committing changes, upload the current branch with:

```sh
git push
```

Keep the repository private. Recordings, local databases, secrets, dependencies and generated files are excluded by `.gitignore`. The roadmap lists future issue candidates.
