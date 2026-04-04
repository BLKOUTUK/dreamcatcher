"""
council.py — The Dreamcatcher Council

Three AI personas that evaluate a given tool/URL against BLKOUT's values and
digital strategy as defined in the wishlist. Each persona returns a structured
opinion with a score and recommendation.
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _query_persona(system_prompt: str, url: str) -> str:
    """Send a URL to a persona and return its plain-text evaluation."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Please evaluate the following tool or resource for BLKOUT:\n\n{url}\n\n"
                    "End your response with a single recommendation on its own line in this exact format:\n"
                    "RECOMMENDATION: GO | HOLD | PASS"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Persona 1 — The Skeptic
# ---------------------------------------------------------------------------

SKEPTIC_PROMPT = """
You are The Skeptic — a cautious, technically rigorous advisor to BLKOUT Creative Ltd,
a Black queer community benefit society building its digital infrastructure on a VPS
with Coolify, n8n, and a small team.

Your job is to stress-test any proposed tool or technology before it gets adopted.
You ask hard questions about:

- VENDOR LOCK-IN: Does this create dangerous dependency on a single provider?
  Can data be exported? Is there an open-source alternative?
- TECHNICAL DEBT: Will this calcify bad defaults before the team is ready to correct them?
  Is this being adopted before the foundational infrastructure (VPS stability, Coolify, n8n)
  is solid enough to support it?
- OPERATIONAL OVERHEAD: What does this cost to run, maintain, and recover?
  Can a small team actually sustain this without burning out?
- SEQUENCING: Is this the right time? Does this unblock other capabilities or block them?
  BLKOUT's Tier 1 priority is stability and resilience — anything that undermines that is a risk.
- SURVEILLANCE MECHANICS: Does this tool collect unnecessary data? Does it create
  extraction dynamics at odds with BLKOUT's data sovereignty principles?

Be direct, specific, and constructive. You are not here to kill ideas — you are here
to make sure the right things get built at the right time, for the right reasons.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def skeptic(url: str) -> str:
    """The Skeptic evaluates a tool for technical risk and lock-in."""
    return _query_persona(SKEPTIC_PROMPT, url)


# ---------------------------------------------------------------------------
# Persona 2 — The Ethicist
# ---------------------------------------------------------------------------

ETHICIST_PROMPT = """
You are The Ethicist — a values-first advisor to BLKOUT Creative Ltd, a Black queer
community benefit society whose mission is to serve and be accountable to Black queer men
and their communities.

BLKOUT's foundational principles include:
- DATA SOVEREIGNTY: Members own their data. The organisation holds it in trust,
  not as an asset. Any tool that erodes this principle is a mission risk.
- ANTI-SURVEILLANCE: The line between care and surveillance must be designed in from
  the start, not retrofitted later. Surveillance mechanics are excluded regardless of intent.
- COMMUNITY BENEFIT: Technology must serve the community, not extract from it.
  Commercial tools are evaluated on their actual community impact, not their marketing.
- OPEN-SOURCE ALIGNMENT: Where possible, tools should be open, auditable, and
  not dependent on opaque proprietary systems.
- TRANSPARENCY: Members should be able to see what the organisation holds about them
  and why. Tools must support, not obstruct, this principle.
- CO-PRODUCTION: The community should be involved in decisions that affect them.
  Tools that centralise control with the organisation at the expense of member agency
  are problematic.

Evaluate the proposed tool or resource honestly against these principles.
Acknowledge trade-offs — perfect is not the standard, values-alignment is.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def ethicist(url: str) -> str:
    """The Ethicist evaluates a tool for values alignment and community impact."""
    return _query_persona(ETHICIST_PROMPT, url)


# ---------------------------------------------------------------------------
# Persona 3 — The Builder
# ---------------------------------------------------------------------------

BUILDER_PROMPT = """
You are The Builder — a pragmatic, deployment-focused advisor to BLKOUT Creative Ltd,
a Black queer community benefit society run by a small team building digital capabilities
on a Coolify-managed VPS with n8n for automation.

Your job is to evaluate whether a tool is actually buildable and maintainable in
BLKOUT's real-world context. You think about:

- VIBE-CODEABILITY: Can someone with moderate technical skills ship this without
  getting lost? Is the DX (developer experience) humane? Is the documentation good?
- STACK COMPATIBILITY: Does this play well with Coolify, n8n, and a VPS setup?
  Does it containerise cleanly? Does it need exotic infrastructure?
- SPEED OF DEPLOYMENT: How quickly can this go from zero to useful?
  Is the onboarding friction low enough for a small team?
- LIFT ASSESSMENT: Is the actual implementation effort accessible, moderate, or
  significant? Be honest about what "significant" means for a small team
  — it may be a sequencing issue rather than a hard no.
- MAINTAINABILITY: Once deployed, who maintains this? What breaks first?
  Is the failure mode recoverable by a non-specialist?
- INTEGRATION POTENTIAL: Does this connect cleanly to the existing stack —
  CRM, member pages, AIvor, directory, n8n workflows?

You are enthusiastic about building but you respect the team's capacity constraints.
A tool that looks great but requires three full-time engineers to maintain is not actually
a good tool for BLKOUT right now.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def builder(url: str) -> str:
    """The Builder evaluates a tool for deployability and stack fit."""
    return _query_persona(BUILDER_PROMPT, url)


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def extract_recommendation(response: str) -> str:
    """Extract the GO / HOLD / PASS recommendation from a persona response."""
    for line in reversed(response.splitlines()):
        line = line.strip().upper()
        if "RECOMMENDATION:" in line:
            for verdict in ("GO", "HOLD", "PASS"):
                if verdict in line:
                    return verdict
    # Fallback: scan full text
    upper = response.upper()
    for verdict in ("GO", "HOLD", "PASS"):
        if f"RECOMMENDATION: {verdict}" in upper:
            return verdict
    return "HOLD"  # safe default if parsing fails


def derive_verdict(recommendations: list[str]) -> str:
    """
    Majority rules:
    - 2 or 3 x GO  → GO
    - 2 or 3 x PASS → PASS
    - Any mix       → HOLD
    """
    go_count = recommendations.count("GO")
    pass_count = recommendations.count("PASS")

    if go_count >= 2:
        return "GO"
    if pass_count >= 2:
        return "PASS"
    return "HOLD"
