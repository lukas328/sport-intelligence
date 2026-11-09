"use client";

import { useId, useState, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** A file field in the app's own words (the browser's "Choose File / No file chosen" stays in the
 * browser's language): a quiet button that opens the picker and the chosen file's name. The input
 * itself stays in the form, so uncontrolled forms keep working. */
export function FileField({
  label,
  hint,
  button,
  empty,
  className,
  onChange,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label?: string; hint?: string; button: string; empty: string }) {
  const id = useId();
  const [file, setFile] = useState<string | null>(null);
  return (
    <div className={cn("space-y-1", className)}>
      {label && <p className="text-sm font-semibold">{label}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <input
          id={id}
          type="file"
          className="peer sr-only"
          aria-label={label ?? button}
          aria-describedby={hint ? `${id}-hint` : undefined}
          onChange={(e) => {
            setFile(e.target.files?.[0]?.name ?? null);
            onChange?.(e);
          }}
          {...props}
        />
        <label
          htmlFor={id}
          className="inline-flex min-h-10 cursor-pointer items-center rounded-md bg-raised px-4 text-sm font-medium ring-1 ring-inset ring-border hover:bg-surface peer-focus-visible:ring-2 peer-focus-visible:ring-accent"
        >
          {button}
        </label>
        <span className="min-w-0 truncate text-sm text-muted">{file ?? empty}</span>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
    </div>
  );
}
