# HACK.md — Plant Atlas

> The team's single source of truth for the day. Every fact carries a marker:
> `[verified: source]` · `[declared]` · `[unverified]`. An empty section says `MISSING — needed before <phase>`.

Team: engine developer (pipeline, ontology, eval) · product developer (plant corpus, app, pitch) · Presenter: MISSING — needed before 12:00
Clock: video 12:30 · freeze 16:00 · pitch delivery 16:45 · Credit: $25, $0 spent [verified: Control8, 11:21] · Gate 1 (12:30, video): Fit 30, Right-to-win 25, Explainability 20, Willingness to invest 15, Sentiment 10 · Gate 2 (17:05): Technical feasibility 18, Build quality 17, Financial sustainability 13, Selling story 12, Frictionless adoption and deploy 12, Fidelity to the 12:30 proposal 10, Demo or reality (weight not read) [declared: track page pasted by the team]
Track: Building an ontology from a knowledge base (track-3-ontology)

## Shortlist and gate
Chosen before the event: Plant Atlas [declared]. No Potential/Readiness score: intake 1-3 (problem owner, workaround, payer) not given yet.

## The 8hack canvas

### Q1 · Problem
MISSING — needed before the 12:30 video. Draft to confirm: the safety manager (RSPP) of a manufacturing plant cannot tell, on a given day, whether an operator may use a machine, because the answer is spread across the law, the manuals, the internal procedures and the verification log; today: a spreadsheet and memory [unverified].

### Q2 · Focus
One decision: "Can role R use machine M today?" (qualification valid, verifications not overdue), for one fictional plant. We ignore: live plant data, HR systems, any law outside work-equipment safety.

### Q3 · UVP to test
Draft: For the plant safety manager who must decide who can use which machine today, Plant Atlas answers allowed / blocked / unknown with the quoted rule behind each step — unlike search over the documents — because every fact carries a verbatim anchor in its source and dates are computed, not guessed.
Hypothesis: schema-first, anchor-checked extraction (B) answers more competency questions correctly than model-first extraction (A) and plain search, on the same corpus.
Test today: eval/run_eval.py on 15 questions (10 design, 5 held out).
Kill criterion (ex-ante, PROPOSED — team to confirm): B is correct on fewer than 2 more questions than plain search out of 15, or scores below A on the 5 held-out → we pitch the comparison as a negative result (anchors buy precision, not accuracy). Result: pending

### Q4 · USPs
1. search gets date/condition questions wrong → dated facts + rules computed at query time → a correct "blocked" · proof: press P-3 question side by side · vs plain search · angle: proof [unverified]
2. a changed document silently breaks answers → changed sections re-extracted, old facts closed not deleted → answers stay right, change is shown · proof: doc_change.py before/after · vs term graphs · angle: mechanism [unverified]
3. invented facts → no anchor, no fact → counted rejections · proof: proposed / anchored / rejected table · vs model-first extraction · angle: mechanism [unverified]

### Q5 · Single points of failure
| # | Component | How it fails | L/M/H | Impact | Mitigation | Owner | By |
|---|-----------|--------------|-------|--------|------------|-------|----|
| D1 | Legal texts download | site blocks or terms unclear | M | corpus | by hand in browser, 20 min max per source; start with 2 sources | product | 12:10 |
| D2 | Model writes SPARQL | invalid query at demo | H | demo | cached answers for the demo questions; recorded run | engine | 16:00 |
| D3 | Gateway credit $25 | 402 mid-eval | M | numbers | cheap model, cost log, eval on cached extraction | engine | 15:00 |
| D4 | Venue wifi / one laptop | no network | M | demo | results.md and answers stored; backup video | product | 16:00 |
| V1 | Riskiest assumption: B beats A and search on held-out questions | false | M | thesis | kill criterion above | engine | 15:00 |
| V2 | Buyer: nobody named who pays | no business case (20/100) | H | thesis | name segment, price, one real person today | product | 14:30 |

### Q6 · First things to build
Order and done-checks: the coding brief, §8 (kept outside the repo). Time left for building ≈ 3h20, brief time boxes sum to ≈ 6h30 → cuts below.
Cut list (PROPOSED): Neo4j viewer, graph drawing, correction button, decision model, recorded_at; corpus limited to 2 legal sources + the fictional plant first; Strategy A on a subset if behind at 15:00; verifier and reconciliation at their minimum.

### Q7 · Target audience
MISSING — needed before 14:30 (economic model and financial validation at 16:30).

### Q8 · Moat technologies
MISSING — needed before pitch. Copy test to answer: what in the anchor method can a team with the same model not copy in a weekend?

## Landscape (as of 2026-11-11)
Track market research in Control8 (Palantir, Fabric IQ, Graphwise, Cognite, Neo4j builder). Gap named there: ontology from documents, kept current on change, with a published score [verified: track research].

## Evidence log
| When | Who | Quote or observation | Assumption |
|------|-----|----------------------|------------|

## Verification log
| When | What an agent produced | What a human checked, and how | What the agent got wrong |
|------|------------------------|-------------------------------|--------------------------|

## Checkpoints
## Pitch
## Next week
