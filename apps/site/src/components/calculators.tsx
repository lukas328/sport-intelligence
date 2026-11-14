"use client";

import { useId, useState } from "react";
import { fmt } from "@/lib/i18n";

type RateText = {
  goals: string;
  shots: string;
  saves: string;
  conceded: string;
  sentenceShooting: string;
  sentenceKeeper: string;
  empty: string;
  invalid: string;
  copy: string;
  copied: string;
  small: string;
};

const num = (v: string) => (v.trim() === "" ? NaN : Number(v.replace(",", ".")));

/** Two numbers in, the rate with its base out, as a sentence to copy. Nothing leaves the page. */
export function RateCalc({ kind, title, text }: { kind: "shooting" | "keeper"; title: string; text: RateText }) {
  const id = useId();
  const [a, setA] = useState(kind === "shooting" ? "12" : "10");
  const [b, setB] = useState(kind === "shooting" ? "20" : "25");
  const [copied, setCopied] = useState(false);
  const x = num(a);
  const y = num(b);
  const base = kind === "shooting" ? y : x + y; // shots, or saves plus goals conceded
  let out = text.empty;
  let ok = false;
  if (Number.isFinite(x) && Number.isFinite(y) && x >= 0 && y >= 0 && base > 0) {
    if (kind === "shooting" && x > y) out = text.invalid;
    else {
      const p = Math.round((x / base) * 100);
      out = fmt(kind === "shooting" ? text.sentenceShooting : text.sentenceKeeper, { a: x, b: base, p });
      ok = true;
    }
  }
  const labels = kind === "shooting" ? [text.goals, text.shots] : [text.saves, text.conceded];
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(out);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <section aria-labelledby={`${id}-t`} className="border-t-2 border-ink pt-5">
      <h2 id={`${id}-t`} className="text-[1.75rem] md:text-[2rem]">
        {title}
      </h2>
      <div className="mt-4 flex flex-wrap gap-4">
        {[a, b].map((v, i) => (
          <label key={i} className="flex flex-col gap-1 font-bold">
            {labels[i]}
            <input
              id={`${id}-${kind}-${i}`}
              inputMode="numeric"
              value={v}
              onChange={(e) => (i ? setB : setA)(e.target.value)}
              className="h-14 w-32 border-2 border-ink bg-paper px-3 text-[1.375rem] font-normal tabular-nums"
            />
          </label>
        ))}
      </div>
      <p aria-live="polite" className="font-slant mt-5 text-[1.75rem] leading-tight md:text-[2.25rem]">
        {out}
      </p>
      {ok && base < 10 && <p className="mt-2 text-ink-2">{text.small}</p>}
      {ok && (
        <button type="button" onClick={copy} className="btn btn-line mt-4">
          {copied ? text.copied : text.copy}
        </button>
      )}
    </section>
  );
}

/** Minutes and a setting in, an estimate in GB out. */
export function StorageCalc({ text, options }: { text: { minutes: string; setting: string; result: string }; options: { id: string; label: string; mb: number }[] }) {
  const id = useId();
  const [minutes, setMinutes] = useState("90");
  const [opt, setOpt] = useState(options[0]!.id);
  const mb = options.find((o) => o.id === opt)?.mb ?? options[0]!.mb;
  const min = num(minutes);
  const gb = Number.isFinite(min) && min > 0 ? Math.round((min * mb) / 100) / 10 : NaN;
  return (
    <div className="border-t-2 border-ink pt-5">
      <div className="flex flex-wrap gap-4">
        <label className="flex flex-col gap-1 font-bold">
          {text.minutes}
          <input id={`${id}-min`} inputMode="numeric" value={minutes} onChange={(e) => setMinutes(e.target.value)} className="h-14 w-32 border-2 border-ink bg-paper px-3 text-[1.375rem] font-normal tabular-nums" />
        </label>
        <label className="flex min-w-0 flex-col gap-1 font-bold">
          {text.setting}
          <select id={`${id}-set`} value={opt} onChange={(e) => setOpt(e.target.value)} className="h-14 max-w-full border-2 border-ink bg-paper px-3 font-normal">
            {options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p aria-live="polite" className="font-num mt-5 text-[2.75rem] leading-none text-club-text md:text-[3.5rem]">
        {Number.isFinite(gb) ? fmt(text.result, { gb: String(gb).replace(".", ",") }) : "?"}
      </p>
    </div>
  );
}
