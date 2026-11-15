from pathlib import Path

from backend.analysis.audio import decode
from backend.analysis.harmony import estimate_chords, extract_features
from backend.analysis.melody import extract_melody
from backend.analysis.rhythm import analyze_rhythm
from backend.models import AnalysisOptions, Measure, Project, TempoPoint


def analyze(
    project: Project, original: Path, playback: Path, options: AnalysisOptions, progress=lambda *_: None
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
    features = extract_features(y, audio.rate, options.start)
    project.source.duration = audio.duration
    project.source.sample_rate = audio.rate
    project.waveform = audio.waveform
    project.bpm, project.tempo_confidence = rhythm.bpm, rhythm.confidence
    project.tempo_map = [TempoPoint(time=options.start, bpm=rhythm.bpm)]
    project.beats = rhythm.beats
    project.meter = options.meter
    project.key, project.key_mode, project.key_confidence = features.key, features.mode, features.confidence
    project.warnings = rhythm.warnings + [
        "Chord and key confidence are heuristic scores, not probabilities. Review estimates against the recording.",
        "Mixed recordings, pedal tones and dense voicings can confuse harmony. Extensions and slash basses need manual review.",
    ]
    for a, b in zip(rhythm.boundaries, rhythm.boundaries[1:]):
        project.measures.append(
            Measure(
                start=a,
                end=b,
                meter=options.meter,
                chords=estimate_chords(features, a, b, options.meter.quarters),
            )
        )
    if project.measures:
        project.measures[0].section = "A"
    progress(76, "Building the rehearsal chart")
    # Only suggest repeats backed by identical estimated chord sequences.
    signatures = [tuple(c.symbol for c in m.chords) for m in project.measures]
    for size in (4, 8, 12, 16):
        if len(signatures) >= size * 2 and signatures[:size] == signatures[size : size * 2]:
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
