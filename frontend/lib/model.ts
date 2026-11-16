export type Meter = { numerator: number; denominator: 2 | 4 | 8 | 16 };
export type Chord = {
  id: string;
  beat: number;
  symbol: string;
  confidence: number;
  manual: boolean;
};
export type Note = {
  id: string;
  beat: number;
  duration: number;
  midi: number;
  confidence: number;
  manual: boolean;
};
export type Measure = {
  id: string;
  start: number;
  end: number;
  meter: Meter;
  chords: Chord[];
  notes: Note[];
  section: string;
  cue: string;
  repeat_start: boolean;
  repeat_end: boolean;
};
export type Project = {
  schema_version: 1;
  id: string;
  revision: number;
  title: string;
  composer: string;
  source: {
    filename: string;
    reference_url: string;
    duration: number;
    sample_rate: number;
  };
  bpm: number;
  tempo_confidence: number;
  tempo_map: { time: number; bpm: number }[];
  key: string;
  key_mode: "major" | "minor";
  key_confidence: number;
  key_manual?: boolean;
  feel: "straight" | "swing" | "unspecified";
  meter: Meter;
  meter_confidence: number;
  beats: number[];
  measures: Measure[];
  waveform: number[];
  warnings: string[];
  form_suggestions: string[];
  updated_at: string;
};
export type Summary = Pick<
  Project,
  "id" | "title" | "composer" | "bpm" | "key" | "updated_at" | "revision"
> & { measures: number; duration: number };
export type Job = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  project_id?: string;
};
export const quarters = (meter: Meter) =>
  (meter.numerator * 4) / meter.denominator;
export const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0")}`;
export const newMeasure = (
  start: number,
  bpm: number,
  meter: Meter,
): Measure => ({
  id: crypto.randomUUID(),
  start,
  end: start + (quarters(meter) * 60) / bpm,
  meter: { ...meter },
  chords: [],
  notes: [],
  section: "",
  cue: "",
  repeat_start: false,
  repeat_end: false,
});

export function splitMeasure(measure: Measure): Measure[] {
  if (measure.meter.numerator % 2)
    throw new Error(
      "Split currently requires an even meter numerator, such as 4/4 or 6/8.",
    );
  const half = quarters(measure.meter) / 2;
  const mid = (measure.start + measure.end) / 2;
  const a = structuredClone(measure),
    b = structuredClone(measure);
  a.meter.numerator /= 2;
  b.meter.numerator /= 2;
  a.end = mid;
  a.repeat_end = false;
  b.id = crypto.randomUUID();
  b.start = mid;
  b.section = "";
  b.cue = "";
  b.repeat_start = false;
  a.chords = a.chords.filter((c) => c.beat < half);
  b.chords = b.chords
    .filter((c) => c.beat >= half)
    .map((c) => ({ ...c, beat: c.beat - half }));
  if (!b.chords.some((c) => c.beat === 0)) {
    const prior = [...a.chords].sort((x, y) => y.beat - x.beat)[0];
    if (prior) b.chords.unshift({ ...prior, id: crypto.randomUUID(), beat: 0 });
  }
  a.notes = a.notes
    .filter((n) => n.beat < half)
    .map((n) => ({ ...n, duration: Math.min(n.duration, half - n.beat) }));
  b.notes = b.notes
    .filter((n) => n.beat + n.duration > half)
    .map((n) => ({
      ...n,
      id: crypto.randomUUID(),
      beat: Math.max(0, n.beat - half),
      duration: n.duration - Math.max(0, half - n.beat),
    }));
  return [a, b];
}

export function regrid(
  project: Project,
  bpm: number,
  meter: Meter,
  offset: number,
): Project {
  if (
    !Number.isFinite(bpm) ||
    bpm < 30 ||
    bpm > 300 ||
    !Number.isFinite(offset) ||
    offset < 0
  )
    throw new Error("Use 30–300 BPM and a nonnegative start time.");
  const q = quarters(meter);
  if (
    project.measures.some(
      (m) =>
        m.chords.some((c) => c.beat >= q) ||
        m.notes.some((n) => n.beat + n.duration > q),
    )
  )
    throw new Error(
      "Some events would fall outside this meter. Move or remove those events before changing the grid.",
    );
  const copy = structuredClone(project);
  copy.bpm = bpm;
  copy.meter = { ...meter };
  copy.tempo_map = [{ time: offset, bpm }];
  copy.measures = copy.measures.map((m, i) => ({
    ...m,
    meter: { ...meter },
    start: offset + (i * q * 60) / bpm,
    end: offset + ((i + 1) * q * 60) / bpm,
  }));
  copy.beats = Array.from(
    { length: Math.ceil(copy.measures.length * q) },
    (_, i) => offset + (i * 60) / bpm,
  );
  return copy;
}
