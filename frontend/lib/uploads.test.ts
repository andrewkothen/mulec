import { test } from "node:test";
import assert from "node:assert/strict";
import { selectAudioFiles } from "./uploads";

test("batch selection keeps valid audio, rejects invalid files and does not duplicate prior selections", () => {
  const audio = (name: string, size = 100) =>
    ({ name, size, lastModified: 42 }) as File;
  const first = audio("First.WAV"),
    second = audio("Second.mp3");
  const result = selectAudioFiles(
    [first],
    [
      first,
      audio("First.WAV"),
      second,
      audio("notes.txt"),
      audio("empty.wav", 0),
      audio("large.wav", 151 * 1024 * 1024),
    ],
  );
  assert.deepEqual(result.files, [first, second]);
  assert.equal(result.rejected.length, 3);
});
