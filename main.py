"""
main.py — Dreamcatcher API

FastAPI app exposing a single POST /evaluate endpoint.
Submits a URL to all three council members (The Skeptic, The Ethicist, The Builder)
and returns their individual evaluations plus a combined Verdict: GO | HOLD | PASS.
"""

import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env file (for local development; in production set env vars directly)
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from council import (
    builder,
    derive_verdict,
    ethicist,
    extract_recommendation,
    skeptic,
)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook."""
    print("🔮 Dreamcatcher is awake. The Council is ready.")
    yield
    print("🔮 Dreamcatcher is shutting down.")


app = FastAPI(
    title="Dreamcatcher",
    description=(
        "An AI council that evaluates tools and technologies against "
        "BLKOUT's values, digital strategy, and infrastructure constraints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    url: HttpUrl

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"url": "https://notion.so"}
            ]
        }
    }


class EvaluateResponse(BaseModel):
    url: str
    skeptic: str
    ethicist: str
    builder: str
    skeptic_recommendation: str
    ethicist_recommendation: str
    builder_recommendation: str
    verdict: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
async def health_check():
    """Simple health check — confirms the service is running."""
    return {"status": "ok", "service": "dreamcatcher"}


@app.post("/evaluate", response_model=EvaluateResponse, tags=["council"])
async def evaluate(request: EvaluateRequest):
    """
    Submit a URL to the Dreamcatcher Council for evaluation.

    The three council members — The Skeptic, The Ethicist, and The Builder —
    each assess the tool independently. Their individual recommendations are
    then combined into a final Verdict:

    - **GO** — 2 or 3 council members recommend it
    - **PASS** — 2 or 3 council members reject it
    - **HOLD** — mixed signals; needs more information or isn't the right time
    """
    url_str = str(request.url)

    try:
        # Run all three personas concurrently for speed
        skeptic_response, ethicist_response, builder_response = await asyncio.gather(
            asyncio.to_thread(skeptic, url_str),
            asyncio.to_thread(ethicist, url_str),
            asyncio.to_thread(builder, url_str),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Council member failed to respond: {exc}",
        ) from exc

    # Extract individual recommendations
    skeptic_rec = extract_recommendation(skeptic_response)
    ethicist_rec = extract_recommendation(ethicist_response)
    builder_rec = extract_recommendation(builder_response)

    # Derive final verdict
    verdict = derive_verdict([skeptic_rec, ethicist_rec, builder_rec])

    return EvaluateResponse(
        url=url_str,
        skeptic=skeptic_response,
        ethicist=ethicist_response,
        builder=builder_response,
        skeptic_recommendation=skeptic_rec,
        ethicist_recommendation=ethicist_rec,
        builder_recommendation=builder_rec,
        verdict=verdict,
    )
