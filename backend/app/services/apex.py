"""Apex AI customer care assistant backed by Google Gemini.

Each ElimuPro component has its own knowledge card. The selected card, plus
general platform facts, becomes the Gemini system instruction so the assistant
answers like a customer care agent for that component. Only the user's role,
first name and school name are sent to Gemini, never records or contact details.
"""
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from threading import Lock

from flask import current_app

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PLATFORM_FACTS = """\
ElimuPro is a school management platform for Kenyan primary, junior secondary and senior secondary schools.
Roles: students, parents/guardians, teachers, school administrators (admin, principal, deputy), bursars and the platform super admin.
Every record belongs to one school; a school can only see its own data.
School fees are paid DIRECTLY to the school using the payment details the school publishes (bank, paybill, till, cash).
ElimuPro does not hold school-fee money and takes no commission on school fees. Bursars record and verify fee payments;
a receipt upload or screenshot is not confirmation until the school verifies it.
There is no attendance module.
Password reset is not self-service yet: users should ask their school administrator for help.
ElimuPro platform support: ask the school administrator first; schools contact the ElimuPro team through their account manager."""

COMPONENTS = {
    "general": {
        "name": "ElimuPro (general)",
        "knowledge": """\
Help with anything about ElimuPro: signing up, logging in, the student application/admission workflow,
results, timetables, fees, announcements, parent accounts and which component fits a school's needs.
Student signup flow: create account -> complete 3-step application -> submit (reference ELM-YYYY-XXXXXX)
-> school reviews (may request changes, reject or approve) -> on approval the same login opens the student dashboard.
Components sold to schools: Academic Analytics, Financial Analytics, ZeroQ Admissions, ZeroQ Transfers, CareerGPS and Apex AI.
Current component prices:
{pricing}""",
    },
    "academic_analytics": {
        "name": "Academic Analytics",
        "knowledge": """\
Academic Analytics gives a school insight into exam results and learner performance across classes, streams and subjects.
Pricing: {pricing}
Prices are set by the ElimuPro super admin and may change; the price on the school's invoice is final.
Academic Analytics is priced separately from Financial Analytics.""",
    },
    "financial_analytics": {
        "name": "Financial Analytics",
        "knowledge": """\
Financial Analytics gives school leadership and bursars insight into fee collection, balances and payment trends.
Pricing: {pricing}
It is billed independently of Academic Analytics.
It reports on the school's own fee ledger; it never moves fee money. School fees are always paid directly to the school.""",
    },
    "zeroq_admissions": {
        "name": "ZeroQ Admissions",
        "knowledge": """\
ZeroQ digital admissions: "No queue. No paperwork. Just scan."
An admitted student completes admission requirements digitally and gets a secure QR admission pass in the student portal (ZeroQ tab).
On reporting day school staff scan the pass; each pass can only be used once and is tied to one school.
Passes can expire or be revoked by the school; if a pass shows expired, revoked or already used, the student should contact the admissions office.
Pricing: {pricing} It is charged to the school once per admission (never twice for the same admission).
Apex AI may explain the process but never makes or changes admission decisions.""",
    },
    "zeroq_transfers": {
        "name": "ZeroQ Transfers",
        "knowledge": """\
ZeroQ Transfers handles moving a learner between schools digitally, without paperwork queues.
Pricing: {pricing} It is charged once per transfer and priced separately from admissions.
Transfer approval is decided by the schools involved, not by Apex AI. Parents should contact the receiving school's
administration for requirements and status.""",
    },
    "careergps": {
        "name": "CareerGPS",
        "knowledge": """\
CareerGPS guides learners on career paths and subject/pathway choices that match their strengths and interests.
Pricing: {pricing} This is an annual entitlement with start and end dates:
the student is not charged per login or per use. If the price changes, an already-active entitlement stays valid until it ends.
Renewal happens for the next academic year.""",
    },
    "apex_ai": {
        "name": "Apex AI",
        "knowledge": """\
Apex AI is ElimuPro's AI assistant (this assistant). It answers questions about ElimuPro and its components.
Plans: Free and Pro. Pricing: {pricing} Apex AI plans are priced separately from Academic Analytics,
Financial Analytics, ZeroQ and CareerGPS and are not bundled into them.
Apex AI cannot see student records, change data, take payments or make admission decisions.""",
    },
}

