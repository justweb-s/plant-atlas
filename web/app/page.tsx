"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Ask from "./components/Ask";
import CellView from "./components/CellView";
import Trust from "./components/Trust";
import { IconShield } from "./components/icons";

const TABS = [
  ["ask", "Chiedi"],
  ["cell", "La tua cella"],
  ["trust", "Perché fidarsi"],
] as const;
type Tab = (typeof TABS)[number][0];

// Core's ontology view (public/atlas.html), shown under the header when «Ontologia» is on.
const VIEWS = [
  ["embed", "Fatti e confronto con il RAG"],
  ["docs", "Mappa dei documenti"],
] as const;
type View = (typeof VIEWS)[number][0];

const pill = (on: boolean) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition sm:px-4 ${
    on ? "bg-surface text-foreground shadow-sm" : "text-muted hover:text-foreground"
  }`;

export default function Home() {
  const [tab, setTab] = useState<Tab>("ask");
  const [atlas, setAtlas] = useState(false);
  const [view, setView] = useState<View>("embed");
  const [status, setStatus] = useState<{ fake: boolean; today: string } | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    fetch("/api/status")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setStatus)
      .catch(() => setDown(true));
  }, []);

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <button onClick={() => setTab("ask")} className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white dark:text-background">
              <IconShield className="h-5 w-5" />
            </span>
            Plant Atlas
          </button>
          <nav className="flex gap-1 rounded-xl bg-surface-2 p-1" role="tablist">
            {TABS.map(([key, label]) => (
              <button
                key={key}
                role="tab"
                aria-selected={tab === key}
                onClick={() => setTab(key)}
                className={pill(tab === key)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="flex gap-1 rounded-xl bg-surface-2 p-1">
            <button
              role="switch"
              aria-checked={atlas}
              onClick={() => setAtlas((on) => !on)}
              className={`flex items-center gap-2 ${pill(atlas)}`}
            >
              <span
                aria-hidden
                className={`relative inline-block h-4 w-7 rounded-full transition ${atlas ? "bg-accent" : "bg-border"}`}
              >
                <span
                  className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${atlas ? "left-3.5" : "left-0.5"}`}
                />
              </span>
              Ontologia
            </button>
          </div>
        </div>
        {atlas && (
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 pb-3 sm:px-6">
            <div className="flex gap-1 rounded-xl bg-surface-2 p-1" role="tablist">
              {VIEWS.map(([key, label]) => (
                <button key={key} role="tab" aria-selected={view === key} onClick={() => setView(key)} className={pill(view === key)}>
                  {label}
                </button>
              ))}
            </div>
            <Link href="/atlas" className="text-sm font-medium text-muted transition hover:text-foreground">
              Apri a tutta pagina
            </Link>
          </div>
        )}
      </header>

      {atlas && (
        <iframe
          key={view}
          // The view reads the hash only on load: the key and the query reload the frame on each switch.
          src={`/atlas.html?view=${view}#${view}`}
          title="Ontologia di Plant Atlas"
          className="block w-full border-0 border-b border-border"
          style={{ height: "max(800px, 80dvh)" }}
        />
      )}

      <main className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        {down && (
          <p className="mt-6 rounded-xl bg-bad-soft px-4 py-3 text-sm text-bad">
            Il motore non risponde. Avvialo con <code>python -m uvicorn server.main:app --port 8000</code> e ricarica la
            pagina.
          </p>
        )}
        {status?.fake && (
          <p className="mt-6 rounded-xl bg-warn-soft px-4 py-3 text-sm text-warn">
            Modalità di prova: i dati in questa pagina sono finti, non sono risultati reali.
          </p>
        )}
        {tab === "ask" && <Ask today={status?.today} />}
        {tab === "cell" && <CellView />}
        {tab === "trust" && <Trust />}
      </main>
    </>
  );
}
