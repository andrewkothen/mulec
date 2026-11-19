"use client";
import { useEffect, useRef, useState } from "react";
import type { VexFlowMeasure } from "opensheetmusicdisplay";
import { Project, quarters } from "@/lib/model";
import { exportBlob } from "@/lib/api";

export default function Notation({
  project,
  part,
  time,
  currentBar,
  firstBar = 1,
  rhythm = false,
}: {
  project: Project;
  part: string;
  time: number | null;
  currentBar: number;
  firstBar?: number;
  rhythm?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const position = useRef({ time, currentBar });
  const movePlayhead = useRef<(() => void) | null>(null);
  useEffect(() => {
    position.current = { time, currentBar };
    movePlayhead.current?.();
  }, [time, currentBar]);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    let resize: ResizeObserver | undefined;
    let line: SVGLineElement | undefined;
    let frame = 0;
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const [{ OpenSheetMusicDisplay, unitInPixels }, blob] =
          await Promise.all([
            import("opensheetmusicdisplay"),
            exportBlob(project, "musicxml", "letter", part, {
              rhythm,
              firstBar,
            }),
          ]);
        if (!active || !container.current) return;
        const target = container.current;
        target.replaceChildren();
        const osmd = new OpenSheetMusicDisplay(target, {
          autoResize: false,
          disableCursor: true,
          backend: "svg",
          drawingParameters: "default",
          drawTitle: false,
          drawComposer: false,
          drawPartNames: false,
          newSystemFromXML: true,
          drawMeasureNumbersOnlyAtSystemStart: true,
          useXMLMeasureNumbers: true,
        });
        osmd.EngravingRules.RehearsalMarkYOffset = 24;
        await document.fonts.load('16px "Mulec Jazz"');
        osmd.EngravingRules.DefaultFontFamily = "Mulec Jazz";
        // Keep a separate place on the staff for each bar of the recording.
        osmd.EngravingRules.AutoGenerateMultipleRestMeasuresFromRestMeasures = false;
        await osmd.load(await blob.text());
        if (!active) return;
        const playhead = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "line",
        );
        line = playhead;
        playhead.classList.add("score-playhead");
        playhead.setAttribute("aria-hidden", "true");
        let pages: SVGSVGElement[] = [];
        movePlayhead.current = () => {
          const { time, currentBar } = position.current;
          const model = project.measures[currentBar];
          const sheet = osmd.GraphicSheet;
          const measure = sheet.MeasureList[currentBar]?.[0] as
            VexFlowMeasure | undefined;
          if (time === null || !model || !measure) {
            playhead.remove();
            return;
          }
          const pageIndex = sheet.MusicPages.indexOf(
            measure.ParentMusicSystem.Parent,
          );
          const page = pages[pageIndex];
          if (!page) {
            playhead.remove();
            return;
          }
          const stave = measure.getVFStave();
          const beat =
            (Math.max(0, time - model.start) / (model.end - model.start)) *
            quarters(model.meter);
          const endX = stave.getNoteEndX();
          let previousBeat = 0;
          let previousX = stave.getNoteStartX();
          let nextBeat = quarters(model.meter);
          let nextX = endX;
          // Staff spacing varies with note and chord density. Interpolate between
          // engraved events so the playhead crosses them at their written beats.
          for (const entry of measure.staffEntries) {
            const entryBeat = entry.relInMeasureTimestamp.RealValue * 4;
            const entryX =
              entry.PositionAndShape.AbsolutePosition.x * unitInPixels;
            if (entryBeat > beat) {
              nextBeat = entryBeat;
              nextX = entryX;
              break;
            }
            previousBeat = entryBeat;
            previousX = entryX;
          }
          const progress =
            nextBeat > previousBeat
              ? (beat - previousBeat) / (nextBeat - previousBeat)
              : 0;
          const x = previousX + (nextX - previousX) * progress;
          playhead.setAttribute("x1", String(x));
          playhead.setAttribute("x2", String(x));
          playhead.setAttribute("y1", String(stave.getYForLine(0) - 7));
          playhead.setAttribute("y2", String(stave.getYForLine(4) + 7));
          playhead.dataset.bar = String(currentBar + firstBar);
          if (playhead.parentNode !== page) page.append(playhead);
        };
        let width = -1;
        const render = () => {
          const nextWidth = target.clientWidth;
          if (!active || nextWidth === 0 || nextWidth === width) return;
          width = nextWidth;
          osmd.render();
          pages = Array.from(
            target.querySelectorAll<SVGSVGElement>('svg[id^="osmdSvgPage"]'),
          );
          movePlayhead.current?.();
          setLoading(false);
        };
        render();
        resize = new ResizeObserver(() => {
          cancelAnimationFrame(frame);
          frame = requestAnimationFrame(render);
        });
        resize.observe(target);
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
      resize?.disconnect();
      cancelAnimationFrame(frame);
      line?.remove();
      movePlayhead.current = null;
    };
  }, [project, part, rhythm, firstBar]);
  return (
    <div className="notation">
      {loading && <p className="muted">Engraving your notation…</p>}
      {error && <p className="error-inline">{error}</p>}
      <div ref={container} />
    </div>
  );
}
