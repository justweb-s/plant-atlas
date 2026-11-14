"use client";

import { useEffect, useRef, useState } from "react";
import { AnswerResponse, Question, itDate, post, show, why } from "../lib";
import { IconArrow, IconDoc, IconSearch, IconShield } from "./icons";

const GROUPS: { title: string; hint: string; ids: string[] }[] = [
  { title: "Scadenze e verifiche", hint: "cosa fare, ed entro quando", ids: ["CQ21", "CQ22", "CQ26", "CQ11", "CQ12", "CQ08"] },
  { title: "La legge che cambia", hint: "quale testo vale oggi", ids: ["CQ24", "CQ09", "CQ10", "CQ13", "CQ14", "CQ15"] },
  { title: "Obblighi e conformità", hint: "chi deve fare cosa", ids: ["CQ25", "CQ23", "CQ27", "CQ06", "CQ07", "CQ01", "CQ02", "CQ03", "CQ04", "CQ05"] },
];

const SOURCES: Record<string, string> = {
  REG: "Regolamento (UE) 2023/1230",
  DIR: "Direttiva 2006/42/CE",
  CORR: "Rettifica del Regolamento (UE) 2023/1230",

  DM2011: "DM 11 aprile 2011",
  DLGSALLVII: "D.Lgs. 81/08",
  "igea-equipment": "Elenco apparecchi IGEA",
  "ur5e-manual": "Manuale UR5e",
  "ur10e-manual": "Manuale UR10e",
  "nanoscan3-manual": "Manuale nanoScan3",
  "mastar-manual": "Manuale MA STAR 3.5 A",
};

function sourceName(locator: string) {
  const [doc, ...rest] = locator.split(", ");
  return [SOURCES[doc] ?? (/^DLGS/.test(doc) ? "D.Lgs. 81/08" : doc), ...rest].join(", ");
}

type Asked = { label: string; question: string; cq: string | null; expected?: string; as_of: string | null };
type Result = AnswerResponse | "loading";

