import numpy as np
import pytest
import soundfile as sf

from backend.analysis.audio import decode
from backend.analysis.pipeline import analyze
from backend.analysis.melody import extract_melody
from backend.analysis.harmony import HarmonicFeatures, estimate_chart_chords
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


def test_silent_and_invalid_audio(tmp_path):
    path = tmp_path / "silent.wav"
    sf.write(path, np.zeros(22050 * 3), 22050)
    with pytest.raises(ValueError, match="silent"):
        decode(path, tmp_path / "out.wav")
    path.write_text("not audio")
    with pytest.raises(ValueError, match="decoded"):
        decode(path, tmp_path / "out.wav")
