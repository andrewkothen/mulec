"""SQLite project snapshots and jobs; audio is stored outside the database."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from backend.models import Project


class ConflictError(Exception):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.audio = root / "audio"
        self.audio.mkdir(exist_ok=True)
        with self.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL, updated TEXT NOT NULL)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            for row in db.execute("SELECT id, body FROM jobs").fetchall():
                job = json.loads(row[1])
                if job["status"] in ("queued", "running"):
                    job.update(
                        status="error",
                        message="Analysis was interrupted by a server restart. Import the audio again.",
                    )
                    db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(job), row[0]))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.root / "mulec.sqlite3", timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connection() as db:
            projects = [
                json.loads(row[0]) for row in db.execute("SELECT body FROM projects ORDER BY updated DESC")
            ]
        return [
            {k: p[k] for k in ("id", "title", "composer", "bpm", "key", "updated_at", "revision")}
            | {"measures": len(p["measures"]), "duration": p["source"]["duration"]}
            for p in projects
        ]

    def get(self, project_id):
        with self.connection() as db:
            row = db.execute("SELECT body FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise KeyError(project_id)
        return Project.model_validate_json(row[0])

    def save(self, project: Project, *, new=False):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM projects WHERE id=?", (project.id,)).fetchone()
            if row and new:
                raise ConflictError("This project already exists")
            if row and json.loads(row[0])["revision"] != project.revision:
                raise ConflictError(
                    "A newer version was saved in another tab. Reload the project before saving."
                )
            copy = project.model_copy(deep=True)
            copy.revision += 1
            copy.updated_at = datetime.now(timezone.utc).isoformat()
            db.execute(
                "INSERT OR REPLACE INTO projects VALUES (?, ?, ?)",
                (copy.id, copy.model_dump_json(), copy.updated_at),
            )
        return copy

    def job(self, job_id, body=None):
        with self.connection() as db:
            if body is not None:
                db.execute("INSERT OR REPLACE INTO jobs VALUES (?, ?)", (job_id, json.dumps(body)))
                return body
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        return json.loads(row[0])
