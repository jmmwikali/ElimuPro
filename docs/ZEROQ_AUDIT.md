# ZeroQ audit

Audit of ZeroQ against the 18-part requirements brief. Every status is backed by evidence from this repository.
Statuses: **PASS** implemented and tested. **PARTIAL** implemented but incomplete. **FAIL** broken. **MISSING** not built.
**BLOCKED** needs something that is not available (credential, authorisation, third-party service). **NOT TESTED**.

"Before" is the state at the start of this work; "Now" is after it.

## 1. Overall readiness

ZeroQ before this work was a **post-admission QR pass and arrival check-in** for students already enrolled by their school.
It was solid at that job (tests below) and did nothing else the brief describes: no results, no document upload,
no review workflow, no eligibility or placement, no transfers, no stores.

This work adds the first two priorities from the brief: **KJSEA results submission with a verification workflow**, and
**admission document upload with automated file checks, human review, progress tracking and notifications**. They are
real, tested and honest about their limits. Everything that needs an external data source, an OCR service, a 3D or
store ecosystem, or a decision about tenancy is still missing and is listed with the exact blocker in section 6.

ZeroQ is **not** ready for real students and schools as described in the brief. It is ready for a pilot of: results
entry checked by school staff, document collection and human review, and QR check-in.

## 2. Requirement by requirement

### Part 1: Student registration and KJSEA results
| Requirement | Status | Evidence |
| --- | --- | --- |
| Account creation / secure sign-in | PASS | `routes/auth.py` register creates account and draft application; JWT login. Existing tests. |
| Enter student details | PASS | Application form (`routes/admissions.py`). |
| Enter candidate / assessment number | PASS (new) | `assessment_results.candidate_number`; format checked (4 to 30 letters, numbers, `/`, `-`). The official format is not assumed. |
| Enter results manually | PASS (new) | `PUT /zeroq/my/results`; `test_results_draft_then_submit_with_honest_status_wording`, 10 validation cases. |
| Upload results document | PASS (new) | Built-in document type `kjsea_results` (`test_kjsea_results_slip_can_be_uploaded_without_school_configuration`). |
| OCR / document reading of that upload | BLOCKED | No OCR service is configured. Needs a provider decision and credentials (see section 6). |
| Review extracted information, correct errors | BLOCKED | Depends on OCR. Students currently type results and a reviewer compares them with the upload. |
| Clear status (received / verified / needs review) | PASS (new) | Eight statuses with student-facing wording; "Verified by school" never claims official verification. |
| Structure and consistency validation | PARTIAL | Duplicate subjects, empty rows, length, year range, candidate format, and the same candidate number submitted by two students (flagged to reviewer). The official grading scale is not loaded, so result values are not validated against it. |
| Integration with an official results source | BLOCKED | No authorised API is available or assumed. Transparent fallback built: student entry plus reviewer verification. |
| Required statuses and status history | PASS (new) | `assessment_results.status`, append-only `assessment_result_events`. |

### Part 2: Eligibility and school discovery
| Requirement | Status | Evidence |
| --- | --- | --- |
| Eligibility engine, school recommendations, profiles, comparison | MISSING | No eligibility rules, school directory or profile data exist. `schools` holds name, county, contact fields only. |
| Official placement and policy rules | BLOCKED | Needs the official rules and data under authorisation. Must not be invented. |
| Architecture for cross-school discovery | BLOCKED (decision) | Every user and record belongs to one school; a student picks their school at signup. Discovery before placement needs platform-level candidate accounts and a school directory. This is a design decision for you. |

### Part 3: Official placement
MISSING and BLOCKED. No placement data source, no placement model. No scraping of restricted systems was attempted.
A student-entered "school I was placed in" flow with independent validation is not built.

### Part 4: School change and transfer
MISSING. No transfer or change-of-placement model, workflow, or approvals. (Pricing exists for "ZeroQ Transfers" as a
product, but nothing implements it.)

### Part 5: School document download centre
| Requirement | Status | Evidence |
| --- | --- | --- |
| Per-school downloadable official documents (letters, forms, fees, rules) | MISSING | Schools cannot publish documents; none are invented. |
| Student can download their own uploaded copy | PASS (new) | Signed, time-limited link; `test_signed_download_link_serves_the_file_once_authorised`. |
| "Print, sign by hand, scan, upload" guidance | PASS (new) | Shown on the student Documents card. |

