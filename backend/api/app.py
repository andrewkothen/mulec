from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.analysis.pipeline import analyze
from backend.fixtures import make_demo
from backend.models import AnalysisOptions, Project, Source, uid
from backend.music import export
from backend.music.theory import chord_object, pitch_class, transpose_project
from backend.storage import ConflictError, Store

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 150 * 1024 * 1024
logger = logging.getLogger("mulec")


def validate_music(project):
    pitch_class(project.key)
    if project.source.reference_url:
        reference_url(project.source.reference_url)
    for measure in project.measures:
        for chord in measure.chords:
            chord_object(chord.symbol)


def reference_url(value):
    if not value:
        return value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password or not (
        host in {"youtube.com", "www.youtube.com", "youtu.be", "music.youtube.com", "bandcamp.com"}
        or host.endswith(".bandcamp.com")
    ):
        raise ValueError("Reference links must be HTTPS YouTube or Bandcamp URLs")
    return value


def create_app(data_dir: Path | None = None):
    store = Store(data_dir or Path(os.environ.get("MULEC_DATA_DIR", ROOT / "data")))
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mulec-analysis")
    slots = BoundedSemaphore(2)

    @asynccontextmanager
    async def lifespan(app):
        yield
        executor.shutdown(wait=True)

    app = FastAPI(title="Mulec", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in {"http://127.0.0.1:8765", "http://localhost:8765", "http://localhost:3000", "http://127.0.0.1:3000"}:
            return JSONResponse({"detail": "Only the local Mulec application may access this API"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Project or job not found"}, status_code=404)

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "name": "Mulec", "local_only": True}

    @app.get("/api/projects")
    def projects():
        return store.list()

    @app.get("/api/projects/{project_id}")
    def project(project_id: str):
        return store.get(project_id)

    @app.put("/api/projects/{project_id}")
    def save(project_id: str, body: Project):
        original = store.get(project_id)
        if body.id != project_id:
            raise HTTPException(422, "Project identity cannot change")
        if body.source != original.source:
            raise HTTPException(422, "Source metadata is immutable; import a new project to change the audio")
        validate_music(body)
        return store.save(body)

    @app.post("/api/projects/import")
    async def import_json(request: Request):
        chunks, length = [], 0
        async for chunk in request.stream():
            length += len(chunk)
            if length > 10 * 1024 * 1024:
                raise HTTPException(413, "Project JSON must be under 10 MB")
            chunks.append(chunk)
        project = Project.model_validate_json(b"".join(chunks))
        validate_music(project)
        project.id, project.revision = uid(), 0
        project.warnings.append("Imported JSON contains notation only. Original audio is not included in project exports.")
        project.warnings = project.warnings[-30:]
        return store.save(project, new=True)

    def run_job(job_id, project, path, options):
        def progress(percent, message):
            store.job(job_id, {"id": job_id, "status": "running", "progress": percent, "message": message})
        try:
            result = analyze(project, path, store.audio / f"{project.id}.wav", options, progress)
            store.save(result, new=True)
            store.job(job_id, {"id": job_id, "status": "done", "progress": 100, "project_id": project.id,
                               "message": "Chart ready for review"})
        except Exception as exc:
            logger.exception("Local analysis failed")
            message = str(exc) if isinstance(exc, ValueError) else "Analysis failed. Try a shorter WAV file; details are in the local server log."
            store.job(job_id, {"id": job_id, "status": "error", "progress": 0, "message": message})
            (store.audio / f"{project.id}.wav").unlink(missing_ok=True)
        finally:
            path.unlink(missing_ok=True)
            slots.release()

    @app.post("/api/analyze", status_code=202)
    async def upload(file: UploadFile = File(...), options: str = Form("{}"),
                     title: str = Form(""), composer: str = Form(""), reference: str = Form("")):
        try:
            settings = AnalysisOptions.model_validate_json(options)
            reference_url(reference)
            name = Path(file.filename or "audio").name
            project = Project(title=title or Path(name).stem, composer=composer,
                              source=Source(filename=name, reference_url=reference))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if Path(name).suffix.lower() not in {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aiff", ".aif"}:
            raise HTTPException(422, "Supported formats: WAV, FLAC, MP3, M4A, OGG and AIFF")
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Two analyses are already queued. Wait for one to finish.")
        path = store.audio / f"{project.id}.upload"
        try:
            size = 0
            with path.open("wb") as dest:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413, "Audio uploads are limited to 150 MB")
                    dest.write(chunk)
            job_id = uid()
            job = store.job(job_id, {"id": job_id, "status": "queued", "progress": 0, "message": "Waiting for local analysis"})
            executor.submit(run_job, job_id, project, path, settings)
            return job
        except BaseException:
            path.unlink(missing_ok=True)
            slots.release()
            raise
        finally:
            await file.close()

    @app.post("/api/demo", status_code=202)
    def demo():
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Wait for the current analyses to finish")
        project = Project(title="Sunday Sketch", composer="Mulec original test fixture · CC0",
                          source=Source(filename="sunday-sketch.wav"))
        path = store.audio / f"{project.id}.upload"
        try:
            make_demo(path.with_suffix(".wav"))
            path.with_suffix(".wav").rename(path)
            job_id = uid()
            job = store.job(job_id, {"id": job_id, "status": "queued", "progress": 0, "message": "Analyzing original demo audio"})
            executor.submit(run_job, job_id, project, path, AnalysisOptions())
            return job
        except BaseException:
            slots.release()
            raise

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return store.job(job_id)

    @app.get("/api/projects/{project_id}/audio")
    def audio(project_id: str):
        project = store.get(project_id)
        path = store.audio / f"{project.id}.wav"
        if not path.exists():
            raise HTTPException(404, "No audio is attached to this imported chart")
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/transpose")
    def transpose(body: Project, semitones: int = 0):
        if not -24 <= semitones <= 24:
            raise HTTPException(422, "Choose a transposition between -24 and 24 semitones")
        validate_music(body)
        return transpose_project(body, semitones)

    @app.post("/api/export/{format}")
    def export_project(format: str, body: Project, paper: str = "letter", part: str = "concert"):
        validate_music(body)
        if paper not in ("letter", "a4") or part not in ("concert", "bb", "eb"):
            raise HTTPException(422, "Unsupported paper size or instrument part")
        semitones = {"concert": 0, "bb": 2, "eb": 9}[part]
        project = transpose_project(body, semitones) if semitones else body
        if format == "musicxml":
            content, mime = export.musicxml(project), "application/vnd.recordare.musicxml+xml"
        elif format == "pdf":
            content, mime = export.pdf(project, paper, {"concert": "Concert pitch", "bb": "Bb instrument", "eb": "Eb instrument"}[part]), "application/pdf"
        elif format == "midi":
            content, mime = export.midi_bytes(project), "audio/midi"
        elif format == "json":
            content, mime = json.dumps(project.model_dump(), indent=2).encode(), "application/json"
        else:
            raise HTTPException(404, "Unknown export format")
        return Response(content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="mulec-chart.{format}"'})

    frontend = ROOT / "frontend" / "out"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
