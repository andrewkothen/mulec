import numpy as np
import pytest
import soundfile as sf

from backend.analysis.audio import decode
from backend.analysis.pipeline import analyze
from backend.fixtures import make_demo
from backend.models import AnalysisOptions, Project


def test_real_audio_pipeline(tmp_path):
    path=make_demo(tmp_path/"original.wav")
    p=analyze(Project(),path,tmp_path/"playback.wav",AnalysisOptions())
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
    path=make_demo(tmp_path/"original.wav")
    p=analyze(Project(),path,tmp_path/"play.wav",AnalysisOptions(start=4,end=12,bpm=100))
    assert p.bpm == 100
    assert p.measures[0].start == 4
    assert p.measures[-1].end == 12
    assert p.source.duration == 16


def test_silent_and_invalid_audio(tmp_path):
    path=tmp_path/"silent.wav"
    sf.write(path,np.zeros(22050*3),22050)
    with pytest.raises(ValueError,match="silent"):
        decode(path,tmp_path/"out.wav")
    path.write_text("not audio")
    with pytest.raises(ValueError,match="decoded"):
        decode(path,tmp_path/"out.wav")
