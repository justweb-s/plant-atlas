"use client";

import { useEffect, useState } from "react";
import { Fact, Machine, itDate } from "../lib";
import { IconClock, IconDoc, IconLift, IconRobot, IconScan } from "./icons";

const INFO: Record<string, { kind: string; role: string; icon: "robot" | "scan" | "lift" }> = {
  UR5e: { kind: "Braccio robotico collaborativo", role: "Il braccio che lavora oggi nella cella", icon: "robot" },
  UR10e: { kind: "Braccio robotico collaborativo", role: "Il braccio più grande che sostituirà l'UR5e", icon: "robot" },
  nanoScan3: { kind: "Laser scanner di sicurezza", role: "Sorveglia l'area pericolosa attorno al braccio", icon: "scan" },
  "MA STAR 3.5 A": { kind: "Ponte sollevatore a due colonne", role: "Il ponte nella baia accanto alla cella", icon: "lift" },
};

const EVERY: Record<string, string> = { P1Y: "ogni anno", P6M: "ogni 6 mesi", P3M: "ogni 3 mesi", P1M: "ogni mese" };

function label(f: Fact): { name: string; value: string } {
  const v = String(f.value);
  switch (f.fact) {
    case "reach_mm":
      return { name: "Sbraccio", value: `${v} mm` };
    case "max_payload_kg":
      return { name: "Carico massimo", value: `${v} kg` };
    case "rated_load_kg":
      return { name: "Portata", value: `${Number(v).toLocaleString("it-IT")} kg` };
    case "legal_status":
      return { name: "Per la legge è", value: v === "partly completed machinery" ? "una quasi-macchina" : v };
    case "declaration":
      return {
        name: "Dichiarazione",
        value: v.startsWith("Declaration of Incorporation")
          ? "Dichiarazione di incorporazione (Direttiva 2006/42/CE, All. II B)"
          : "Dichiarazione CE di conformità (Direttiva 2006/42/CE), senza organismo notificato",
      };
    case "put_into_service_only_when":
      return { name: "Messa in servizio", value: "solo dopo l'integrazione in una macchina completa e conforme" };
    case "minimum_distance_formula":
      return { name: "Distanza minima", value: v.replace("hazardous area protection", "protezione dell'area pericolosa") };
    case "cro_default_mm":
      return { name: "Supplemento CRO", value: `${Number(v).toLocaleString("it-IT")} mm` };
    case "max_resolution_hazardous_area_mm":
      return { name: "Risoluzione massima (area pericolosa)", value: `${v} mm` };
    case "regular_check_interval":
      return { name: "Prova regolare", value: EVERY[v] ?? v };
    case "load_nut_check_interval":
      return { name: "Controllo del dado portante", value: EVERY[v] ?? v };
    case "harmonised_standard":
      return { name: "Norma armonizzata", value: v };
    case "declaration_date":
      return { name: "Data della dichiarazione", value: itDate(v) };
    default:
      return { name: f.fact.replaceAll("_", " "), value: v };
  }
}

const Icon = ({ kind, className }: { kind: string; className?: string }) =>
  kind === "robot" ? <IconRobot className={className} /> : kind === "scan" ? <IconScan className={className} /> : <IconLift className={className} />;

export default function CellView() {
  const [data, setData] = useState<{ machines: Machine[]; not_yet: string[] } | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/machines")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="mt-10 text-center text-muted">Non riesco a leggere le macchine della cella.</p>;
  if (!data)
    return (
      <div className="mt-10 grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-64 animate-pulse rounded-2xl bg-surface-2" />
        ))}
      </div>
    );

  const recurring = data.machines.flatMap((m) =>
    m.facts.filter((f) => f.fact.endsWith("_interval")).map((f) => ({ machine: m.id, ...label(f), quote: f.quote })),
  );
  const partly = data.machines.filter((m) => m.facts.some((f) => f.value === "partly completed machinery"));
  const nFacts = data.machines.reduce((n, m) => n + m.facts.length, 0);

  return (
    <section className="pt-6">
      <h1 className="text-3xl font-semibold tracking-tight">La tua cella</h1>
      <p className="mt-2 max-w-2xl text-muted">
        {data.machines.length} macchine reali e {nFacts} fatti presi dai manuali ufficiali dei costruttori. Tocca un
        fatto per leggere le parole del manuale.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <p className="flex items-center gap-2 font-semibold">
            <IconClock className="h-5 w-5 text-accent" /> Da fare periodicamente
          </p>
          <ul className="mt-3 space-y-3">
            {recurring.map((r) => (
              <li key={r.machine + r.name} className="flex items-start justify-between gap-3 text-sm">
                <span>
                  <span className="font-medium">{r.name}</span>
                  <span className="block text-muted">{r.machine}</span>
                </span>
                <span className="shrink-0 rounded-full bg-accent-soft px-3 py-1 font-semibold text-accent">{r.value}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="card border-warn/40 p-5">
          <p className="font-semibold text-warn">Attenzione: quasi-macchine</p>
          <p className="mt-2 text-sm">
            {partly.map((m) => m.id).join(" e ")} {partly.length === 1 ? "è una quasi-macchina" : "sono quasi-macchine"}:
            il costruttore dà una dichiarazione di incorporazione, non di conformità. La conformità dell&apos;insieme
            tocca a chi integra la cella.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {data.machines.map((m) => {
          const info = INFO[m.id] ?? { kind: m.type, role: m.cell_role, icon: "robot" as const };
          const maker = m.facts[0]?.source?.manufacturer;
          const url = m.facts[0]?.source?.url;
          return (
            <article key={m.id} className="card p-5">
              <div className="flex items-start gap-4">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <Icon kind={info.icon} className="h-6 w-6" />
                </span>
                <div className="min-w-0">
                  <h2 className="text-xl font-semibold">{m.id}</h2>
                  <p className="text-sm text-muted">
                    {info.kind}
                    {maker ? ` · ${maker}` : ""}
                  </p>
                  <p className="mt-1 text-sm">{info.role}</p>
                </div>
              </div>
              <ul className="mt-4 divide-y divide-border">
                {m.facts.map((f) => {
                  const l = label(f);
                  return (
                    <li key={f.fact}>
                      <details className="group py-2.5">
                        <summary className="flex items-baseline justify-between gap-4 text-sm">
                          <span className="text-muted">{l.name}</span>
                          <span className="text-right font-medium group-open:text-accent">{l.value}</span>
                        </summary>
                        <p className="mt-2 rounded-xl border-l-4 border-accent bg-surface-2 p-3 text-sm italic text-muted">
                          «{f.quote}»
                          <span className="mt-1 block text-xs not-italic">
                            {f.source?.title}
                            {f.page ? `, p. ${f.page}` : ""}
                          </span>
                        </p>
                      </details>
                    </li>
                  );
                })}
              </ul>
              {url && (
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-accent"
                >
                  <IconDoc className="h-4 w-4" /> Apri il manuale ufficiale
                </a>
              )}
            </article>
          );
        })}
      </div>

      <div className="mt-6 rounded-2xl border border-dashed border-border p-5 text-sm text-muted">
        <p className="font-semibold text-foreground">Cosa non sappiamo ancora</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Robot mobile (MiR250): nessun manuale sul sito del costruttore, solo copie di terzi.</li>
          <li>Pressa o saldatrice: nessun manuale raccolto.</li>
          <li>
            Il ponte MA STAR non indica un organismo notificato: che sia stato autocertificato dipende dalla norma EN
            1493:2022, ancora da verificare.
          </li>
        </ul>
      </div>
    </section>
  );
}