export default function Ask({ today }: { today?: string }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [text, setText] = useState("");
  const [day, setDay] = useState("");
  const [asked, setAsked] = useState<Asked | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [others, setOthers] = useState<Record<string, Result> | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/questions")
      .then((r) => r.json())
      .then((qs: Question[]) => setQuestions(qs.filter((q) => q.split === "design")))
      .catch(() => {});
  }, []);

  async function ask(q: Question | null, free?: string) {
    const question = q ? q.question : (free ?? "").trim();
    if (!question) return;
    const as_of = day && day !== today ? day : null;
    const a: Asked = { label: q ? q.question_it : question, question, cq: q?.id ?? null, expected: q?.expected, as_of };
    setAsked(a);
    setResult("loading");
    setOthers(null);
    setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    try {
      setResult(await post<AnswerResponse>("/api/answer", { question, mode: "B", as_of, cq: a.cq, lang: "it" }));
    } catch {
      setResult({ mode: "B", error: { state: "not_cached", detail: "errore" } });
    }
  }

  async function compare() {
    if (!asked) return;
    setOthers({ rag: "loading", A: "loading" });
    for (const mode of ["rag", "A"]) {
      post<AnswerResponse>("/api/answer", { question: asked.question, mode, as_of: asked.as_of, cq: asked.cq })
        .catch((): AnswerResponse => ({ mode, error: { state: "not_cached", detail: "errore" } }))
        .then((r) => setOthers((prev) => ({ ...(prev ?? {}), [mode]: r })));
    }
  }

  const byId = Object.fromEntries(questions.map((q) => [q.id, q]));

  return (
    <section>
      <div className="mx-auto max-w-3xl pt-6 text-center sm:pt-10">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">
          Cosa vuoi sapere <span className="gradient-text">sulle tue macchine?</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-muted sm:text-lg">
          Fai una domanda. La risposta arriva con le parole esatte della legge o del manuale da cui viene. Se non lo
          sappiamo, te lo diciamo.
        </p>

        <form
          className="card mt-8 flex items-center gap-2 p-2 pl-4 text-left"
          onSubmit={(e) => {
            e.preventDefault();
            ask(null, text);
          }}
        >
          <IconSearch className="h-5 w-5 shrink-0 text-muted" />
          <input
            aria-label="La tua domanda"
            className="min-w-0 flex-1 bg-transparent py-3 text-base outline-none placeholder:text-muted"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Scrivi la tua domanda (per ora in inglese)…"
          />
          <button
            type="submit"
            disabled={!text.trim()}
            className="flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white transition disabled:opacity-40 dark:text-background"
          >
            Chiedi <IconArrow className="h-4 w-4" />
          </button>
        </form>

        <label className="mt-3 inline-flex items-center gap-2 text-sm text-muted">
          Rispondi com&apos;era il giorno
          <input
            type="date"
            className="rounded-lg border border-border bg-surface px-2 py-1 text-foreground"
            value={day || today || ""}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
      </div>

      <div ref={resultRef} className="scroll-mt-24">
        {asked && result && (
          <AnswerPanel asked={asked} result={result} others={others} onCompare={compare} today={today} />
        )}
      </div>

      <div className="mt-12">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Oppure parti da qui</h2>
        <div className="mt-4 grid gap-6 lg:grid-cols-3">
          {GROUPS.map((g) => (
            <div key={g.title}>
              <p className="font-semibold">{g.title}</p>
              <p className="text-sm text-muted">{g.hint}</p>
              <div className="mt-3 space-y-2">
                {g.ids
                  .map((id) => byId[id])
                  .filter(Boolean)
                  .map((q) => (
                    <button
                      key={q.id}
                      onClick={() => {
                        setText("");
                        ask(q);
                      }}
                      className={`card lift flex w-full items-start gap-3 p-3 text-left text-sm ${
                        asked?.cq === q.id ? "border-accent" : ""
                      }`}
                    >
                      <span className="flex-1">{q.question_it}</span>
                      <IconArrow className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                    </button>
                  ))}
                {questions.length === 0 &&
                  [0, 1, 2].map((i) => <div key={i} className="h-14 animate-pulse rounded-2xl bg-surface-2" />)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function AnswerPanel({
  asked,
  result,
  others,
  onCompare,
  today,
}: {
  asked: Asked;
  result: Result;
  others: Record<string, Result> | null;
  onCompare: () => void;
  today?: string;
}) {
  const [all, setAll] = useState(false);
  const answer = result !== "loading" ? result.answer : undefined;
  const error = result !== "loading" ? result.error : undefined;
  const score = result !== "loading" ? result.score : undefined;
  const unknown = answer && answer.value === null;
  const steps = answer?.steps ?? [];
  const shown = all ? steps : steps.slice(0, 4);
  const short = answer && !unknown ? show(answer.value) : "";
  const isShort = short.length > 0 && short.length <= 40;

  return (
    <article className="card rise mx-auto mt-10 max-w-6xl overflow-hidden">
      <div className="border-b border-border bg-surface-2 px-5 py-4 sm:px-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">
          La tua domanda · {asked.as_of ? `al ${itDate(asked.as_of)}` : today ? `oggi, ${itDate(today)}` : "oggi"}
        </p>
        <p className="mt-1 text-lg font-medium">{asked.label}</p>
      </div>

      <div className="px-5 py-6 sm:px-7">
        {result === "loading" && (
          <p className="flex items-center gap-3 text-muted">
            <span className="dots flex gap-1">
              <span className="h-2 w-2 rounded-full bg-accent" />
              <span className="h-2 w-2 rounded-full bg-accent" />
              <span className="h-2 w-2 rounded-full bg-accent" />
            </span>
            Cerco tra i fatti in vigore…
          </p>
        )}

        {error && (
          <div className="rounded-xl bg-warn-soft p-4 text-warn">
            <p className="font-semibold">Non posso rispondere adesso</p>
            <p className="mt-1 text-sm">{why(error)}</p>
          </div>
        )}

        {unknown && (
          <div className="rounded-xl bg-surface-2 p-4">
            <p className="text-xl font-semibold">Non lo so.</p>
            <p className="mt-1 text-sm text-muted">
              Nessun fatto in vigore, con la sua fonte, risponde a questa domanda. Preferiamo dirtelo piuttosto che
              inventare una risposta.
            </p>
            {answer?.text && <p className="mt-3 text-sm">{answer.text}</p>}
          </div>
        )}

        {answer && !unknown && (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-accent">Risposta</p>
              {score !== undefined &&
                (score === 1 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-ok-soft px-3 py-1 text-xs font-semibold text-ok">
                    <IconShield className="h-3.5 w-3.5" /> Coincide con la risposta attesa
                  </span>
                ) : (
                  <span className="rounded-full bg-warn-soft px-3 py-1 text-xs font-semibold text-warn">
                    {score > 0 ? "Coincide solo in parte con la risposta attesa" : "Diversa dalla risposta attesa"}
                  </span>
                ))}
            </div>
            {isShort && <p className="mt-2 text-4xl font-semibold tracking-tight">{short}</p>}
            {!isShort && Array.isArray(answer.value) && (
              <ul className="mt-3 flex flex-wrap gap-2">
                {(answer.value as unknown[]).map((v, i) => (
                  <li key={i} className="rounded-lg bg-accent-soft px-3 py-1 text-sm font-medium">
                    {String(v)}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-base leading-relaxed">{answer.text}</p>
            {score !== undefined && score < 1 && asked.expected && (
              <p className="mt-3 rounded-xl bg-warn-soft p-3 text-sm">
                <span className="font-semibold">Risposta attesa:</span> {asked.expected}
              </p>
            )}
          </>
        )}
      </div>

      {steps.length > 0 && (
        <div className="border-t border-border px-5 py-6 sm:px-7">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">
            Da dove viene · {steps.length} {steps.length === 1 ? "passo" : "passi"}, ognuno con la sua fonte
          </p>
          <ol className="mt-4 grid gap-4 lg:grid-cols-2">
            {shown.map((s, i) => (
              <li key={i} className="flex gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  {(s.quote || s.locator) && (
                    <div className="rounded-xl border-l-4 border-accent bg-surface-2 p-3">
                      {s.locator && (
                        <p className="flex items-center gap-1.5 text-xs font-semibold text-accent">
                          <IconDoc className="h-3.5 w-3.5" /> {sourceName(s.locator)}
                        </p>
                      )}
                      {s.quote && <p className="mt-1 text-sm leading-relaxed">«{s.quote}»</p>}
                    </div>
                  )}
                  <p className="mt-1.5 text-xs text-muted">Fatto registrato: {s.text}</p>
                </div>
              </li>
            ))}
          </ol>
          {steps.length > 4 && (
            <button onClick={() => setAll(!all)} className="mt-4 text-sm font-semibold text-accent">
              {all ? "Mostra meno" : `Mostra tutti i ${steps.length} passi`}
            </button>
          )}
        </div>
      )}

      {result !== "loading" && (
        <div className="border-t border-border bg-surface-2 px-5 py-4 sm:px-7">
          {!others ? (
            <button onClick={onCompare} className="text-sm font-semibold text-accent">
              Confronta con gli altri metodi →
            </button>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["rag", "Ricerca semplice nei documenti"],
                ["A", "Estrazione libera, senza schema"],
              ].map(([key, label]) => {
                const r = others[key];
                return (
                  <div key={key} className="rounded-xl border border-border bg-surface p-3 text-sm">
                    <p className="font-semibold">{label}</p>
                    {(!r || r === "loading") && <p className="mt-1 text-muted">…</p>}
                    {r && r !== "loading" && r.error && <p className="mt-1 text-muted">{why(r.error)}</p>}
                    {r && r !== "loading" && r.answer && (
                      <p className="mt-1">
                        {r.answer.value === null ? "Non lo so." : r.answer.text}
                        {r.score !== undefined && (
                          <span className={`ml-2 font-semibold ${r.score === 1 ? "text-ok" : "text-warn"}`}>
                            {r.score === 1 ? "giusta" : r.score > 0 ? "in parte" : "sbagliata"}
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
