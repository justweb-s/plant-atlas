"use client";

import { useEffect, useMemo, useState } from "react";

type Question = { id: string; split: string; type: string; question: string; question_it: string; expected: string };
type Step = { text: string; quote: string | null; locator: string | null; sparql: string | null };
type Answer = { value: unknown; text: string; steps: Step[]; tokens: number };
type ApiError = { state: "not_built" | "not_cached"; detail: string };
type AnswerResponse = { mode: string; answer?: Answer; error?: ApiError; score?: number };
type Cell = { state: string; score?: number; value?: unknown };
type Row = { id: string; split: string; question: string; results: Record<string, Cell> };
type Ontology = {
  build: { n_classes: number; n_properties: number; n_triples: number; cost_usd: number; seconds: number } | null;
  build_error: ApiError | null;
  validation: { conforms: boolean; violations: string[] } | null;
  counts: Record<string, number> | null;
  turtle_available: boolean;
};

const MODES: { key: string; label: string }[] = [
  { key: "B", label: "Plant Atlas (B)" },
  { key: "rag", label: "Ricerca semplice (RAG)" },
  { key: "A", label: "Estrazione libera (A)" },
];

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

function mark(score?: number) {
  if (score === undefined) return "";
  return score === 1 ? "✓" : score > 0 ? "~" : "✗";
}

function why(e: ApiError) {
  return e.state === "not_built"
    ? "Non ancora costruito."
    : "Questa domanda, in questo giorno, non è ancora nella cache: serve la chiave del team.";
}

function show(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.join(" · ");
  if (typeof value === "boolean") return value ? "sì" : "no";
  return String(value);
}

