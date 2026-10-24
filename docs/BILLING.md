# Billing: component invoices paid by M-Pesa (Cyzora Pay)

Schools pay ElimuNova for Academic Analytics, Financial Analytics, ZeroQ and CareerGPS. The platform super admin issues an
invoice, the school admin pays it with an M-Pesa STK push sent through Cyzora `POST /charges`, and the invoice is marked
paid only after Cyzora confirms it. **School fees are not part of this.** Those stay as recorded payments, and the
older Daraja route in `routes/finance.py` is untouched. Apex AI Pro is priced in USD and cannot be invoiced here yet.

## How a payment flows

1. Super admin: Platform > Invoices > Issue invoice (school, component, quantity, billing period). The server prices it from
   the live pricing tables and stores that price on the invoice. One component cannot be invoiced twice to a school for the
   same period/batch label.
2. School admin: Billing > Pay with M-Pesa. The server sends `POST /charges` (amount in cents, `account_ref` = invoice number,
   an `Idempotency-Key` per attempt) and records a `payment_attempts` row as `pending`. **Nothing is marked paid yet.**
3. Cyzora sends `charge.succeeded` / `charge.failed` / `charge.expired` to the webhook. The handler verifies
   `X-Cyzora-Signature` (HMAC-SHA256 of the raw body, constant-time compare, 401 on mismatch), then fetches the charge with
   `GET /charges/{id}` instead of trusting the body, checks the amount equals the invoice amount, and only then marks the invoice
   paid. Repeated webhooks change nothing.
4. The Billing page polls `POST /billing/invoices/<id>/refresh` for about two minutes. That endpoint asks Cyzora directly, so a
   payment whose webhook was lost is still recovered. The UI shows "paid" only when the server says so.

Fail-safe rules: a wrong amount (`amount_mismatch`), a test event on a live key (or the reverse), an unknown charge, or a
voided/already-paid invoice never marks anything paid and is written to the audit log (`billing.*`). A payment that arrives for
an invoice that is already settled or void is logged as `billing.unexpected_payment` so it can be refunded by hand.

## Configuration

| Variable | Notes |
| --- | --- |
| `CYZORA_SECRET_KEY` | `sk_test_...` while testing, `sk_live_...` in production. Server only. Empty keeps online payments off (pay returns 503). |
| `CYZORA_WEBHOOK_SECRET` | `whsec_...`, from the Cyzora Webhooks page. The webhook returns 503 until it is set. |
| `CYZORA_BASE_URL` | Default `https://api.cyzora.co.ke/api/v1`. |
| `CYZORA_TIMEOUT`, `CYZORA_RETRY_DELAY` | Defaults 20 s and 1 s. A 429, or a 409 with the same idempotency key, is retried twice with doubling delay. |

## Set up in the Cyzora dashboard

1. API keys: create a secret key (`sk_test_...` first). Do not use the `pk_` key; it is only for hosted checkout.
2. Webhooks: add `https://<your-api-domain>/api/v1/billing/webhooks/cyzora`, subscribe to `charge.succeeded`, `charge.failed`
   and `charge.expired`, and copy the `whsec_...` secret into `CYZORA_WEBHOOK_SECRET`.
3. Redirect domains are not needed (this uses STK push with our own screen, not hosted checkout).
4. Going live needs a verified Cyzora business. Switch both secrets to the live values together.

## Test end to end with a test key

1. Set `CYZORA_SECRET_KEY=sk_test_...` and `CYZORA_WEBHOOK_SECRET=whsec_...`, run `flask --app run:app db upgrade`, restart the API.
2. In the Cyzora Webhooks page press **Send test**: the response should be 200 (`webhook.test`).
3. As super admin, issue an invoice. As that school's admin, open Billing and pay with each test number:
   `0700000001` succeeds (invoice turns paid), `0700000002` fails (balance too low), `0700000003` fails (cancelled),
   `0700000004` times out. After a failure the invoice stays unpaid and you can retry after 2 minutes.
4. Check `audit_logs` for `billing.pay_started` and `billing.invoice_paid`.

## Not verified against the live Cyzora docs

`docs.cyzora.co.ke` was unreachable when this was written, so it follows the integration brief. The brief does not show the
JSON of a charge, so `services/cyzora.py::charge_fields` assumes `id`, `status`, `amount` (cents, or `amount_cents`) and
`receipt`, inside `data` or at the top level for webhooks. If a name differs, payments fail safe (stay unpaid) and only that
function changes. Confirm with a real `sk_test_` charge before going live.

Known limits: a prompt that is still pending blocks a second one for 2 minutes; if the first later succeeds and a second also
succeeds, the second is logged as `unexpected_payment`. Admissions and transfers are billed by batch label; there is no
automatic usage count, so avoid issuing overlapping batches.
