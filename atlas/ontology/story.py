"""Owner: Core. One page in Italian: a safety officer's question, its answer and the path of checked facts behind it.

    python -m atlas.ontology.story        # writes ontology/B/story.html

The page sits next to dashboard.html and view.html and replaces nothing. It reuses dashboard.build() (design
questions, recorded answers, verdicts, totals) and adds only what the story needs: the trace of each graph
procedure, the facts on the path with their exact quotes, and the "what changes if" results derived from them.
No model call. Only design questions are read; the second split enters only as aggregated totals.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from atlas.ontology import dashboard

ROOT = dashboard.ROOT
OUT = ROOT / "ontology" / "B" / "story.html"
DESIGN = dashboard.DESIGN

# Measured today, stated as given (not read from a file).
COST_LAW_USD = 0.36
COST_OTHER_USD = 0.30

LAYERS = [("law", "Legge"), ("guidance", "Guida"), ("manufacturer", "Costruttore"), ("company", "Azienda"), ("plant", "Stabilimento")]

SOURCES = {
    "REG": "Regolamento (UE) 2023/1230", "DIR": "Direttiva 2006/42/CE", "CORR": "Rettifica del Regolamento",
    "DLGSALLVII": "D.Lgs. 81/08, Allegato VII", "DM2011": "DM 11 aprile 2011", "igea-equipment": "Elenco apparecchi IGEA",
    "ur5e-manual": "Manuale UR5e", "ur10e-manual": "Manuale UR10e", "nanoscan3-manual": "Manuale nanoScan3",
    "mastar-manual": "Manuale Mastar", "inail-guide": "Guida INAIL", "robot-cell-sheet": "Scheda della cella robot",
    "unict-guideline": "Linee guida UniCT", "univpm-guideline": "Linee guida UnivPM", "CATALOGUE": "Catalogo dei modelli",
}

SKILLS = {
    "verification_interval": "Regola dell'intervallo di verifica", "value_on_date": "Data letta dal calendario della legge",
    "single_value": "Un valore, confrontato tra le fonti", "members_of": "Membri di un elenco",
}

NODES = {
    "device": "I dati dell'apparecchio: tipo, portata, anno, settore", "annex_rows": "Le righe dell'Allegato VII sul sollevamento",
    "fixed_or_mobile": "Fisso o mobile?", "capacity": "Portata sopra il limite scritto nelle righe?",
    "sector": "Il settore del sito", "age": "L'età dell'apparecchio alla data", "row": "La riga dell'Allegato VII che corrisponde",
    "dated_facts": "I fatti con una data, per questo soggetto", "in_force": "Il fatto in vigore; quello corretto resta nella traccia",
    "compare": "La data, o il confronto con il giorno chiesto", "relation_facts": "I fatti di questa relazione, per questo soggetto",
    "choose": "Scelta per soggetto, punto e rango dello strato", "settle": "Se due fonti si contraddicono, vince la più autorevole",
}

PREDICATES = {
    "verificationInterval": "va verificato", "deviceKind": "tipo", "capacityKg": "portata (kg)", "yearBuilt": "anno di costruzione",
    "siteSector": "settore", "appliesFrom": "si applica dal", "repealedFrom": "abrogata dal", "retentionPeriod": "va conservato per",
    "hasTimeLimit": "entro", "verifiedBy": "verificato da", "requiresPeriodicCheck": "va controllato",
    "putIntoServiceOnlyWhen": "in servizio solo se", "placingAllowedUntil": "immissione sul mercato fino al",
}

OK_REASON = {"procedure": "grazie a una procedura a grafo", "history": "grazie alla storia delle correzioni",
             "order": "grazie all'ordine tra le fonti", "layers": "attraverso più strati", "single": "da un fatto controllato"}
KO_REASON = {"nodoc": "il documento non è nell'ontologia", "noextract": "il fatto non è mai stato estratto",
             "unused": "il fatto c'è ma l'agente non l'ha usato", "list": "fatti giusti, elenco incompleto o con voci in più",
             "unknown": "ha risposto non lo so", "neighbour": "ha risposto da un fatto vicino a quello giusto"}
KO_DETAIL = {
    "nodoc": "La risposta attesa richiede un documento che non è mai stato letto nell'ontologia.",
    "noextract": "Il documento c'è, ma dal passaggio che serve non è stato estratto nessun fatto in vigore.",
    "unused": "L'ontologia ha fatti dal passaggio giusto. L'agente ha risposto da altri fatti.",
    "list": "I fatti vengono dai passaggi giusti. Nell'elenco però mancano voci, o ce ne sono in più.",
    "unknown": "I fatti ci sono, ma l'agente non è arrivato a una risposta.",
    "neighbour": "L'agente ha risposto da un fatto vicino a quello giusto.",
}
ITEM_MARK = {"matched": "trovata", "extra": "in più", "missing": "mancante"}
REJECT_WORDS = {"no_anchor": "la frase non è nel documento", "missing_condition": "la condizione è andata persa",
                "value_not_in_quote": "il valore non è nella frase", "not_in_schema": "relazione fuori dallo schema",
                "condition_no_anchor": "la condizione non è nel documento"}
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_name(doc: str) -> str:
    if doc in SOURCES:
        return SOURCES[doc]
    m = re.fullmatch(r"DLGS(\d+)", doc)
    return f"D.Lgs. 81/08, art. {m.group(1)}" if m else doc


def shorten(text: str, limit: int = 60) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def words(value, every: bool = False):
    """A recorded value in plain Italian. Lists stay lists; free text stays as recorded."""
    if isinstance(value, list):
        return [words(v, every) for v in value]
    if value is None or value == "":
        return "Non lo so"
    if value is True:
        return "Sì"
    if value is False:
        return "No"
    text = str(value).strip()
    m = re.fullmatch(r"P(\d+)([YMD])", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        one, many = {"Y": ("anno", "anni"), "M": ("mese", "mesi"), "D": ("giorno", "giorni")}[unit]
        if every:
            return f"ogni {one}" if n == 1 else f"ogni {n} {many}"
        return f"{n} {one if n == 1 else many}"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
    return text


def mark(row: dict | None) -> str:
    row = row or {}
    score = row.get("score") or 0
    if score >= 0.999:
        return "giusta"
    if row.get("value") in (None, "", []):
        return "non lo sa"
    return "giusta in parte" if score > 0 else "sbagliata"


def _norm(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


class _Facts:
    """The facts a page embeds, read from the store, each with its exact quote."""

    def __init__(self, store) -> None:
        self.store = store
        self.by_id = {s.id: s for s in store.statements}
        self.out: dict[str, dict] = {}

    def keep(self, i: str) -> str | None:
        s = self.by_id.get(i)
        if s is None:
            return None
        if i not in self.out:
            self.out[i] = {
                "s": s.subject, "p": PREDICATES.get(s.predicate, s.predicate), "o": s.object, "w": s.object_as_written or "",
                "ow": words(s.object), "c": s.condition or "", "q": s.quote or "", "d": s.source_doc, "src": source_name(s.source_doc),
                "a": s.anchor or "", "l": self.store.layer_of(s), "st": s.status,
                "from": str(s.in_force_from) if s.in_force_from else "", "to": str(s.in_force_to) if s.in_force_to else "",
            }
        return i


def _checks(ids: list[str], facts: _Facts, health: dict) -> dict:
    """The three checks, counted on the facts in force that support this answer."""
    live = [facts.by_id[i] for i in ids if facts.by_id[i].status == "current"]
    found = len(live) if health.get("quote_missing") == 0 and health.get("piece_missing") == 0 else sum(1 for s in live if s.quote)
    value = sum(1 for s in live if _norm(s.object_as_written or s.object) in _norm(s.quote))
    cond = sum(1 for s in live if s.condition)
    return {"n": len(live), "quote": found, "value": value, "cond": cond}


def _what_if(q: dict, support: list[str], used: list[str], tr: dict | None, facts: _Facts, scenes: list) -> list[dict]:
    out = []
    by = facts.by_id
    live = [i for i in support if by[i].status == "current"]
    # the closed fact a supporting fact replaced, and the conflict a supporting fact won
    replaced = next(((by[by[i].conflicts_with], by[i]) for i in live
                     if by[i].conflicts_with in by and by[by[i].conflicts_with].status == "closed"), None)
    lost = next(((g, by[i]) for i in live for g in facts.store.statements
                 if g.status == "conflict" and (g.conflicts_with == i or by[i].conflicts_with == g.id)), None)
    # ...togli un documento
    docs: dict[str, list[str]] = {}
    for i in live:
        docs.setdefault(by[i].source_doc, []).append(i)
    rows = []
    for doc, ids in docs.items():
        n = len(ids)
        row = {"doc": source_name(doc), "n": n, "facts": [facts.keep(i) for i in ids]}
        if replaced and replaced[1].id in ids and replaced[0].source_doc != doc:
            old = replaced[0]
            row["result"] = f"Tornerebbe il valore di prima: {words(old.object)}"
            row["why"] = (f"Il fatto in vigore viene da qui e ne sostituisce uno chiuso: {source_name(old.source_doc)}, {old.anchor}. "
                          "Senza questo documento resta solo quello.")
            row["facts"].append(facts.keep(old.id))
        else:
            row["result"] = "Non lo so: manca la frase che lo dimostra"
            row["why"] = (f"{n} {'fatto usato viene' if n == 1 else 'fatti usati vengono'} da questo documento. "
                          "Senza la frase, la risposta non ha più un appoggio.")
        rows.append(row)
    if rows:
        out.append({"kind": "doc", "label": "…togli un documento", "note": "calcolato dai fatti usati", "rows": rows})
    # ...la data è un'altra
    skill = (tr or {}).get("skill")
    if skill == "value_on_date" and replaced:
        old, new = replaced
        day = words(str(new.in_force_from)) if new.in_force_from else ""
        out.append({"kind": "date", "label": "…la data è un'altra", "note": "dai fatti chiusi e da quelli in vigore", "rows": [
            {"doc": f"Prima del {day}" if day else "Prima della rettifica", "result": words(old.object),
             "why": f"È il valore che stampava {source_name(old.source_doc)}, {old.anchor}. Oggi quel fatto è chiuso.", "facts": [facts.keep(old.id)]},
            {"doc": f"Dal {day}" if day else "Dopo la rettifica", "result": words(new.object),
             "why": f"È il valore corretto da {source_name(new.source_doc)}, {new.anchor}. È il fatto in vigore.", "facts": [facts.keep(new.id)]},
        ]})
    elif skill == "verification_interval":
        device = next((re.match(r"(.*-d\d+)-", i).group(1) for i in used if re.match(r".*-d\d+-", i)), None)
        for sc in scenes:
            variants = sc.get("variants") or []
            if device and len(variants) == 2 and all(v.get("rule") for v in variants) \
                    and any(str(c.get("f", "")).startswith(device + "-") for c in variants[0].get("cards", [])):
                out.append({"kind": "date", "label": "…la data è un'altra", "note": "restituito dalla regola, un anno dopo", "rows": [
                    {"doc": v.get("date", ""), "result": words(v["rule"].get("interval"), True),
                     "why": "È l'intervallo che la regola restituisce per questo apparecchio in quella data.",
                     "facts": [facts.keep(v["rule"]["row_id"])] if v["rule"].get("row_id") in by else []} for v in variants]})
                break
    # ...cambia una fonte
    if lost:
        loser, winner = lost
        ra, rb = facts.store.rank_of(winner), facts.store.rank_of(loser)
        out.append({"kind": "source", "label": "…cambia una fonte", "note": "dall'ordine tra le fonti", "rows": [
            {"doc": f"{source_name(loser.source_doc)} dice {words(loser.object)}", "result": f"Vince {source_name(winner.source_doc)}: {words(winner.object)}",
             "why": ("Le due fonti si contraddicono. " + (f"Nell'ordine tra le fonti la prima che vale ha rango {ra}, l'altra {rb}. " if ra != rb else "")
                     + "Il fatto che perde resta nell'ontologia, segnato come in conflitto."),
             "facts": [facts.keep(winner.id), facts.keep(loser.id)]}]})
    elif replaced:
        old, new = replaced
        day = words(str(new.in_force_from)) if new.in_force_from else ""
        out.append({"kind": "source", "label": "…cambia una fonte", "note": "dalla storia delle correzioni", "rows": [
            {"doc": f"{source_name(old.source_doc)} diceva {words(old.object)}", "result": f"{source_name(new.source_doc)} dice {words(new.object)}",
             "why": f"La fonte nuova ha corretto la vecchia{' il ' + day if day else ''}. Il vecchio fatto è chiuso, non cancellato: si può ancora leggere.",
             "facts": [facts.keep(new.id), facts.keep(old.id)]}]})
    return out


def _question(q: dict, tr: dict | None, facts: _Facts, metrics: dict, health: dict, scenes: list, rec: dict | None = None) -> dict:
    rec = rec or {}
    if isinstance(rec.get("trace"), dict):
        tr = {"skill": rec["trace"].get("skill"), "trace": rec["trace"]}
    outputs_it = rec.get("outputs_it") or []
    by = facts.by_id
    b, r, v = q.get("B") or {}, q.get("rag") or {}, q["verdict"]
    every = q["it"].strip().lower().startswith("ogni quanto")
    path: list[dict] = [{"k": "q", "title": "La domanda", "out": shorten(q["it"], 90)}]
    used: list[str] = []
    support: list[str] = []
    answer_facts: list[str] = []
    recorded = True

    def take(ids, into):
        got = []
        for i in ids or []:
            if i in by:
                facts.keep(i)
                got.append(i)
                for bag in (used, into):
                    if bag is not None and i not in bag:
                        bag.append(i)
        return got

    if tr:
        every_node = tr["trace"]["nodes"]
        italian = outputs_it if rec.get("translated") and len(outputs_it) == len(every_node) else [None] * len(every_node)
        for n, it in zip(every_node, italian):
            n["_it"] = it
        nodes = [n for n in every_node if n.get("status") == "run"]
        path.append({"k": "proc", "title": "La procedura scelta", "out": SKILLS.get(tr["skill"], tr["skill"].replace("_", " ")),
                     "sub": f"{len(nodes)} passi eseguiti dal codice, {tr['trace'].get('model_calls', 0)} chiamate al modello nel grafo"})
        for n in nodes:
            ids = take(n.get("fact_ids"), None if n.get("kind") == "lookup" else support)
            if n.get("kind") == "answer":
                answer_facts = ids
                continue
            path.append({"k": "node", "title": NODES.get(n["id"], n.get("does") or n["id"]), "out": str(n.get("_it") or n.get("output") or ""), "facts": ids})
        take([s.get("statement_id") for s in rec.get("steps") or []], None)
    else:
        steps = q.get("steps") or []
        ids = [s.get("statement_id") for s in rec.get("steps") or [] if s.get("statement_id") in by] or [s.get("f") for s in steps if s.get("f") in by]
        recorded = bool(ids)
        path.append({"k": "proc", "title": "La procedura scelta", "out": "Ricerca tra i fatti",
                     "sub": "l'agente cerca i fatti e risponde solo da quelli" if recorded else "questa risposta non ha passi registrati"})
        for i in take(ids, support):
            s = by[i]
            path.append({"k": "fact", "title": shorten(s.subject, 70),
                         "out": f"{PREDICATES.get(s.predicate, s.predicate)}: {words(s.object, every)}", "facts": [i]})
        answer_facts = support[:1]
    if support:
        path.append({"k": "check", "title": "Il controllo", "checks": _checks(support, facts, health)})
    path.append({"k": "answer", "title": "La risposta", "out": words(b.get("value"), every), "facts": answer_facts})

    ok = bool(v.get("ok"))
    verdict = {"ok": ok, "kind": v["kind"], "structure": bool(v.get("structure"))}
    if ok:
        verdict.update(label="Giusta", tone="ok", reason=OK_REASON.get(v["kind"], "da fatti controllati"))
        m = metrics.get("by_skill", {}).get((tr or {}).get("skill"), {})
        if tr and m.get("answered") and m.get("model_calls_without"):
            verdict["calls"] = [round(m["model_calls_with"] / m["answered"]), round(m["model_calls_without"] / m["answered"])]
    else:
        state = mark(b)
        verdict.update(label={"giusta in parte": "Giusta in parte", "non lo sa": "Non risponde"}.get(state, "Sbagliata"),
                       tone="bad" if state == "sbagliata" else "warn", reason=KO_REASON.get(v["kind"], "non è arrivata alla risposta giusta"))
        broken = {"k": "broken", "title": "Dove si è rotto", "out": KO_DETAIL.get(v["kind"], ""), "reason": verdict["reason"]}
        if v.get("items"):
            broken["items"] = [{"t": words(it["t"], every), "m": ITEM_MARK.get(it["m"], it["m"])} for it in v["items"]]
        if v.get("ev"):
            ev = v["ev"]
            broken["ev"] = {"src": source_name(ev.get("source", "")), "a": ev.get("locator", ""), "passage": ev.get("quote", "")}
        if v.get("fact") and v["fact"] in by:
            broken["facts"] = [facts.keep(v["fact"])]
            broken["fact_note"] = "il fatto che non è stato usato" if v["kind"] == "unused" else "il fatto da cui ha risposto"
        if b.get("score") is not None:
            broken["score"] = round(float(b["score"]), 2)
        path.append(broken)

    layers = []
    for i in used:
        layer = facts.out[i]["l"]
        if layer not in layers:
            layers.append(layer)
    return {
        "id": q["id"], "it": q["it"], "short": shorten(q["it"]),
        "group": "struct" if ok and verdict["structure"] else "fail" if not ok else "other",
        "value": words(b.get("value"), every), "text": b.get("text") or "", "mark": mark(b),
        "text_it": rec.get("text_it") if rec.get("translated") and rec.get("text") == (b.get("text") or "") else "",
        "rag": {"value": words(r.get("value"), every), "text": r.get("text") or "", "mark": mark(r)},
        "verdict": verdict, "path": path, "layers": layers, "open": (answer_facts or support or [None])[0],
        "skill": (tr or {}).get("skill"), "recorded": recorded,
        "whatif": _what_if(q, support, used, tr, facts, scenes) if b.get("value") not in (None, "", []) else [],
    }


def _board_sentence(group: str, b: dict, r: dict) -> str:
    n = b["n"]
    if r["correct"] > b["correct"]:
        head = f"Sulle {group} la ricerca semplice ne indovina {r['correct']} su {n} e Plant Atlas {b['correct']}"
    elif r["correct"] < b["correct"]:
        head = f"Sulle {group} Plant Atlas ne indovina {b['correct']} su {n} e la ricerca semplice {r['correct']}"
    else:
        head = f"Sulle {group} sono pari: {b['correct']} giuste su {n} ciascuno"
    tail = ("fa più errori" if b["wrong"] > r["wrong"] else "fa meno errori" if b["wrong"] < r["wrong"] else "fa gli stessi errori")
    return f"{head}. Plant Atlas {tail} ({b['wrong']} contro {r['wrong']}) e dice «non lo so» {b['unknown']} volte contro {r['unknown']}."


def build(store=None) -> dict:
    data = dashboard.build(store)
    store = store or dashboard.atlas_page.viewer._store()
    design = {q["id"] for q in data["questions"]}
    tpath = ROOT / "ontology" / "B" / "skill_traces.json"
    traces = {k: v for k, v in _load(tpath).items() if k in design} if tpath.exists() else {}
    metrics = _load(ROOT / "ontology" / "B" / "skill_metrics.json")
    impact = _load(ROOT / "ontology" / "B" / "impact.json")
    counts = store.counts()
    facts = _Facts(store)
    from atlas.ontology import recorded
    answers = {k: v for k, v in recorded.load().items() if k in design}
    questions = [_question(q, traces.get(q["id"]), facts, metrics, impact["health"], data["scenes"], answers.get(q["id"])) for q in data["questions"]]
    order = {"verification_interval": 0, "value_on_date": 1, "single_value": 2}
    struct = sorted((q for q in questions if q["group"] == "struct"),
                    key=lambda q: (q["rag"]["mark"] == "giusta", order.get(q["skill"], 9), q["id"]))
    questions = struct + [q for q in questions if q["group"] == "fail"] + [q for q in questions if q["group"] == "other"]

    reasons = sorted(((k[len("rejected_"):], n) for k, n in counts.items() if k.startswith("rejected_")), key=lambda x: -x[1])
    by_skill = metrics.get("by_skill", {})
    answered = sum(m.get("answered", 0) for m in by_skill.values())
    calls = None
    if answered and sum(m.get("model_calls_without", 0) for m in by_skill.values()):
        calls = [round(sum(m["model_calls_with"] for m in by_skill.values()) / answered),
                 round(sum(m["model_calls_without"] for m in by_skill.values()) / answered)]
    totals = data["totals"]
    figures = {
        "in_force": counts["status_current"], "documents": data["whole"]["totals"]["documents"], "layers": data["whole"]["totals"]["layers"],
        "proposed": counts["proposed_total"], "rejected": counts["rejected"],
        "reasons": [{"reason": REJECT_WORDS.get(k, k.replace("_", " ")), "key": k, "n": n} for k, n in reasons[:2]],
        "health": {"checked": impact["health"]["checked"], "found": impact["health"]["quote_found"]},
        "skills": {"answered": metrics["answered_by_skill"], "questions": metrics["questions"], "calls": calls,
                   "tokens_with": metrics["tokens_with"], "tokens_without": metrics["tokens_without"], "procedures": len(by_skill)},
        "cost": {"law": COST_LAW_USD, "other": COST_OTHER_USD},
        "pieces": sum(d["pieces"] for d in impact["documents"]), "registered": len(impact["documents"]),
    }
    board = {"rows": [
        {"label": "Domande di progetto", "B": totals["B"]["design"], "rag": totals["rag"]["design"],
         "say": _board_sentence("domande di progetto", totals["B"]["design"], totals["rag"]["design"])},
        {"label": "Domande mai viste dal sistema", "B": totals["B"]["held"], "rag": totals["rag"]["held"],
         "say": _board_sentence("domande mai viste", totals["B"]["held"], totals["rag"]["held"])},
    ], "n": totals["B"]["design"]["n"] + totals["B"]["held"]["n"]}
    return {"layers": [{"name": k, "label": v} for k, v in LAYERS], "questions": questions, "facts": facts.out,
            "figures": figures, "board": board}


START, END = "const DATA = ", ";/*DATA-END*/"


def render(data: dict) -> str:
    return PAGE.replace("__DATA__", dashboard.embedded(data))


def extract_data(html: str) -> dict:
    a = html.index(START) + len(START)
    return json.loads(html[a:html.index(END, a)])


def write(path: Path | None = None, store=None) -> Path:
    path = Path(path or OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(build(store)), encoding="utf-8")
    return path


PAGE = r"""<title>Plant Atlas, la risposta e il suo percorso</title>
<meta charset="utf-8">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap">
<style>
:root{
  --bg:#f6f7f9; --card:#ffffff; --soft:#eef0f4; --line:#dde1e8; --text:#161a22; --muted:#5d6675; --accent:#1f2a44; --on-accent:#ffffff;
  --shadow:0 6px 24px rgba(22,26,34,.08);
  --ok:#1a7f43; --ok-bg:#e4f4ea; --warn:#a15c00; --warn-bg:#fbefd9; --bad:#b42318; --bad-bg:#fbe6e3;
  --law:#3f51c9; --law-bg:#e6e9fb; --guidance:#0a7c8f; --guidance-bg:#dcf1f4; --manufacturer:#7a3fc4; --manufacturer-bg:#eee4fa;
  --company:#b32a6d; --company-bg:#f9e2ee; --plant:#6b5a48; --plant-bg:#eee8e1;
  --focus:#2563eb;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --bg:#0f1218; --card:#181c25; --soft:#202531; --line:#2c3342; --text:#e9ecf2; --muted:#9aa4b5; --accent:#dfe5f3; --on-accent:#10131a;
    --shadow:0 6px 24px rgba(0,0,0,.35);
    --ok:#5fd08a; --ok-bg:#15301f; --warn:#f0b24d; --warn-bg:#36280f; --bad:#ff8a7d; --bad-bg:#3a1a17;
    --law:#96a4ff; --law-bg:#22284d; --guidance:#5fcbdb; --guidance-bg:#12343a; --manufacturer:#c29bf5; --manufacturer-bg:#2f2147;
    --company:#f08bbd; --company-bg:#40192c; --plant:#cdb89f; --plant-bg:#342c23;
    --focus:#8ab4ff;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0f1218; --card:#181c25; --soft:#202531; --line:#2c3342; --text:#e9ecf2; --muted:#9aa4b5; --accent:#dfe5f3; --on-accent:#10131a;
  --shadow:0 6px 24px rgba(0,0,0,.35);
  --ok:#5fd08a; --ok-bg:#15301f; --warn:#f0b24d; --warn-bg:#36280f; --bad:#ff8a7d; --bad-bg:#3a1a17;
  --law:#96a4ff; --law-bg:#22284d; --guidance:#5fcbdb; --guidance-bg:#12343a; --manufacturer:#c29bf5; --manufacturer-bg:#2f2147;
  --company:#f08bbd; --company-bg:#40192c; --plant:#cdb89f; --plant-bg:#342c23;
  --focus:#8ab4ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}
h1,h2,h3,.big,.num{font-family:"Space Grotesk",Inter,system-ui,sans-serif}
header.top{display:flex;flex-wrap:wrap;align-items:flex-end;gap:8px 20px;margin-bottom:32px}
header.top h1{font-size:30px;line-height:1.1;margin:0 0 6px}
header.top p{margin:0;color:var(--muted);font-size:16px;max-width:60ch}
.badge{margin-left:auto;font-size:12px;font-weight:600;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:4px 12px;background:var(--card);white-space:nowrap}
body.embed header.top{display:none}
section{margin-top:44px}
section:first-of-type{margin-top:0}
h2{font-size:13px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin:0 0 14px;font-weight:600}
h3{font-size:14px;margin:0 0 8px;font-weight:600}
button{font:inherit;color:inherit;cursor:pointer}
button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
a{color:var(--law)}
.grp{margin-bottom:14px}
.grp .lab{font-size:13px;font-weight:600;margin-bottom:8px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.qchip{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:7px 14px;font-size:14px;text-align:left;line-height:1.3}
.qchip:hover{border-color:var(--muted)}
.qchip[aria-pressed="true"]{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.qchip .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;background:var(--ok);vertical-align:1px}
.qchip.fail .dot{background:var(--warn)}
details.more summary{cursor:pointer;color:var(--muted);font-size:13px;font-weight:600;margin-bottom:8px;width:max-content}
.hero{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:28px}
.hero .q{font-size:24px;line-height:1.3;margin:0 0 20px;font-weight:600;font-family:"Space Grotesk",Inter,system-ui,sans-serif;max-width:34ch}
.hero .big{font-size:64px;line-height:1.05;font-weight:700;margin:0 0 16px;letter-spacing:-.01em}
.hero .big.mid{font-size:30px;line-height:1.25}
.hero ul.big{font-size:19px;line-height:1.4;font-weight:600;padding-left:22px;margin:0 0 16px;letter-spacing:0}
.hero ul.big li{margin:3px 0}
.heroGrid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:28px;align-items:start}
.sys{border-left:3px solid var(--line);padding:2px 0 2px 16px;color:var(--text)}
.sys .lab,.lab2{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.sys p{margin:0}
.sys details.orig{margin-top:10px;color:var(--muted);font-size:13px}
.sys details.orig summary{cursor:pointer;font-weight:600;width:max-content}
.sys details.orig p{margin-top:6px}
.verdict{display:inline-flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font-size:15px;margin-top:4px}
.pill{font-weight:700;border-radius:999px;padding:4px 14px;font-size:14px}
.pill.ok{background:var(--ok-bg);color:var(--ok)} .pill.warn{background:var(--warn-bg);color:var(--warn)} .pill.bad{background:var(--bad-bg);color:var(--bad)}
.pathBox{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:22px 24px}
.pathHead{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-bottom:18px}
.strip{display:flex;gap:4px;flex:1 1 320px;min-width:0}
.strip span{flex:1;font-size:12px;font-weight:600;text-align:center;padding:5px 4px;border-radius:6px;background:var(--soft);color:var(--muted);opacity:.65;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.strip span.on{opacity:1}
.strip span.on.L-law{background:var(--law-bg);color:var(--law)} .strip span.on.L-guidance{background:var(--guidance-bg);color:var(--guidance)}
.strip span.on.L-manufacturer{background:var(--manufacturer-bg);color:var(--manufacturer)} .strip span.on.L-company{background:var(--company-bg);color:var(--company)}
.strip span.on.L-plant{background:var(--plant-bg);color:var(--plant)}
.btn{border:1px solid var(--line);background:var(--card);border-radius:8px;padding:6px 14px;font-size:13px;font-weight:600}
.btn:hover{border-color:var(--muted)}
.path{display:flex;flex-wrap:wrap;align-items:flex-start;gap:16px 28px}
.step{flex:1 1 150px;max-width:230px;min-width:0;position:relative;border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--card);opacity:0;transform:translateY(10px);transition:opacity .4s ease,transform .4s ease}
.step.in{opacity:1;transform:none}
.step + .step::before{content:"\2192";position:absolute;left:-22px;top:14px;color:var(--muted);font-size:16px;line-height:1}
.step .t{font-size:12px;font-weight:600;color:var(--muted);line-height:1.35;margin-bottom:6px}
.step .o{font-size:14px;line-height:1.4;overflow-wrap:anywhere}
.step .sub{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.4}
.step.k-q,.step.k-proc{background:var(--soft)}
.step.k-answer{border-color:var(--ok);background:var(--ok-bg)}
.step.k-answer.warn{border-color:var(--warn);background:var(--warn-bg)}
.step.k-answer.bad{border-color:var(--bad);background:var(--bad-bg)}
.step.k-answer .o{font-family:"Space Grotesk",Inter,system-ui,sans-serif;font-size:18px;font-weight:700}
.step.k-broken{border-color:var(--bad);background:var(--bad-bg);flex:2 1 320px;max-width:520px}
.step.k-broken .t{color:var(--bad)}
.step ul.ck{list-style:none;margin:0;padding:0;font-size:13px}
.step ul.ck li{display:flex;gap:6px;margin:4px 0;line-height:1.35}
.step ul.ck .tick{color:var(--ok);font-weight:700}
.step ul.ck small{color:var(--muted);display:block}
.fchips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.fchip{border:1px solid transparent;border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600;line-height:1.5;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fchip[aria-pressed="true"]{border-color:currentColor}
.L-law{background:var(--law-bg);color:var(--law)} .L-guidance{background:var(--guidance-bg);color:var(--guidance)}
.L-manufacturer{background:var(--manufacturer-bg);color:var(--manufacturer)} .L-company{background:var(--company-bg);color:var(--company)}
.L-plant{background:var(--plant-bg);color:var(--plant)}
ul.items{list-style:none;margin:10px 0 0;padding:0;font-size:13px}
ul.items li{display:flex;gap:8px;align-items:baseline;margin:4px 0}
ul.items .m{flex:none;font-size:11px;font-weight:700;border-radius:4px;padding:1px 6px;background:var(--card)}
ul.items .m.trovata{color:var(--ok)} ul.items .m.mancante{color:var(--bad)} ul.items .m.in-più{color:var(--warn)}
.fpanel{margin-top:18px;border:1px solid var(--line);border-left-width:4px;border-radius:12px;padding:16px 18px;background:var(--bg)}
.fpanel.L-law{border-left-color:var(--law);color:inherit;background:var(--bg)} .fpanel.L-guidance{border-left-color:var(--guidance);color:inherit;background:var(--bg)}
.fpanel.L-manufacturer{border-left-color:var(--manufacturer);color:inherit;background:var(--bg)} .fpanel.L-company{border-left-color:var(--company);color:inherit;background:var(--bg)}
.fpanel.L-plant{border-left-color:var(--plant);color:inherit;background:var(--bg)}
.fpanel .hint{color:var(--muted);margin:0}
.fpanel blockquote{margin:10px 0;font-size:16px;line-height:1.5;font-style:italic;overflow-wrap:anywhere}
.fpanel .meta{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--muted)}
.fpanel .meta b{color:var(--text);font-weight:600}
.fpanel .fact{font-size:14px;font-weight:600}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.cmp .col{border:1px solid var(--line);border-radius:12px;padding:18px 20px;background:var(--card);min-width:0}
.cmp .v{font-family:"Space Grotesk",Inter,system-ui,sans-serif;font-size:26px;font-weight:700;line-height:1.2;margin:6px 0 10px;overflow-wrap:anywhere}
.cmp .v.mid{font-size:17px}
.cmp p{margin:10px 0 0;color:var(--muted);font-size:14px}
.note{color:var(--muted);font-size:14px;margin:12px 0 0}
.wif{display:flex;flex-wrap:wrap;gap:8px}
.wif .btn[aria-expanded="true"]{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
.wres{margin-top:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.wres .box{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--card);min-width:0}
.wres .r{font-family:"Space Grotesk",Inter,system-ui,sans-serif;font-size:18px;font-weight:700;margin:4px 0 6px;line-height:1.25}
.wres p{margin:0;font-size:14px;color:var(--muted)}
.figs{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.fig{border:1px solid var(--line);border-radius:12px;padding:16px;background:var(--card);min-width:0}
.fig .num{font-size:30px;font-weight:700;line-height:1.1;margin-bottom:6px}
.fig .num small{font-size:15px;font-weight:600;color:var(--muted)}
.fig p{margin:0;font-size:13px;color:var(--muted);line-height:1.45}
.fig p b{color:var(--text);font-weight:600}
.board{margin-top:20px;border:1px solid var(--line);border-radius:12px;background:var(--card);padding:18px 20px}
.brow{display:grid;grid-template-columns:220px minmax(0,1fr);gap:8px 20px;padding:12px 0;border-top:1px solid var(--line)}
.brow:first-of-type{border-top:0;padding-top:0}
.brow .who{font-weight:600}
.bar{display:grid;grid-template-columns:120px minmax(0,1fr);gap:10px;align-items:center;font-size:13px;margin:4px 0}
.stack{display:flex;height:22px;border-radius:6px;overflow:hidden;background:var(--soft)}
.stack span{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;min-width:18px}
.stack .c{background:var(--ok-bg);color:var(--ok)} .stack .u{background:var(--soft);color:var(--muted)} .stack .w{background:var(--bad-bg);color:var(--bad)}
.brow .say{grid-column:2;font-size:14px;color:var(--muted);margin:4px 0 0}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--muted);margin-bottom:12px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.scroll{overflow-x:auto}
.infra{display:flex;gap:26px;min-width:900px;padding:2px}
.ibox{flex:1;position:relative;border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--card)}
.ibox + .ibox::before{content:"\2192";position:absolute;left:-21px;top:14px;color:var(--muted)}
.ibox b{display:block;font-size:14px;margin-bottom:4px;font-family:"Space Grotesk",Inter,system-ui,sans-serif}
.ibox span{font-size:13px;color:var(--muted);line-height:1.4;display:block}
.links{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:16px;font-size:15px;font-weight:600}
@media (max-width:900px){.heroGrid{grid-template-columns:1fr}.figs{grid-template-columns:repeat(2,minmax(0,1fr))}.hero .big{font-size:48px}}
@media (max-width:560px){
  .hero{padding:20px}.hero .q{font-size:20px}.hero .big{font-size:40px}.pathBox{padding:16px}
  .cmp,.figs{grid-template-columns:1fr}
  .path{gap:26px}.step{flex-basis:100%;max-width:none}.step.k-broken{flex-basis:100%;max-width:none}
  .step + .step::before{content:"\2193";left:16px;top:-21px}
  .brow{grid-template-columns:1fr}.brow .say{grid-column:1}.bar{grid-template-columns:96px minmax(0,1fr)}
  .badge{margin-left:0}
}
@media (prefers-reduced-motion: reduce){.step{transition:none;transform:none}}
</style>
<div class="wrap">
<header class="top">
  <div><h1>Plant Atlas</h1><p>Le risposte sulle tue macchine, ognuna con la frase del documento da cui viene.</p></div>
  <span class="badge">risposte registrate</span>
</header>

<section aria-labelledby="h-q">
  <h2 id="h-q">La domanda</h2>
  <div class="grp"><div class="lab">Dove la struttura fa la differenza</div><div class="chips" id="g-struct"></div></div>
  <div class="grp"><div class="lab">Dove sbaglia, e perché</div><div class="chips" id="g-fail"></div></div>
  <details class="more" id="more"><summary>tutte le domande</summary><div class="chips" id="g-other"></div></details>
</section>

<section aria-labelledby="h-a">
  <h2 id="h-a">La risposta</h2>
  <div class="hero" id="hero" aria-live="polite"></div>
</section>

<section aria-labelledby="h-p">
  <h2 id="h-p">Come ci è arrivato</h2>
  <div class="pathBox">
    <div class="pathHead"><div class="strip" id="strip" aria-label="Strati attraversati da questa risposta"></div><button class="btn" id="replay" type="button">Rivedi</button></div>
    <div class="path" id="path"></div>
    <div class="fpanel" id="fpanel"></div>
  </div>
</section>

<section aria-labelledby="h-c">
  <h2 id="h-c">La stessa domanda, con la ricerca semplice</h2>
  <div class="cmp" id="cmp"></div>
  <p class="note">La ricerca legge i passaggi più vicini alla domanda; non ha un percorso da mostrare.</p>
</section>

<section aria-labelledby="h-w" id="s-w">
  <h2 id="h-w">Cosa cambia se…</h2>
  <div class="wif" id="wif"></div>
  <div id="wres"></div>
</section>

<section aria-labelledby="h-v">
  <h2 id="h-v">Il valore, in numeri nostri</h2>
  <div class="figs" id="figs"></div>
  <div class="board" id="board"></div>
</section>

<section aria-labelledby="h-i">
  <h2 id="h-i">Come è fatto</h2>
  <div class="scroll"><div class="infra" id="infra"></div></div>
  <div class="links">
    <a href="dashboard.html#docs">Esplora l'ontologia</a>
    <a href="dashboard.html#build">Costruisci l'ontologia passo passo</a>
    <a href="view.html">Tutti i fatti</a>
  </div>
</section>
</div>
<script>
const DATA = __DATA__;/*DATA-END*/
(function(){
  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const num = n => Number(n).toLocaleString("it-IT");
  const usd = n => Number(n).toLocaleString("it-IT", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const byId = {}; DATA.questions.forEach(q => byId[q.id] = q);
  const layerLabel = {}; DATA.layers.forEach(l => layerLabel[l.name] = l.label);
  const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let current = null, openFact = null, timers = [];

  function valueHtml(v, cls){
    if (Array.isArray(v)) return '<ul class="' + cls + '">' + v.map(x => "<li>" + esc(x) + "</li>").join("") + "</ul>";
    const mid = String(v).length > 28 ? " mid" : "";
    return '<div class="' + cls + mid + '">' + esc(v) + "</div>";
  }
  function plain(v){ return Array.isArray(v) ? v.join("; ") : String(v); }
  function tone(m){ return m === "giusta" ? "ok" : m === "sbagliata" ? "bad" : "warn"; }

  function chips(){
    const box = {struct: $("g-struct"), fail: $("g-fail"), other: $("g-other")};
    DATA.questions.forEach(q => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "qchip" + (q.verdict.ok ? "" : " fail"); b.title = q.it; b.dataset.id = q.id;
      b.setAttribute("aria-pressed", "false");
      b.innerHTML = '<span class="dot"></span>' + esc(q.short);
      b.addEventListener("click", () => select(q.id, true));
      box[q.group].appendChild(b);
    });
  }

  function hero(q){
    const v = q.verdict;
    let line = '<span class="pill ' + v.tone + '">' + esc(v.label) + "</span><span>" + esc(v.reason) + "</span>";
    if (v.calls) line += '<span style="color:var(--muted)">· ' + v.calls[0] + (v.calls[0] === 1 ? " chiamata" : " chiamate") + " al modello invece di " + v.calls[1] + "</span>";
    $("hero").innerHTML = '<p class="q">' + esc(q.it) + '</p><div class="heroGrid"><div>' + valueHtml(q.value, "big")
      + '<div class="verdict">' + line + '</div></div><div class="sys"><div class="lab">' + (q.text_it ? "risposta del sistema, tradotta" : "risposta del sistema") + '</div><p>'
      + esc(q.text_it || q.text || "Nessun testo registrato.") + "</p>" + (q.text_it ? '<details class="orig"><summary>testo originale</summary><p>' + esc(q.text) + "</p></details>" : "") + "</div></div>";
  }

  function fchip(id){
    const f = DATA.facts[id]; if (!f) return "";
    return '<button type="button" class="fchip L-' + f.l + '" data-f="' + esc(id) + '" aria-pressed="false" title="' + esc(layerLabel[f.l] + " · " + f.src + ", " + f.a) + '">' + esc(f.a || f.src) + "</button>";
  }
  function stepHtml(s, q){
    let h = '<div class="t">' + esc(s.title) + "</div>";
    if (s.k === "check"){
      const c = s.checks, of = (a, b) => a + " su " + b;
      h += '<ul class="ck"><li><span class="tick">✓</span><span>frase nel documento<small>' + of(c.quote, c.n) + ", parola per parola</small></span></li>"
        + '<li><span class="tick">' + (c.value === c.n ? "✓" : "·") + "</span><span>valore nella frase<small>" + of(c.value, c.n) + (c.value < c.n ? " alla lettera; gli altri in forma normalizzata" : "") + "</small></span></li>"
        + '<li><span class="tick">' + (c.cond ? "✓" : "·") + "</span><span>condizione conservata<small>" + (c.cond ? of(c.cond, c.cond) + " con una condizione" : "nessuna condizione in questi fatti") + "</small></span></li></ul>";
      return h;
    }
    if (s.out != null && s.out !== "") h += '<div class="o">' + esc(s.k === "answer" && Array.isArray(s.out) ? s.out.length + " voci nell'elenco" : plain(s.out)) + "</div>";
    if (s.sub) h += '<div class="sub">' + esc(s.sub) + "</div>";
    if (s.k === "broken"){
      if (s.ev) h += '<div class="sub"><b>Fonte attesa:</b> ' + esc(s.ev.src) + (s.ev.a ? ", " + esc(s.ev.a) : "") + (s.ev.passage ? "<br>Passaggio mai estratto: «" + esc(s.ev.passage) + "»" : "") + "</div>";
      if (s.items) h += '<ul class="items">' + s.items.map(i => '<li><span class="m ' + esc(i.m.replace(" ", "-")) + '">' + esc(i.m) + "</span><span>" + esc(i.t) + "</span></li>").join("") + "</ul>";
      if (s.fact_note) h += '<div class="sub">' + esc(s.fact_note) + ":</div>";
    }
    if (s.facts && s.facts.length) h += '<div class="fchips">' + s.facts.map(fchip).join("") + "</div>";
    return h;
  }
  function path(q, animate){
    timers.forEach(clearTimeout); timers = [];
    $("strip").innerHTML = DATA.layers.map(l => {
      const on = q.layers.indexOf(l.name) >= 0;
      return '<span class="' + (on ? "on L-" + l.name : "") + '" title="' + esc(l.label + (on ? ": attraversato" : ": non attraversato")) + '">' + esc(l.label) + "</span>";
    }).join("");
    const box = $("path"); box.innerHTML = "";
    q.path.forEach((s, i) => {
      const d = document.createElement("div");
      d.className = "step k-" + s.k + (s.k === "answer" && !q.verdict.ok ? " " + q.verdict.tone : "");
      d.innerHTML = stepHtml(s, q);
      box.appendChild(d);
      if (still || !animate) d.classList.add("in");
      else timers.push(setTimeout(() => d.classList.add("in"), 80 + i * 480));
    });
    showFact(q.open);
  }
  function showFact(id){
    openFact = id;
    document.querySelectorAll(".fchip").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.f === id)));
    const p = $("fpanel"), f = id && DATA.facts[id];
    if (!f){
      p.className = "fpanel";
      p.innerHTML = '<p class="hint">' + (current && !current.recorded && !current.layers.length
        ? "Per questa risposta i passi non sono registrati: non c'è un fatto da aprire qui."
        : "Clicca un fatto colorato per leggere la frase esatta da cui viene.") + "</p>";
      return;
    }
    const state = f.st === "current" ? "in vigore" : f.st === "closed" ? "chiuso" + (f.to ? " dal " + f.to : "") + ", conservato" : f.st === "conflict" ? "in conflitto, ha perso" : f.st;
    p.className = "fpanel L-" + f.l;
    p.innerHTML = '<div class="fact">' + esc(f.s) + " · " + esc(f.p) + " · " + esc(plain(f.ow)) + (f.w && f.w !== f.ow ? ' <span style="color:var(--muted);font-weight:400">(scritto: ' + esc(f.w) + ")</span>" : "") + "</div>"
      + "<blockquote>«" + esc(f.q) + "»</blockquote>"
      + '<div class="meta"><span><b>Fonte</b> ' + esc(f.src) + "</span><span><b>Punto</b> " + esc(f.a) + "</span><span><b>Strato</b> " + esc(layerLabel[f.l] || f.l) + "</span><span><b>Stato</b> " + esc(state) + "</span>"
      + (f.c ? "<span><b>Condizione</b> " + esc(f.c) + "</span>" : "") + "</div>";
  }

  function compare(q){
    const col = (name, v, m, text) => '<div class="col"><div class="lab2">' + name + "</div>" + valueHtml(v, "v").replace('<ul class="v">', '<ul class="v mid" style="padding-left:20px">')
      + '<span class="pill ' + tone(m) + '">' + esc(m) + "</span>" + (text ? "<p>" + esc(text) + "</p>" : "") + "</div>";
    $("cmp").innerHTML = col("Plant Atlas", q.value, q.mark, "") + col("Ricerca semplice", q.rag.value, q.rag.mark, q.rag.text);
  }

  function whatif(q){
    $("s-w").hidden = !q.whatif.length;
    const bar = $("wif"); bar.innerHTML = ""; $("wres").innerHTML = "";
    q.whatif.forEach((w, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "btn"; b.textContent = w.label; b.setAttribute("aria-expanded", "false");
      b.addEventListener("click", () => {
        const was = b.getAttribute("aria-expanded") === "true";
        bar.querySelectorAll("button").forEach(x => x.setAttribute("aria-expanded", "false"));
        if (was){ $("wres").innerHTML = ""; return; }
        b.setAttribute("aria-expanded", "true");
        $("wres").innerHTML = '<div class="wres">' + w.rows.map(r => '<div class="box"><div class="lab2">' + esc(r.doc) + '</div><div class="r">' + esc(plain(r.result)) + "</div><p>" + esc(r.why) + "</p>"
          + (r.facts && r.facts.length ? '<div class="fchips">' + r.facts.map(fchip).join("") + "</div>" : "") + "</div>").join("") + '</div><p class="note">' + esc(w.note) + "</p>";
      });
      bar.appendChild(b);
    });
  }

  function select(id, user){
    const q = byId[id] || DATA.questions[0]; current = q;
    document.querySelectorAll(".qchip").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.id === q.id)));
    if (q.group === "other") $("more").open = true;
    hero(q); path(q, true); compare(q); whatif(q);
    if (user){ try { history.replaceState(null, "", "#" + (document.body.classList.contains("embed") ? "embed&" : "") + "q=" + q.id); } catch (e) {} }
  }

  function figures(){
    const f = DATA.figures, s = f.skills;
    const fig = (n, p) => '<div class="fig"><div class="num">' + n + "</div><p>" + p + "</p></div>";
    $("figs").innerHTML =
      fig(num(f.in_force), "<b>fatti in vigore</b>, da " + f.documents + " documenti su " + f.layers + " strati")
      + fig(num(f.rejected), "<b>fatti rifiutati dal controllo</b> su " + num(f.proposed) + " proposti. Motivi più frequenti: " + f.reasons.map(r => esc(r.reason) + " (" + r.n + ")").join("; "))
      + fig(num(f.health.found) + " <small>su " + num(f.health.checked) + "</small>", "<b>fatti ritrovati oggi parola per parola</b> nei documenti")
      + fig(s.calls ? s.calls[0] + " <small>invece di " + s.calls[1] + "</small>" : String(s.answered), "<b>con una procedura a grafo: " + (s.calls ? s.calls[0] + (s.calls[0] === 1 ? " chiamata" : " chiamate") + " al modello invece di " + s.calls[1] : "meno chiamate al modello") + "</b>. "
          + s.answered + " domande di progetto su " + s.questions + " hanno risposto così. Sul totale: " + num(s.tokens_with) + " token invece di " + num(s.tokens_without))
      + fig("≈ " + usd(f.cost.law + f.cost.other) + " <small>USD</small>", "<b>costo dell'estrazione</b>, misurato oggi: testi di legge circa " + usd(f.cost.law) + " USD, altri strati circa " + usd(f.cost.other) + " USD");
    const stack = t => '<div class="stack" role="img" aria-label="' + t.correct + " giuste, " + t.unknown + " non lo so, " + t.wrong + ' sbagliate">'
      + [["c", t.correct], ["u", t.unknown], ["w", t.wrong]].filter(x => x[1] > 0).map(x => '<span class="' + x[0] + '" style="flex:' + x[1] + '">' + x[1] + "</span>").join("") + "</div>";
    $("board").innerHTML = '<div class="legend"><span><i style="background:var(--ok-bg);border:1px solid var(--ok)"></i>giuste</span><span><i style="background:var(--soft);border:1px solid var(--muted)"></i>non lo so</span><span><i style="background:var(--bad-bg);border:1px solid var(--bad)"></i>sbagliate</span></div>'
      + DATA.board.rows.map(r => '<div class="brow"><div class="who">' + esc(r.label) + ' <span style="color:var(--muted);font-weight:400">(' + r.B.n + ")</span></div><div>"
        + '<div class="bar"><span>Plant Atlas</span>' + stack(r.B) + '</div><div class="bar"><span>Ricerca semplice</span>' + stack(r.rag) + "</div></div>"
        + '<p class="say">' + esc(r.say) + "</p></div>").join("")
      + '<p class="note">' + DATA.board.n + " domande sono un controllo, non un benchmark.</p>";
    const boxes = [
      ["Documenti", f.documents + " documenti, " + f.layers + " strati"],
      ["Registro", num(f.pieces) + " pezzi con impronta"],
      ["Estrazione a puntatore", "il modello indica una frase"],
      ["Controllo", num(f.rejected) + " rifiutati"],
      ["Fatti", num(f.in_force) + " in vigore"],
      ["Agente e procedure", s.procedures + " procedure a grafo"]];
    $("infra").innerHTML = boxes.map(b => '<div class="ibox"><b>' + b[0] + "</b><span>" + b[1] + "</span></div>").join("");
  }

  function fromHash(){
    const parts = location.hash.replace(/^#/, "").split("&");
    document.body.classList.toggle("embed", parts.indexOf("embed") >= 0);
    const q = parts.map(p => /^q=(.+)$/.exec(p)).filter(Boolean)[0];
    return q && byId[decodeURIComponent(q[1])] ? decodeURIComponent(q[1]) : null;
  }

  document.addEventListener("click", e => {
    const b = e.target.closest && e.target.closest(".fchip");
    if (!b) return;
    showFact(openFact === b.dataset.f ? null : b.dataset.f);
    if (openFact && !$("path").contains(b)) $("fpanel").scrollIntoView({block: "nearest", behavior: still ? "auto" : "smooth"});
  });
  $("replay").addEventListener("click", () => current && path(current, true));
  window.addEventListener("hashchange", () => { const id = fromHash(); if (id && (!current || id !== current.id)) select(id, false); });
  chips(); figures();
  select(fromHash() || DATA.questions[0].id, false);
})();
</script>
"""


def main() -> None:
    path = write()
    print(f"wrote {path} ({path.stat().st_size / 1000:.0f} kB)")


if __name__ == "__main__":
    main()
