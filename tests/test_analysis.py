import numpy as np
import pytest
import soundfile as sf

from backend.analysis.audio import decode
from backend.analysis.form import suggest_sections
from backend.analysis.pipeline import analyze
from backend.analysis.melody import extract_melody
from backend.analysis.harmony import HarmonicFeatures, estimate_chart_chords
from backend.analysis.learned_harmony import align_chords, ranked_key
from backend.fixtures import make_demo
from backend.models import AnalysisOptions, Measure, Project


def test_monophonic_melody_is_extracted_from_signal():
    sr = 22050
    time = np.arange(sr * 2) / sr
    y = 0.6 * np.sin(2 * np.pi * 440 * time)
    measures = [Measure(start=0, end=2)]
    extract_melody(y, sr, 0, measures, 0.5)
    assert measures[0].notes
    assert all(n.midi == 69 for n in measures[0].notes)
    assert all(n.confidence >= 0.5 for n in measures[0].notes)


def test_known_key_overrides_inference(tmp_path):
    path = make_demo(tmp_path / "override.wav")
    project = analyze(Project(), path, tmp_path / "out.wav", AnalysisOptions(key="E", key_mode="major"))
    assert (project.key, project.key_mode, project.key_manual) == ("E", "major", True)
    assert project.key_confidence == 0


def test_single_pitch_is_unresolved_not_a_fabricated_seventh():
    chroma = np.zeros((12, 200))
    chroma[8] = 1
    features = HarmonicFeatures(chroma, np.linspace(0, 4, 200), np.ones(200), "E", "major", 0.1)
    chords = estimate_chart_chords(features, [Measure(start=0, end=4)], "E")
    assert [c.symbol for c in chords[0]] == ["?"]


def test_clear_borrowed_chord_is_not_forced_into_known_key():
    chroma = np.zeros((12, 200))
    chroma[[10, 2, 5]] = 1  # Bb major is borrowed in C, but strongly evidenced.
    features = HarmonicFeatures(chroma, np.linspace(0, 4, 200), np.ones(200), "C", "major", 0.1)
    chords = estimate_chart_chords(features, [Measure(start=0, end=4)], "C")
    assert [c.symbol for c in chords[0]] == ["Bb"]


def test_learned_harmony_preserves_inversions_and_cropped_timing():
    predictions = [
        {"start_time": 0, "end_time": 1, "chord": "F#:min/b3"},
        {"start_time": 1, "end_time": 2, "chord": "N"},
        {"start_time": 2, "end_time": 3, "chord": "A:maj/3"},
    ]
    chart = align_chords(
        predictions,
        [Measure(start=10, end=12), Measure(start=12, end=13)],
        10,
        "E",
        "major",
        np.ones(300),
        100,
    )
    assert [(c.beat, c.symbol) for c in chart[0]] == [(0, "F#m/A"), (2, "?")]
    assert [(c.beat, c.symbol) for c in chart[1]] == [(0, "A/C#")]
    assert chart[0][0].confidence is None


def test_learned_key_reports_close_relative_minor():
    tonic, mode, _, alternatives = ranked_key(
        [
            {"key": "E", "mode": "major", "score": 0.44},
            {"key": "C#", "mode": "minor", "score": 0.28},
            {"key": "B", "mode": "major", "score": 0.04},
        ]
    )
    assert (tonic, mode) == ("E", "major")
    assert [(alt.key, alt.mode) for alt in alternatives] == [("C#", "minor")]


def test_real_audio_pipeline(tmp_path):
    path = make_demo(tmp_path / "original.wav")
    p = analyze(Project(), path, tmp_path / "playback.wav", AnalysisOptions())
    assert 112 < p.bpm < 128
    assert 7 <= len(p.measures) <= 9
    assert p.source.duration == 16
    assert len(p.waveform) == 1000
    assert len(p.beats) > 25
    assert any(c.symbol.startswith("C") for c in p.measures[0].chords)
    assert any(c.symbol.startswith("D") for m in p.measures[2:4] for c in m.chords)
    assert p.meter_confidence == 0
    assert p.warnings


def test_region_and_tempo_override(tmp_path):
    path = make_demo(tmp_path / "original.wav")
    p = analyze(Project(), path, tmp_path / "play.wav", AnalysisOptions(start=4, end=12, bpm=100))
    assert p.bpm == 100
    assert p.measures[0].start == 4
    assert p.measures[-1].end == 12
    assert p.source.duration == 16


def test_form_maps_an_audio_reprise_on_the_original_timeline():
    rate = 22050
    t = np.arange(rate) / rate
    verse = sum(np.sin(2 * np.pi * pitch * t) for pitch in (130.8, 164.8, 196))
    chorus = sum(np.sin(2 * np.pi * pitch * t) for pitch in (233.08, 277.18, 349.23, 932.32))
    chorus *= 1 + 0.25 * np.cos(2 * np.pi * 24 * t)
    audio = np.concatenate([np.tile(verse, 8), np.tile(chorus, 8), np.tile(verse, 8)]).astype(np.float32)
    bars = [Measure(start=30 + i, end=31 + i) for i in range(24)]
    labels = suggest_sections(audio, rate, bars, origin=30)
    assert labels == {bars[0].id: "A", bars[8].id: "B", bars[16].id: "A"}


def test_silent_and_invalid_audio(tmp_path):
    path = tmp_path / "silent.wav"
    sf.write(path, np.zeros(22050 * 3), 22050)
    with pytest.raises(ValueError, match="silent"):
        decode(path, tmp_path / "out.wav")
    path.write_text("not audio")
    with pytest.raises(ValueError, match="decoded"):
        decode(path, tmp_path / "out.wav")


def test_research_key_model_requires_explicit_opt_in(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from backend.analysis import learned_harmony

    python = tmp_path / "key" / learned_harmony.PYTHON
    python.parent.mkdir(parents=True)
    python.touch()
    calls = []
    monkeypatch.setattr(
        learned_harmony.subprocess,
        "run",
        lambda *a, **k: calls.append(a) or SimpleNamespace(stdout='[{"key":"C"}]'),
    )
    monkeypatch.delenv("MULEC_ENABLE_RESEARCH_KEY_MODEL", raising=False)
    assert learned_harmony.predict("key", tmp_path / "audio.wav", tmp_path) is None
    assert calls == []
    monkeypatch.setenv("MULEC_ENABLE_RESEARCH_KEY_MODEL", "1")
    assert learned_harmony.predict("key", tmp_path / "audio.wav", tmp_path) == [{"key": "C"}]
    assert len(calls) == 1
