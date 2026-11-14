import Link from "next/link";
import { IconShield } from "./icons";

// The ontology view is Core's generated page (ontology/B/dashboard.html), copied to public/atlas.html.
// Without /api/status on this origin it stays in "recorded answers" mode: that is the Vercel behaviour.
// It is the home page: it opens on #ask, at full height, with the menu to the other pages.
const LINKS = [
  ["ask", "Chiedi"],
  ["ontology", "Ontologia"],
  ["score", "Punteggio"],
  ["changes", "Cambi"],
  ["scenes", "Scene"],
] as const;

export default function AtlasView() {
  return (
    <div className="flex h-dvh flex-col">
      <header className="border-b border-border bg-background">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-2 sm:px-6">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white dark:text-background">
              <IconShield className="h-5 w-5" />
            </span>
            Plant Atlas
          </Link>
          <nav className="flex flex-wrap gap-1 rounded-xl bg-surface-2 p-1">
            {LINKS.map(([hash, label]) => (
              <a
                key={hash}
                // The view reads the hash only on load: the query makes the frame reload on each link.
                href={`/atlas.html?tab=${hash}#${hash}`}
                target="atlas-frame"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-muted transition hover:text-foreground"
              >
                {label}
              </a>
            ))}
            <Link href="/" className="rounded-lg px-3 py-1.5 text-sm font-medium text-muted transition hover:text-foreground">
              App per l&apos;RSPP
            </Link>
          </nav>
        </div>
      </header>
      <iframe
        name="atlas-frame"
        src="/atlas.html?tab=ask#ask"
        title="Ontologia di Plant Atlas"
        className="block w-full flex-1 border-0"
      />
    </div>
  );
}
