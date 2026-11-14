"use client";

import { useEffect, useState } from "react";
import { Cell, Ontology, Question, Row, why } from "../lib";
import { IconDownload } from "./icons";

const METHODS: { key: string; label: string; hint: string }[] = [
  { key: "B", label: "Plant Atlas", hint: "fatti con la loro fonte" },
  { key: "rag", label: "Ricerca semplice", hint: "cerca nei documenti" },
  { key: "A", label: "Estrazione libera", hint: "senza schema" },
];

const REASONS: Record<string, string> = {
  rejected_no_anchor: "la citazione non è nel testo",
  rejected_missing_condition: "il testo ha un «se» o un «salvo» che il fatto aveva perso",
  rejected_value_not_in_quote: "il valore non è nelle parole citate",
  rejected_not_in_schema: "relazione fuori dallo schema",
};

function Pill({ c }: { c?: Cell }) {
  const base = "inline-block min-w-20 rounded-full px-2.5 py-1 text-xs font-semibold";
  if (!c) return <span className={`${base} bg-surface-2 text-muted`}>·</span>;
  if (c.state === "not_built") return <span className={`${base} text-muted`}>non costruito</span>;
  if (c.state === "not_cached") return <span className={`${base} bg-surface-2 text-muted`}>da preparare</span>;
  if (c.state === "unknown" && c.score === 1) return <span className={`${base} bg-ok-soft text-ok`}>giusta: non lo so</span>;
  if (c.state === "unknown") return <span className={`${base} bg-surface-2`}>non lo so</span>;
  const s = c.score ?? 0;
  if (s === 1) return <span className={`${base} bg-ok-soft text-ok`}>giusta</span>;
  if (s > 0) return <span className={`${base} bg-warn-soft text-warn`}>in parte</span>;
  return <span className={`${base} bg-bad-soft text-bad`}>sbagliata</span>;
}

