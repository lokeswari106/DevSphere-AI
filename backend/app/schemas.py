from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from app.diagram_syntax import normalize_er_diagram


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Register(Strict):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Login(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProjectInput(Strict):
    project_name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=20, max_length=12000)
    programming_language: Literal["Python", "JavaScript", "Java"] = "Python"
    framework: Literal[
        "FastAPI",
        "Node.js",
        "React + FastAPI",
        "React + Node.js",
        "Java standard library",
    ] = "FastAPI"
    application_type: Literal["web_application", "api", "library"] = "web_application"


class ProjectUpdate(Strict):
    project_name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=20, max_length=12000)
    expected_revision: int = Field(ge=1)


class Execute(Strict):
    workflow_type: Literal[
        "full",
        "review",
        "quick_review",
        "security",
        "requirements",
        "architecture",
        "database",
        "code",
        "tests",
        "documentation",
        "repair",
    ] = "full"
    instructions: str = Field(default="", max_length=8000)


class Decision(Strict):
    decision: Literal["approve", "reject", "regenerate"]
    artifact_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)
    comment: str = Field(default="", max_length=4000)


class FileChange(Strict):
    content: str = Field(max_length=100000)
    expected_revision: int = Field(ge=1)


class SourceFile(Strict):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=100000)


class ImportFiles(Strict):
    files: list[SourceFile] = Field(min_length=1, max_length=60)
    expected_revision: int = Field(ge=1)


class RequirementInput(Strict):
    content: str = Field(min_length=20, max_length=20000)
    expected_revision: int = Field(ge=1)


class TestRequest(Strict):
    recipe: Literal["python", "node", "java"]


class PlanTask(Strict):
    name: str
    agent: str
    depends_on: list[str]
    acceptance: str


class Plan(Strict):
    summary: str
    classification: str
    milestones: list[str]
    tasks: list[PlanTask]
    constraints: list[str]


class UserStory(Strict):
    role: str
    action: str
    benefit: str
    acceptance_criteria: list[str]


class SRS(Strict):
    summary: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    business_rules: list[str]
    user_stories: list[UserStory]
    edge_cases: list[str]
    complexity: str
    open_questions: list[str]
    assumptions: list[str]


class Diagram(Strict):
    title: str
    mermaid: str


class Architecture(Strict):
    summary: str
    style: Literal["modular_monolith", "monolith", "microservices", "event_driven"]
    components: list[str]
    patterns: list[str]
    tradeoffs: list[str]
    low_level_design: list[str]
    scalability: list[str]
    diagrams: list[Diagram]


class Entity(Strict):
    name: str
    fields: list[str]
    keys: list[str]
    indexes: list[str]


class DatabaseDesign(Strict):
    summary: str
    entities: list[Entity]
    migration_sql: str
    er_diagram: str
    openapi_json: str
    performance_notes: list[str]

    @field_validator("er_diagram")
    @classmethod
    def er_notation(cls, value):
        return normalize_er_diagram(value)


class CodeBundle(Strict):
    summary: str
    files: list[SourceFile] = Field(min_length=1, max_length=60)
    setup_instructions: list[str]
    limitations: list[str]


class Finding(Strict):
    file_path: str
    line_number: int | None
    severity: Literal["info", "low", "medium", "high", "critical"]
    issue_type: str
    description: str
    suggested_fix: str
    improved_code: str


class Review(Strict):
    summary: str
    findings: list[Finding]
    limitations: list[str]


class Delivery(Strict):
    summary: str = Field(max_length=600)
    readme_markdown: str = Field(max_length=2500)
    architecture_markdown: str = Field(max_length=2500)
    testing_markdown: str = Field(max_length=2500)
    deployment_markdown: str = Field(max_length=2500)
    final_report_markdown: str = Field(max_length=2500)
    limitations: list[str] = Field(max_length=8)


class ProposalEdit(Strict):
    artifact_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)
    payload: dict


class ApiField(Strict):
    name: str
    type: Literal["string", "integer", "number", "boolean", "object", "array"]
    required: bool
    description: str


class ApiEndpoint(Strict):
    path: str = Field(pattern=r"^/")
    method: Literal["get", "post", "put", "patch", "delete"]
    summary: str
    request_fields: list[ApiField]
    response_fields: list[ApiField]
    response_is_array: bool
    success_status: int = Field(ge=200, le=399)


class DatabaseDraft(Strict):
    summary: str
    entities: list[Entity]
    migration_sql: str
    er_diagram: str
    endpoints: list[ApiEndpoint] = Field(min_length=1, max_length=15)
    performance_notes: list[str]

    @field_validator("er_diagram")
    @classmethod
    def er_notation(cls, value):
        return normalize_er_diagram(value)