export default function Home() {
  const [tab, setTab] = useState<"ask" | "board" | "onto">("ask");
  const [status, setStatus] = useState<{ fake: boolean; today: string } | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    fetch("/api/status").then((r) => r.json()).then(setStatus).catch(() => setDown(true));
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Plant Atlas</h1>
        <p className="mt-1 text-muted">
          Questa macchina si può usare oggi, e cosa devo fare entro quando? Ogni risposta viene da fatti che portano le
          parole della loro fonte.
        </p>
        {down && (
          <p className="mt-3 rounded-md border border-bad px-3 py-2 text-sm text-bad">
            Il server Python non risponde: avvialo con <code>python -m uvicorn server.main:app --port 8000</code>.
          </p>
        )}
        {status?.fake && (
          <p className="mt-3 rounded-md border border-warn px-3 py-2 text-sm text-warn">
            Modalità finta (ATLAS_FAKE=1): niente in questa pagina è un risultato reale.
          </p>
        )}
      </header>

      <nav className="mb-6 flex gap-1 border-b border-border" role="tablist">
        {([
          ["ask", "Chiedi"],
          ["board", "Tabellone"],
          ["onto", "Ontologia"],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === key ? "border-accent text-foreground" : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "ask" && <Ask today={status?.today} />}
      {tab === "board" && <Board />}
      {tab === "onto" && <OntologyView />}
    </main>
  );
}

function Ask({ today }: { today?: string }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [cq, setCq] = useState("CQ11");
  const [free, setFree] = useState("");
  const [day, setDay] = useState("");
  const [results, setResults] = useState<Record<string, AnswerResponse | "loading">>({});

  useEffect(() => {
    fetch("/api/questions").then((r) => r.json()).then((qs: Question[]) => setQuestions(qs.filter((q) => q.split === "design")));
  }, []);

  const current = useMemo(() => questions.find((q) => q.id === cq), [questions, cq]);

  async function ask() {
    const question = free.trim() || current?.question;
    if (!question) return;
    const as_of = day && day !== today ? day : null;
    const pending: Record<string, "loading"> = {};
    MODES.forEach((m) => (pending[m.key] = "loading"));
    setResults(pending);
    await Promise.all(
      MODES.map(async (m) => {
        try {
          const r = await post<AnswerResponse>("/api/answer", { question, mode: m.key, as_of, cq: free.trim() ? null : cq });
          setResults((prev) => ({ ...prev, [m.key]: r }));
        } catch {
          setResults((prev) => ({ ...prev, [m.key]: { mode: m.key, error: { state: "not_cached", detail: "errore" } } }));
        }
      }),
    );
  }

  return (
    <section>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="text-sm">
          <span className="text-muted">Una domanda scritta prima di costruire</span>
          <select
            className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2"
            value={cq}
            onChange={(e) => setCq(e.target.value)}
          >
            {questions.map((q) => (
              <option key={q.id} value={q.id}>
                {q.id} · {q.question_it}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-muted">Risposta al giorno</span>
          <input
            type="date"
            className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2"
            value={day || today || ""}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
      </div>
      <label className="mt-3 block text-sm">
        <span className="text-muted">…oppure una domanda tua, in inglese (serve la chiave se nessuno l&apos;ha mai fatta)</span>
        <input
          className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2"
          value={free}
          onChange={(e) => setFree(e.target.value)}
          placeholder="Can the vehicle lift still be self-certified after 20 January 2027?"
        />
      </label>
      <button onClick={ask} className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
        Chiedi
      </button>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {MODES.map((m) => (
          <AnswerCard key={m.key} label={m.label} result={results[m.key]} />
        ))}
      </div>
      {current && !free.trim() && (
        <p className="mt-4 text-sm text-muted">
          <span className="font-medium text-foreground">Risposta attesa:</span> {current.expected}
        </p>
      )}
    </section>
  );
}

function AnswerCard({ label, result }: { label: string; result?: AnswerResponse | "loading" }) {
  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <h2 className="flex items-center justify-between font-medium">
        {label}
        {result && result !== "loading" && result.score !== undefined && (
          <span className={result.score === 1 ? "text-ok" : result.score > 0 ? "text-warn" : "text-bad"}>
            {mark(result.score)}
          </span>
        )}
      </h2>
      {!result && <p className="mt-2 text-sm text-muted">—</p>}
      {result === "loading" && <p className="mt-2 text-sm text-muted">Sto cercando nei fatti in vigore…</p>}
      {result && result !== "loading" && result.error && <p className="mt-2 text-sm text-muted">{why(result.error)}</p>}
      {result && result !== "loading" && result.answer && (
        <div className="mt-2 text-sm">
          {result.answer.value === null ? (
            <p className="rounded-md border border-border px-2 py-1 text-muted">
              Non lo so: nessun fatto in vigore risponde a questa domanda.
            </p>
          ) : (
            <p className="font-mono text-xs text-muted">Valore: {show(result.answer.value)}</p>
          )}
          <p className="mt-2">{result.answer.text}</p>
          {result.answer.steps.length > 0 && (
            <ol className="mt-3 space-y-2">
              {result.answer.steps.map((s, i) => (
                <li key={i}>
                  <details className="rounded-md border border-border px-2 py-1">
                    <summary className="cursor-pointer">{s.text}</summary>
                    {s.locator && <p className="mt-1 text-xs font-semibold">{s.locator}</p>}
                    {s.quote && <blockquote className="mt-1 border-l-2 border-accent pl-2 text-xs">“{s.quote}”</blockquote>}
                  </details>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </article>
  );
}

function Board() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [rows, setRows] = useState<Record<string, Row>>({});
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch("/api/questions").then((r) => r.json()).then(setQuestions);
  }, []);

  async function run() {
    setRunning(true);
    setRows({});
    for (const q of questions) {
      const row: Row = await fetch(`/api/score/${q.id}`).then((r) => r.json());
      setRows((prev) => ({ ...prev, [q.id]: row }));
    }
    setRunning(false);
  }

  const cell = (c?: Cell) => {
    if (!c) return <span className="text-muted">·</span>;
    if (c.state === "not_built") return <span className="text-muted">—</span>;
    if (c.state === "not_cached") return <span className="text-muted">…</span>;
    if (c.state === "unknown") return <span className="text-warn">?</span>;
    const s = c.score ?? 0;
    return <span className={s === 1 ? "text-ok" : s > 0 ? "text-warn" : "text-bad"}>{mark(s)}</span>;
  };

  const totals = MODES.map((m) => {
    const got = Object.values(rows).map((r) => r.results[m.key]).filter((c) => c && c.score !== undefined);
    return { ...m, right: got.filter((c) => c.score === 1).length, answered: got.length };
  });

  return (
    <section>
      <p className="text-sm text-muted">
        Le domande scritte prima di costruire, poste a ogni metodo. Le domande tenute da parte (heldout) non le ha mai
        viste nessuna strategia.
      </p>
      <button
        onClick={run}
        disabled={running || questions.length === 0}
        className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {running ? "Calcolo…" : "Calcola il tabellone"}
      </button>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {totals.map((t) => (
          <div key={t.key} className="rounded-lg border border-border bg-surface p-4">
            <p className="text-sm text-muted">{t.label}</p>
            <p className="mt-1 text-2xl font-semibold">
              {t.answered ? `${t.right}/${t.answered}` : "—"}
            </p>
            <p className="text-xs text-muted">giuste su quelle a cui ha risposto</p>
          </div>
        ))}
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              <th className="py-2 pr-3">CQ</th>
              <th className="py-2 pr-3">Domanda</th>
              {MODES.map((m) => (
                <th key={m.key} className="py-2 pr-3 text-center">
                  {m.key === "rag" ? "RAG" : m.key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.id} className="border-b border-border">
                <td className="py-2 pr-3 font-mono text-xs">
                  {q.id}
                  {q.split === "heldout" && <span className="ml-1 text-muted">(heldout)</span>}
                </td>
                <td className="py-2 pr-3">{q.question_it}</td>
                {MODES.map((m) => (
                  <td key={m.key} className="py-2 pr-3 text-center text-base">
                    {cell(rows[q.id]?.results[m.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-muted">
          ✓ giusta · ~ in parte · ✗ sbagliata · ? «non lo so» · … non ancora nella cache · — non ancora costruito
        </p>
      </div>
    </section>
  );
}

const REASONS: Record<string, string> = {
  rejected_no_anchor: "la citazione non è nel testo",
  rejected_missing_condition: "il testo ha un «se» o «salvo» che il fatto ha perso",
  rejected_value_not_in_quote: "il valore non è nelle parole citate",
  rejected_not_in_schema: "relazione fuori dallo schema",
};

function OntologyView() {
  const [strategy, setStrategy] = useState<"A" | "B">("B");
  const [loaded, setLoaded] = useState<{ strategy: string; data: Ontology } | null>(null);

  useEffect(() => {
    fetch(`/api/ontology/${strategy}`)
      .then((r) => r.json())
      .then((data: Ontology) => setLoaded({ strategy, data }));
  }, [strategy]);

  const data = loaded?.strategy === strategy ? loaded.data : null;
  const counts = data?.counts;
  return (
    <section>
      <div className="flex gap-2">
        {(["B", "A"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStrategy(s)}
            className={`rounded-md border px-3 py-1 text-sm ${strategy === s ? "border-accent" : "border-border text-muted"}`}
          >
            Strategia {s}
          </button>
        ))}
      </div>
      {!data && <p className="mt-4 text-sm text-muted">Carico l&apos;ontologia…</p>}
      {data?.build_error && <p className="mt-4 text-sm text-muted">{why(data.build_error)}</p>}
      {data?.build && (
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          {[
            ["classi", data.build.n_classes],
            ["proprietà", data.build.n_properties],
            ["triple", data.build.n_triples.toLocaleString("it-IT")],
            ["costo della costruzione", `$${data.build.cost_usd}`],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg border border-border bg-surface p-4">
              <p className="text-sm text-muted">{k}</p>
              <p className="mt-1 text-2xl font-semibold">{v}</p>
            </div>
          ))}
        </div>
      )}
      {counts && (
        <div className="mt-6 rounded-lg border border-border bg-surface p-4">
          <h2 className="font-medium">Nessuna citazione, nessun fatto</h2>
          <p className="mt-1 text-sm text-muted">
            Il modello propone un fatto indicando una frase; il codice controlla parola per parola che la frase ci sia.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-4">
            {[
              ["proposti dal modello", counts.proposed_total],
              ["ancorati al testo", counts.anchored],
              ["rifiutati", counts.rejected],
              ["corretti dalla rettifica", counts.corrections_applied ?? counts.status_closed],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <p className="text-sm text-muted">{k}</p>
                <p className="text-xl font-semibold">{v ?? 0}</p>
              </div>
            ))}
          </div>
          <ul className="mt-4 space-y-1 text-sm">
            {Object.entries(REASONS).map(([key, label]) =>
              counts[key] ? (
                <li key={key} className="flex items-center gap-3">
                  <span className="w-10 text-right font-mono">{counts[key]}</span>
                  <span
                    className="h-2 rounded bg-bad"
                    style={{ width: `${Math.max(4, (counts[key] / (counts.rejected || 1)) * 240)}px` }}
                  />
                  <span className="text-muted">{label}</span>
                </li>
              ) : null,
            )}
          </ul>
        </div>
      )}
      {data?.validation && (
        <div className="mt-6">
          <h2 className="font-medium">
            Vincoli SHACL:{" "}
            {data.validation.conforms ? (
              <span className="text-ok">rispettati</span>
            ) : (
              <span className="text-bad">{data.validation.violations.length} violazioni</span>
            )}
          </h2>
          <ul className="mt-2 space-y-1 text-sm">
            {data.validation.violations.map((v, i) => (
              <li key={i} className="rounded-md border border-border bg-surface px-2 py-1 font-mono text-xs">
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data?.turtle_available && (
        <a
          href={`/api/ontology/${strategy}/turtle`}
          className="mt-6 inline-block rounded-md border border-accent px-4 py-2 text-sm text-accent"
        >
          Scarica il file Turtle
        </a>
      )}
    </section>
  );
}
