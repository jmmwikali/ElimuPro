# Database

PostgreSQL schema generated from `backend/app/models/` into `database/schema.sql` (23 tables). No attendance tables exist.

Use Flask-Migrate for database changes: run `flask --app run:app db upgrade` from `backend/` to apply committed revisions. Generate a new revision after model changes with `flask --app run:app db migrate -m "describe change"`, review it, then commit it. `python export_schema.py` refreshes the reference SQL; do not use it as a production migration mechanism.

| Group | Tables |
|---|---|
| Platform | `schools`, `users` (role column; `school_id` NULL only for super admin), `audit_logs` |
| Academic structure | `academic_years`, `terms`, `classes`, `streams`, `subjects`, `grade_bands` (school-configurable grading) |
| Learners | `students`, `guardians`, `student_applications`, `application_documents` |
| ZeroQ admissions | `zeroq_passes`, `zeroq_scans` |
| Component pricing | `price_components`, `price_tiers` |
| ZeroQ onboarding | `assessment_results`, `assessment_result_events`, `document_events`, `document_requirements`, `notifications`; `application_documents` extended with storage key, hash, status, version, verification JSON |
| Component billing | `invoices` (price snapshot, unique per school/component/period), `payment_attempts` (one per STK push, unique idempotency key and charge id) |
| Assessment | `exams`, `exam_results`, `timetable_entries` |
| Staff | `teacher_assignments` (teacher user x class x subject; unique per triple; drives every teacher permission) |
| Finance & comms | `fee_structures`, `student_fees`, `payments`, `announcements` |

Rules: every school-owned table has `school_id` (indexed). Uniqueness is per school: `(school_id, admission_number)`, `(school_id, name)` for classes and
subjects, `(school_id, reference)` and `(school_id, receipt_no)` for payments. One application per applicant user (`applicant_user_id` unique);
`student_applications.student_id` and `students.user_id` link an application, its account and the enrolled student record.
ZeroQ passes reference the existing application and student rows, store only a SHA-256 digest of the high-entropy QR token, and track expiry, revocation, first scan, and completion. Scan rows record a token fingerprint and outcome, not the raw token.
Not yet modelled: staff other than teachers, parents (`guardians.user_id` links a guardian row to a parent `users` account; a parent sees exactly the students whose guardian rows point at them), report cards, library, inventory, boarding, transport, notifications, messages,
student-subject links.
