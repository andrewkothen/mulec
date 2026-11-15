"use client";
import { useEffect, useRef, useState } from "react";
import { Project } from "@/lib/model";
import { exportBlob } from "@/lib/api";
export default function Notation({
  project,
  part,
}: {
  project: Project;
  part: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const [{ OpenSheetMusicDisplay }, blob] = await Promise.all([
          import("opensheetmusicdisplay"),
          exportBlob(project, "musicxml", "letter", part),
        ]);
        if (!active || !container.current) return;
        container.current.replaceChildren();
        const osmd = new OpenSheetMusicDisplay(container.current, {
          autoResize: true,
          backend: "svg",
          drawingParameters: "default",
          drawTitle: false,
          drawComposer: false,
        });
        await osmd.load(await blob.text());
        if (active) {
          osmd.render();
          setLoading(false);
        }
      } catch (e) {
        if (active) {
          setError(String(e));
          setLoading(false);
        }
      }
    }, 350);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [project, part]);
  return (
    <div className="notation">
      {loading && <p className="muted">Engraving your notation…</p>}
      {error && <p className="error-inline">{error}</p>}
      <div ref={container} />
    </div>
  );
}
