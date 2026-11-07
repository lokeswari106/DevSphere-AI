import json, re
from openapi_spec_validator import validate
from app.agents.base import call
from app.schemas import DatabaseDraft, DatabaseDesign


def object_schema(fields):
    properties = {}
    for field in fields:
        prop = {"type": field["type"], "description": field["description"]}
        if field["type"] == "array":
            prop["items"] = {"type": "object"}
        properties[field["name"]] = prop
    result = {"type": "object", "properties": properties}
    required = [f["name"] for f in fields if f["required"]]
    if required:
        result["required"] = required
    return result


def compile_openapi(draft):
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Generated project API", "version": "1.0.0"},
        "paths": {},
    }
    for endpoint in draft["endpoints"]:
        path = endpoint["path"]
        method = endpoint["method"]
        if method in spec["paths"].get(path, {}):
            raise ValueError("Duplicate API operation: " + method + " " + path)
        response = object_schema(endpoint["response_fields"])
        if endpoint["response_is_array"]:
            response = {"type": "array", "items": response}
        op = {
            "summary": endpoint["summary"],
            "responses": {
                str(endpoint["success_status"]): {
                    "description": "Successful operation",
                    "content": {"application/json": {"schema": response}},
                },
                "422": {"description": "Invalid input"},
            },
        }
        if endpoint["success_status"] in [204, 304]:
            op["responses"][str(endpoint["success_status"])].pop("content")
        parameters = [
            {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
            for name in re.findall(r"\{([^}]+)\}", path)
        ]
        if parameters:
            op["parameters"] = parameters
        if endpoint["request_fields"]:
            op["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": object_schema(endpoint["request_fields"])
                    }
                },
            }
        spec["paths"].setdefault(path, {})[method] = op
    validate(spec)
    return spec


async def execute(context):
    draft, usage = await call(
        "You are the Database and API Design Agent. Design entities, keys, indexes, migration SQL TEXT for the database selected in the approved architecture, a valid Mermaid erDiagram, and a compact list of REST endpoints. Use at most six entities and ten endpoints for the approved teaching slice. Provide request/response field names and primitive types for each endpoint; use empty lists when no body is needed. The trusted compiler will create and validate OpenAPI from these structured endpoints, so do not emit a serialized OpenAPI string. Include essential validation and authorization considerations in performance_notes. Use simple Mermaid identifiers and types. ER attributes MUST use type then name: erDiagram\n User {\n UUID id PK\n string email\n }\nNever use id: UUID or other colon-separated fields inside an ER entity. Do not claim the migration ran. Keep descriptions concise.",
        context,
        DatabaseDraft,
    )
    draft = DatabaseDraft.model_validate(draft).model_dump()
    try:
        spec = compile_openapi(draft)
    except Exception as exc:
        exc.failed_artifact = draft
        raise
    result = {k: v for k, v in draft.items() if k != "endpoints"}
    result["openapi_json"] = json.dumps(spec, indent=2)
    result["performance_notes"] += [
        "OpenAPI is compiled from model-proposed endpoint fields. Nested array item schemas and authorization contracts need human refinement before client generation."
    ]
    return DatabaseDesign.model_validate(result).model_dump(), usage
