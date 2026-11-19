"use client";

import { useEffect, useState } from "react";
import { api, json } from "@/lib/api";
import { clock, type Measure, type Project } from "@/lib/model";
import type { SongSection } from "@/lib/form";

type Part = {
  id: string;
  name: string;
  variant: number;
  ending: boolean;
  from_bar: number;
  length: number;
  blocks: { first: number; times: number; bars: Measure[] }[];
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
  active,
  onSelect,
}: {
  project: Project;
  part: string;
  active?: SongSection;
  onSelect: (section: SongSection) => void;
}) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    setError("");
    api<Plan>(`/arrangement?part=${part}`, json(project))
      .then((result) => {
        if (alive) setPlan(result);
      })
      .catch((e) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [project, part]);
  if (error) return <p className="error-inline">{error}</p>;
  if (!plan) return <p className="hint">Building the arrangement…</p>;
  return (
    <div className="arrangement" aria-label="Compact arrangement">
      <p className="hint arrangement-count">
        {plan.written_bars} written bars · {plan.total_bars} bars in the
        recording
        {plan.parts.some((p) => p.variant > 0) &&
          " · * different ending or variation"}
      </p>
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
      <div className="arrangement-parts">
        {plan.parts.map((piece) => {
          const times = plan.order.filter((step) => step.part === piece.id);
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
                  block.bars.map((bar, i) => (
                    <div className="arrangement-bar" key={bar.id}>
                      <small>{block.first + i}</small>
                      {bar.chords.length ? (
                        bar.chords.map((chord) => (
                          <span key={chord.id}>
                            <strong>{chord.symbol}</strong>
                            {bar.chords.length > 1 && (
                              <sup>{chord.beat + 1}</sup>
                            )}
                          </span>
                        ))
                      ) : (
                        <span>—</span>
                      )}
                      {bar.cue && <em>{bar.cue}</em>}
                      {i === 0 && block.times > 1 && (
                        <em className="pattern-repeat">
                          Play {block.first}
                          {block.bars.length > 1
                            ? `–${block.first + block.bars.length - 1}`
                            : ""}
                          : {block.times}×
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
