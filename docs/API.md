# API reference (base path `/api/v1`, JSON)

`/api` remains available as a compatibility alias. New clients should use `/api/v1`.

Success: `{"success": true, "data": ..., "message"?: ..., "meta"?: {page, per_page, total, pages}}`.
Error: `{"success": false, "message": "...", "errors"?: {field: message}}` with 400/401/403/404/409/422/503.
Send `Authorization: Bearer <token>`. The role and school always come from the database user, never from the request.
Other schools' record IDs return **404**.

## Health
GET `/health` is a liveness check. GET `/health/ready` checks the database connection and returns 503 when it is unavailable.

## Auth
| Method & path | Who | Notes |
|---|---|---|
| POST `/auth/register` | public | Student signup: `school_id, first_name, last_name, email, phone, password` (+`middle_name`). Creates account + draft application, returns token |
| POST `/auth/login` | public | `email, password` → `{token, user}` |
| GET `/auth/me` | any | user + `is_enrolled`, `application_status` for students |
| POST `/auth/change-password` | any | `current_password, new_password` |

## Schools
GET `/schools/public` (public, active schools with admissions open) · GET/PUT `/schools/me` · GET `/schools/overview` (admin, bursar) ·
GET/POST `/schools`, PATCH `/schools/<id>/status` (super admin).

## Admissions
Student: GET/PUT `/admissions/my`, POST `/admissions/my/submit`.
Admin/principal/deputy: GET `/admissions?status=&q=&page=`, GET `/admissions/<id>`, POST `/admissions/<id>/review` (`action`: under_review | changes_required | rejected, `note` required for the last two),
POST `/admissions/<id>/approve` (`class_id`, optional `stream_id`, `admission_number`, `note`) → creates the student.

## Students
Student: GET/PATCH `/students/me` (phone only), `/students/me/dashboard`, `/me/results`, `/me/fees`, `/me/timetable`, `/me/announcements`.
Staff: GET `/students?q=&class_id=&status=&page=`, GET `/students/<id>`, PATCH `/students/<id>` (admin: `class_id, stream_id, status`).

## Academics
GET/POST `/classes`, POST `/classes/<id>/streams`, GET/POST `/subjects`, GET `/terms`, GET `/grading`, GET/POST `/exams`,
POST `/results` (`exam_id, subject_id, entries[{student_id, marks, remark}]`), POST `/timetable`.

## Finance
GET/POST `/fees/structures`, POST `/fees/assign` (`term_id`), GET `/fees/balances`, GET/POST `/payments`,
POST `/payments/mpesa/stk-push` (503 unless configured; untested).

## Announcements
GET `/announcements` (students see only their audience/class), POST `/announcements` (admin).

## Teachers
Admin/principal/deputy: GET/POST `/teachers` (`first_name, last_name, email, password`, optional `phone`, `role` teacher|class_teacher), PATCH `/teachers/<id>` (`is_active`, `role`),
POST `/teachers/<id>/assignments` (`class_id, subject_id`), DELETE `/teachers/<id>/assignments/<assignment_id>`.
Teacher: GET `/teacher/dashboard`, `/teacher/classes`, `/teacher/classes/<class_id>/students` (403 if not assigned), `/teacher/announcements`.
Teachers are also allowed on: GET `/students` and `/students/<id>` (only learners in assigned classes, no fee data), GET/POST `/exams` (assigned classes only),
GET `/results?exam_id=&subject_id=` (mark sheet) and POST `/results` (403 unless assigned to that class **and** subject; every student must be in the exam's class;
marks must be 0..exam max; duplicate students in one submission are rejected; the whole submission is rejected if any entry is invalid).

