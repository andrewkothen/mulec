"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AudioLines,
  Library,
  Plus,
  SlidersHorizontal,
  Music2,
  ArrowUpRight,
  Upload,
  FileMusic,
  ArrowLeft,
  Undo2,
  Redo2,
  Download,
  Save,
  ChevronRight,
  CircleHelp,
  Check,
  LoaderCircle,
  FolderOpen,
} from "lucide-react";
import { api, exportBlob, json } from "@/lib/api";
import {
  Job,
  Measure,
  Meter,
  Project,
  Summary,
  clock,
  newMeasure,
  quarters,
  regrid,
  splitMeasure,
} from "@/lib/model";
import Player from "@/components/Player";
import Notation from "@/components/Notation";
import MeasureEditor, { TextField } from "@/components/MeasureEditor";

type Tab = "library" | "new" | "editor" | "settings";
const KEYS = [
  "C",
  "C#",
  "Db",
  "D",
  "Eb",
  "E",
  "F",
  "F#",
  "Gb",
  "G",
  "G#",
  "Ab",
  "A",
  "Bb",
  "B",
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("library"),
    [library, setLibrary] = useState<Summary[]>([]);
  const [project, setProject] = useState<Project | null>(null),
    [selected, setSelected] = useState<number | null>(null);
  const [past, setPast] = useState<Project[]>([]),
    [future, setFuture] = useState<Project[]>([]),
    [dirty, setDirty] = useState(false);
  const revision = useRef(0),
    liveProject = useRef(project);
  liveProject.current = project;
  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [job, setJob] = useState<Job | null>(null);
  const [mode, setMode] = useState<"chords" | "lead" | "form">("chords"),
    [part, setPart] = useState("concert"),
    [display, setDisplay] = useState<Project | null>(null);
  const [time, setTime] = useState(0),
    [seek, setSeek] = useState<{ time: number; nonce: number } | null>(null);
  const [paper, setPaper] = useState("letter"),
    [dark, setDark] = useState(false),
    [showExport, setShowExport] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null),
    jsonInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null),
    [title, setTitle] = useState(""),
    [composer, setComposer] = useState(""),
    [reference, setReference] = useState("");
  const [regionStart, setRegionStart] = useState("0"),
    [regionEnd, setRegionEnd] = useState(""),
    [tempo, setTempo] = useState(""),
    [knownKey, setKnownKey] = useState(""),
    [knownMode, setKnownMode] = useState("major"),
    [meter, setMeter] = useState("4/4"),
    [melody, setMelody] = useState(false),
    [sensitivity, setSensitivity] = useState("0.75");
  const [gridBpm, setGridBpm] = useState("120"),
    [gridMeter, setGridMeter] = useState("4/4"),
    [gridOffset, setGridOffset] = useState("0");
  const handleError = (e: unknown) => {
    setError(e instanceof Error ? e.message : String(e));
    setBusy(false);
  };
  const refresh = useCallback(
    () =>
      api<Summary[]>("/projects")
        .then(setLibrary)
        .catch((e) => setError(e.message)),
    [],
  );
  useEffect(() => {
    void refresh();
    setDark(localStorage.getItem("mulec-dark") === "true");
    setPaper(localStorage.getItem("mulec-paper") || "letter");
  }, [refresh]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  useEffect(() => {
    const f = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [dirty]);
  useEffect(() => {
    if (project) {
      setGridBpm(String(project.bpm));
      setGridMeter(`${project.meter.numerator}/${project.meter.denominator}`);
      setGridOffset(String(project.measures[0]?.start || 0));
    }
  }, [
    project?.id,
    project?.bpm,
    project?.meter.numerator,
    project?.meter.denominator,
  ]);
  useEffect(() => {
    if (!project) {
      setDisplay(null);
      return;
    }
    if (part === "concert") {
      setDisplay(project);
      return;
    }
    let active = true;
    api<Project>(`/transpose?semitones=${part === "bb" ? 2 : 9}`, json(project))
      .then((p) => {
        if (active) setDisplay(p);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [project, part]);
  function adopt(p: Project) {
    setProject(p);
    revision.current = p.revision;
    setPast([]);
    setFuture([]);
    setDirty(false);
    setSelected(null);
    setPart("concert");
    setTab("editor");
    setTime(0);
    setError("");
  }
  async function open(id: string) {
    if (
      dirty &&
      !window.confirm("Discard unsaved edits and open another chart?")
    )
      return;
    try {
      adopt(await api<Project>(`/projects/${id}`));
    } catch (e) {
      handleError(e);
    }
  }
  function edit(p: Project) {
    if (!project) return;
    setPast((v) => [...v.slice(-79), project]);
    setFuture([]);
    setProject(p);
    setDirty(true);
    setNotice("");
  }
  function update(fn: (p: Project) => void) {
    if (!project) return;
    const copy = structuredClone(project);
    fn(copy);
    edit(copy);
  }
  function undo() {
    if (!project || !past.length) return;
    setFuture([project, ...future]);
    setProject(past[past.length - 1]);
    setPast(past.slice(0, -1));
    setDirty(true);
    setSelected(null);
  }
  function redo() {
    if (!project || !future.length) return;
    setPast([...past, project]);
    setProject(future[0]);
    setFuture(future.slice(1));
    setDirty(true);
    setSelected(null);
  }
  async function save() {
    if (!project) return;
    const snapshot = project;
    setBusy(true);
    setError("");
    try {
      const p = await api<Project>(
        `/projects/${project.id}`,
        json({ ...project, revision: revision.current }, "PUT"),
      );
      if (liveProject.current === snapshot) {
        setProject(p);
        revision.current = p.revision;
        setDirty(false);
        setNotice("Saved on this computer");
      } else if (liveProject.current?.id === p.id) {
        revision.current = p.revision;
        setProject((current) =>
          current ? { ...current, revision: p.revision } : current,
        );
        setNotice(
          "Saved earlier edits. Your newest changes are still unsaved.",
        );
      }
      await refresh();
    } catch (e) {
      handleError(e);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "error") return;
    let active = true;
    const id = setInterval(async () => {
      try {
        const next = await api<Job>(`/jobs/${job.id}`);
        if (!active) return;
        setJob(next);
        if (next.status === "done" && next.project_id) {
          const completed = await api<Project>(`/projects/${next.project_id}`);
          if (dirtyRef.current) {
            setNotice(
              "Your new transcription is ready in Library. Current unsaved edits have been kept.",
            );
          } else {
            adopt(completed);
          }
          setJob(null);
          setBusy(false);
          await refresh();
        } else if (next.status === "error") {
          setError(next.message);
          setBusy(false);
        }
      } catch (e) {
        if (active) handleError(e);
      }
    }, 1000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [job?.id, job?.status, refresh]);
  async function demo() {
    if (dirty && !window.confirm("Open a new demo and discard unsaved edits?"))
      return;
    setDirty(false);
    setBusy(true);
    setError("");
    setTab("new");
    try {
      setJob(await api<Job>("/demo", { method: "POST" }));
    } catch (e) {
      handleError(e);
    }
  }
  async function analyze(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (
      dirty &&
      !window.confirm("Start a new transcription and discard unsaved edits?")
    )
      return;
    setDirty(false);
    setBusy(true);
    setError("");
    const [numerator, denominator] = meter.split("/").map(Number);
    const form = new FormData();
    form.append("file", file);
    form.append("title", title || file.name.replace(/\.[^.]+$/, ""));
    form.append("composer", composer);
    form.append("reference", reference);
    form.append(
      "options",
      JSON.stringify({
        start: Number(regionStart),
        end: regionEnd ? Number(regionEnd) : null,
        bpm: tempo ? Number(tempo) : null,
        key: knownKey || null,
        key_mode: knownMode,
        meter: { numerator, denominator },
        melody,
        sensitivity: Number(sensitivity),
      }),
    );
    try {
      setJob(await api<Job>("/analyze", { method: "POST", body: form }));
    } catch (e) {
      handleError(e);
    }
  }
  async function download(format: string) {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const blob = await exportBlob(project, format, paper, part);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.title.replace(/[^a-zA-Z0-9 -]/g, "") || "Mulec"}-${part}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setShowExport(false);
      setNotice(`${format.toUpperCase()} exported from your current edits`);
    } catch (e) {
      handleError(e);
    } finally {
      setBusy(false);
    }
  }
  async function importProject(file: File) {
    if (
      dirty &&
      !window.confirm("Discard unsaved edits and import this chart?")
    )
      return;
    try {
      if (file.size > 10 * 1024 * 1024)
        throw new Error("Project JSON must be under 10 MB");
      adopt(
        await api<Project>("/projects/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: await file.text(),
        }),
      );
      await refresh();
    } catch (e) {
      handleError(e);
    }
  }
  function changeMeasure(m: Measure) {
    if (!project || selected === null) return;
    const prev = project.measures[selected - 1],
      next = project.measures[selected + 1];
    if (
      m.start < 0 ||
      m.end <= m.start ||
      (prev && m.start < prev.end - 0.001) ||
      (next && m.end > next.start + 0.001)
    ) {
      setError(
        "Bar times must be ordered without overlap. Use the global grid correction to shift all bars.",
      );
      return;
    }
    const q = quarters(m.meter);
    const sorted = [...m.notes].sort((a, b) => a.beat - b.beat);
    if (
      m.chords.some((c) => c.beat < 0 || c.beat >= q) ||
      new Set(m.chords.map((c) => c.beat)).size !== m.chords.length ||
      sorted.some(
        (n, i) =>
          n.midi < 0 ||
          n.midi > 127 ||
          !Number.isInteger(n.midi) ||
          n.duration <= 0 ||
          n.beat < 0 ||
          n.beat + n.duration > q ||
          (i > 0 && n.beat < sorted[i - 1].beat + sorted[i - 1].duration),
      )
    ) {
      setError(
        "Events must fit within the bar. Chord beats must be unique; melody notes cannot overlap.",
      );
      return;
    }
    setError("");
    update((p) => {
      p.measures[selected] = m;
    });
  }
  const currentBar =
    project?.measures.findIndex((m) => time >= m.start && time < m.end) ?? -1;
  const lowConfidence =
    project?.measures.reduce(
      (n, m) =>
        n + m.chords.filter((c) => !c.manual && c.confidence < 0.5).length,
      0,
    ) || 0;
  const sections =
    display?.measures.reduce<
      { name: string; start: number; count: number; chords: string[] }[]
    >((acc, m, i) => {
      if (m.section || !acc.length)
        acc.push({
          name: m.section || "Unlabeled",
          start: i,
          count: 0,
          chords: [],
        });
      const item = acc[acc.length - 1];
      item.count++;
      item.chords.push(m.chords.map((c) => c.symbol).join("  ") || "—");
      return acc;
    }, []) || [];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setTab("library");
          }}
        >
          <span className="brand-mark">
            <AudioLines size={24} />
          </span>
          mulec<span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">YOUR LOCAL STUDIO</div>
        <nav>
          {(
            [
              { id: "library", label: "Library", icon: Library },
              { id: "new", label: "New transcription", icon: Plus },
              { id: "editor", label: "Chart editor", icon: Music2 },
              { id: "settings", label: "Settings", icon: SlidersHorizontal },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "nav-item selected" : "nav-item"}
              disabled={item.id === "editor" && !project}
              onClick={() => setTab(item.id)}
            >
              <item.icon size={18} />
              {item.label}
              {item.id === "library" && (
                <span className="nav-count">{library.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-badge">
            <span /> Everything stays here
          </div>
          <p>
            Your recordings. Your computer.
            <br />
            No cloud, no account required.
          </p>
          <div className="version">
            MULEC <span>EARLY ACCESS · 0.1</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span className="breadcrumb">
            Workspace <ChevronRight size={14} />{" "}
            {tab === "library"
              ? "Library"
              : tab === "new"
                ? "New transcription"
                : tab === "settings"
                  ? "Settings"
                  : project?.title}
          </span>
          <span className="offline">
            <span /> Local processing
          </span>
        </header>
        {error && (
          <div role="alert" className="alert error">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}
        {notice && (
          <div role="status" className="alert success">
            <Check size={16} />
            {notice}
            <button
              aria-label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              ×
            </button>
          </div>
        )}
        {tab === "library" && (
          <div className="page library-page">
            <div className="page-title">
              <div>
                <div className="eyebrow">FROM RECORDING TO REHEARSAL</div>
                <h1>Your music, on the page.</h1>
                <p>Turn a recording into a chart your band can play.</p>
              </div>
              <button className="primary" onClick={() => setTab("new")}>
                <Plus size={17} /> New transcription
              </button>
            </div>
            <div className="intro-card">
              <div>
                <span className="pill">
                  A LITTLE LESS TRANSCRIBING. A LOT MORE PLAYING.
                </span>
                <h2>Listen. Refine. Rehearse.</h2>
                <p>
                  Find the pulse and harmony in your recording, make it yours in
                  the editor, and bring a clear chart to the next session.
                </p>
                <button
                  className="secondary"
                  onClick={() => void demo()}
                  disabled={busy}
                >
                  Try an original demo <ArrowUpRight size={16} />
                </button>
              </div>
              <div className="mini-score" aria-hidden="true">
                <div className="mini-title">
                  The next good idea<span>♩ = …</span>
                </div>
                <div className="mini-staff">
                  {["Listen", "Find the changes", "Make it yours", "Play"].map(
                    (x, i) => (
                      <div key={x}>
                        <small>0{i + 1}</small>
                        <strong>{x}</strong>
                        <span>／　／</span>
                      </div>
                    ),
                  )}
                </div>
                <div className="mini-footer">
                  A CHART THAT STARTS WITH YOUR RECORDING
                </div>
              </div>
            </div>
            <div className="section-heading">
              <h2>
                Recent charts <span>{library.length}</span>
              </h2>
              <button
                className="text-button"
                onClick={() => jsonInput.current?.click()}
              >
                <FolderOpen size={16} /> Import project JSON
              </button>
            </div>
            {library.length === 0 ? (
              <div className="empty-library">
                <div className="empty-icon">
                  <FileMusic size={28} />
                </div>
                <h3>Your first chart starts here</h3>
                <p>
                  Import a recording, or try the original demo to explore the
                  workspace.
                </p>
                <button className="text-button" onClick={() => setTab("new")}>
                  Import your audio <ArrowUpRight size={16} />
                </button>
              </div>
            ) : (
              <div className="chart-library">
                {library.map((p) => (
                  <button
                    className="chart-card"
                    key={p.id}
                    onClick={() => void open(p.id)}
                  >
                    <div className="card-icon">
                      <FileMusic size={24} />
                    </div>
                    <div>
                      <h3>{p.title}</h3>
                      <p>
                        {p.measures} bars <span>·</span> {p.key} <span>·</span>{" "}
                        {Math.round(p.bpm)} BPM
                      </p>
                      <small>
                        {new Date(p.updated_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}{" "}
                        · {clock(p.duration)}
                      </small>
                    </div>
                    <ArrowUpRight size={18} />
                  </button>
                ))}
              </div>
            )}
            <div className="library-note">
              <CircleHelp size={17} />
              <p>
                Good charts start with a good listen. Automatic estimates are a
                starting point; your ears make the final call.
              </p>
            </div>
          </div>
        )}
        {tab === "new" && (
          <div className="page import-page">
            <button className="text-button" onClick={() => setTab("library")}>
              <ArrowLeft size={15} /> Back to library
            </button>
            <div className="page-title">
              <div>
                <div className="eyebrow">01 / BRING YOUR MUSIC</div>
                <h1>Start with a recording.</h1>
                <p>Your audio is analyzed right here on your computer.</p>
              </div>
            </div>
            {job && job.status !== "error" ? (
              <section className="processing">
                <div className="processing-icon">
                  <AudioLines size={34} />
                </div>
                <h2>{job.message}</h2>
                <p>Local analysis may take a few minutes on the first run.</p>
                <progress max="100" value={job.progress} />
                <span>{job.progress}%</span>
                <p className="hint">
                  You can browse your library while this runs.
                </p>
              </section>
            ) : (
              <form onSubmit={(e) => void analyze(e)} className="import-form">
                <button
                  type="button"
                  className="dropzone"
                  onClick={() => fileInput.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const f = e.dataTransfer.files[0];
                    if (f) {
                      setFile(f);
                      if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
                    }
                  }}
                >
                  <span className="upload-icon">
                    <Upload size={25} />
                  </span>
                  <strong>{file ? file.name : "Drop a recording here"}</strong>
                  <span>
                    {file
                      ? `${(file.size / 1024 / 1024).toFixed(1)} MB · Click to choose a different file`
                      : "or click to browse your files"}
                  </span>
                  <small>
                    WAV, MP3, FLAC, M4A, OGG, AIFF · up to 150 MB / 15 minutes
                  </small>
                </button>
                <input
                  ref={fileInput}
                  type="file"
                  accept=".wav,.mp3,.flac,.m4a,.ogg,.aiff,.aif"
                  className="sr-only"
                  aria-label="Audio recording"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setFile(f);
                      if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
                    }
                  }}
                />
                <div className="field-pair">
                  <label>
                    Song title
                    <input
                      value={title}
                      maxLength={160}
                      placeholder="An idea worth playing"
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </label>
                  <label>
                    Composer / artist <span>optional</span>
                    <input
                      value={composer}
                      maxLength={160}
                      placeholder="Your name or band"
                      onChange={(e) => setComposer(e.target.value)}
                    />
                  </label>
                </div>
                <label>
                  YouTube or Bandcamp reference <span>optional</span>
                  <input
                    type="url"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="https://…"
                  />
                </label>
                <p className="hint">
                  Reference links stay with your chart. Import a local audio
                  file you’re authorized to use; Mulec does not download from
                  these platforms.
                </p>
                <details className="analysis-options">
                  <summary>
                    Analysis options <span>region, tempo, meter & melody</span>
                  </summary>
                  <div className="field-pair">
                    <label>
                      Known key
                      <select
                        value={knownKey}
                        onChange={(e) => setKnownKey(e.target.value)}
                      >
                        <option value="">Estimate automatically</option>
                        {KEYS.map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Known key mode
                      <select
                        value={knownMode}
                        disabled={!knownKey}
                        onChange={(e) => setKnownMode(e.target.value)}
                      >
                        <option value="major">Major</option>
                        <option value="minor">Minor</option>
                      </select>
                    </label>
                    <label>
                      Region start (seconds)
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        value={regionStart}
                        onChange={(e) => setRegionStart(e.target.value)}
                      />
                    </label>
                    <label>
                      Region end (seconds)
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        value={regionEnd}
                        placeholder="End of recording"
                        onChange={(e) => setRegionEnd(e.target.value)}
                      />
                    </label>
                    <label>
                      Tempo override (BPM)
                      <input
                        type="number"
                        min="30"
                        max="300"
                        value={tempo}
                        onChange={(e) => setTempo(e.target.value)}
                        placeholder="Detect automatically"
                      />
                    </label>
                    <label>
                      Time signature
                      <select
                        value={meter}
                        onChange={(e) => setMeter(e.target.value)}
                      >
                        {[
                          "4/4",
                          "3/4",
                          "2/4",
                          "5/4",
                          "6/8",
                          "7/8",
                          "9/8",
                          "12/8",
                        ].map((x) => (
                          <option key={x}>{x}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={melody}
                      onChange={(e) => setMelody(e.target.checked)}
                    />{" "}
                    Experimental melody guide (up to 2 minutes)
                  </label>
                  {melody && (
                    <label>
                      Voicing confidence threshold
                      <select
                        value={sensitivity}
                        onChange={(e) => setSensitivity(e.target.value)}
                      >
                        <option value="0.5">Sensitive — more notes</option>
                        <option value="0.75">Balanced</option>
                        <option value="0.9">Conservative — fewer notes</option>
                      </select>
                    </label>
                  )}
                  <p className="hint">
                    Melody works best on a single voice or instrument. Meter is
                    an assumption you can correct. No genre or song form is
                    imposed.
                  </p>
                </details>
                <div className="import-footer">
                  <span>
                    <AudioLines size={16} /> 100% local analysis
                  </span>
                  <button
                    className="primary"
                    type="submit"
                    disabled={!file || busy}
                  >
                    {busy ? (
                      <LoaderCircle size={17} className="spin" />
                    ) : (
                      <Music2 size={17} />
                    )}{" "}
                    Analyze recording
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
        {tab === "editor" && project && display && (
          <div className="editor-page">
            <div className="editor-title">
              <div>
                <div className="eyebrow">CHART WORKSPACE</div>
                <h1>{project.title}</h1>
                <span className="save-state">
                  {dirty ? "Unsaved edits" : "Saved locally"} <span>·</span>{" "}
                  {project.measures.length} bars
                </span>
              </div>
              <div className="editor-toolbar">
                <button
                  className="icon"
                  aria-label="Undo"
                  disabled={!past.length}
                  onClick={undo}
                >
                  <Undo2 size={18} />
                </button>
                <button
                  className="icon"
                  aria-label="Redo"
                  disabled={!future.length}
                  onClick={redo}
                >
                  <Redo2 size={18} />
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => void save()}
                >
                  <Save size={16} /> Save
                </button>
                <div className="export-menu">
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => setShowExport(!showExport)}
                  >
                    <Download size={16} /> Export
                  </button>
                  {showExport && (
                    <div className="dropdown">
                      <span>
                        {part === "concert"
                          ? "Concert pitch"
                          : part === "bb"
                            ? "B-flat part"
                            : "E-flat part"}{" "}
                        · {paper.toUpperCase()}
                      </span>
                      {[
                        { id: "pdf", label: "Printable chord chart · PDF" },
                        { id: "musicxml", label: "Notation · MusicXML" },
                        { id: "midi", label: "Melody · MIDI" },
                        { id: "json", label: "Project · JSON" },
                      ].map((f) => (
                        <button
                          key={f.id}
                          disabled={
                            f.id === "midi" &&
                            !project.measures.some((m) => m.notes.length)
                          }
                          onClick={() => void download(f.id)}
                        >
                          {f.label}
                          <ArrowUpRight size={14} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="workspace">
              <aside className="audio-panel">
                <Player project={project} seek={seek} onTime={setTime} />
                <div className="analysis-summary">
                  <div className="eyebrow">THE FIRST LISTEN</div>
                  <div className="stat-row">
                    <div>
                      <strong>{Math.round(project.bpm)}</strong>
                      <span>
                        BPM · {Math.round(project.tempo_confidence * 100)}%
                        confidence
                      </span>
                    </div>
                    <div>
                      <strong>
                        {project.key}
                        <small>{project.key_mode === "minor" ? "m" : ""}</small>
                      </strong>
                      <span>
                        {project.key_manual
                          ? "key set by you"
                          : "estimated key · review"}
                      </span>
                    </div>
                    <div>
                      <strong>
                        {project.meter.numerator}/{project.meter.denominator}
                      </strong>
                      <span>selected meter</span>
                    </div>
                  </div>
                  <div className="review-note">
                    <span className="confidence-dot" />
                    <p>
                      {lowConfidence
                        ? `${lowConfidence} chord estimates to review`
                        : "Listen through and review the chart"}
                      <small>Amber dots mark uncertain harmony.</small>
                    </p>
                  </div>
                </div>
                {selected !== null && project.measures[selected] ? (
                  <MeasureEditor
                    key={project.measures[selected].id}
                    measure={project.measures[selected]}
                    index={selected}
                    onChange={changeMeasure}
                    onClose={() => setSelected(null)}
                    onDelete={() => {
                      update((p) => {
                        p.measures.splice(selected, 1);
                      });
                      setSelected(null);
                    }}
                    onSplit={() => {
                      try {
                        const parts = splitMeasure(project.measures[selected]);
                        update((p) => {
                          p.measures.splice(selected, 1, ...parts);
                        });
                      } catch (e) {
                        handleError(e);
                      }
                    }}
                  />
                ) : (
                  <div className="edit-tip">
                    <Music2 size={22} />
                    <h3>Make the chart yours.</h3>
                    <p>
                      Select a bar to correct chords, add a rehearsal cue, or
                      edit melody notes.
                    </p>
                  </div>
                )}
                <details className="inspector-details">
                  <summary>Song & beat grid</summary>
                  <TextField
                    label="Title"
                    value={project.title}
                    onChange={(v) => {
                      if (v.trim())
                        update((p) => {
                          p.title = v;
                        });
                    }}
                  />
                  <TextField
                    label="Composer / artist"
                    value={project.composer}
                    onChange={(v) =>
                      update((p) => {
                        p.composer = v;
                      })
                    }
                  />
                  <div className="field-pair">
                    <label>
                      Key signature
                      <select
                        value={project.key}
                        onChange={(e) =>
                          update((p) => {
                            p.key = e.target.value;
                            p.key_manual = true;
                          })
                        }
                      >
                        {KEYS.map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Mode
                      <select
                        value={project.key_mode}
                        onChange={(e) =>
                          update((p) => {
                            p.key_mode = e.target.value as Project["key_mode"];
                            p.key_manual = true;
                          })
                        }
                      >
                        <option value="major">Major</option>
                        <option value="minor">Minor</option>
                      </select>
                    </label>
                  </div>
                  <p className="hint">
                    Your key setting overrides the estimate. It does not
                    reanalyze chords or transpose pitches. Use Transpose below
                    to move the music.
                  </p>
                  <label>
                    Feel
                    <select
                      value={project.feel}
                      onChange={(e) =>
                        update((p) => {
                          p.feel = e.target.value as Project["feel"];
                        })
                      }
                    >
                      <option value="unspecified">Unspecified</option>
                      <option value="straight">Straight</option>
                      <option value="swing">Swing</option>
                    </select>
                  </label>
                  <div className="field-pair">
                    <label>
                      BPM
                      <input
                        type="number"
                        min="30"
                        max="300"
                        value={gridBpm}
                        onChange={(e) => setGridBpm(e.target.value)}
                      />
                    </label>
                    <label>
                      Meter
                      <select
                        value={gridMeter}
                        onChange={(e) => setGridMeter(e.target.value)}
                      >
                        {[
                          "4/4",
                          "3/4",
                          "2/4",
                          "5/4",
                          "6/8",
                          "7/8",
                          "9/8",
                          "12/8",
                        ].map((m) => (
                          <option key={m}>{m}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <label>
                    First bar start (seconds)
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={gridOffset}
                      onChange={(e) => setGridOffset(e.target.value)}
                    />
                  </label>
                  <button
                    className="secondary small full"
                    onClick={() => {
                      try {
                        const [n, d] = gridMeter.split("/").map(Number);
                        edit(
                          regrid(
                            project,
                            Number(gridBpm),
                            {
                              numerator: n,
                              denominator: d as Meter["denominator"],
                            },
                            Number(gridOffset),
                          ),
                        );
                      } catch (e) {
                        handleError(e);
                      }
                    }}
                  >
                    Apply uniform beat grid
                  </button>
                  <p className="hint">
                    Replaces timing and meter across all bars, keeping musical
                    events. Undo is available.
                  </p>
                  <label>
                    Transpose music
                    <select
                      defaultValue=""
                      onChange={async (e) => {
                        const value = e.target.value;
                        e.target.value = "";
                        if (!value) return;
                        try {
                          edit(
                            await api<Project>(
                              `/transpose?semitones=${value}`,
                              json(project),
                            ),
                          );
                        } catch (error) {
                          handleError(error);
                        }
                      }}
                    >
                      <option value="">Choose interval…</option>
                      {Array.from({ length: 25 }, (_, i) => i - 12)
                        .filter((n) => n !== 0)
                        .map((n) => (
                          <option key={n} value={n}>
                            {n > 0 ? "+" : ""}
                            {n} semitones
                          </option>
                        ))}
                    </select>
                  </label>
                </details>
                <details className="inspector-details">
                  <summary>Analysis notes</summary>
                  {project.warnings.map((w, i) => (
                    <p className="hint" key={i}>
                      {w}
                    </p>
                  ))}
                  {project.form_suggestions.map((w, i) => (
                    <p className="hint" key={`f${i}`}>
                      {w}
                    </p>
                  ))}
                </details>
              </aside>
              <section className="chart-panel">
                <div className="chart-controls">
                  <div className="segmented">
                    {(["chords", "lead", "form"] as const).map((m) => (
                      <button
                        key={m}
                        className={mode === m ? "active" : ""}
                        onClick={() => setMode(m)}
                      >
                        {m === "chords"
                          ? "Chord chart"
                          : m === "lead"
                            ? "Lead sheet"
                            : "Form"}
                      </button>
                    ))}
                  </div>
                  <select
                    aria-label="Instrument part"
                    value={part}
                    onChange={(e) => setPart(e.target.value)}
                  >
                    <option value="concert">Concert pitch</option>
                    <option value="bb">B♭ instrument (+2)</option>
                    <option value="eb">E♭ instrument (+9)</option>
                  </select>
                </div>
                <div className="paper">
                  {lowConfidence >
                    project.measures.reduce((n, m) => n + m.chords.length, 0) /
                      2 && (
                    <p className="harmony-warning" role="note">
                      Harmony needs substantial review. These are uncertain
                      estimates, not a verified transcription. “?” means
                      unresolved harmony.
                    </p>
                  )}
                  <div className="paper-kicker">
                    {mode === "lead"
                      ? "LEAD SHEET"
                      : mode === "form"
                        ? "REHEARSAL ROADMAP"
                        : "RHYTHM SECTION CHART"}
                    <span>
                      {part === "concert"
                        ? "CONCERT"
                        : part === "bb"
                          ? "B♭ PART"
                          : "E♭ PART"}
                    </span>
                  </div>
                  <h2>{display.title}</h2>
                  <div className="paper-meta">
                    <span>{display.composer || "Original recording"}</span>
                    <span>
                      {display.key} {display.key_mode} ·{" "}
                      {display.meter.numerator}/{display.meter.denominator} · ♩
                      = {Math.round(display.bpm)}
                    </span>
                  </div>
                  {mode === "lead" ? (
                    <>
                      <p className="hint">
                        {project.measures.some((m) => m.notes.length)
                          ? "Edit notes by selecting a bar in Chord chart. Export MusicXML for full notation; PDF export is a chord chart."
                          : "No melody yet. Add notes in a bar’s editor, or analyze a short region with the experimental melody option."}
                      </p>
                      <Notation project={project} part={part} />
                    </>
                  ) : mode === "form" ? (
                    <div className="form-chart">
                      {sections.map((s, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setSelected(s.start);
                            setMode("chords");
                            setSeek({
                              time: project.measures[s.start].start,
                              nonce: Date.now(),
                            });
                          }}
                        >
                          <span className="section-box">{s.name}</span>
                          <div>
                            <strong>{s.count} bars</strong>
                            <small>
                              Bars {s.start + 1}–{s.start + s.count}
                            </small>
                            <p>{s.chords.join("  |  ")}</p>
                          </div>
                          <ArrowUpRight size={17} />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="measures">
                      {display.measures.map((m, i) => (
                        <div
                          key={m.id}
                          className={`measure-wrap ${m.section ? "section-start" : ""}`}
                        >
                          {m.section && (
                            <div className="rehearsal-mark">{m.section}</div>
                          )}
                          <button
                            aria-label={`Bar ${i + 1}: ${m.chords.map((c) => c.symbol).join(", ") || "empty"}`}
                            className={`measure ${selected === i ? "chosen" : ""} ${currentBar === i ? "playing" : ""}`}
                            onClick={() => {
                              setSelected(i);
                              setSeek({
                                time: project.measures[i].start,
                                nonce: Date.now(),
                              });
                            }}
                          >
                            <span className="bar-number">{i + 1}</span>
                            <span className="repeat-mark">
                              {m.repeat_start ? "|: " : ""}
                              {m.repeat_end ? " :|" : ""}
                            </span>
                            <span className="chord-events">
                              {m.chords.length ? (
                                m.chords.map((c) => (
                                  <span className="chord-event" key={c.id}>
                                    <strong>{c.symbol}</strong>
                                    <small>
                                      {c.beat + 1}
                                      {!c.manual && c.confidence < 0.5 && (
                                        <i
                                          title={`Confidence ${Math.round(c.confidence * 100)}%`}
                                        />
                                      )}
                                    </small>
                                  </span>
                                ))
                              ) : (
                                <span className="empty-bar">＋</span>
                              )}
                            </span>
                            {m.cue ? (
                              <span className="cue">{m.cue}</span>
                            ) : (
                              <span
                                className="rhythm-slashes"
                                aria-hidden="true"
                              >
                                ／　／　／　／
                              </span>
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="paper-footer">
                    <span>MULEC</span>
                    <span>
                      {part === "concert"
                        ? "Made for the next rehearsal."
                        : "Editing uses concert pitch. Preview and exports are transposed."}
                    </span>
                  </div>
                </div>
                {mode === "chords" && (
                  <button
                    className="add-measure"
                    onClick={() =>
                      update((p) => {
                        p.measures.push(
                          newMeasure(
                            p.measures.at(-1)?.end || 0,
                            p.bpm,
                            p.meter,
                          ),
                        );
                      })
                    }
                  >
                    <Plus size={15} /> Add measure
                  </button>
                )}
              </section>
            </div>
          </div>
        )}
        {tab === "settings" && (
          <div className="page settings-page">
            <div className="eyebrow">YOUR WORKSPACE</div>
            <h1>A few things, your way.</h1>
            <div className="settings-card">
              <h3>Reading & printing</h3>
              <label>
                Paper size
                <select
                  value={paper}
                  onChange={(e) => {
                    setPaper(e.target.value);
                    localStorage.setItem("mulec-paper", e.target.value);
                  }}
                >
                  <option value="letter">US Letter</option>
                  <option value="a4">A4</option>
                </select>
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={dark}
                  onChange={(e) => {
                    setDark(e.target.checked);
                    localStorage.setItem(
                      "mulec-dark",
                      String(e.target.checked),
                    );
                  }}
                />{" "}
                Dark workspace chrome
              </label>
              <p className="hint">
                The chart stays light for comfortable music reading.
              </p>
            </div>
            <div className="settings-card">
              <h3>Local by design</h3>
              <p>
                Audio, analysis and projects stay on this computer. Projects are
                stored in the app’s data folder using SQLite; audio is stored
                alongside it.
              </p>
              <p>
                Back up the entire data folder to preserve recordings. JSON
                exports carry notation and metadata, without audio.
              </p>
              <h4>What to expect from the first version</h4>
              <p>
                Beat and harmony estimates help you start a chart. Complex mixes
                need correction. Meter and downbeat placement need review.
                Melody is experimental; form suggestions only flag repeated
                chord patterns.
              </p>
              <p>
                PDF export creates a chord chart. MusicXML carries melody,
                rests, harmony, repeats and rehearsal marks to a notation
                editor.
              </p>
            </div>
          </div>
        )}
        <input
          className="sr-only"
          ref={jsonInput}
          type="file"
          accept=".json"
          aria-label="Import project JSON"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void importProject(f);
            e.target.value = "";
          }}
        />
      </main>
    </div>
  );
}
