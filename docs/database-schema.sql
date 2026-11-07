-- Generated from SQLAlchemy metadata. Use Alembic migrations for installation.


CREATE TABLE users (
	name VARCHAR(80) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash TEXT NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
)

;



CREATE TABLE projects (
	user_id VARCHAR(36) NOT NULL,
	project_name VARCHAR(120) NOT NULL,
	description TEXT NOT NULL,
	programming_language VARCHAR(30) NOT NULL,
	framework VARCHAR(50) NOT NULL,
	application_type VARCHAR(30) NOT NULL,
	project_status VARCHAR(30) NOT NULL,
	revision INTEGER NOT NULL,
	deleted BOOLEAN NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CHECK (revision > 0),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_projects_user_id ON projects (user_id);


CREATE TABLE audit_events (
	project_id VARCHAR(36),
	user_id VARCHAR(36),
	event_type VARCHAR(80) NOT NULL,
	event_data JSONB NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_audit_events_project_id ON audit_events (project_id);


CREATE TABLE generated_files (
	file_name VARCHAR(180) NOT NULL,
	file_path VARCHAR(240) NOT NULL,
	file_content TEXT NOT NULL,
	programming_language VARCHAR(30) NOT NULL,
	version INTEGER NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (project_id, file_path, version),
	CHECK (version > 0),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_generated_files_project_id ON generated_files (project_id);


CREATE TABLE project_documents (
	stale BOOLEAN DEFAULT 'false' NOT NULL,
	document_type VARCHAR(60) NOT NULL,
	document_content JSONB NOT NULL,
	version INTEGER NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (project_id, document_type, version),
	CHECK (version > 0),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_project_documents_project_id ON project_documents (project_id);


CREATE TABLE project_requirements (
	requirement_type VARCHAR(40) NOT NULL,
	requirement_content JSONB NOT NULL,
	version INTEGER NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (project_id, requirement_type, version),
	CHECK (version > 0),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_project_requirements_project_id ON project_requirements (project_id);


CREATE TABLE project_versions (
	version_number INTEGER NOT NULL,
	change_summary TEXT NOT NULL,
	manifest JSONB NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (project_id, version_number),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_project_versions_project_id ON project_versions (project_id);


CREATE TABLE workflow_runs (
	workflow_type VARCHAR(40) NOT NULL,
	status VARCHAR(40) NOT NULL,
	stage INTEGER NOT NULL,
	context JSONB NOT NULL,
	request JSONB NOT NULL,
	source_hash VARCHAR(64) NOT NULL,
	error TEXT,
	lease_until TIMESTAMP WITH TIME ZONE,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_workflow_runs_project_id ON workflow_runs (project_id);
CREATE UNIQUE INDEX one_active_run_per_project ON workflow_runs (project_id) WHERE status IN ('queued', 'running', 'awaiting_approval', 'testing');
CREATE INDEX ix_workflow_runs_status ON workflow_runs (status);


CREATE TABLE agent_tasks (
	run_id VARCHAR(36) NOT NULL,
	agent_name VARCHAR(60) NOT NULL,
	task_name VARCHAR(100) NOT NULL,
	task_status VARCHAR(30) NOT NULL,
	priority INTEGER NOT NULL,
	input_data JSONB NOT NULL,
	output_data JSONB NOT NULL,
	error_message TEXT,
	started_at TIMESTAMP WITH TIME ZONE,
	completed_at TIMESTAMP WITH TIME ZONE,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id) REFERENCES workflow_runs (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_agent_tasks_run_id ON agent_tasks (run_id);
CREATE INDEX ix_agent_tasks_project_id ON agent_tasks (project_id);


CREATE TABLE approvals (
	run_id VARCHAR(36),
	checkpoint VARCHAR(40) NOT NULL,
	status VARCHAR(30) NOT NULL,
	artifact_hash VARCHAR(64) NOT NULL,
	base_revision INTEGER NOT NULL,
	payload JSONB NOT NULL,
	comment TEXT NOT NULL,
	decided_by VARCHAR(36),
	decided_at TIMESTAMP WITH TIME ZONE,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id) REFERENCES workflow_runs (id),
	FOREIGN KEY(decided_by) REFERENCES users (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_approvals_status ON approvals (status);
CREATE INDEX ix_approvals_run_id ON approvals (run_id);
CREATE INDEX ix_approvals_project_id ON approvals (project_id);


CREATE TABLE code_reviews (
	run_id VARCHAR(36) NOT NULL,
	file_id VARCHAR(36),
	file_path VARCHAR(240) NOT NULL,
	line_number INTEGER,
	severity VARCHAR(20) NOT NULL,
	issue_type VARCHAR(50) NOT NULL,
	issue_description TEXT NOT NULL,
	suggested_fix TEXT NOT NULL,
	improved_code TEXT NOT NULL,
	evidence_status VARCHAR(40) NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CHECK (severity IN ('info','low','medium','high','critical')),
	FOREIGN KEY(run_id) REFERENCES workflow_runs (id),
	FOREIGN KEY(file_id) REFERENCES generated_files (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_code_reviews_project_id ON code_reviews (project_id);
CREATE INDEX ix_code_reviews_run_id ON code_reviews (run_id);


CREATE TABLE test_results (
	run_id VARCHAR(36),
	test_type VARCHAR(40) NOT NULL,
	test_status VARCHAR(40) NOT NULL,
	source_hash VARCHAR(64) NOT NULL,
	recipe VARCHAR(40) NOT NULL,
	total_tests INTEGER,
	passed_tests INTEGER,
	failed_tests INTEGER,
	execution_output TEXT NOT NULL,
	details JSONB NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id) REFERENCES workflow_runs (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_test_results_run_id ON test_results (run_id);
CREATE INDEX ix_test_results_test_status ON test_results (test_status);
CREATE INDEX ix_test_results_project_id ON test_results (project_id);


CREATE TABLE agent_executions (
	agent_task_id VARCHAR(36) NOT NULL,
	execution_status VARCHAR(30) NOT NULL,
	execution_logs JSONB NOT NULL,
	retry_count INTEGER NOT NULL,
	execution_time FLOAT NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(agent_task_id) REFERENCES agent_tasks (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
)

;
CREATE INDEX ix_agent_executions_project_id ON agent_executions (project_id);
CREATE INDEX ix_agent_executions_agent_task_id ON agent_executions (agent_task_id);
