"use client";

export function PrintButton({ label }: { label: string }) {
  return (
    <button type="button" onClick={() => window.print()} className="no-print mt-4 rounded-xl ring-1 ring-inset ring-border px-4 py-2">
      {label}
    </button>
  );
}
