from pathlib import Path
from tempfile import TemporaryDirectory

import soundfile as sf

from backend.analysis.audio import decode
from backend.analysis.harmony import estimate_chart_chords, extract_features
from backend.analysis.learned_harmony import align_chords, predict, ranked_key
from backend.analysis.melody import extract_melody
from backend.analysis.rhythm import analyze_rhythm
from backend.models import AnalysisOptions, Measure, Project, TempoPoint


def analyze(
    project: Project,
    original: Path,
    playback: Path,
    options: AnalysisOptions,
    progress=lambda *_: None,
    *,
    models: Path | None = None,
):
    progress(8, "Decoding local audio")
    audio = decode(original, playback)
    end = min(options.end or audio.duration, audio.duration)
    if end - options.start < 2:
        raise ValueError("Select a region with at least two seconds of audio")
    if options.melody and end - options.start > 120:
        raise ValueError(
            "Optional melody analysis is limited to a two-minute region. Turn it off or shorten the region."
        )
    y = audio.samples[int(options.start * audio.rate) : int(end * audio.rate)]
    progress(24, "Finding pulse and beat grid")
    rhythm = analyze_rhythm(y, audio.rate, options.start, options.meter.quarters, options.bpm)
    progress(48, "Listening for key and harmony")
    key_predictions, chord_predictions = None, None
    if models is not None:
        with TemporaryDirectory() as temp:
            wave = playback
            if options.start or end < audio.duration:
                wave = Path(temp) / "region.wav"
                sf.write(wave, y, audio.rate)
            if not options.key:
                key_predictions = predict("key", wave, models)
            progress(58, "Tracking chord changes")
            chord_predictions = predict("chords", wave, models)
    features = None
    if not (options.key or key_predictions) or not chord_predictions:
        features = extract_features(y, audio.rate, options.start)
    project.source.duration = audio.duration
    project.source.sample_rate = audio.rate
    project.waveform = audio.waveform
    project.bpm, project.tempo_confidence = rhythm.bpm, rhythm.confidence
    project.tempo_map = [TempoPoint(time=options.start, bpm=rhythm.bpm)]
    project.beats = rhythm.beats
    project.meter = options.meter
    if options.key:
        project.key, project.key_mode = options.key, options.key_mode
        project.key_manual = True
        project.key_confidence = 0  # A user setting is not an inference confidence.
    elif key_predictions:
        project.key, project.key_mode, project.key_confidence, project.key_alternatives = ranked_key(
            key_predictions
        )
    else:
        assert features is not None
        project.key, project.key_mode, project.key_confidence = (
            features.key,
            features.mode,
            features.confidence,
        )
    project.warnings = rhythm.warnings + [
        f"Key: {'set by you' if options.key else 'S-KEY' if key_predictions else 'local pitch profiles'}. "
        f"Chords: {'LV-Chordia' if chord_predictions else 'local chord templates'}.",
    ]
    for a, b in zip(rhythm.boundaries, rhythm.boundaries[1:]):
        project.measures.append(
            Measure(
                start=a,
                end=b,
                meter=options.meter,
            )
        )
    if chord_predictions:
        chart = align_chords(
            chord_predictions, project.measures, options.start, project.key, project.key_mode, y, audio.rate
        )
    else:
        assert features is not None
        chart = estimate_chart_chords(features, project.measures, project.key, project.key_mode)
    for measure, chords in zip(project.measures, chart):
        measure.chords = chords
    if project.measures:
        project.measures[0].section = "A"
    progress(76, "Building the rehearsal chart")
    # Only suggest repeats backed by identical estimated chord sequences.
    signatures = [tuple(c.symbol for c in m.chords) for m in project.measures]
    for size in (4, 8, 12, 16):
        if (
            len(signatures) >= size * 2
            and any(chord not in {"?", "N.C."} for bar in signatures[:size] for chord in bar)
            and signatures[:size] == signatures[size : size * 2]
        ):
            project.form_suggestions.append(
                f"Bars 1–{size} and {size + 1}–{size * 2} have matching chord estimates; possible repeated phrase."
            )
    if options.melody:
        progress(82, "Extracting an experimental monophonic melody guide")
        extract_melody(y, audio.rate, options.start, project.measures, options.sensitivity)
        project.warnings.append(
            "Melody uses monophonic pYIN; full-band recordings can follow bass or accompaniment. Notes require review."
        )
    return Project.model_validate(project.model_dump())