### Part 6: Upload and automated verification
| Check | Status | Evidence / limit |
| --- | --- | --- |
| Upload PDF and images | PASS | `test_good_pdf_passes_checks...`, `test_images_good_and_low_resolution`. |
| Correct file type | PASS | Detected from file bytes, not the name (`test_unsupported_files_are_refused_and_not_stored`). |
| Damaged / corrupt / password-protected | PASS | `test_corrupt_pdf_asks_for_a_corrected_copy`, `test_password_protected_pdf_is_flagged`, `test_fake_image_with_png_header_is_unreadable`. |
| Readability | PARTIAL | Photos under 700 px on the short side are flagged. This is a rough heuristic, labelled as such. |
| Duplicate file used by another student | PASS | `test_same_file_for_another_student_goes_to_a_human`. |
| Basic metadata inspection | PARTIAL | Producer and creator shown as information only; the result says metadata proves nothing. |
| Correct document type, required pages, required fields | BLOCKED | Needs text extraction. |
| Names, dates, reference numbers consistent across documents | BLOCKED | Needs text extraction. |
| Signatures, stamps, handwriting vs typed | BLOCKED | No detection configured. Never claimed. |
| Authenticity, template comparison, official reference validation | BLOCKED | Needs reference data and authorisation. Automated checks cannot prove authenticity. |
| Structured result with reasons and next action | PASS | `application_documents.verification` JSON: checks run, checks **not performed** (listed every time), reasons, recommended action, human-review flag. No invented scores or fraud probabilities (asserted in a test). |
| Statuses | PASS | uploaded, processing, passed automated checks, human review required, correction needed, rejected, approved. Passing never equals approval. |

### Part 7: Human review and admin dashboard
| Requirement | Status | Evidence |
| --- | --- | --- |
| Review dashboard, prioritised queue | PASS (new) | `/admin/zeroq-review`; `test_queue_puts_what_needs_a_human_first`; browser run. |
| Flag details (student, type, reason, extracted info, rules, history, notes, recommended action) | PARTIAL | All shown except "extracted information" (needs OCR) and per-document "applicable rules" (none configured). |
| Approve, request correction, reject with reason, escalate, add note | PASS | `test_reviewer_decisions_are_recorded_and_the_student_is_told`, `test_correction_loop`. |
| Previous submissions and review history | PASS | Versions kept (`test_reupload_creates_a_new_version...`); event history with reviewer names. |
| Every action logged | PASS | `audit_logs` plus `document_events`; exact audit actions asserted. |
| School isolation | PASS | `test_documents_are_isolated_between_students_and_schools`, `test_results_are_private_to_the_student_and_their_school`. |
| Dedicated "document reviewer" role | MISSING | Only school admin, principal and deputy can review. Adding a role touches every role check; not done. |
| Escalation target | PARTIAL | Escalation flags the document prominently; there is no separate escalation owner. |

### Part 8: Verification tracking
| Requirement | Status | Evidence |
| --- | --- | --- |
| Student sees submission date, stage, documents received/missing, checks completed, awaiting review, outstanding issues, latest update, next action | PASS (new) | `GET /zeroq/my/progress`; `test_progress_tells_the_student_what_to_do_next`. |
| Relevant deadline | MISSING | No deadline setting exists; the page says so instead of inventing one. |
| Admin-configurable processing times and escalation rules | MISSING | |
| Three weeks is an estimate, not a delay | PASS | No delay exists anywhere. |
| Notifications: received, processed, correction, reviewer request, decision | PASS (in-app) | `test_notifications_list_and_mark_read`. |
| Email / SMS notifications | BLOCKED | No delivery provider is configured in the project. |

### Part 9: 3D, drone and school media
MISSING. No school media model, storage, viewer or placeholder. Nothing is fabricated. Needs a decision on tours
(for example a third-party tour embed) and school-supplied media.

### Part 10: Partner stores and shopping
MISSING. No stores, products, stock, orders or fulfilment. The existing Cyzora billing is for schools paying ElimuNova
and could be reused for student purchases later, but no shopping model exists.

