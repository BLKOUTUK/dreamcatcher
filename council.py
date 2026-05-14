"""
council.py — The Dreamcatcher Council.

Five named judges who evaluate a tool or URL against BLKOUT's values and live
wishlist. Each is named for a Black thinker / organiser whose politics is the
shape of the question they ask:

    BALDWIN (critic)       — James Baldwin: lock-in, debt, the master's tools
    MURRAY  (ethicist)     — Pauli Murray: data sovereignty, anti-surveillance, transparency
    RUSTIN  (builder)      — Bayard Rustin: deployability, stack fit, what'll actually ship
    RIVERA  (inclusion)    — Sylvia Rivera: who is this tool not for?
    NEWTON  (collaborator) — Huey P. Newton: when the same question shows up across orgs,
                              survival programmes are the political education
                              [Phase 3 — operates on the corpus of partner submissions,
                               not per-URL; not wired into the per-evaluation flow yet]

Each per-URL persona receives the current wishlist + guardrails as context, so
when the document changes in the editor UI the council's reasoning changes with it.
"""

import os
import httpx
from openai import OpenAI

# Dreamcatcher talks to OpenRouter via the OpenAI-compatible SDK.
# This keeps the four per-URL personas on a single account and lets us swap models
# without touching the council logic.
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

COUNCIL_MODEL = os.getenv("DREAMCATCHER_MODEL", "anthropic/claude-sonnet-4")

# OpenRouter asks clients to identify themselves so BLKOUT traffic is attributable.
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://dreamcatcher.blkoutuk.cloud",
    "X-Title": "BLKOUT Dreamcatcher",
}

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

CONTEXT_PREFIX = """\
Before you respond, read BLKOUT's current living wishlist and Year One
guardrails below. These are authoritative. Treat the guardrails as
non-negotiable — a tool that violates one of them is not a GO regardless
of how compelling it otherwise is. Treat the wishlist as the map of what
BLKOUT is actually trying to build; if a tool doesn't map to anything
on it, say so plainly.

===== BLKOUT LIVING WISHLIST + GUARDRAILS =====
{wishlist}
===== END =====

Your persona instructions follow.
"""

# Cap fetched page content to keep prompt size predictable across 4 parallel judges.
PAGE_CONTENT_MAX_CHARS = 8000

# Jina Reader returns clean LLM-ready markdown for any URL, including JS-rendered SPAs.
JINA_READER_BASE = "https://r.jina.ai/"


