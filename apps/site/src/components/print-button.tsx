"use client";

export function PrintButton({ label }: { label: string }) {
  return (
    <button type="button" onClick={() => window.print()} className="no-print btn btn-line mt-6">
      {label}
    </button>
  );
}
