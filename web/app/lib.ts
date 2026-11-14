export type Question = { id: string; split: string; type: string; question: string; question_it: string; expected: string };
export type Step = { text: string; quote: string | null; locator: string | null; sparql: string | null };
export type Answer = { value: unknown; text: string; steps: Step[]; tokens: number };
export type ApiError = { state: "not_built" | "not_cached"; detail: string };
export type AnswerResponse = { mode: string; answer?: Answer; error?: ApiError; score?: number };
export type Cell = { state: string; score?: number; value?: unknown };
export type Row = { id: string; split: string; question: string; results: Record<string, Cell> };
export type Ontology = {
  build: { n_classes: number; n_properties: number; n_triples: number; cost_usd: number; seconds: number } | null;
  build_error: ApiError | null;
  validation: { conforms: boolean; violations: string[] } | null;
  counts: Record<string, number> | null;
  turtle_available: boolean;
};
export type Fact = {
  fact: string;
  value: string | number;
  quote: string;
  page?: number;
  source: { title: string; manufacturer: string; url: string; pages: number } | null;
};
export type Machine = { id: string; type: string; cell_role: string; facts: Fact[] };

export async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export function show(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.join(" · ");
  if (typeof value === "boolean") return value ? "Sì" : "No";
  if (typeof value === "string" && /^(yes|true)$/i.test(value)) return "Sì";
  if (typeof value === "string" && /^(no|false)$/i.test(value)) return "No";
  return String(value);
}

export function why(e: ApiError) {
  return e.state === "not_built"
    ? "Questo metodo non è ancora stato costruito."
    : "Questa domanda non è ancora stata preparata: per farla la prima volta serve il collegamento al modello.";
}

export function itDate(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}
