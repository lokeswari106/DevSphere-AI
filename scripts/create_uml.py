"""Rebuild editable diagrams for the implemented DevSphere architecture."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];d=root/'docs/diagrams';d.mkdir(parents=True,exist_ok=True)
diagrams={
'01-use-case':('Use case diagram','Shows developer actions and the boundaries of the AI provider and isolated runner.', '''left to right direction
actor Developer
actor "AI provider" as LLM
actor "Sandbox runner" as Runner
rectangle "DevSphere AI" {
usecase "Manage own projects" as P
usecase "Plan and design" as D
usecase "Approve / edit / regenerate" as A
usecase "Generate source" as C
usecase "Review and assess security" as R
usecase "Run approved tests" as T
usecase "Export delivery" as E
}
Developer --> P
Developer --> D
Developer --> A
Developer --> C
Developer --> R
Developer --> T
Developer --> E
D --> LLM
C --> LLM
R --> LLM
T --> Runner'''),
'02-class':('Class diagram','Core persisted entities and service responsibilities. The complete column dictionary is in the database schema.', '''class User { id; email; password_hash }
class Project { id; revision; project_status }
class Run { workflow_type; stage; status; lease_until }
class AgentTask { task_name; input_data; output_data }
class Approval { checkpoint; artifact_hash; base_revision; status }
class GeneratedFile { file_path; version; content_hash }
class TestResult { source_hash; test_status; execution_output }
class Orchestrator { +advance(run_id); +perform(run_id,stage) }
class ArtifactService { +propose(); +apply_files(); +invalidate() }
User "1" --> "0..*" Project : owns
Project "1" *-- "0..*" Run
Run "1" *-- "0..*" AgentTask
Project "1" *-- "0..*" Approval
Project "1" *-- "0..*" GeneratedFile
Project "1" *-- "0..*" TestResult
Orchestrator ..> Run
Orchestrator ..> ArtifactService
ArtifactService ..> Approval'''),
'03-object':('Object diagram','Illustrative snapshot of a workflow paused for architecture review; identifiers here are explanatory examples.', '''object "student : User" as U { email = student@example.com }
object "urlShortener : Project" as P { revision = 2 }
object "generation : Run" as R { stage = architecture\nstatus = awaiting_approval }
object "design : AgentTask" as T { status = completed }
object "reviewGate : Approval" as A { checkpoint = architecture\nstatus = pending\nbase_revision = 2 }
U --> P
P --> R
R --> T
R --> A'''),
'04-component':('Component diagram','One modular application, one relational database and one separate trusted runner. Agent modules are Python functions.', '''[React browser] as UI
package "FastAPI modular monolith" {
[Authentication and ownership] as Auth
[REST API] as API
[Orchestrator] as O
[Eight agent modules] as Agents
[Artifacts and exports] as Artifacts
}
database PostgreSQL as DB
[Ollama / OpenAI] as LLM
[Trusted runner process] as Runner
[Disposable test container] as Box
UI --> API : HTTPS / polling
API --> Auth
API --> O
API --> Artifacts
O --> Agents
Agents --> LLM : structured JSON
O --> DB
Artifacts --> DB
Auth --> DB
Runner --> DB : claim approved job
Runner --> Box : bounded execution'''),
'05-composite-structure':('Composite structure diagram','Internal collaboration of the orchestrator component; ports are logical interfaces rather than separate network services.', '''component "Orchestrator" {
portin "Workflow command" as In
portout "Provider adapter" as Out
[Stage dispatcher] as D
[Dependency validator] as V
[Context builder] as C
[Agent invocation] as I
[Result validator] as R
[Approval gate] as G
In --> D
D --> V
V --> C
C --> I
I --> Out
I --> R
R --> G
G --> D : after approval
}'''),
'06-deployment':('Deployment diagram','Local execution has a VM boundary for generated code. A free temporary tunnel exposes only the authenticated application.', '''node "Browser / evaluator" as B
cloud "Optional HTTPS tunnel" as T
node "Student computer" {
node "Trusted application processes" {
artifact "FastAPI + compiled React :8010" as App
artifact "Separate runner controller" as R
artifact "Ollama :11434" as O
}
database "PostgreSQL :55433" as DB
node "Dedicated Docker / Colima VM" {
node "Disposable sandbox container" as S
}
}
B --> App : localhost
B --> T : HTTPS
T --> App : local HTTP
App --> DB
App --> O
R --> DB
R --> S : no mounts / no network
note bottom of S
Read-only root; non-root user
512 MB; one CPU; time limit
No database or model credentials
end note'''),
'07-package':('Package diagram','Source dependencies follow the modular monolith layout. The API never imports the sandbox executor.', '''package "app.api" as API
package "app.security" as Sec
package "app.schemas / contracts" as Schemas
package "app.services.orchestration" as Orch
package "app.agents" as Agents
package "app.services.provider" as Provider
package "app.services.artifacts / exports" as Artifacts
package "app.models / db" as DB
package "scripts.run_sandbox_worker" as Runner
package "app.services.sandbox" as Sandbox
API --> Sec
API --> Schemas
API --> Orch
API --> Artifacts
Orch --> Agents
Agents --> Provider
Agents --> Schemas
Orch --> DB
Artifacts --> DB
Runner --> Sandbox
Runner --> DB'''),
'08-profile':('Profile diagram','Design vocabulary used in this project. Stereotypes describe responsibilities; enforcement is implemented in validation, transactions and runner constraints.', '''class Component <<metaclass>>
class Artifact <<metaclass>>
class "AI Agent" as Agent <<stereotype>> { outputSchema: string\nmaxAttempts: integer = 3 }
class "Approval Gate" as Gate <<stereotype>> { bindsRevision: boolean = true\nbindsHash: boolean = true }
class "Untrusted Source" as Source <<stereotype>> { executableOnlyInSandbox: boolean = true }
Agent ..> Component : extends
Gate ..> Component : extends
Source ..> Artifact : extends'''),
'09-activity':('Activity diagram','Full workflow includes explicit human gates and a conditional repair loop. Review-only workflows omit generation stages.', '''start
:Create project and requirement;
:Orchestrator generates plan;
:Review or edit plan;
:Requirements agent;
:Approve requirements;
:Architecture agent;
:Approve architecture;
:Database / API agent;
:Approve database and API;
:Code generation agent;
:Approve source changes;
fork
:Quality review agent;
fork again
:Security agent;
end fork
:Generate test files;
:Approve tests and execution;
:Run isolated tests;
if (Tests passed?) then (yes)
:Generate documentation;
else (no)
:Inspect actual failure;
if (Request repair?) then (yes)
:Start repair workflow with prior context;
:Reapprove changes and rerun;
else (no)
:Continue only with disclosed failures;
endif
:Generate documentation;
endif
:Review final delivery;
stop'''),
'10-state-machine':('State machine diagram','Persisted workflow status transitions, including a lease-expiry recovery path and cancellation.', '''[*] --> queued
queued --> running : dispatcher claims lease
running --> queued : stage completed
running --> awaiting_approval : proposal persisted
awaiting_approval --> queued : approve or regenerate
awaiting_approval --> testing : approve test execution
testing --> queued : tests passed
testing --> awaiting_approval : tests failed
running --> failed : retry budget exhausted
running --> queued : expired lease recovered
failed --> queued : explicit retry
awaiting_approval --> completed : delivery approved
queued --> cancelled : cancel
running --> cancelled : cancel
awaiting_approval --> cancelled : reject / cancel
testing --> cancelled : cancel
completed --> [*]
cancelled --> [*]'''),
'11-sequence':('Sequence diagram','Optimistic approval binds both artifact content and project revision, preventing a stale browser action from committing different work.', '''actor Developer as U
participant Browser as B
participant API
participant Orchestrator as O
database PostgreSQL as DB
participant "AI agent / provider" as AI
U -> B : start workflow
B -> API : POST execute
API -> DB : ownership + active-run constraint
API --> B : 202 run_id
O -> DB : claim queued run with lease
O -> AI : structured context and output schema
AI --> O : structured artifact
O -> DB : store task output and pending approval
B -> API : poll workflow
API --> B : artifact + hash + revision
U -> B : inspect / edit / approve
B -> API : POST decision(hash, revision)
API -> DB : lock owned project and proposal
alt matching hash and revision
API -> DB : commit version + enqueue next stage
API --> B : 200 approved
else stale proposal
API --> B : 409 conflict
end'''),
'12-communication':('Communication diagram','Numbered messages express collaboration around an approved test run. This uses object notation for UML communication links.', '''object "developer:User" as U
object "browser:Workspace" as B
object "api:ApprovalService" as API
object "db:SharedState" as DB
object "runner:TrustedController" as R
object "box:IsolatedProcess" as S
U --> B : 1. approve execution
B --> API : 1.1 decision(hash,revision)
API --> DB : 1.2 persist approved snapshot
R --> DB : 2. claim queued job
R --> S : 2.1 execute fixed recipe
S --> R : 2.2 exit code and logs
R --> DB : 2.3 persist actual result
B --> API : 3. poll tests
API --> DB : 3.1 read owned results
API --> B : 3.2 counts and source hash'''),
'13-interaction-overview':('Interaction overview diagram','High-level references to detailed interactions. Decisions route complete generation, review-only or repair without running every agent.', '''start
:ref - Authenticate and select owned project;
if (Workflow type?) then (full)
:ref - Plan, requirements and design approvals;
:ref - Source generation and approval;
elseif (review only?) then (yes)
:ref - Upload and approve source snapshot;
else (repair)
:ref - Read failure logs and prior artifacts;
:ref - Propose targeted changes;
endif
:ref - Parallel review and security interaction;
if (Tests requested?) then (yes)
:ref - Test approval and isolated execution;
endif
:ref - Documentation and delivery approval;
stop'''),
'14-timing':('Timing diagram','Illustrative ordering only; the horizontal units are logical ticks, not measured latency or a performance benchmark.', '''robust "Workflow" as W
robust "Approval" as A
robust "Runner" as R
@0
W is running
A is absent
R is idle
@10
W is awaiting_approval
A is pending
@20
A is approved
W is testing
R is running
@40
R is passed
W is queued
@50
W is running
@60
W is awaiting_approval
A is pending
@70
A is approved
W is completed
R is idle'''),
'15-database-er':('Database ER diagram','All thirteen PostgreSQL tables are included. Project ownership is resolved through users and projects for every API operation.', '''hide circle
entity users { *id : varchar(36) <<PK>>\n email : varchar(254) <<unique>>\n password_hash : text }
entity projects { *id <<PK>>\n user_id <<FK>>\n revision : integer }
entity project_requirements { *id <<PK>>\n project_id <<FK>>\n requirement_content : jsonb\n version : integer }
entity workflow_runs { *id <<PK>>\n project_id <<FK>>\n status : varchar\n stage : integer }
entity agent_tasks { *id <<PK>>\n project_id <<FK>>\n run_id <<FK>>\n input_data : jsonb\n output_data : jsonb }
entity agent_executions { *id <<PK>>\n project_id <<FK>>\n agent_task_id <<FK>>\n execution_logs : jsonb }
entity generated_files { *id <<PK>>\n project_id <<FK>>\n file_path : varchar\n version : integer }
entity code_reviews { *id <<PK>>\n project_id <<FK>>\n run_id <<FK>>\n file_id <<FK>> }
entity test_results { *id <<PK>>\n project_id <<FK>>\n run_id <<FK>>\n source_hash : varchar }
entity project_documents { *id <<PK>>\n project_id <<FK>>\n version : integer\n stale : boolean }
entity project_versions { *id <<PK>>\n project_id <<FK>>\n version_number : integer }
entity approvals { *id <<PK>>\n project_id <<FK>>\n run_id <<FK>>\n decided_by <<FK>> }
entity audit_events { *id <<PK>>\n project_id <<FK>>\n user_id <<FK>> }
users ||--o{ projects
projects ||--o{ project_requirements
projects ||--o{ workflow_runs
projects ||--o{ agent_tasks
projects ||--o{ agent_executions
projects ||--o{ generated_files
projects ||--o{ code_reviews
projects ||--o{ test_results
projects ||--o{ project_documents
projects ||--o{ project_versions
projects ||--o{ approvals
projects ||--o{ audit_events
workflow_runs ||--o{ agent_tasks
agent_tasks ||--o{ agent_executions
generated_files |o--o{ code_reviews
workflow_runs ||--o{ code_reviews
workflow_runs |o--o{ test_results
workflow_runs |o--o{ approvals
users |o--o{ approvals
users |o--o{ audit_events''')
}
header='@startuml\nskinparam dpi 180\nskinparam backgroundColor white\nskinparam defaultFontName SansSerif\nskinparam defaultFontSize 14\nskinparam shadowing false\nskinparam ArrowColor #255F54\nskinparam roundcorner 8\n'
import json
for key,(title,explanation,source) in diagrams.items():
    # PlantUML class/object/entity bodies need physical newlines, not compact semicolons.
    source=source.replace('; ', '\n').replace(' { ', ' {\n ').replace(' }','\n}')
    (d/(key+'.puml')).write_text(header+'title '+title+'\n'+source+'\n@enduml\n')
(d/'index.json').write_text(json.dumps([{'file':key,'title':v[0],'explanation':v[1]} for key,v in diagrams.items()],indent=2))
text='# UML and workflow handbook\n\nThe diagrams describe the implemented DevSphere application. Each diagram has editable PlantUML source, PNG and SVG versions. The object and timing diagrams are explanatory examples, not fabricated runtime evidence.\n\n'
for key,(title,explanation,source) in diagrams.items():
    text+=f'## {title}\n\n{explanation}\n\n![{title}](diagrams/{key}.png)\n\n[Editable source](diagrams/{key}.puml) · [Vector image](diagrams/{key}.svg)\n\n'
text+='## Rebuild\n\nInstall Java and PlantUML, then run `python scripts/create_uml.py`, `plantuml -tpng docs/diagrams/*.puml` and `plantuml -tsvg docs/diagrams/*.puml`. Runtime project diagrams use Mermaid in the browser; PlantUML is only a documentation build tool.\n\nReference: [PlantUML documentation](https://plantuml.com/).\n'
(root/'docs/03-uml-handbook.md').write_text(text)
