# Plant Atlas

The machine-safety register that checks itself. It reads regulations, machine manuals and internal procedures, looks at photos taken on the shop floor, and tells for each machine whether it can be used today — citing the page or the photo that proves it, and recording every decision.

Built on 14 November 2026 at the KVA Hackathon "AI brain for industry".

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env — then put the key in .env
streamlit run app/streamlit_app.py
```

`ATLAS_FAKE=1` (the default in `.env.example`) runs the app on fake data, without the core or a model key.

## Layout

| Path | What |
|---|---|
| `atlas/contracts.py` | shared types: Statement, Answer, Card, Verdict |
| `atlas/api.py` | the only functions the app calls |
| `atlas/core/` | statements, `write_statement`, `as_of`, state rules, event log |
| `atlas/reader/` | documents → statements with page citations |
| `atlas/vision/` | photos → observed statements |
| `atlas/fake.py` | fake data for the app |
| `app/` | Streamlit app |
| `data/` | fictional plant, manual, procedure, photos (all made on the day) |
| `tests/` | the five test questions |

Collaboration rules: [AGENTS.md](AGENTS.md). Models and AI tools used: [AI_TOOLS.md](AI_TOOLS.md).

## Licence

To be chosen by the team (see `LICENSE`).
