# 🔮 Dreamcatcher

> *An AI council that evaluates tools and technologies against BLKOUT's values, digital strategy, and infrastructure constraints.*

Dreamcatcher is a lightweight FastAPI service that helps BLKOUT Creative Ltd make better decisions about which tools and technologies to adopt. Rather than deferring to a single AI opinion or a vendor's marketing copy, it convenes a **council of three distinct AI personas** — each with a different lens — and synthesises their views into a clear verdict.

---

## The Council

| Persona | Focus |
|---|---|
| 🔍 **The Skeptic** | Technical debt, vendor lock-in, operational overhead, and sequencing risk |
| ⚖️ **The Ethicist** | Data sovereignty, anti-surveillance, open-source alignment, and community impact |
| 🛠️ **The Builder** | Vibe-codeability, stack compatibility, deployment speed, and maintainability |

Each council member evaluates a submitted URL independently. Their individual recommendations — **GO**, **HOLD**, or **PASS** — are combined by majority rule into a final **Verdict**.

---

## How it works

```
POST /evaluate  { "url": "https://notion.so" }

→ The Skeptic thinks...
→ The Ethicist thinks...
→ The Builder thinks...
→ Verdict: HOLD
```

**Verdict logic:**
- `GO` — 2 or 3 council members recommend it
- `PASS` — 2 or 3 council members reject it
- `HOLD` — mixed signals; not the right time, or needs more information

---

## Project structure

```
dreamcatcher/
├── main.py           # FastAPI app — POST /evaluate endpoint
├── council.py        # The three AI personas and verdict logic
├── requirements.txt  # Python dependencies
├── Dockerfile        # Production-ready container (Coolify-compatible)
├── .env.example      # Environment variable template
└── wishlist.md       # BLKOUT's digital capabilities wishlist (the Council's context)
```

---

## Getting started

### Prerequisites

- Python 3.12+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### Local development

```bash
# 1. Clone the repo
git clone https://github.com/blkout/dreamcatcher.git
cd dreamcatcher

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs (Swagger UI) at `http://localhost:8000/docs`.

### Example request

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://airtable.com"}'
```

Example response:

```json
{
  "url": "https://airtable.com",
  "skeptic": "Airtable is a proprietary SaaS platform with significant vendor lock-in risk...",
  "ethicist": "Airtable's data practices raise questions about member data sovereignty...",
  "builder": "Airtable is genuinely fast to ship with, but the export limitations are a concern...",
  "skeptic_recommendation": "HOLD",
  "ethicist_recommendation": "PASS",
  "builder_recommendation": "HOLD",
  "verdict": "HOLD"
}
```

---

## Deployment on Coolify

1. Push this repo to GitHub
2. In your Coolify dashboard, create a new **Dockerfile**-based service
3. Point it at this repository
4. Set the environment variable: `OPENAI_API_KEY=sk-...`
5. Set the port to `8000`
6. Deploy

That's it. The container will build and serve on your VPS.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | Your OpenAI API key — used by all three council members |

---

## API reference

### `GET /`
Health check. Returns `{ "status": "ok", "service": "dreamcatcher" }`.

### `POST /evaluate`
Submit a tool or resource URL for council evaluation.

**Request body:**
```json
{ "url": "https://example.com" }
```

**Response:**
```json
{
  "url": "string",
  "skeptic": "string",
  "ethicist": "string",
  "builder": "string",
  "skeptic_recommendation": "GO | HOLD | PASS",
  "ethicist_recommendation": "GO | HOLD | PASS",
  "builder_recommendation": "GO | HOLD | PASS",
  "verdict": "GO | HOLD | PASS"
}
```

Full interactive documentation is available at `/docs` when the service is running.

---

## Context

Dreamcatcher was built to support decision-making for [BLKOUT Creative Ltd](https://blkout.co.uk), a Black queer community benefit society. The Council's personas are grounded in BLKOUT's digital capabilities wishlist — a values-first framework that prioritises data sovereignty, community benefit, anti-surveillance design, and infrastructure resilience over novelty or vendor convenience.

The wishlist (`wishlist.md`) informs every system prompt. The Council doesn't evaluate tools in the abstract — it evaluates them for this organisation, with these constraints, at this stage of the build.

---

## Licence

MIT — do what you like, give credit where it's due.
