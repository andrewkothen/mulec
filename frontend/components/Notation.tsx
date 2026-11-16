"use client";
import { useEffect, useRef, useState } from "react";
import { Project } from "@/lib/model";
import { exportBlob } from "@/lib/api";
export default function Notation({
  project,
  part,
  rhythm = false,
}: {
  project: Project;
  part: string;
  rhythm?: boolean;
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
          exportBlob(project, "musicxml", "letter", part, { rhythm }),
        ]);
        if (!active || !container.current) return;
        container.current.replaceChildren();
        const osmd = new OpenSheetMusicDisplay(container.current, {
          autoResize: true,
          backend: "svg",
          drawingParameters: "default",
          drawTitle: false,
          drawComposer: false,
          drawPartNames: false,
          newSystemFromXML: true,
          drawMeasureNumbersOnlyAtSystemStart: true,
        });
        osmd.EngravingRules.RehearsalMarkYOffset = 24;
        await osmd.load(await blob.text());
        if (active) {
          osmd.render();
          setLoading(false);
        }
      } catch (e) {
        if (active) {
          container.current?.replaceChildren();
          setError(
            `The lead sheet could not be rendered. Check the key in Song & beat grid, or export MusicXML. Details: ${String(e)}`,
          );
          setLoading(false);
        }
      }
    }, 350);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [project, part, rhythm]);
  return (
    <div className="notation">
      {loading && <p className="muted">Engraving your notation…</p>}
      {error && <p className="error-inline">{error}</p>}
      <div ref={container} />
    </div>
  );
}
