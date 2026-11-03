"use client";

export function PrintButton({ label }: { label: string }) {
  return (
    <button type="button" onClick={() => window.print()} className="no-print mt-4 rounded-md border border-border px-4 py-2">
      {label}
    </button>
  );
}