export default function Trust() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [rows, setRows] = useState<Record<string, Row>>({});
  const [done, setDone] = useState(false);
  const [onto, setOnto] = useState<Ontology | null>(null);

  useEffect(() => {
    let stop = false;
    fetch("/api/ontology/B").then((r) => r.json()).then(setOnto).catch(() => {});
    (async () => {
      const qs: Question[] = await fetch("/api/questions").then((r) => r.json());
      if (stop) return;
      setQuestions(qs);
      for (const q of qs) {
        if (stop) return;
        try {
          const row: Row = await fetch(`/api/score/${q.id}`).then((r) => r.json());
          setRows((prev) => ({ ...prev, [q.id]: row }));
        } catch {}
      }
      setDone(true);
    })().catch(() => {});
    return () => {
      stop = true;
    };
  }, []);

  const totals = METHODS.map((m) => {
    const cells = Object.values(rows).map((r) => r.results[m.key]).filter(Boolean);
    const scored = cells.filter((c) => c.score !== undefined);
    return {
      ...m,
      built: cells.length === 0 || cells.some((c) => c.state !== "not_built"),
      right: scored.filter((c) => c.score === 1).length,
      part: scored.filter((c) => (c.score ?? 0) > 0 && c.score !== 1).length,
      wrong: scored.filter((c) => c.score === 0 && c.state === "answered").length,
      unknown: cells.filter((c) => c.state === "unknown").length,
      scored: scored.length,
    };
  });
  const counts = onto?.counts;
  const progress = questions.length ? Math.round((Object.keys(rows).length / questions.length) * 100) : 0;

  return (
    <section className="pt-6">
      <h1 className="text-3xl font-semibold tracking-tight">Perché fidarsi</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Le domande le abbiamo scritte prima di costruire, con la risposta giusta accanto. Qui vedi come va ogni metodo,
        anche dove sbaglia.
      </p>

      {counts && (
        <div className="card mt-6 p-6">
          <h2 className="text-lg font-semibold">Nessuna citazione, nessun fatto</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Il modello propone un fatto e indica la frase da cui viene. Il codice controlla, parola per parola, che la
            frase sia davvero nel testo. Se non c&apos;è, il fatto non entra.
          </p>
          <div className="mt-5 grid items-center gap-4 sm:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <Big n={counts.proposed_total} label="fatti proposti dal modello" />
            <span className="hidden text-2xl text-muted sm:block">→</span>
            <Big n={counts.anchored} label="entrati, con la loro citazione" tone="ok" />
            <span className="hidden text-2xl text-muted sm:block">+</span>
            <Big n={counts.rejected} label="rifiutati dal controllo" tone="bad" />
          </div>
          <ul className="mt-5 space-y-2 text-sm">
            {Object.entries(REASONS).map(([key, text]) =>
              counts[key] ? (
                <li key={key} className="grid grid-cols-[2.5rem_8rem_1fr] items-center gap-3">
                  <span className="text-right font-semibold">{counts[key]}</span>
                  <span className="h-2 overflow-hidden rounded-full bg-surface-2">
                    <span
                      className="block h-full rounded-full bg-bad"
                      style={{ width: `${Math.max(6, (counts[key] / (counts.rejected || 1)) * 100)}%` }}
                    />
                  </span>
                  <span className="text-muted">{text}</span>
                </li>
              ) : null,
            )}
          </ul>
          {(counts.corrections_applied ?? 0) > 0 && (
            <p className="mt-4 text-sm">
              <span className="font-semibold">{counts.corrections_applied} fatti</span> sono stati corretti dalla
              rettifica ufficiale: i vecchi restano, chiusi, con la data.
            </p>
          )}
        </div>
      )}

      <h2 className="mt-10 text-lg font-semibold">Il tabellone</h2>
      {!done && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        {totals.map((t) => (
          <div key={t.key} className={`card p-5 ${t.key === "B" ? "border-accent" : ""}`}>
            <p className="font-semibold">{t.label}</p>
            <p className="text-sm text-muted">{t.hint}</p>
            {t.built ? (
              <>
                <p className="mt-3 text-4xl font-semibold tracking-tight">
                  {t.scored ? t.right : "—"}
                  {t.scored > 0 && <span className="text-lg font-medium text-muted"> giuste su {t.scored}</span>}
                </p>
                {t.scored > 0 && (
                  <p className="mt-1 text-sm text-muted">
                    {t.part} in parte · {t.wrong} sbagliate · {t.unknown} «non lo so»
                  </p>
                )}
              </>
            ) : (
              <p className="mt-3 text-sm text-muted">Non ancora costruito.</p>
            )}
          </div>
        ))}
      </div>

      <div className="card mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wider text-muted">
              <th className="px-4 py-3 font-semibold">Domanda</th>
              {METHODS.map((m) => (
                <th key={m.key} className="px-3 py-3 text-center font-semibold">
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">
                  {q.question_it}
                  <span className="ml-2 whitespace-nowrap text-xs text-muted">
                    {q.id}
                    {q.split === "heldout" && " · tenuta da parte"}
                  </span>
                </td>
                {METHODS.map((m) => (
                  <td key={m.key} className="px-3 py-3 text-center">
                    <Pill c={rows[q.id]?.results[m.key]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">
        «Tenuta da parte»: nessun metodo l&apos;ha vista mentre veniva costruito. «Da preparare»: la domanda non è ancora
        stata fatta al modello.
      </p>

      <h2 className="mt-10 text-lg font-semibold">L&apos;ontologia</h2>
      {onto?.build_error && <p className="mt-2 text-sm text-muted">{why(onto.build_error)}</p>}
      {onto?.build && (
        <div className="mt-4 grid gap-4 sm:grid-cols-4">
          {[
            ["classi", onto.build.n_classes],
            ["proprietà", onto.build.n_properties],
            ["triple", onto.build.n_triples.toLocaleString("it-IT")],
            ["costo per costruirla", `${onto.build.cost_usd.toLocaleString("it-IT")} $`],
          ].map(([k, v]) => (
            <div key={String(k)} className="card p-4">
              <p className="text-2xl font-semibold">{v}</p>
              <p className="text-sm text-muted">{k}</p>
            </div>
          ))}
        </div>
      )}
      {onto?.validation && (
        <details className="card mt-4 p-4">
          <summary className="flex items-center justify-between gap-3 text-sm font-semibold">
            <span>Controllo dei vincoli (SHACL)</span>
            {onto.validation.conforms ? (
              <span className="rounded-full bg-ok-soft px-3 py-1 text-xs text-ok">tutti rispettati</span>
            ) : (
              <span className="rounded-full bg-warn-soft px-3 py-1 text-xs text-warn">
                {onto.validation.violations.length} dati da sistemare · mostra
              </span>
            )}
          </summary>
          <ul className="mt-3 space-y-1">
            {onto.validation.violations.map((v, i) => (
              <li key={i} className="rounded-lg bg-surface-2 px-3 py-2 font-mono text-xs break-words">
                {v}
              </li>
            ))}
          </ul>
        </details>
      )}
      {onto?.build && (
        <a
          href="/api/ontology/B/view"
          target="_blank"
          rel="noreferrer"
          className="card lift mt-4 flex items-center justify-between gap-4 p-5"
        >
          <span>
            <span className="block font-semibold">Guarda l&apos;ontologia nel tempo</span>
            <span className="block text-sm text-muted">
              Sposta la data e vedi quali fatti sono in vigore, quali sono stati chiusi e come cambiano i 24 apparecchi.
            </span>
          </span>
          <span className="text-2xl text-accent">→</span>
        </a>
      )}
      {onto?.turtle_available && (
        <a
          href="/api/ontology/B/turtle"
          className="mt-4 inline-flex items-center gap-2 rounded-xl border border-accent px-4 py-2.5 text-sm font-semibold text-accent"
        >
          <IconDownload className="h-4 w-4" /> Scarica l&apos;ontologia (Turtle)
        </a>
      )}
    </section>
  );
}

function Big({ n, label, tone }: { n?: number; label: string; tone?: "ok" | "bad" }) {
  return (
    <div className="rounded-xl bg-surface-2 p-4">
      <p className={`text-3xl font-semibold tracking-tight ${tone === "ok" ? "text-ok" : tone === "bad" ? "text-bad" : ""}`}>
        {(n ?? 0).toLocaleString("it-IT")}
      </p>
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}