### Part 11: QR admission credential and card
| Requirement | Status | Evidence |
| --- | --- | --- |
| Unique credential, secure student association, school id, status, issue date, expiry, revocation | PASS | `zeroq_passes`; token hashed with SHA-256; 256-bit random token. |
| Protected verification endpoint | PASS | `POST /zeroq/scan` (school staff only, school-bound). |
| No sensitive data inside the QR | PASS | Opaque token; `test_student_pass_is_opaque_and_scan_is_one_time`. |
| Issued only after requirements are met | PARTIAL | Requires the school to have approved and enrolled the application (a human decision). It does **not** check that results are verified or documents approved. Gating on those is a policy choice for you. |
| Valid / expired / revoked / used states shown to staff | PASS | Existing tests (4 passing). |
| Student views the card on screen | PASS | `/student/zeroq`. |
| Print-ready PDF, wallet size 85.6 x 54 mm, branding | MISSING | A print stylesheet exists but there is no print or download button on the ZeroQ page and no card layout. The QR is shown once at issue (the server keeps only a hash), so a reload needs a new pass. |
| QR does not unlock records | PASS | Scan returns only name, admission number, class, status. |

### Part 12: Reporting and supply collection
Reporting check-in and completion: PASS (existing). Supply collection workflow with order QR codes: MISSING.

### Part 13: School administration and onboarding
| Requirement | Status | Evidence |
| --- | --- | --- |
| School profile, contact, website | PARTIAL | `PUT /schools/me` edits name, motto, address, phone, email, website, colour. |
| Admission documents and requirements | PASS (new) | `document_requirements`; CRUD tested. |
| Eligibility rules, supply lists, stores, media, 3D, review rules, transfers | MISSING | |
| Verified school profile before showing as official | MISSING | |
| Roles: ZeroQ platform admin, school admin, reviewers, students, parents, stores, reporting staff | PARTIAL | Platform admin, school admin and student exist. Reviewers share the admin roles; parents have no ZeroQ access; no store or reporting-staff roles. |

### Part 14: Security, privacy and data protection
| Safeguard | Status | Evidence |
| --- | --- | --- |
| Secure authentication, RBAC, server-side authorisation | PASS | `roles_required`, school-scoped queries; role and school come from the database, never the token or request. |
| Private storage, no public bucket | PASS (with a deployment caveat) | Files go to a private folder with random names and mode 0600, outside any static route (`test_file_is_stored_privately_with_a_random_name`). Local disk is lost on most hosts unless a persistent volume is mounted (compose mounts one). For production, move to private object storage. |
| Signed, time-limited download links | PASS | 5-minute links; forged, expired and missing-file cases tested. |
| File type and size validation | PASS | Type from bytes, 10 MB limit, 413 for oversized requests. |
| Malware scanning | BLOCKED | No scanner configured (for example ClamAV). Uploaded files are stored but never executed or served inline. |
| Rate limiting | PARTIAL | Uploads (10 a minute per student) and Apex AI. Login and other endpoints have none (the README already says so). In-process, per worker. |
| Audit logs | PASS | Uploads, links, downloads, reviews, requirement changes, results transitions. |
| Retention and deletion policy | MISSING | |
| Consent and guardian workflow for minors | MISSING | Students are minors; this needs a designed flow. |
| Kenyan data protection compliance | NOT ASSESSED | Needs review by qualified counsel (for example registration and lawful basis). Nothing here claims compliance. |
| Row Level Security | N/A | The project does not use Supabase; isolation is application-level (`school_id` on every query) and tested. Database-level RLS needs its own design. |
| AI analysis leaking data | PASS | No document is sent to any AI or third party. |

### Part 15: Admin analytics
PARTIAL. `GET /zeroq/review/summary` (documents by status, corrections outstanding, results to verify) and the existing
dashboard (applicants, arrivals, scans) exist. Participating schools, stores, orders, transfers and integration errors
are MISSING. Document requirements are stored in the database; processing targets and verification rules are not.

