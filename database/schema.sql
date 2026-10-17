-- ElimuPro PostgreSQL schema (generated from backend/app/models by export_schema.py)

CREATE TABLE schools (
	id SERIAL NOT NULL,
	name VARCHAR(200) NOT NULL,
	slug VARCHAR(120) NOT NULL,
	school_type VARCHAR(30),
	county VARCHAR(80),
	motto VARCHAR(255),
	address VARCHAR(255),
	phone VARCHAR(30),
	email VARCHAR(255),
	website VARCHAR(255),
	logo_url VARCHAR(500),
	primary_color VARCHAR(9),
	admission_prefix VARCHAR(10),
	admissions_open BOOLEAN NOT NULL,
	is_active BOOLEAN NOT NULL,
	is_demo BOOLEAN NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (slug)
);

CREATE TABLE academic_years (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	name VARCHAR(20) NOT NULL,
	is_current BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (school_id, name),
	FOREIGN KEY(school_id) REFERENCES schools (id)
);
CREATE INDEX ix_academic_years_school_id ON academic_years (school_id);

CREATE TABLE classes (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	name VARCHAR(60) NOT NULL,
	level_order INTEGER,
	PRIMARY KEY (id),
	UNIQUE (school_id, name),
	FOREIGN KEY(school_id) REFERENCES schools (id)
);
CREATE INDEX ix_classes_school_id ON classes (school_id);

CREATE TABLE grade_bands (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	min_mark NUMERIC(5, 2) NOT NULL,
	grade VARCHAR(10) NOT NULL,
	remark VARCHAR(80),
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id)
);
CREATE INDEX ix_grade_bands_school_id ON grade_bands (school_id);

CREATE TABLE subjects (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	code VARCHAR(20),
	PRIMARY KEY (id),
	UNIQUE (school_id, name),
	FOREIGN KEY(school_id) REFERENCES schools (id)
);
CREATE INDEX ix_subjects_school_id ON subjects (school_id);

CREATE TABLE users (
	id SERIAL NOT NULL,
	school_id INTEGER,
	email VARCHAR(255) NOT NULL,
	phone VARCHAR(20),
	password_hash VARCHAR(255) NOT NULL,
	first_name VARCHAR(80) NOT NULL,
	middle_name VARCHAR(80),
	last_name VARCHAR(80) NOT NULL,
	role VARCHAR(30) NOT NULL,
	is_active BOOLEAN NOT NULL,
	last_login TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	UNIQUE (email)
);
CREATE INDEX ix_users_role ON users (role);
CREATE INDEX ix_users_school_id ON users (school_id);

CREATE TABLE announcements (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	author_id INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	content TEXT NOT NULL,
	priority VARCHAR(10) NOT NULL,
	audience VARCHAR(20) NOT NULL,
	class_id INTEGER,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(author_id) REFERENCES users (id),
	FOREIGN KEY(class_id) REFERENCES classes (id)
);
CREATE INDEX ix_announcements_school_id ON announcements (school_id);

