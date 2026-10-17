# Apex AI customer care (Google Gemini)

Apex AI is a floating "Ask Apex AI" chat available on every page (landing page and all portals).
It acts as ElimuPro customer care and answers per component:

| Component id | Topic |
| --- | --- |
| `general` | ElimuPro in general (signup, admissions workflow, portals) |
| `academic_analytics` | Academic Analytics (KSh 10,000 / 15,000 per term) |
| `financial_analytics` | Financial Analytics (KSh 10,000 / 15,000 per term, priced independently) |
| `zeroq_admissions` | ZeroQ Admissions (KSh 450 per admission) |
| `zeroq_transfers` | ZeroQ Transfers (KSh 400 per transfer) |
| `careergps` | CareerGPS (KSh 1,000 per student per academic year) |
| `apex_ai` | Apex AI plans (Free, Pro USD 5) |

The widget preselects a topic from the current page (e.g. ZeroQ pages → ZeroQ Admissions) and keeps a separate
conversation per topic. Users can switch topic from the "Help with" menu.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | empty | Server-side only. Empty disables the assistant (chat returns 503). Get one at https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any Gemini model that supports `generateContent` |
| `GEMINI_TIMEOUT` | `20` | Seconds |
| `APEX_RATE_LIMIT_PER_MINUTE` | `12` | Per signed-in user, or per IP for visitors. In-process, so per worker |

## API

- `GET /api/v1/apex/components` → `{components: [{id, name}], enabled}`
- `POST /api/v1/apex/chat` with `{component, message, history: [{role: "user"|"assistant", text}]}` → `{reply, component}`.
  Auth is optional; a valid token adds the user's role, first name and school name to the prompt.
  Errors: 422 invalid input, 429 rate limited, 503 Gemini not configured or unreachable.

## Guardrails

- The knowledge for each component lives in `backend/app/services/apex.py`; the browser cannot change the system prompt
  (history is limited to user/assistant turns, 10 exchanges, 1,000 characters each).
- No records, emails or phone numbers are sent to Gemini.
- The assistant is told never to invent prices or payment details, never to ask for passwords/PINs/OTPs, never to claim it
  changed anything, and to state that school fees are paid directly to the school.
- Prices in the prompt match the pricing spec defaults. When the pricing engine is built, update `COMPONENTS` (or load prices
  from it) so Apex AI quotes the live configuration.