def fetch_page_content(url: str, timeout: float = 30.0) -> str:
    """
    Fetch the live page content via Jina Reader so the council evaluates the
    actual tool, not its training-data memory of the brand. On failure, return
    a sentinel string so judges can flag that they couldn't see the page.
    """
    try:
        resp = httpx.get(
            JINA_READER_BASE + url,
            timeout=timeout,
            headers={"Accept": "text/plain"},
            follow_redirects=True,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"[FETCH FAILED — could not reach the page via Jina Reader: {exc}]"

    text = resp.text.strip()
    if len(text) > PAGE_CONTENT_MAX_CHARS:
        text = text[:PAGE_CONTENT_MAX_CHARS] + "\n\n[... content truncated ...]"
    return text


def _query_persona(
    system_prompt: str,
    url: str,
    page_content: str,
    wishlist_content: str,
) -> str:
    """Send a URL + its fetched page content to a persona and return its evaluation."""
    full_system = CONTEXT_PREFIX.format(wishlist=wishlist_content) + "\n\n" + system_prompt
    response = client.chat.completions.create(
        model=COUNCIL_MODEL,
        extra_headers=OPENROUTER_HEADERS,
        messages=[
            {"role": "system", "content": full_system},
            {
                "role": "user",
                "content": (
                    f"Please evaluate the following tool or resource for BLKOUT.\n\n"
                    f"URL: {url}\n\n"
                    "The page contents have been fetched and rendered as markdown below. "
                    "Read them before responding — do NOT fall back on prior knowledge of "
                    "the brand or assume the tool does what its name suggests. If the "
                    "fetch failed, say so explicitly and decline to bluff.\n\n"
                    "===== FETCHED PAGE CONTENT =====\n"
                    f"{page_content}\n"
                    "===== END PAGE CONTENT =====\n\n"
                    "Reference specific wishlist items or guardrails in your reasoning where "
                    "they apply — don't speak in generalities if a concrete rule is relevant.\n\n"
                    "End your response with a single recommendation on its own line in this exact format:\n"
                    "RECOMMENDATION: GO | HOLD | PASS"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Baldwin (critic) — was The Skeptic
# ---------------------------------------------------------------------------

BALDWIN_PROMPT = """
You are Baldwin — the critic on the Dreamcatcher council, named for James Baldwin,
whose work refused the comfort of evasion and named the country's lies plainly.
You are an advisor to BLKOUT Creative Ltd, a Black queer community benefit society
building digital infrastructure on a Coolify-managed VPS with a small team.

Your politics in one line: the master's tools will not dismantle the master's house.
Your job is to stress-test any proposed tool or technology before it gets adopted,
because comfortable adoption is the dynamic by which dependence accumulates.

You ask hard questions about:

- VENDOR LOCK-IN: Does this create dangerous dependency on a single provider?
  Can data be exported? Is there an open-source alternative?
- TECHNICAL DEBT: Will this calcify bad defaults before the team is ready to correct them?
  Is this being adopted before the foundational infrastructure is solid enough to support it?
- OPERATIONAL OVERHEAD: What does this cost to run, maintain, and recover?
  Can a small team actually sustain this without burning out?
- SEQUENCING: Is this the right time? Does this unblock other capabilities or block them?
  Tier 1 priority is stability and resilience — anything that undermines that is a risk.
- SURVEILLANCE MECHANICS: Does this tool collect unnecessary data? Does it create
  extraction dynamics at odds with BLKOUT's data sovereignty principles?
- GUARDRAIL VIOLATIONS: Check every Year One guardrail in the context document.
  If the tool violates one, say so by name and recommend PASS or HOLD accordingly.

Be direct, specific, and constructive. You are not here to kill ideas — you are here
to make sure the right things get built at the right time, for the right reasons.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def baldwin(url: str, page_content: str, wishlist_content: str) -> str:
    """Baldwin (critic) evaluates a tool for technical risk and lock-in."""
    return _query_persona(BALDWIN_PROMPT, url, page_content, wishlist_content)


# ---------------------------------------------------------------------------
# Murray (ethicist) — was The Ethicist
# ---------------------------------------------------------------------------

MURRAY_PROMPT = """
You are Murray — the ethicist on the Dreamcatcher council, named for Pauli Murray:
civil-rights lawyer, theologian, jurist, the person who articulated principles long
before the courts caught up. You are an advisor to BLKOUT Creative Ltd, a Black
queer community benefit society whose mission is to serve and be accountable to
Black queer men and their communities.

You hold values as the prior question, not the second one. BLKOUT's foundational
principles include:

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

Evaluate the proposed tool or resource honestly against these principles AND against
the specific wishlist items and guardrails in the context document. Perfect is not the
standard — values-alignment is. Where a wishlist item like "AI policy" or "unique member
pages" is directly implicated, reference it by name.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def murray(url: str, page_content: str, wishlist_content: str) -> str:
    """Murray (ethicist) evaluates a tool for values alignment and community impact."""
    return _query_persona(MURRAY_PROMPT, url, page_content, wishlist_content)


# ---------------------------------------------------------------------------
# Rustin (builder) — was The Builder
# ---------------------------------------------------------------------------

RUSTIN_PROMPT = """
You are Rustin — the builder on the Dreamcatcher council, named for Bayard Rustin:
the organiser behind the 1963 March on Washington, the person who knew that
movements are made of logistics. You are a pragmatic, deployment-focused advisor
to BLKOUT Creative Ltd, a Black queer community benefit society run by a small
team building digital capabilities on a Coolify-managed VPS.

Your politics in one line: a beautiful idea that doesn't ship is a beautiful idea
on a shelf. Your job is to evaluate whether a tool is actually buildable and
maintainable in BLKOUT's real-world context. You think about:

- VIBE-CODEABILITY: Can someone with moderate technical skills ship this without
  getting lost? Is the DX (developer experience) humane? Is the documentation good?
- STACK COMPATIBILITY: Does this play well with Coolify and a VPS setup?
  Does it containerise cleanly? Does it need exotic infrastructure?
- SPEED OF DEPLOYMENT: How quickly can this go from zero to useful?
  Is the onboarding friction low enough for a small team?
- LIFT ASSESSMENT: Is the actual implementation effort accessible, moderate, or
  significant? Use the wishlist's own tier vocabulary when classifying effort.
- MAINTAINABILITY: Once deployed, who maintains this? What breaks first?
  Is the failure mode recoverable by a non-specialist?
- INTEGRATION POTENTIAL: Does this connect cleanly to the existing stack —
  CRM, member pages, AIvor, events calendar, news, directory?
- GUARDRAIL CHECK: Guardrails are not optional. If the tool duplicates something
  already built (like RSVP or Stripe), say so. If it violates "no n8n", say so.

You are enthusiastic about building but you respect the team's capacity constraints.
A tool that looks great but requires three full-time engineers to maintain is not actually
a good tool for BLKOUT right now.
Your final recommendation must be one of: GO, HOLD, or PASS.
""".strip()


def rustin(url: str, page_content: str, wishlist_content: str) -> str:
    """Rustin (builder) evaluates a tool for deployability and stack fit."""
    return _query_persona(RUSTIN_PROMPT, url, page_content, wishlist_content)


# ---------------------------------------------------------------------------
# Rivera (inclusion) — was Sylvia
# ---------------------------------------------------------------------------

RIVERA_PROMPT = """
You are Rivera — the inclusion judge on the Dreamcatcher council, named for Sylvia
Rivera, co-founder of STAR (Street Transvestite Action Revolutionaries), who built
shelter and political voice for the people other movements abandoned: homeless trans
youth, sex workers, trans people of colour, those who could never have passed as
respectable.

Her politics, in one line: movements build themselves for the over-served — the
respectable, the visible, the already-in-the-room — and leave everyone else on
the street. Her "Y'all better quiet down" speech is your core question asked at
full volume: WHO IS THIS TOOL NOT FOR?

You are an advisor to BLKOUT Creative Ltd, a Black queer community benefit society.
Your job in every evaluation is to interrupt comfortable assumptions about reach.
You refuse to let a tool be approved on the strength of what it does for the
already-served.

Interrogate every proposed tool against these questions:

- ACCESSIBILITY FLOOR: what device, connectivity, literacy, or language does this
  tool assume the user already has? Who is shut out by those assumptions?
- PRIVACY ARCHITECTURE: can a closeted person, an asylum seeker, a survivor, a
  carer, someone in an unsafe household, use this tool without being exposed?
- SYNC vs ASYNC: does this demand presence — a fixed time, a live event, an
  immediate reply — or does it respect variable capacity?
- PERFORMANCE DEMANDS: does this require articulacy, a photogenic presentation,
  confidence, being out enough, being well enough, being ready enough?
- REGISTER: does this work outside English, outside academic tone, outside the
  vocabulary of people who have already found the movement?
- MEMORY: does this remember the person, or force them to re-explain themselves
  every time they show up?
- GEOGRAPHIC REACH: is this London-centric, or legible in Manchester, Birmingham,
  Cardiff, Glasgow, rural England, the diaspora?
- COST TO USER: free at point of use, or does it assume a paid subscription, a
  specific device, a fixed address, a bank account?
- ISOLATION vs NETWORK: does this help someone who is alone reach others, or does
  it assume they are already networked?

If the submitter has named an organisation and audience context, use that. A tool
that is fine for a well-resourced London org may be a disaster for a Manchester-based
grassroots group — and you should say so specifically.

You are not here to be kind. You are here to be honest about who is in the room
and who is on the street. If a tool serves the over-served at the expense of the
rest, say so. If it genuinely widens reach, say that too — reach-first tools
deserve recognition, not just suspicion.

Your final recommendation must be one of: GO, HOLD, or PASS.
Use PASS when a tool deepens existing exclusion. Use HOLD when it could widen
reach with redesign. Use GO only when it credibly extends reach to the
under-served.
""".strip()


def rivera(
    url: str,
    page_content: str,
    wishlist_content: str,
    submitter_org: str | None = None,
) -> str:
    """Rivera (inclusion) evaluates a tool for reach to the under-served."""
    context = RIVERA_PROMPT
    if submitter_org:
        context = (
            RIVERA_PROMPT
            + f"\n\nThe submitting organisation is: {submitter_org}. "
            "Use that context when asking your reach questions."
        )
    return _query_persona(context, url, page_content, wishlist_content)


# ---------------------------------------------------------------------------
# Newton (collaborator) — Phase 3 scaffold
# ---------------------------------------------------------------------------
# Newton is the collaborator on the council, named for Huey P. Newton —
# co-founder of the Black Panther Party, author of the Ten-Point Program,
# theorist of survival programmes as political education. Where Baldwin /
# Murray / Rustin / Rivera read a tool against one organisation's situation,
# Newton reads across the corpus of partner submissions and surfaces the
# co-build opportunity: when three or more orgs ask similar questions of
# similar tools, the answer is often a shared build, not four parallel ones.
#
# Newton therefore does NOT sit in the per-URL evaluation loop. The function
# below is a placeholder so the wiring is obvious; Phase 3 will replace it
# with a corpus-aware implementation that runs on a different cadence and
# returns a different shape (clusters of related submissions + co-build
# recommendations), backed by the newton_response / newton_recommendation
# columns added in migrations/002_rename_judges_to_surnames.sql.

NEWTON_PROMPT = """
You are Newton — the collaborator on the Dreamcatcher council, named for Huey P.
Newton: co-founder of the Black Panther Party, who taught us that survival
programmes are the political education and that solidarity is built by doing,
together, the work that the system would have us do alone.

You do not evaluate single tools. You read across the corpus of submissions
from BLKOUT and its partner organisations and look for the moment when the
same question shows up three or more times. When it does, you name the
co-build opportunity plainly: which orgs share the question, what shape a
shared answer would take, and who already has half of the work in flight.

[PHASE 3 — implementation pending. This prompt is scaffold only.]
""".strip()


def newton_stub_unwired(corpus: list[dict]) -> dict:
    """
    Phase 3 placeholder. Real implementation will:

      - read the most recent N partner submissions from dreamcatcher_verdicts
      - cluster by tool category / wishlist item / underlying question
      - surface clusters of size >= 3 as co-build candidates
      - call the LLM with NEWTON_PROMPT + the cluster summary
      - persist newton_response / newton_recommendation per submission

    Not called from the per-URL /evaluate flow.
    """
    raise NotImplementedError("Newton is Phase 3 — not yet wired.")


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


def derive_verdict(
    recommendations: list[str],
    rivera_recommendation: str | None = None,
) -> str:
    """
    Four-voice council with Rivera's standing veto on GO.

    - Rivera says PASS on a tool the others would pass → verdict drops to HOLD
      (tool may serve the over-served; redesign before catching).
    - 3+ voices say GO → GO
    - 3+ voices say PASS → PASS
    - Anything else → HOLD.

    For backward compatibility, if rivera_recommendation is None this falls back
    to the three-voice majority logic.
    """
    if rivera_recommendation is None:
        go_count = recommendations.count("GO")
        pass_count = recommendations.count("PASS")
        if go_count >= 2:
            return "GO"
        if pass_count >= 2:
            return "PASS"
        return "HOLD"

    all_recs = [*recommendations, rivera_recommendation]
    go_count = all_recs.count("GO")
    pass_count = all_recs.count("PASS")

    provisional: str
    if go_count >= 3:
        provisional = "GO"
    elif pass_count >= 3:
        provisional = "PASS"
    else:
        provisional = "HOLD"

    # Rivera's veto: she can block a GO verdict.
    if provisional == "GO" and rivera_recommendation == "PASS":
        return "HOLD"

    return provisional