### Part 16: Database, backend and integration audit
| Entity | Status |
| --- | --- |
| Student profiles, guardians | exists (`students`, `guardians`) |
| Assessment results, result verification | **added** (`assessment_results`, `assessment_result_events`) |
| School profiles | exists, minimal |
| Eligibility rules, official placements, transfer requests | MISSING |
| Admission documents and versions | reused `application_documents` (extended with storage, status, version, verification) |
| Verification results, review decisions | **added** (`verification` JSON, `document_events`) |
| School requirements | **added** (`document_requirements`) |
| School media and 3D assets | MISSING |
| QR credentials | exists (`zeroq_passes`, `zeroq_scans`) |
| Partner stores, products, orders, items, collections | MISSING |
| Notifications | **added** (`notifications`) |
| Audit logs | exists (`audit_logs`) |

No duplicate tables were created. The migration (`e8a2c6d41f93`) upgrades, downgrades and upgrades cleanly on SQLite
with no schema drift. It has **not** been run against PostgreSQL (NOT TESTED); constraints are explicitly named so it
should behave the same.

## 3. Test scenarios A to R (actual results)

| Test | Result | Notes |
| --- | --- | --- |
| A Results submission | PARTIAL | Manual entry submitted, saved, status correct (PASS). Upload and OCR extraction: BLOCKED. |
| B Eligibility | MISSING | |
| C Official placement | MISSING / BLOCKED | |
| D School discovery | MISSING | |
| E Document download | PARTIAL | Student downloads their own copy (PASS). School document centre missing. |
| F Upload and verification entry | PASS | Includes handwritten-then-scanned files as PDF or image. |
| G Automated validation | PARTIAL | Reports exactly the checks run and the ones not run. |
| H Suspicious document | PARTIAL | Corrupt, protected, low-resolution, duplicate flagged with reasons. Inconsistent names or missing fields cannot be detected without OCR. |
| I Human review | PASS | API tests plus a real browser run (school lists requirements, student uploads, reviewer approves and verifies, student sees the outcome). |
| J Corrections | PASS | Notification, new version, progress updates. |
| K Transfer | MISSING | |
| L 3D view | MISSING | |
| M Store purchase | MISSING | |
| N QR card | PARTIAL | QR pass works (PASS); print-ready wallet-size PDF missing. |
| O QR revocation | PASS | Student and admin revocation; existing `test_pass_revoke_expiry_and_school_binding`. |
| P Student access control | PASS | |
| Q School isolation | PASS | Results, documents, links, requirements, summaries. |
| R Mobile | PARTIAL | New pages checked at 390 px: no horizontal overflow, uploads and forms usable. The camera scanner was not re-tested on a device (NOT TESTED). |

Automated suite: 226 tests passing in total, of which 54 are new for this module. I also deliberately broke five protections (another student's
document link, file-type check, link expiry, the verification-basis requirement, school scoping) and confirmed a test fails each time.

## 4. What exists but is simulated or mock

Nothing. No mock data is presented as a real integration. The demo seed contains demo schools and students only.

## 5. Integrations genuinely connected

None of the ZeroQ-specific ones. Existing optional integrations: Gemini (Apex AI) and Cyzora (billing) need credentials and have not been run against the live services.

## 6. Blockers and what is needed

| Needed | Why |
| --- | --- |
| OCR / document AI provider and credentials (for example a cloud document service or a self-hosted OCR) | Reading results slips and forms, field checks, name and date consistency |
| An authorised results or placement data source, and its rules | Official verification, eligibility, placement. Confirm with the education authorities; none is assumed to exist |
| Decision on tenancy for pre-placement students | Discovery across schools |
| Persistent private object storage (for example S3-compatible) | Production file storage; local disk is a pilot setup |
| Malware scanning service | Safe handling of uploads |
| Email or SMS provider | Notifications outside the app |
| Counsel review and a guardian-consent design | Student data protection |
| Content and media from schools; a 3D tour approach | Profiles and virtual tours |
| Partner store agreements and a fulfilment design | Shopping and collection |

## 7. Recommended next steps, in order

1. Decide the tenancy question and the policy for gating the QR pass on verified results and approved documents.
2. Pick an OCR provider and add it behind the existing check pipeline (`services/zeroq_documents.run_checks`): the
   "not performed" list shrinks as checks are added.
3. Print-ready wallet-size QR card (PDF) and a download button.
4. School document centre and school profile content.
5. Email or SMS delivery for the existing in-app notifications.
6. Private object storage and malware scanning before real student documents are accepted.
7. Eligibility and placement only once an authorised data source and rules are confirmed.
8. Transfers, then partner stores.