CREATE TABLE audit_logs (
	id SERIAL NOT NULL,
	school_id INTEGER,
	user_id INTEGER,
	action VARCHAR(80) NOT NULL,
	entity VARCHAR(60),
	entity_id INTEGER,
	details JSON,
	ip_address VARCHAR(45),
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_school_id ON audit_logs (school_id);

CREATE TABLE streams (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	class_id INTEGER NOT NULL,
	name VARCHAR(60) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (class_id, name),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(class_id) REFERENCES classes (id)
);
CREATE INDEX ix_streams_school_id ON streams (school_id);
CREATE INDEX ix_streams_class_id ON streams (class_id);

CREATE TABLE teacher_assignments (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	teacher_id INTEGER NOT NULL,
	class_id INTEGER NOT NULL,
	subject_id INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (teacher_id, class_id, subject_id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(teacher_id) REFERENCES users (id),
	FOREIGN KEY(class_id) REFERENCES classes (id),
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
);
CREATE INDEX ix_teacher_assignments_teacher_id ON teacher_assignments (teacher_id);
CREATE INDEX ix_teacher_assignments_class_id ON teacher_assignments (class_id);
CREATE INDEX ix_teacher_assignments_school_id ON teacher_assignments (school_id);

CREATE TABLE terms (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	academic_year_id INTEGER NOT NULL,
	name VARCHAR(40) NOT NULL,
	start_date DATE,
	end_date DATE,
	is_current BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(academic_year_id) REFERENCES academic_years (id)
);
CREATE INDEX ix_terms_school_id ON terms (school_id);

CREATE TABLE exams (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	term_id INTEGER NOT NULL,
	class_id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	max_score INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(term_id) REFERENCES terms (id),
	FOREIGN KEY(class_id) REFERENCES classes (id)
);
CREATE INDEX ix_exams_class_id ON exams (class_id);
CREATE INDEX ix_exams_school_id ON exams (school_id);

CREATE TABLE fee_structures (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	term_id INTEGER NOT NULL,
	class_id INTEGER,
	name VARCHAR(120) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(term_id) REFERENCES terms (id),
	FOREIGN KEY(class_id) REFERENCES classes (id)
);
CREATE INDEX ix_fee_structures_school_id ON fee_structures (school_id);

CREATE TABLE students (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	user_id INTEGER,
	admission_number VARCHAR(30) NOT NULL,
	first_name VARCHAR(80) NOT NULL,
	middle_name VARCHAR(80),
	last_name VARCHAR(80) NOT NULL,
	date_of_birth DATE,
	gender VARCHAR(10),
	nationality VARCHAR(60),
	county VARCHAR(80),
	previous_school VARCHAR(200),
	phone VARCHAR(20),
	email VARCHAR(255),
	class_id INTEGER,
	stream_id INTEGER,
	status VARCHAR(20) NOT NULL,
	admitted_on DATE,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (school_id, admission_number),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(class_id) REFERENCES classes (id),
	FOREIGN KEY(stream_id) REFERENCES streams (id)
);
CREATE INDEX ix_students_school_id ON students (school_id);
CREATE INDEX ix_students_status ON students (status);
CREATE INDEX ix_students_class_id ON students (class_id);

CREATE TABLE timetable_entries (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	class_id INTEGER NOT NULL,
	stream_id INTEGER,
	day_of_week INTEGER NOT NULL,
	start_time TIME WITHOUT TIME ZONE NOT NULL,
	end_time TIME WITHOUT TIME ZONE NOT NULL,
	subject_id INTEGER,
	title VARCHAR(100),
	teacher_name VARCHAR(120),
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(class_id) REFERENCES classes (id),
	FOREIGN KEY(stream_id) REFERENCES streams (id),
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
);
CREATE INDEX ix_timetable_entries_class_id ON timetable_entries (class_id);
CREATE INDEX ix_timetable_entries_school_id ON timetable_entries (school_id);

CREATE TABLE exam_results (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	exam_id INTEGER NOT NULL,
	student_id INTEGER NOT NULL,
	subject_id INTEGER NOT NULL,
	marks NUMERIC(5, 2) NOT NULL,
	remark VARCHAR(255),
	PRIMARY KEY (id),
	UNIQUE (exam_id, student_id, subject_id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(exam_id) REFERENCES exams (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	FOREIGN KEY(subject_id) REFERENCES subjects (id)
);
CREATE INDEX ix_exam_results_student_id ON exam_results (student_id);
CREATE INDEX ix_exam_results_school_id ON exam_results (school_id);

CREATE TABLE guardians (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	student_id INTEGER NOT NULL,
	user_id INTEGER,
	full_name VARCHAR(160) NOT NULL,
	relationship_type VARCHAR(40),
	phone VARCHAR(20),
	email VARCHAR(255),
	is_emergency_contact BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_guardians_student_id ON guardians (student_id);
CREATE INDEX ix_guardians_school_id ON guardians (school_id);

CREATE TABLE payments (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	student_id INTEGER NOT NULL,
	term_id INTEGER NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	method VARCHAR(20) NOT NULL,
	reference VARCHAR(60) NOT NULL,
	receipt_no VARCHAR(30) NOT NULL,
	status VARCHAR(20) NOT NULL,
	recorded_by INTEGER,
	paid_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (school_id, reference),
	UNIQUE (school_id, receipt_no),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	FOREIGN KEY(term_id) REFERENCES terms (id),
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);
CREATE INDEX ix_payments_student_id ON payments (student_id);
CREATE INDEX ix_payments_school_id ON payments (school_id);

CREATE TABLE student_applications (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	applicant_user_id INTEGER NOT NULL,
	student_id INTEGER,
	reference_no VARCHAR(30),
	status VARCHAR(20) NOT NULL,
	first_name VARCHAR(80),
	middle_name VARCHAR(80),
	last_name VARCHAR(80),
	date_of_birth DATE,
	gender VARCHAR(10),
	nationality VARCHAR(60),
	county VARCHAR(80),
	previous_school VARCHAR(200),
	applying_class_id INTEGER,
	guardian_name VARCHAR(160),
	guardian_relationship VARCHAR(40),
	guardian_phone VARCHAR(20),
	guardian_email VARCHAR(255),
	emergency_contact_name VARCHAR(160),
	emergency_contact_phone VARCHAR(20),
	review_note TEXT,
	reviewed_by INTEGER,
	reviewed_at TIMESTAMP WITHOUT TIME ZONE,
	submitted_at TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	UNIQUE (applicant_user_id),
	FOREIGN KEY(applicant_user_id) REFERENCES users (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	UNIQUE (reference_no),
	FOREIGN KEY(applying_class_id) REFERENCES classes (id),
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE INDEX ix_student_applications_status ON student_applications (status);
CREATE INDEX ix_student_applications_school_id ON student_applications (school_id);

CREATE TABLE student_fees (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	student_id INTEGER NOT NULL,
	term_id INTEGER NOT NULL,
	fee_structure_id INTEGER,
	description VARCHAR(120) NOT NULL,
	amount_due NUMERIC(12, 2) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	FOREIGN KEY(term_id) REFERENCES terms (id),
	FOREIGN KEY(fee_structure_id) REFERENCES fee_structures (id)
);
CREATE INDEX ix_student_fees_school_id ON student_fees (school_id);
CREATE INDEX ix_student_fees_student_id ON student_fees (student_id);

CREATE TABLE application_documents (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	application_id INTEGER NOT NULL,
	doc_type VARCHAR(60) NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	file_url VARCHAR(500) NOT NULL,
	uploaded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(application_id) REFERENCES student_applications (id)
);
CREATE INDEX ix_application_documents_application_id ON application_documents (application_id);
CREATE INDEX ix_application_documents_school_id ON application_documents (school_id);

CREATE TABLE zeroq_passes (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	application_id INTEGER NOT NULL,
	student_id INTEGER NOT NULL,
	reference VARCHAR(30) NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	expected_on DATE NOT NULL,
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITHOUT TIME ZONE,
	used_at TIMESTAMP WITHOUT TIME ZONE,
	completed_at TIMESTAMP WITHOUT TIME ZONE,
	issued_by INTEGER,
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(application_id) REFERENCES student_applications (id),
	FOREIGN KEY(student_id) REFERENCES students (id),
	UNIQUE (reference),
	UNIQUE (token_hash),
	FOREIGN KEY(issued_by) REFERENCES users (id)
);
CREATE INDEX ix_zeroq_passes_expires_at ON zeroq_passes (expires_at);
CREATE INDEX ix_zeroq_passes_application_id ON zeroq_passes (application_id);
CREATE INDEX ix_zeroq_passes_student_id ON zeroq_passes (student_id);
CREATE INDEX ix_zeroq_passes_school_id ON zeroq_passes (school_id);

CREATE TABLE zeroq_scans (
	id SERIAL NOT NULL,
	school_id INTEGER NOT NULL,
	pass_id INTEGER,
	scanned_by INTEGER NOT NULL,
	token_fingerprint VARCHAR(64) NOT NULL,
	outcome VARCHAR(30) NOT NULL,
	scanned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(school_id) REFERENCES schools (id),
	FOREIGN KEY(pass_id) REFERENCES zeroq_passes (id),
	FOREIGN KEY(scanned_by) REFERENCES users (id)
);
CREATE INDEX ix_zeroq_scans_scanned_at ON zeroq_scans (scanned_at);
CREATE INDEX ix_zeroq_scans_outcome ON zeroq_scans (outcome);
CREATE INDEX ix_zeroq_scans_school_id ON zeroq_scans (school_id);
CREATE INDEX ix_zeroq_scans_pass_id ON zeroq_scans (pass_id);
CREATE INDEX ix_zeroq_scans_scanned_by ON zeroq_scans (scanned_by);
