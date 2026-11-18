import type { Measure } from "./model";

export type SongSection = {
  first: number;
  end: number;
  label: string;
  group: string;
  id: string;
  time: number;
};

export function songSections(measures: Measure[]) {
  const sections: SongSection[] = [];
  measures.forEach((measure, index) => {
    const name = measure.section.trim();
    if (!name && index > 0) return;
    const previous = sections.at(-1);
    if (previous) previous.end = index;
    sections.push({
      first: index,
      end: measures.length,
      label: name || "Opening",
      group: name.toLowerCase(),
      id: measure.id,
      time: measure.start,
    });
  });
  return sections;
}
