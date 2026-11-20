# Runtime and licensing notes

The source repository is public for inspection. No project-wide reuse license has been granted; see COPYRIGHT.md. No recorded music, credentials or model weights are committed. The chart font is bundled with its OFL license; dependency executables are installed separately. `uv.lock` and `frontend/package-lock.json` record resolved versions; source builds use those lockfiles.

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
| MuseJazzText / Mulec Jazz | Offline handwritten chart typography | SIL OFL 1.1; original, renamed TrueType derivative, license and provenance in `frontend/public/fonts/` |
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

## Optional harmony models

LV-Chordia code is MIT-licensed at the pinned revision; its installation remains separate from this repository. S-KEY code is MIT-licensed, but its bundled model weights are restricted to noncommercial research. The default harmony setup installs only LV-Chordia. S-KEY installation requires `--research-key-model`, and inference requires `MULEC_ENABLE_RESEARCH_KEY_MODEL=1`, including for previously installed models. Neither model's weights are tracked in Mulec. These upstream terms are separate from the rights reserved for Mulec source.

- [Pinned S-KEY terms](https://github.com/deezer/skey/blob/80d9590e150b836a341dfc6dbf05aa20bc81d10b/README.md#-license)
- [Pinned LV-Chordia license](https://github.com/openmirlab/lv-chordia/blob/d8ab9ac99bce081bb79065d717f96e2c3b2099c8/LICENSE)
