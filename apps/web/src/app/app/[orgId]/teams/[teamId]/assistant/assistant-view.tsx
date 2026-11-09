"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowUp, Play } from "lucide-react";
import { control } from "@/components/ui/field";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Message = Schemas["MessageOut"];
type Chart = NonNullable<Schemas["Answer"]["chart"]>;

/** Single-series bar list: one hue, values as text next to each bar (no legend needed). */
function BarList({ chart }: { chart: Chart }) {
  const max = Math.max(...chart.values.map(Math.abs), 1e-9);
  const fmt = (v: number) => (Math.abs(v) <= 1 && !Number.isInteger(v) ? `${Math.round(v * 100)} %` : String(v));
  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-medium">{chart.title}</figcaption>
      <ul className="space-y-1.5">
        {chart.labels.map((label, i) => {
          const v = chart.values[i] ?? 0;
          return (
            <li key={`${label}-${i}`} className="grid grid-cols-[minmax(5rem,10rem)_1fr_3.5rem] items-center gap-2 text-sm" title={`${label}: ${fmt(v)}`}>
              <span className="truncate text-muted">{label}</span>
              <span className="h-3 rounded-r bg-surface" aria-hidden>
                <span className="block h-3 rounded-r bg-foreground" style={{ width: `${(Math.abs(v) / max) * 100}%` }} />
              </span>
              <span className="tabular-nums">{fmt(v)}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

function AnswerCard({ m, orgId, onAsk }: { m: Message; orgId: string; onAsk: (q: string) => void }) {
  const t = useTranslations("assistant");
  const [rated, setRated] = useState<number | null>(m.rating ?? null);
  const rate = useMutation({
    mutationFn: async (rating: -1 | 1) => {
      const r = await api.POST("/v1/orgs/{org_id}/assistant/messages/{message_id}/rating", {
        params: { path: { org_id: orgId, message_id: m.id } },
        body: { rating },
      });
      if (r.error) throw r.error;
      return rating;
    },
    onSuccess: (v) => setRated(v),
  });
  const a = m.answer;
  return (
    <div className="space-y-3">
      <p className="font-semibold">{m.question}</p>
      <div className="space-y-3 border-l-2 border-foreground/20 pl-4">
        <p>{a.text}</p>
        {a.sample_size != null && <p className="text-sm text-muted">{t("sample", { n: a.sample_size })}</p>}
        {a.chart && <BarList chart={a.chart} />}
        {a.clips && a.clips.length > 0 && (
          <div className="space-y-1">
            <p className="text-sm font-medium">{t("clips")}</p>
            <ul className="flex flex-wrap gap-2">
              {a.clips.map((c) => (
                <li key={c.event_id}>
                  <Link
                    href={`/app/${orgId}/matches/${c.match_id}?t=${c.t_ms ?? 0}`}
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 text-sm font-semibold ring-1 ring-inset ring-foreground/20 hover:bg-surface"
                  >
                    <Play aria-hidden className="size-3 fill-current" /> {c.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!a.answerable && a.suggestion && (
          <p className="text-sm">
            {t("tryInstead")}{" "}
            <button type="button" className="font-medium underline underline-offset-4" onClick={() => onAsk(a.suggestion!)}>
              {a.suggestion}
            </button>
          </p>
        )}
        <details className="text-sm text-muted">
          <summary className="cursor-pointer">{t("how", { count: m.tool_calls.length })}</summary>
          <ul className="mt-1 list-disc pl-5">
            {m.tool_calls.map((c, i) => (
              <li key={i}>
                <code>{c.name}</code>
                {c.summary && Object.keys(c.summary).length > 0 && ` (${Object.entries(c.summary).map(([k, v]) => `${k}: ${v}`).join(", ")})`}
                {c.error && ` ${t("toolError")}`}
              </li>
            ))}
          </ul>
          {!m.validated && <p className="mt-1">{t("notValidated")}</p>}
        </details>
        <div className="flex items-center gap-2 text-sm" aria-label={t("rateLabel")}>
          <button type="button" aria-pressed={rated === 1} className="rounded-md px-3 py-1 ring-1 ring-border hover:bg-surface aria-pressed:bg-foreground aria-pressed:text-background" onClick={() => rate.mutate(1)}>
            {t("good")}
          </button>
          <button type="button" aria-pressed={rated === -1} className="rounded-md px-3 py-1 ring-1 ring-border hover:bg-surface aria-pressed:bg-foreground aria-pressed:text-background" onClick={() => rate.mutate(-1)}>
            {t("bad")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function AssistantView({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("assistant");
  const tr = useTranslations();
  const locale = useLocale();
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<ErrorKey | null>(null);
  const history = useQuery({
    queryKey: ["assistant-conversations", teamId],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/assistant", { params: { path: { org_id: orgId, team_id: teamId } } })).data ?? [],
  });
  const ask = useMutation({
    mutationFn: async (q: string) => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/assistant", {
        params: { path: { org_id: orgId, team_id: teamId } },
        body: { question: q, conversation_id: conversation, lang: (["de-CH", "fr", "en"].includes(locale) ? locale : "de-CH") as "de-CH" | "fr" | "en" },
      });
      if (r.error) throw r.error;
      return r.data;
    },
    onMutate: () => setError(null),
    onSuccess: (m) => {
      setConversation(m.conversation_id);
      setMessages((ms) => [...ms, m]);
      setQuestion("");
      void history.refetch();
    },
    onError: (e) => setError(errorKey(e)),
  });
  const open = async (id: string) => {
    const r = await api.GET("/v1/orgs/{org_id}/assistant/{conversation_id}", { params: { path: { org_id: orgId, conversation_id: id } } });
    if (r.data) {
      setConversation(id);
      setMessages(r.data.messages);
    }
  };
  // a question handed over from the start page or the command palette
  const params = useSearchParams();
  const asked = useRef(false);
  useEffect(() => {
    const q = params.get("q")?.trim();
    if (q && q.length >= 3 && !asked.current) {
      asked.current = true;
      ask.mutate(q);
    }
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim().length >= 3) ask.mutate(question.trim());
  };
  const examples = [t("example1"), t("example2"), t("example3")];
  const form = (
    <form onSubmit={submit} className="relative">
      <label className="block">
        <span className="sr-only">{t("question")}</span>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("placeholder")}
          maxLength={500}
          className={cn(control, "min-h-14 pr-28 pl-4 text-base")}
        />
      </label>
      <Button type="submit" className="absolute top-2 right-2" disabled={ask.isPending || question.trim().length < 3}>
        <ArrowUp aria-hidden />
        {t("ask")}
      </Button>
    </form>
  );
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_16rem]">
      <section className="space-y-4" aria-labelledby="assistant-title">
        <div>
          <h2 id="assistant-title" className="sr-only">{t("title")}</h2>
          <p className="text-sm text-muted">{t("hint")}</p>
        </div>
        {/* before the first question the field comes first (on phones it was below the fold) */}
        {messages.length === 0 && form}
        {messages.length === 0 && (
          <div className="space-y-1">
            <p className="text-sm text-muted">{t("examples")}</p>
            <ul className="divide-y divide-foreground/10 border-y border-foreground/10">
              {examples.map((q) => (
                <li key={q}>
                  <button type="button" className="flex min-h-11 w-full items-center text-left text-sm font-medium hover:underline" onClick={() => ask.mutate(q)}>
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="space-y-8" aria-live="polite">
          {messages.map((m) => (
            <AnswerCard key={m.id} m={m} orgId={orgId} onAsk={(q) => ask.mutate(q)} />
          ))}
          {ask.isPending && <p className="text-sm text-muted">{t("thinking")}</p>}
        </div>
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        {messages.length > 0 && form}
      </section>
      <aside className="space-y-2 lg:border-l lg:border-foreground/15 lg:pl-6" aria-label={t("history")}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t("history")}</h3>
          <button type="button" className="min-h-8 text-sm font-medium underline underline-offset-4" onClick={() => { setConversation(null); setMessages([]); }}>
            {t("new")}
          </button>
        </div>
        {history.data && history.data.length === 0 && <p className="text-sm text-muted">{t("historyNone")}</p>}
        <ul className="space-y-1 text-sm">
          {(history.data ?? []).map((c) => (
            <li key={c.id}>
              <button type="button" className="min-h-8 w-full truncate text-left hover:underline aria-[current=true]:font-semibold" aria-current={c.id === conversation} onClick={() => void open(c.id)}>
                {c.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
