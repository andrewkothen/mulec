# Runtime and licensing notes

The repository remains private. No project-wide redistribution license has been selected on the owner's behalf. No recorded music, credentials, model weights or dependency binaries are committed. `uv.lock` and `frontend/package-lock.json` record resolved versions; source builds use those lockfiles.

| Component | Purpose | Upstream license / considerations |
| --- | --- | --- |
| Next.js, React | Static browser interface | MIT |
| TypeScript | Type checking | Apache-2.0 |
| WaveSurfer.js | Local waveform/audio interaction | BSD-3-Clause |
| OpenSheetMusicDisplay | MusicXML rendering | BSD-3-Clause; preserve bundled/transitive notices, including engraving fonts |
| FastAPI, uvicorn | Local HTTP service | MIT / BSD-3-Clause |
| librosa | MIR features and beat/pitch estimation | ISC |
| NumPy, SciPy | Numerical DSP | BSD-3-Clause |
| soundfile | WAV I/O | BSD-3-Clause; libsndfile dependency is LGPL |
| music21 | Music theory and notation export | BSD-3-Clause; no bundled corpus content is copied into this repository |
| ReportLab | Chord-chart PDF generation | BSD-style |
| imageio-ffmpeg | Local FFmpeg executable discovery | Wrapper BSD-2-Clause; FFmpeg executable licensing depends on its build, often GPL-enabled |
| SQLite | Local database | Public domain |
| Playwright, pytest, Ruff | Development verification | Apache-2.0 / MIT / MIT |
| PyMuPDF | Development-only PDF visual inspection | AGPL-3.0/commercial; used only as a local QA tool, not imported by runtime application |

The app invokes FFmpeg as a separate installed executable and does not vendor or distribute it. Check the exact FFmpeg build and all upstream notices before packaging a redistributable installer. No nonfree/proprietary codec bundle is introduced by this repository. PyMuPDF is not required to run the application; use Poppler for PDF QA if its licensing better suits a future distribution.

Original test fixture code and its generated sound are dedicated to the public domain under CC0 by this project. It synthesizes tones and noise, uses no samples or existing musical composition, and is labeled as a synthetic benchmark.

Primary technical references:

- [Next.js installation and static frontend](https://nextjs.org/docs/app/getting-started/installation)
- [librosa beat tracking](https://librosa.org/doc/main/generated/librosa.beat.beat_track.html)
- [librosa chroma features](https://librosa.org/doc/main/generated/librosa.feature.chroma_stft.html)
- [music21 documentation](https://www.music21.org/music21docs/)
- [WaveSurfer documentation](https://wavesurfer.xyz/docs/)
- [OpenSheetMusicDisplay](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay)

No accuracy claim is based only on the existence of these libraries. Verification and known limits are documented separately.