## Parents
Admin/principal/deputy: GET `/parents` (parent logins with linked children), POST `/students/<id>/parent-account`
(`guardian_id`, `email`, `password`): creates a parent login for one of the student's guardians, or, if `email` already belongs to a parent of the same school,
links the guardian to that account (password not needed) so siblings share a login. 409 if the guardian already has a login or the email belongs to another role/school.
Parent: GET `/parent/dashboard`, `/parent/children/<student_id>` (+ `/results`, `/fees`, `/timetable`), `/parent/announcements` (audiences "all" and "parents", class-targeted notices only for classes of their children).
A parent can reach only children linked through a guardian record; any other student id (including other schools') returns 404. Parents get 403 on every staff, teacher and student endpoint.

## ZeroQ
Student: GET `/zeroq/my`, POST `/zeroq/my/pass` (optional `expected_on: YYYY-MM-DD`), POST `/zeroq/my/pass/revoke`.
School admin/principal/deputy: GET `/zeroq/dashboard`, GET `/zeroq/queue?date=YYYY-MM-DD&q=`, POST `/zeroq/scan` (`qr_value`), POST `/zeroq/<pass_id>/complete`, POST `/zeroq/<pass_id>/revoke`.
The QR value is an opaque, one-time token; scan results are validated server-side and are bound to the authenticated user's school. Invalid, expired, revoked, reused, and wrong-school scans return a clear `status` and are logged. Camera failures and network errors must not be presented as verified. Scan history has no staff browsing endpoint in this first slice.

## Pricing
Super admin only (every other role gets 403): GET `/pricing` lists every component with its current price; PUT `/pricing/<key>` edits one.
Keys: `academic_analytics`, `financial_analytics`, `zeroq_admissions`, `zeroq_transfers`, `careergps`, `apex_ai_pro_monthly` (USD 5 per month), `apex_ai_pro_yearly` (USD 40 per year).
PUT accepts `is_active`, `description`, `name`, plus `amount` for a flat component or `tiers` for a tiered one (sending the wrong one is a 422).
`tiers` is a list of `{up_to_students, amount}`: 2 to 6 bands, limits strictly increasing, and the last band has `up_to_students: null` (no upper limit).
A limit is **inclusive**: a school with exactly 1,000 students pays the "up to 1,000" band, so no school size falls in a gap.
Amounts are 0 to 10,000,000 with at most 2 decimals. Nothing is written until validation passes, and each edit is written to the audit log with the before and after values.
Until a component is first edited it uses the launch default from `services/pricing.py`; the first edit creates its row. Billing unit and currency are fixed per component.
`services.pricing.price_for(component, students)` returns the unit price for a school size and is what invoicing should call.

## Billing
See [BILLING.md](BILLING.md). Super admin: GET/POST `/billing/invoices` (`school_id`, `component_key`, `quantity`, `reference`), POST `/billing/invoices/<id>/void`.
School admin/principal/deputy (own school only, other schools' ids return 404): GET `/billing/invoices`, GET `/billing/invoices/<id>`,
POST `/billing/invoices/<id>/pay` (`phone`; sends the STK push, answers 202, never marks paid), POST `/billing/invoices/<id>/refresh` (asks Cyzora for the latest status).
Public but signed: POST `/billing/webhooks/cyzora` (requires a valid `X-Cyzora-Signature`; 401 otherwise, 503 until configured).
Invoice amounts are whole KES shillings; Cyzora receives cents. `pay` errors: 409 already paid or a prompt was just sent, 422 bad phone or provider refusal, 429 provider busy, 502 provider unreachable, 503 not configured.

## ZeroQ onboarding, documents and review
Student: GET/PUT `/zeroq/my/results` (`assessment_year`, `candidate_number`, `subjects: [{subject, result}]`), POST `/zeroq/my/results/<id>/submit`,
GET `/zeroq/my/requirements`, GET `/zeroq/my/documents`, POST `/zeroq/my/documents` (multipart `doc_type`, `file`; PDF/JPEG/PNG/WebP up to `ZEROQ_MAX_UPLOAD_MB`),
POST `/zeroq/my/documents/<id>/link` (signed 5-minute download path), GET `/zeroq/my/progress`, GET `/zeroq/my/notifications`, POST `/zeroq/my/notifications/read`.
Public but signed: GET `/zeroq/documents/file?token=...` (410 when forged, expired or the file is gone).
School admin/principal/deputy (own school only): GET/POST `/zeroq/requirements`, PATCH `/zeroq/requirements/<id>`, GET `/zeroq/review/summary`,
GET `/zeroq/review/results[?status=needs_action|all|<status>]`, GET `/zeroq/review/results/<id>`, POST `/zeroq/review/results/<id>/action` (`start_review|request_info|verify|reject|fail`, `note`, `basis`),
GET `/zeroq/review/documents[?status=needs_action|all|<status>&q=]`, GET `/zeroq/review/documents/<id>`, POST `/zeroq/review/documents/<id>/action` (`approve|request_correction|reject|escalate|note`, `note`), POST `/zeroq/review/documents/<id>/link`.
Other schools' ids return 404. Uploads are limited to 10 per minute per student (429); oversized files return 413.
