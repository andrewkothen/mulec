"use client";

import { useEffect, useState } from "react";
import { api, json } from "@/lib/api";
import { clock, type Chord, type Measure, type Project } from "@/lib/model";
import type { SongSection } from "@/lib/form";

type Part = {
  id: string;
  name: string;
  variant: number;
  ending: boolean;
  from_bar: number;
  length: number;
  blocks: {
    first: number;
    times: number;
    reference?: {
      name: string;
      variant: number;
      first: number;
      length: number;
    };
    bars: (Omit<Measure, "chords"> & {
      chords: (Chord & { display: string })[];
    })[];
  }[];
};
type Plan = {
  parts: Part[];
  order: {
    id: string;
    part: string;
    name: string;
    variant: number;
    first: number;
    end: number;
    time: number;
  }[];
  written_bars: number;
  total_bars: number;
};

export default function Arrangement({
  project,
  part,
  condensed,
  active,
  onSelect,
}: {
  project: Project;
  part: string;
  condensed: boolean;
  active?: SongSection;
  onSelect: (section: SongSection) => void;
}) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    setError("");
    api<Plan>(`/arrangement?part=${part}&condensed=${condensed}`, json(project))
      .then((result) => {
        if (alive) setPlan(result);
      })
      .catch((e) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [project, part, condensed]);
  if (error) return <p className="error-inline">{error}</p>;
  if (!plan) return <p className="hint">Building the arrangement…</p>;
  return (
    <div
      className={`arrangement${condensed ? " is-condensed" : ""}`}
      aria-label="Compact arrangement"
    >
      <p className="hint arrangement-count">
        {condensed && "Condensed · "}
        {plan.written_bars} written bars · {plan.total_bars} bars in the
        recording
        {plan.parts.some((p) => p.variant > 0) &&
          " · * different ending or variation"}
      </p>
      {condensed && (
        <p className="hint">
          Shorter musical bars, with staff lines and rhythm slashes. Exact
          repeated phrases use references; changed material stays written out.
        </p>
      )}
      <ol className="arrangement-order" aria-label="Arrangement order">
        {plan.order.map((step) => (
          <li key={step.id}>
            <button
              aria-current={step.id === active?.id ? "step" : undefined}
              onClick={() =>
                onSelect({
                  ...step,
                  label: step.name,
                  group: step.name.toLowerCase(),
                })
              }
            >
              {step.name}
              {step.variant > 0 ? ` *${step.variant}` : ""}
              <small>{clock(step.time)}</small>
            </button>
          </li>
        ))}
      </ol>
      <p className="arrangement-legend">
        △ major · - minor · ×4 = four total passes · small numbers = beats
      </p>
      <div className="arrangement-parts">
        {plan.parts.map((piece) => {
          const times = plan.order.filter((step) => step.part === piece.id);
          const allBars = piece.blocks.flatMap((block) => block.bars);
          return (
            <section
              className="arrangement-part"
              key={piece.id}
              aria-label={`Part ${piece.name}`}
            >
              <div className="arrangement-heading">
                <h3>
                  {piece.name}
                  {piece.variant > 0 ? ` *${piece.variant}` : ""}
                </h3>
                <span>
                  {piece.ending
                    ? `Changed ending from bar ${piece.from_bar}`
                    : `${piece.length} bars`}
                </span>
                <span>{times.map((step) => clock(step.time)).join(" · ")}</span>
              </div>
              <div className="arrangement-bars">
                {piece.blocks.flatMap((block) =>
                  block.reference
                    ? [
                        <div
                          className="arrangement-reference"
                          key={`reference-${block.first}`}
                        >
                          {block.first}–
                          {block.first + block.reference.length - 1}: play{" "}
                          {block.reference.name}
                          {block.reference.variant
                            ? ` *${block.reference.variant}`
                            : ""}{" "}
                          {block.reference.first}–
                          {block.reference.first + block.reference.length - 1}
                          {block.times > 1 ? ` ×${block.times}` : ""}
                        </div>,
                      ]
                    : block.bars.map((bar, i) => (
                        <div
                          className={`arrangement-bar${(i === 0 && block.times > 1) || bar.repeat_start ? " repeat-begin" : ""}${(i === block.bars.length - 1 && block.times > 1) || bar.repeat_end ? " repeat-finish" : ""}`}
                          key={bar.id}
                        >
                          <small>{block.first + i}</small>
                          <div className="bar-harmony">
                            {bar.chords.length ? (
                              bar.chords.map((chord) => (
                                <span
                                  key={chord.id}
                                  title={chord.symbol}
                                  aria-label={chord.symbol}
                                >
                                  <strong>{chord.display}</strong>
                                  {bar.chords.length > 1 && (
                                    <sup>
                                      {beatLabel(
                                        chord.beat,
                                        bar.meter.denominator,
                                      )}
                                    </sup>
                                  )}
                                </span>
                              ))
                            ) : (
                              <span>—</span>
                            )}
                          </div>
                          <svg
                            className="rhythm-staff"
                            viewBox="0 0 140 30"
                            preserveAspectRatio="none"
                            aria-hidden="true"
                          >
                            {[5, 10, 15, 20, 25].map((y) => (
                              <line key={y} x1="0" y1={y} x2="140" y2={y} />
                            ))}
                            {((i === 0 && block.times > 1) ||
                              bar.repeat_start) && (
                              <>
                                <circle cx="7" cy="12.5" r="1" />
                                <circle cx="7" cy="17.5" r="1" />
                              </>
                            )}
                            {((i === block.bars.length - 1 &&
                              block.times > 1) ||
                              bar.repeat_end) && (
                              <>
                                <circle cx="133" cy="12.5" r="1" />
                                <circle cx="133" cy="17.5" r="1" />
                              </>
                            )}
                            {Array.from(
                              { length: bar.meter.numerator },
                              (_, beat) => {
                                const x =
                                  8 +
                                  (124 * (beat + 0.5)) / bar.meter.numerator;
                                return (
                                  <path
                                    key={beat}
                                    d={`M ${x - 3} 21 L ${x + 4} 10 L ${x + 4} 14 L ${x - 3} 25 Z`}
                                  />
                                );
                              },
                            )}
                          </svg>
                          {(allBars.indexOf(bar) === 0 ||
                            allBars[allBars.indexOf(bar) - 1].meter
                              .numerator !== bar.meter.numerator ||
                            allBars[allBars.indexOf(bar) - 1].meter
                              .denominator !== bar.meter.denominator) && (
                            <span className="bar-meter">
                              {bar.meter.numerator}/{bar.meter.denominator}
                            </span>
                          )}
                          {bar.cue && <em>{bar.cue}</em>}
                          {i === 0 && block.times > 1 && (
                            <em className="pattern-repeat">
                              <span className={condensed ? "sr-only" : ""}>
                                <span className="sr-only">Play </span>
                                {block.first}
                                {block.bars.length > 1
                                  ? `–${block.first + block.bars.length - 1}`
                                  : ""}
                                :{" "}
                              </span>
                              {block.times}×
                            </em>
                          )}
                        </div>
                      )),
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function beatLabel(beat: number, denominator: number) {
  const value = (beat * denominator) / 4 + 1;
  return value % 1 === 0.5 ? `${Math.floor(value)}&` : String(value);
}
