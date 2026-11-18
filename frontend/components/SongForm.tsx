"use client";

import { TextField } from "@/components/MeasureEditor";
import type { SongSection } from "@/lib/form";
import { clock } from "@/lib/model";

export default function SongForm({
  sections,
  active,
  full,
  finding,
  onFind,
  onSelect,
  onView,
  onRename,
  onEditBar,
}: {
  sections: SongSection[];
  active: SongSection;
  full: boolean;
  finding: boolean;
  onFind?: () => void;
  onSelect: (section: SongSection) => void;
  onView: (full: boolean) => void;
  onRename: (name: string) => void;
  onEditBar: () => void;
}) {
  const groups = new Map<string, number>();
  for (const section of sections)
    groups.set(section.group, (groups.get(section.group) ?? 0) + 1);
  const repeatGroups = [...groups.values()].filter((count) => count > 1).length;
  const occurrences = groups.get(active.group) ?? 1;
  return (
    <section className="form-nav" aria-label="Song roadmap">
      <div className="form-nav-toolbar">
        <div className="segmented" aria-label="Form layout">
          <button
            className={!full ? "active" : ""}
            aria-pressed={!full}
            onClick={() => onView(false)}
          >
            By section
          </button>
          <button
            className={full ? "active" : ""}
            aria-pressed={full}
            onClick={() => onView(true)}
          >
            Full chart
          </button>
        </div>
        {onFind && (
          <button className="secondary" disabled={finding} onClick={onFind}>
            {finding ? "Listening…" : "Find sections"}
          </button>
        )}
      </div>
      <p className="hint form-count">
        {sections.length} {sections.length === 1 ? "section" : "sections"}
        {repeatGroups
          ? ` · ${repeatGroups} repeated ${repeatGroups === 1 ? "group" : "groups"}`
          : ""}
      </p>
      <ol className="form-steps" aria-label="Sections in playback order">
        {sections.map((section) => (
          <li key={section.id}>
            <button
              onClick={() => onSelect(section)}
              aria-current={section.id === active.id ? "step" : undefined}
              title={`Bars ${section.first + 1}–${section.end}`}
            >
              <strong>{section.label}</strong>
              <span>{clock(section.time)}</span>
            </button>
          </li>
        ))}
      </ol>
      {!full && (
        <div className="form-selection">
          <TextField
            key={active.id}
            label={occurrences > 1 ? "Section group name" : "Section name"}
            value={active.group ? active.label : ""}
            maxLength={60}
            onChange={onRename}
          />
          <span className="hint">
            Bars {active.first + 1}–{active.end}
            {occurrences > 1 && ` · ${occurrences} occurrences`}
          </span>
          <button className="secondary" onClick={onEditBar}>
            Edit first bar
          </button>
        </div>
      )}
    </section>
  );
}
