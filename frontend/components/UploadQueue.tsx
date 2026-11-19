"use client";

import type { UploadTask } from "@/lib/useUploadQueue";

export default function UploadQueue({
  items,
  onOpen,
  onRetry,
  onRemove,
  onClear,
}: {
  items: UploadTask[];
  onOpen: (id: string) => void;
  onRetry: (id: string) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  if (!items.length) return null;
  const done = items.filter((item) => item.status === "done").length;
  const active = items.some((item) =>
    ["waiting", "uploading", "running"].includes(item.status),
  );
  return (
    <details className="upload-queue" open>
      <summary>
        Import queue{" "}
        <span>
          {done} of {items.length} ready
        </span>
      </summary>
      {active && (
        <p className="hint">
          Songs are analyzed one at a time. Keep this window open until the
          queue finishes; you can keep editing.
        </p>
      )}
      <ol aria-label="Import queue">
        {items.map((item) => (
          <li key={item.id} data-status={item.status}>
            <div className="queue-description">
              <strong>{item.name}</strong>
              <span>
                {item.status === "error" ? "Failed: " : ""}
                {item.message}
              </span>
              {item.status === "running" && (
                <progress
                  aria-label={`Analysis progress for ${item.name}`}
                  max={100}
                  value={item.progress}
                />
              )}
            </div>
            {item.status === "done" && item.projectId && (
              <button
                type="button"
                className="secondary"
                onClick={() => onOpen(item.projectId!)}
              >
                Open chart
              </button>
            )}
            {item.status === "error" && (
              <button
                type="button"
                className="secondary"
                onClick={() => onRetry(item.id)}
              >
                Retry
              </button>
            )}
            {["waiting", "error"].includes(item.status) && (
              <button
                type="button"
                className="text-button"
                aria-label={`Remove ${item.name} from queue`}
                onClick={() => onRemove(item.id)}
              >
                Remove
              </button>
            )}
          </li>
        ))}
      </ol>
      {done > 0 && (
        <button type="button" className="text-button" onClick={onClear}>
          Clear finished
        </button>
      )}
    </details>
  );
}