# Which price rows each Apex topic quotes. "general" quotes all of them.
PRICE_KEYS = {
    "general": None,
    "academic_analytics": ["academic_analytics"],
    "financial_analytics": ["financial_analytics"],
    "zeroq_admissions": ["zeroq_admissions"],
    "zeroq_transfers": ["zeroq_transfers"],
    "careergps": ["careergps"],
    "apex_ai": ["apex_ai_pro"],
}

RULES = """\
You are Apex AI, the friendly customer care assistant for ElimuPro.
You are currently helping with: {component}.
Behave like a professional customer care agent:
- Greet warmly, be concise (short paragraphs or a few bullet points), patient and polite. Use simple English; reply in Kiswahili if the user writes in Kiswahili.
- Answer ONLY from the facts below. If you do not know, say so and direct the user to their school administrator or the ElimuPro team. Never invent prices, features, dates, phone numbers, emails, bank accounts, paybills or till numbers.
- You cannot see or change any account, record, result, payment or application. Never claim you have done something on the user's behalf.
- Never ask for or accept passwords, PINs, M-Pesa PINs, card numbers or OTP codes. If shared, tell the user not to share them.
- For fee payment questions, remind the user that fees go directly to the school using the school's published details.
- If the question belongs to another ElimuPro component, answer briefly and suggest switching to that topic.
- Stay on ElimuPro topics; politely decline unrelated requests.

User context: {user_context}

Component facts:
{knowledge}

Platform facts:
{platform}"""

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_TURNS = 10


class ApexUnavailable(Exception):
    """Gemini is not configured or did not return a usable answer."""


def component_list():
    return [{"id": key, "name": c["name"]} for key, c in COMPONENTS.items()]


def price_text(component):
    """Live prices from the pricing tables, so Apex AI never quotes a stale figure."""
    from . import pricing
    wanted = PRICE_KEYS[component]
    return "\n".join(pricing.describe(c) for c in pricing.get_components() if wanted is None or c["key"] in wanted)


def system_prompt(component, user=None):
    if user:
        school = user.school.name if user.school_id and user.school else "ElimuPro platform"
        user_context = f"signed-in {user.role.replace('_', ' ')} named {user.first_name} at {school}"
    else:
        user_context = "visitor who is not signed in"
    c = COMPONENTS[component]
    knowledge = c["knowledge"].replace("{pricing}", price_text(component))
    return RULES.format(component=c["name"], user_context=user_context,
                        knowledge=knowledge, platform=PLATFORM_FACTS)


def clean_history(history):
    """Keep only well-formed recent turns; the browser is not trusted to shape the prompt."""
    turns = []
    for item in history if isinstance(history, list) else []:
        if not isinstance(item, dict):
            continue
        role, text = item.get("role"), item.get("text")
        if role in ("user", "assistant") and isinstance(text, str) and text.strip():
            turns.append({"role": role, "text": text.strip()[:MAX_MESSAGE_CHARS]})
    return turns[-MAX_HISTORY_TURNS * 2:]


def ask_gemini(system, history, message):
    key = current_app.config.get("GEMINI_API_KEY")
    if not key:
        raise ApexUnavailable("Apex AI is not configured yet")
    contents = [{"role": "model" if t["role"] == "assistant" else "user", "parts": [{"text": t["text"]}]}
                for t in history]
    contents.append({"role": "user", "parts": [{"text": message}]})
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600},
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model=current_app.config["GEMINI_MODEL"]),
        data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=current_app.config["GEMINI_TIMEOUT"]) as res:
            body = json.loads(res.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        current_app.logger.warning("Gemini request failed: %s", e)
        raise ApexUnavailable("Apex AI could not be reached") from e
    try:
        parts = body["candidates"][0]["content"]["parts"]
        reply = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        reply = ""
    if not reply:
        raise ApexUnavailable("Apex AI did not return an answer")
    return reply


class RateLimiter:
    """Small in-process sliding-window limiter so one caller cannot drain the Gemini quota."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key, limit, window=60):
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


limiter = RateLimiter()
