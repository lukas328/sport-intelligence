"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
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
                <span className="block h-3 rounded-r bg-accent" style={{ width: `${(Math.abs(v) / max) * 100}%` }} />
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
      <p className="ml-auto max-w-[85%] rounded-lg bg-surface px-3 py-2 text-right">{m.question}</p>
      <Card className="space-y-3">
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
                    className="inline-flex min-h-8 items-center rounded-full border border-border px-3 text-sm hover:bg-surface"
                  >
                    ▶ {c.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!a.answerable && a.suggestion && (
          <p className="text-sm">
            {t("tryInstead")}{" "}
            <button type="button" className="text-accent underline" onClick={() => onAsk(a.suggestion!)}>
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
          <button type="button" aria-pressed={rated === 1} className="rounded border border-border px-2 py-0.5 aria-pressed:bg-surface" onClick={() => rate.mutate(1)}>
            {t("good")}
          </button>
          <button type="button" aria-pressed={rated === -1} className="rounded border border-border px-2 py-0.5 aria-pressed:bg-surface" onClick={() => rate.mutate(-1)}>
            {t("bad")}
          </button>
        </div>
      </Card>
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
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim().length >= 3) ask.mutate(question.trim());
  };
  const examples = [t("example1"), t("example2"), t("example3")];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_16rem]">
      <section className="space-y-4" aria-labelledby="assistant-title">
        <div>
          <h2 id="assistant-title" className="text-xl font-semibold">{t("title")}</h2>
          <p className="text-sm text-muted">{t("hint")}</p>
        </div>
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {examples.map((q) => (
              <button key={q} type="button" className="rounded-full border border-border px-3 py-1 text-sm hover:bg-surface" onClick={() => ask.mutate(q)}>
                {q}
              </button>
            ))}
          </div>
        )}
        <div className="space-y-6" aria-live="polite">
          {messages.map((m) => (
            <AnswerCard key={m.id} m={m} orgId={orgId} onAsk={(q) => ask.mutate(q)} />
          ))}
          {ask.isPending && <p className="text-sm text-muted">{t("thinking")}</p>}
        </div>
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        <form onSubmit={submit} className="flex gap-2">
          <label className="flex-1">
            <span className="sr-only">{t("question")}</span>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t("placeholder")}
              maxLength={500}
              className="min-h-10 w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>
          <Button type="submit" disabled={ask.isPending || question.trim().length < 3}>
            {t("ask")}
          </Button>
        </form>
      </section>
      <aside className="space-y-2" aria-label={t("history")}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t("history")}</h3>
          <button type="button" className="text-sm text-accent underline" onClick={() => { setConversation(null); setMessages([]); }}>
            {t("new")}
          </button>
        </div>
        <ul className="space-y-1 text-sm">
          {(history.data ?? []).map((c) => (
            <li key={c.id}>
              <button type="button" className="w-full truncate text-left hover:underline" aria-current={c.id === conversation} onClick={() => void open(c.id)}>
                {c.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
