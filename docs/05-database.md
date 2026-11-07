# PostgreSQL data dictionary

Persistent JSON payloads use JSONB. UUID-format identifiers are stored as varchar(36). Timestamps include a timezone. Python supplies ID and timestamp defaults. The migration files are the installation authority.

## users

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| name | VARCHAR(80) | No | - |
| email | VARCHAR(254) | No | Unique;  |
| password_hash | TEXT | No | - |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: PrimaryKeyConstraint, UniqueConstraint.

## projects

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| user_id | VARCHAR(36) | No | users.id |
| project_name | VARCHAR(120) | No | - |
| description | TEXT | No | - |
| programming_language | VARCHAR(30) | No | - |
| framework | VARCHAR(50) | No | - |
| application_type | VARCHAR(30) | No | - |
| project_status | VARCHAR(30) | No | - |
| revision | INTEGER | No | - |
| deleted | BOOLEAN | No | - |
| updated_at | TIMESTAMP WITH TIME ZONE | No | - |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_projects_user_id, CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint.

## audit_events

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| project_id | VARCHAR(36) | Yes | projects.id |
| user_id | VARCHAR(36) | Yes | users.id |
| event_type | VARCHAR(80) | No | - |
| event_data | JSONB | No | - |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_audit_events_project_id, ForeignKeyConstraint, ForeignKeyConstraint, PrimaryKeyConstraint.

## generated_files

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| file_name | VARCHAR(180) | No | - |
| file_path | VARCHAR(240) | No | - |
| file_content | TEXT | No | - |
| programming_language | VARCHAR(30) | No | - |
| version | INTEGER | No | - |
| content_hash | VARCHAR(64) | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_generated_files_project_id, CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, UniqueConstraint.

## project_documents

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| stale | BOOLEAN | No | - |
| document_type | VARCHAR(60) | No | - |
| document_content | JSONB | No | - |
| version | INTEGER | No | - |
| content_hash | VARCHAR(64) | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_project_documents_project_id, UniqueConstraint, CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint.

## project_requirements

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| requirement_type | VARCHAR(40) | No | - |
| requirement_content | JSONB | No | - |
| version | INTEGER | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_project_requirements_project_id, PrimaryKeyConstraint, CheckConstraint, UniqueConstraint, ForeignKeyConstraint.

## project_versions

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| version_number | INTEGER | No | - |
| change_summary | TEXT | No | - |
| manifest | JSONB | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_project_versions_project_id, ForeignKeyConstraint, UniqueConstraint, PrimaryKeyConstraint.

## workflow_runs

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| workflow_type | VARCHAR(40) | No | - |
| status | VARCHAR(40) | No | - |
| stage | INTEGER | No | - |
| context | JSONB | No | - |
| request | JSONB | No | - |
| source_hash | VARCHAR(64) | No | - |
| error | TEXT | Yes | - |
| lease_until | TIMESTAMP WITH TIME ZONE | Yes | - |
| updated_at | TIMESTAMP WITH TIME ZONE | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_workflow_runs_project_id, one_active_run_per_project, ix_workflow_runs_status, ForeignKeyConstraint, PrimaryKeyConstraint.

## agent_tasks

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| run_id | VARCHAR(36) | No | workflow_runs.id |
| agent_name | VARCHAR(60) | No | - |
| task_name | VARCHAR(100) | No | - |
| task_status | VARCHAR(30) | No | - |
| priority | INTEGER | No | - |
| input_data | JSONB | No | - |
| output_data | JSONB | No | - |
| error_message | TEXT | Yes | - |
| started_at | TIMESTAMP WITH TIME ZONE | Yes | - |
| completed_at | TIMESTAMP WITH TIME ZONE | Yes | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_agent_tasks_run_id, ix_agent_tasks_project_id, ForeignKeyConstraint, ForeignKeyConstraint, PrimaryKeyConstraint.

## approvals

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| run_id | VARCHAR(36) | Yes | workflow_runs.id |
| checkpoint | VARCHAR(40) | No | - |
| status | VARCHAR(30) | No | - |
| artifact_hash | VARCHAR(64) | No | - |
| base_revision | INTEGER | No | - |
| payload | JSONB | No | - |
| comment | TEXT | No | - |
| decided_by | VARCHAR(36) | Yes | users.id |
| decided_at | TIMESTAMP WITH TIME ZONE | Yes | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_approvals_status, ix_approvals_run_id, ix_approvals_project_id, PrimaryKeyConstraint, ForeignKeyConstraint, ForeignKeyConstraint, ForeignKeyConstraint.

## code_reviews

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| run_id | VARCHAR(36) | No | workflow_runs.id |
| file_id | VARCHAR(36) | Yes | generated_files.id |
| file_path | VARCHAR(240) | No | - |
| line_number | INTEGER | Yes | - |
| severity | VARCHAR(20) | No | - |
| issue_type | VARCHAR(50) | No | - |
| issue_description | TEXT | No | - |
| suggested_fix | TEXT | No | - |
| improved_code | TEXT | No | - |
| evidence_status | VARCHAR(40) | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_code_reviews_project_id, ix_code_reviews_run_id, CheckConstraint, ForeignKeyConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, ForeignKeyConstraint.

## test_results

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| run_id | VARCHAR(36) | Yes | workflow_runs.id |
| test_type | VARCHAR(40) | No | - |
| test_status | VARCHAR(40) | No | - |
| source_hash | VARCHAR(64) | No | - |
| recipe | VARCHAR(40) | No | - |
| total_tests | INTEGER | Yes | - |
| passed_tests | INTEGER | Yes | - |
| failed_tests | INTEGER | Yes | - |
| execution_output | TEXT | No | - |
| details | JSONB | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_test_results_run_id, ix_test_results_test_status, ix_test_results_project_id, ForeignKeyConstraint, PrimaryKeyConstraint, ForeignKeyConstraint.

## agent_executions

| Column | SQL type | Nullable | Constraint/reference |
| --- | --- | --- | --- |
| agent_task_id | VARCHAR(36) | No | agent_tasks.id |
| execution_status | VARCHAR(30) | No | - |
| execution_logs | JSONB | No | - |
| retry_count | INTEGER | No | - |
| execution_time | FLOAT | No | - |
| project_id | VARCHAR(36) | No | projects.id |
| id | VARCHAR(36) | No | Primary key;  |
| created_at | TIMESTAMP WITH TIME ZONE | No | - |

Indexes and constraints: ix_agent_executions_project_id, ix_agent_executions_agent_task_id, ForeignKeyConstraint, PrimaryKeyConstraint, ForeignKeyConstraint.

## Transaction rules

Only one active workflow may exist per project; PostgreSQL enforces a partial unique index. API writes lock the owned project before checking its revision. Approvals additionally lock the proposal and bind its artifact hash. Immutable file/document versions use composite uniqueness constraints. Cross-project operations first check ownership and return 404 for a resource the user does not own. This release uses service-level ownership checks rather than PostgreSQL row-level security.
