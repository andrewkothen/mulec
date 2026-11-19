"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { Job } from "./model";

export type UploadTask = {
  id: string;
  name: string;
  file?: File;
  title: string;
  composer: string;
  reference: string;
  options: string;
  autoOpen: boolean;
  status: "waiting" | "uploading" | "running" | "done" | "error";
  progress: number;
  message: string;
  jobId?: string;
  projectId?: string;
};
type NewUpload = Omit<UploadTask, "id" | "status" | "progress" | "message">;
const pause = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

export function useUploadQueue(onReady: (task: UploadTask) => Promise<void>) {
  const [items, setItems] = useState<UploadTask[]>([]);
  const current = useRef<UploadTask[]>([]),
    pumping = useRef(false),
    mounted = useRef(true);
  const ready = useRef(onReady);
  ready.current = onReady;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  function update(id: string, change: Partial<UploadTask>) {
    current.current = current.current.map((item) =>
      item.id === id ? { ...item, ...change } : item,
    );
    if (mounted.current) setItems([...current.current]);
  }
  async function pump() {
    if (pumping.current) return;
    pumping.current = true;
    try {
      while (mounted.current) {
        const task = current.current.find((item) => item.status === "waiting");
        if (!task) break;
        let jobId = task.jobId;
        try {
          if (!jobId) {
            if (!task.file)
              throw new Error("Select this recording again to retry.");
            update(task.id, {
              status: "uploading",
              message: "Uploading on this computer…",
            });
            const form = new FormData();
            form.append("file", task.file);
            for (const key of [
              "title",
              "composer",
              "reference",
              "options",
            ] as const)
              form.append(key, task[key]);
            let submitted: Job;
            try {
              submitted = await api<Job>("/analyze", {
                method: "POST",
                body: form,
                signal: AbortSignal.timeout(120000),
              });
            } catch (error) {
              if (error instanceof ApiError && error.status === 429) {
                update(task.id, {
                  status: "waiting",
                  message: "Waiting for the current analysis to finish…",
                });
                await pause(5000);
                continue;
              }
              throw error;
            }
            jobId = submitted.id;
            update(task.id, {
              jobId,
              status: "running",
              progress: submitted.progress,
              message: submitted.message,
            });
          } else
            update(task.id, {
              status: "running",
              message: "Reconnecting to analysis…",
            });
          let failures = 0;
          while (mounted.current) {
            await pause(1000);
            if (!mounted.current) break;
            let job: Job;
            try {
              job = await api<Job>(`/jobs/${jobId}`, {
                signal: AbortSignal.timeout(10000),
              });
              failures = 0;
            } catch (error) {
              if (error instanceof ApiError && error.status === 404) {
                jobId = undefined;
                throw new Error(
                  "Analysis history is unavailable. Retry to upload this recording again.",
                );
              }
              if (++failures < 3) continue;
              throw new Error(
                `Could not check progress. Retry to reconnect; this song may still finish in Library. ${error instanceof Error ? error.message : error}`,
              );
            }
            if (job.status === "error") {
              jobId = undefined;
              throw new Error(job.message);
            }
            if (job.status === "done") {
              if (!job.project_id)
                throw new Error(
                  "Analysis finished without a chart. Check Library.",
                );
              const complete = {
                ...task,
                jobId,
                file: undefined,
                status: "done" as const,
                progress: 100,
                message: "Ready in Library",
                projectId: job.project_id,
              };
              update(task.id, complete);
              await ready.current(complete);
              break;
            }
            update(task.id, {
              status: "running",
              progress: job.progress,
              message: job.message,
            });
          }
        } catch (error) {
          update(task.id, {
            status: "error",
            jobId,
            message: error instanceof Error ? error.message : String(error),
          });
        }
      }
    } finally {
      pumping.current = false;
    }
  }
  function enqueue(tasks: NewUpload[]) {
    current.current = [
      ...current.current,
      ...tasks.map((task) => ({
        ...task,
        id: crypto.randomUUID(),
        status: "waiting" as const,
        progress: 0,
        message: "Waiting to analyze",
      })),
    ];
    setItems([...current.current]);
    void pump();
  }
  function retry(id: string) {
    update(id, { status: "waiting", progress: 0, message: "Waiting to retry" });
    void pump();
  }
  function remove(id: string) {
    current.current = current.current.filter(
      (item) =>
        item.id !== id || !["waiting", "error", "done"].includes(item.status),
    );
    setItems([...current.current]);
  }
  function clearFinished() {
    current.current = current.current.filter((item) => item.status !== "done");
    setItems([...current.current]);
  }
  const active = items.some((item) =>
    ["waiting", "uploading", "running"].includes(item.status),
  );
  return { items, active, enqueue, retry, remove, clearFinished };
}
