"use client";

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

export default function Home() {
  const [tab, setTab] = useState<Tab>("ask");
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
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition sm:px-4 ${
                  tab === key ? "bg-surface text-foreground shadow-sm" : "text-muted hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

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
