import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs/promises";

test("global multi-file drop queues songs, continues after a failed file, and accepts more files", async ({
  page,
  request,
}) => {
  const fixture = (
    await fs.readFile(path.resolve("../tmp/sunday-sketch.wav"))
  ).toString("base64");
  const prefix = `Batch ${Date.now()}`;
  await page.goto("/");
  await page.evaluate(
    ({ fixture, prefix }) => {
      const transfer = new DataTransfer();
      const bytes = Uint8Array.from(atob(fixture), (c) => c.charCodeAt(0));
      transfer.items.add(
        new File([bytes], `${prefix} one.wav`, {
          type: "audio/wav",
          lastModified: 42,
        }),
      );
      transfer.items.add(
        new File(["not an audio recording"], `${prefix} broken.wav`, {
          type: "audio/wav",
        }),
      );
      transfer.items.add(
        new File([bytes], `${prefix} two.wav`, {
          type: "audio/wav",
          lastModified: 42,
        }),
      );
      transfer.items.add(
        new File(["notes"], "notes.txt", { type: "text/plain" }),
      );
      document.body.dispatchEvent(
        new DragEvent("dragenter", { bubbles: true, dataTransfer: transfer }),
      );
      document.body.dispatchEvent(
        new DragEvent("drop", {
          bubbles: true,
          cancelable: true,
          dataTransfer: transfer,
        }),
      );
    },
    { fixture, prefix },
  );
  await expect(
    page.getByRole("heading", { name: "Start with a recording." }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("list", { name: "Selected recordings" })
      .getByRole("listitem"),
  ).toHaveCount(3);
  await expect(page.locator(".alert.error")).toContainText("notes.txt");
  await expect(page.getByLabel("Audio recording")).toHaveAttribute(
    "multiple",
    "",
  );
  await page.locator("summary").filter({ hasText: "Analysis options" }).click();
  await page
    .getByRole("combobox", { name: "Known key", exact: true })
    .selectOption("C");
  await page
    .getByRole("spinbutton", { name: "Tempo override (BPM)" })
    .fill("120");
  await page
    .getByRole("button", { name: "Analyze 3 recordings", exact: true })
    .click();
  const queue = page.getByRole("list", { name: "Import queue" });
  await expect(queue.getByRole("listitem")).toHaveCount(3);
  // Add another file while the earlier batch is still working.
  await page.getByLabel("Audio recording").setInputFiles({
    name: `${prefix} three.wav`,
    mimeType: "audio/wav",
    buffer: Buffer.from(fixture, "base64"),
  });
  await page.getByRole("button", { name: "Add to queue", exact: true }).click();
  await expect(queue.getByRole("listitem")).toHaveCount(4);
  await expect(queue.locator('[data-status="done"]')).toHaveCount(3, {
    timeout: 120000,
  });
  await expect(queue.locator('[data-status="error"]')).toHaveCount(1);
  await expect(
    queue.locator(
      '[data-status="waiting"], [data-status="running"], [data-status="uploading"]',
    ),
  ).toHaveCount(0);
  const summaries = await (await request.get("/api/projects")).json();
  expect(
    summaries.filter((item: { title: string }) =>
      item.title.startsWith(prefix),
    ),
  ).toHaveLength(3);
  await page.getByRole("button", { name: /^Library/ }).click();
  await expect(
    page.getByRole("button", { name: new RegExp(`${prefix} two`) }),
  ).toBeVisible();
  await page.screenshot({ path: "../tmp/batch-upload.png", fullPage: false });
  await page
    .getByRole("button", { name: "Clear finished", exact: true })
    .click();
  await expect(queue.getByRole("listitem")).toHaveCount(1);
});

test("theoretical minor keys render and a manual E key survives reload", async ({
  page,
  request,
}) => {
  const imported = await request.post("/api/projects/import", {
    data: {
      title: "Key signature regression",
      key: "Db",
      key_mode: "minor",
      measures: [
        {
          start: 0,
          end: 2,
          section: "Intro",
          chords: [{ symbol: "Dbm" }],
          notes: [{ midi: 61, duration: 4 }],
        },
        {
          start: 2,
          end: 4,
          section: "Verse 1",
          meter: { numerator: 6, denominator: 8 },
          chords: [{ symbol: "Gb" }],
        },
      ],
    },
  });
  expect(imported.ok()).toBeTruthy();
  await page.goto("/");
  await page
    .getByRole("button", { name: /Key signature regression/ })
    .first()
    .click();
  await page.getByRole("button", { name: "Lead sheet", exact: true }).click();
  await expect(page.locator(".notation svg").first()).toBeVisible();
  await expect(page.locator(".notation")).not.toContainText("BadKeySignature");
  await expect(page.locator(".notation")).not.toContainText("Concert chart");
  await page.getByText("Song & beat grid", { exact: true }).click();
  await page
    .getByRole("combobox", { name: /^Key signature/ })
    .selectOption("E");
  await page.getByRole("combobox", { name: /^Mode/ }).selectOption("major");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Saved on this computer",
  );
  await expect(page.locator(".notation svg").first()).toBeVisible();
  const saved = await request.get(
    `/api/projects/${(await imported.json()).id}`,
  );
  expect(await saved.json()).toMatchObject({
    key: "E",
    key_mode: "major",
    key_manual: true,
  });
  await page.screenshot({
    path: "../tmp/key-fix/renderer-regression.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Form", exact: true }).click();
  await page.getByRole("button", { name: "By section", exact: true }).click();
  const staff = page.locator(".form-paper .notation");
  await expect(staff.getByText("Intro", { exact: true })).toBeVisible();
  await page
    .getByRole("region", { name: "Song roadmap" })
    .getByRole("button", { name: /Verse 1/ })
    .click();
  await expect(staff.getByText("Verse 1", { exact: true })).toBeVisible();
  await expect(staff.getByText("Intro", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Full chart", exact: true }).click();
  await expect(staff.getByText("Intro", { exact: true })).toBeVisible();
  await staff.screenshot({ path: "../tmp/pdfs/mixed-meter-form.png" });
});

test("real audio → editable chart → saved project → printable export", async ({
  page,
  baseURL,
}) => {
  const errors: string[] = [],
    external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    if (
      new URL(route.request().url()).origin !== baseURL &&
      !route.request().url().startsWith("blob:")
    ) {
      external.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your music, on the page." }),
  ).toBeVisible();
  await page.screenshot({ path: "../tmp/library.png", fullPage: true });
  await page
    .getByRole("button", { name: "New transcription", exact: true })
    .last()
    .click();
  await page
    .getByLabel("Audio recording")
    .setInputFiles(path.resolve("../tmp/sunday-sketch.wav"));
  await page.getByLabel("Song title", { exact: true }).fill("Sunday Sketch");
  await page
    .getByLabel("Composer / artist")
    .fill("Mulec original fixture · CC0");
  await page.getByRole("button", { name: "Analyze recording" }).click();
  await expect(
    page.getByRole("heading", { name: "Sunday Sketch", exact: true }).first(),
  ).toBeVisible({ timeout: 120000 });
  await page.getByRole("button", { name: /^Bar 1:/ }).click();
  const chord = page
    .getByRole("textbox", { name: "Chord symbol", exact: true })
    .first();
  await chord.fill("Bbmaj7/F");
  await chord.press("Tab");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Saved on this computer",
  );
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).not.toContainText(
    "Bbmaj7/F",
  );
  await page.getByRole("button", { name: "Redo", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  await page
    .getByRole("combobox", { name: "Instrument part" })
    .selectOption("bb");
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Cmaj7/G",
  );
  await page
    .getByRole("combobox", { name: "Instrument part" })
    .selectOption("concert");
  await page
    .getByRole("combobox", { name: "Chord notation" })
    .selectOption("nashville");
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "b7maj7/4",
  );
  await page
    .getByRole("combobox", { name: "Chord notation" })
    .selectOption("jazz");
  await page.getByRole("button", { name: /^Bar 1:/ }).click();
  await page.getByText("Melody notes (0)", { exact: true }).click();
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await page.getByRole("button", { name: "Close bar editor" }).click();
  await page.screenshot({ path: "../tmp/workspace.png", fullPage: true });
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Printable chord chart · PDF" })
    .click();
  await (await download).saveAs("../tmp/mulec-chart.pdf");
  await page.getByRole("button", { name: "Lead sheet", exact: true }).click();
  await expect(page.locator(".notation svg").first()).toBeVisible({
    timeout: 30000,
  });
  const playhead = page.locator(".notation .score-playhead");
  await page.getByRole("spinbutton", { name: "To (s)" }).fill("2.8");
  const loop = page.getByRole("button", { name: "Loop selected region" });
  await loop.click();
  await expect(playhead).toHaveAttribute("data-bar", "1");
  const initialX = Number(await playhead.getAttribute("x1"));
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect
    .poll(async () => Number(await playhead.getAttribute("x1")))
    .toBeGreaterThan(initialX + 5);
  await expect(playhead).toHaveAttribute("data-bar", "2");
  await expect(playhead).toHaveAttribute("data-bar", "1");
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await loop.click();
  await page.screenshot({ path: "../tmp/lead-sheet.png", fullPage: true });
  await page.getByRole("button", { name: "Chord chart", exact: true }).click();
  await page.getByRole("button", { name: /^Bar 5:/ }).click();
  const section = page.getByRole("textbox", {
    name: "Section / rehearsal mark",
  });
  await section.fill("A");
  await section.press("Tab");
  await page.getByRole("button", { name: "Form", exact: true }).click();
  await page.getByRole("button", { name: "By section", exact: true }).click();
  const roadmap = page.getByRole("region", { name: "Song roadmap" });
  await expect(roadmap).toContainText("2 occurrences");
  await expect(playhead).toHaveAttribute("data-bar", "5");
  await roadmap.getByRole("button", { name: /^A 0:00$/ }).click();
  await expect(playhead).toHaveAttribute("data-bar", "1");
  await roadmap.getByRole("button", { name: /^A 0:0[78]$/ }).click();
  await expect(playhead).toHaveAttribute("data-bar", "5");
  await page.screenshot({ path: "../tmp/pdfs/rhythm-chart-preview.png" });
  await page.getByRole("button", { name: "Chord chart", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../tmp/mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.reload();
  await page
    .getByRole("button", { name: /Sunday Sketch/ })
    .first()
    .click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  expect(
    (await fs.readFile("../tmp/mulec-chart.pdf")).subarray(0, 4).toString(),
  ).toBe("%PDF");
});

test("compact arrangement merges returning parts and exports a bass-player chart", async ({
  page,
  request,
}) => {
  const harmony = ["C", "Am", "F", "G", "C", "Am", "F", "G"];
  const response = await request.post("/api/projects/import", {
    data: {
      title: "Arrangement regression",
      measures: Array.from({ length: 24 }, (_, i) => ({
        start: i * 2,
        end: i * 2 + 2,
        section: i === 0 ? "A" : i === 8 ? "B" : i === 16 ? "F" : "",
        chords: [{ symbol: i >= 8 && i < 16 ? "Dm7" : harmony[i % 8] }],
      })),
    },
  });
  expect(response.ok()).toBeTruthy();
  await page.goto("/");
  await page
    .getByRole("button", { name: /Arrangement regression/ })
    .first()
    .click();
  await page.getByRole("button", { name: "Form", exact: true }).click();
  await page.getByRole("button", { name: "Arrangement", exact: true }).click();
  const compact = page.getByLabel("Compact arrangement", { exact: true });
  const order = compact.getByRole("list", { name: "Arrangement order" });
  await order.getByRole("button", { name: /^F/ }).click();
  await page.getByRole("combobox", { name: "Same part as" }).selectOption("a");
  await expect(compact.locator(".arrangement-part")).toHaveCount(2);
  await expect(order.getByRole("button", { name: /^A/ })).toHaveCount(2);
  const rename = page.getByLabel("Section group name", { exact: true });
  await rename.fill("Verse");
  await rename.press("Tab");
  await expect(
    compact.getByRole("heading", { name: "Verse", exact: true }),
  ).toBeVisible();
  await expect(compact).toContainText("5 written bars");
  await expect(compact).toContainText("Play 1–4: 2×");
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(() => document.fonts.check('16px "Mulec Jazz"')),
  ).toBeTruthy();
  await expect(compact.locator(".rhythm-staff")).toHaveCount(5);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Saved on this computer",
  );
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Compact arrangement · PDF", exact: true })
    .click();
  await (await download).saveAs("../tmp/arrangement/regression.pdf");
  await page.screenshot({
    path: "../tmp/arrangement/compact-browser.png",
    fullPage: true,
  });
  await page.reload();
  await page
    .getByRole("button", { name: /Arrangement regression/ })
    .first()
    .click();
  await page.getByRole("button", { name: "Form", exact: true }).click();
  await expect(
    compact.getByRole("heading", { name: "Verse", exact: true }),
  ).toBeVisible();
  const saved = await request.get(
    `/api/projects/${(await response.json()).id}`,
  );
  expect((await saved.json()).measures[16].section).toBe("Verse");
});
