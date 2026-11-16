const degrees = [
  "1",
  "b2",
  "2",
  "b3",
  "3",
  "4",
  "#4",
  "5",
  "b6",
  "6",
  "b7",
  "7",
];
const majorKeys = [
  "C",
  "Db",
  "D",
  "Eb",
  "E",
  "F",
  "F#",
  "G",
  "Ab",
  "A",
  "Bb",
  "B",
];
const naturals: Record<string, number> = {
  C: 0,
  D: 2,
  E: 4,
  F: 5,
  G: 7,
  A: 9,
  B: 11,
};

function pitchClass(note: string) {
  const [letter, accidental] = note;
  return (
    (naturals[letter] +
      (accidental === "#" ? 1 : accidental === "b" ? -1 : 0) +
      12) %
    12
  );
}

export function nashvilleReference(tonic: string, mode: "major" | "minor") {
  return mode === "minor" ? majorKeys[(pitchClass(tonic) + 3) % 12] : tonic;
}

export function nashvilleChord(symbol: string, reference: string) {
  const chord = symbol
    .replaceAll("♭", "b")
    .replaceAll("♯", "#")
    .match(/^([A-G][b#]?)(.*)$/);
  if (!chord || symbol === "N.C." || symbol === "NC") return symbol;
  const tonic = pitchClass(reference);
  const degree = (note: string) =>
    degrees[(pitchClass(note) - tonic + 12) % 12];
  return (
    degree(chord[1]) +
    chord[2].replace(/\/([A-G][b#]?)$/, (_, bass) => "/" + degree(bass))
  );
}
