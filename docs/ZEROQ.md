# ZeroQ

ZeroQ is an additive digital admission-pass and arrival-check-in module inside ElimuNova. It reuses the existing React 18, Flask, SQLAlchemy, PostgreSQL, JWT, school, user, student, and student-application records. It does not introduce a second identity system or duplicate student profile.

## Implemented flow

1. An enrolled student opens `/student/zeroq` and requests a pass.
2. The server creates a 256-bit random bearer token, returns it once for QR rendering, and stores only its SHA-256 digest.
3. The school officer opens `/admin/zeroq/scanner`. A user gesture requests camera access through ZXing; the decoded value is sent to the API.
4. The API validates the token, expiry, revocation, school binding, admission state, and one-time scan claim. It returns a student record only to an authorized officer from the same school.
5. The officer confirms the returned record and completes admission. A repeat scan cannot complete the admission a second time.

The admin overview and today's arrival queue are available at `/admin/zeroq` and `/admin/zeroq/queue`. These screens use the existing responsive ElimuNova shell and role guards.

## Schema

The Alembic revision `718717373009` adds:

| Table | Purpose |
|---|---|
| `zeroq_passes` | School, existing application/student references, opaque-token digest, unique reference, expected date, expiry, revocation, scan and completion timestamps, issuer. |
| `zeroq_scans` | School, optional local pass reference, authenticated scanner, token fingerprint, outcome, and timestamp. |

The current admission state remains in `student_applications`; ZeroQ does not change that existing state machine. Pass states are derived as `ready`, `checked_in`, `completed`, `expired`, or `revoked`.

## Security boundaries

- Existing JWT authentication and roles are reused. Admin endpoints are currently restricted to `school_admin`, `principal`, and `deputy_principal`; students can only manage their own pass.
- Every query is scoped by the authenticated user's `school_id`. A cross-school record lookup returns 404; cross-school QR validation reveals no student details.
- Scan claiming is an atomic conditional update, reducing the chance that simultaneous duplicate scans both succeed.
- Raw QR values are not stored in the database or returned by the pass-read endpoint. Invalid values are logged as hashes.
- Existing `audit_logs` records pass issue/revoke, scans, and completion. Ordinary application administrators have no ZeroQ audit-log editing endpoint.
- Offline scans are never treated as verified. The PWA service worker caches the app shell only, not API responses or student records.

**PostgreSQL RLS is not configured in this repository.** Tenant isolation currently depends on Flask authorization and `school_id`-scoped SQLAlchemy queries, consistent with the rest of ElimuNova. Supabase is not in the existing stack, so this module does not claim Supabase auth or RLS. Database-level RLS needs a separately approved design for application DB roles, migration behavior, and test coverage.

## Camera and QR

The camera scanner uses `@zxing/browser` and a real browser video stream. Camera access needs explicit user permission and a secure context (HTTPS, or localhost during development). It handles permission denial, missing cameras, invalid tokens, expired/revoked/used passes, wrong institutions, and network errors. A network failure displays an unverified state; it never queues a scan for later approval.

The payload has the form `ZEROQ1.<random-token>`. The token has 256 bits of generated entropy, expires after 30 days, is single-use, and can be revoked or replaced before check-in. A regenerated token invalidates prior active passes. The pass reference and student data are not embedded in the QR.

## Deliberately deferred

The current clone has no private file-storage provider or document-upload endpoint. No ZeroQ document upload, signed URL, review/rejection workflow, medical-information collection, or file verification has been added. The existing `application_documents.file_url` is not used for private uploads by this module. A storage provider, private bucket policy, signed URL lifetime, malware scanning, retention, and reviewer permissions need approval before implementation.

Also not added in this slice: a new Admissions Officer role, finance/fee verification, parent notifications, SMS/email delivery, configurable admission states, analytics trends/processing-time metrics, a scan-history browser, offline synchronization, or PostgreSQL RLS. Existing ElimuNova roles remain unchanged. ZeroQ officers can complete approved/enrolled admissions; the slice does not automate admission decisions.

## Configuration, migration, and tests

No new environment variables are required. The module uses the existing `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, and frontend API configuration.

Review the migration, back up the target database, then apply it from `backend/` using the existing procedure:

```powershell
flask --app run:app db upgrade
```

Run backend tests with `python -m pytest -q` from `backend/` and build the frontend with `npm run build` from `frontend/`. For local camera testing, serve the app on `http://localhost` and allow camera access. A deployed scanner requires HTTPS.

Future integrations can connect ZeroQ to ElimuNova parent accounts, notifications, fee records, and reporting after their role, privacy, and data-retention boundaries are approved. Apex AI may summarize admissions trends, but must not make admission decisions.