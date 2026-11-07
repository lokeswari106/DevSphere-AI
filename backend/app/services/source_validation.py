"""Parse generated Python as data; never import or execute it on the host."""

import ast
from app.services.artifacts import validate_files


def validate_generated_bundle(bundle, *, tests_only=False):
    validate_files(bundle["files"])
    for source in bundle["files"]:
        if tests_only and not source["path"].startswith("tests/"):
            raise ValueError("Test agent must write inside tests/")
        if not source["path"].endswith(".py"):
            continue
        try:
            tree = ast.parse(source["content"], filename=source["path"])
            if tests_only and any(
                isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_")
                for node in ast.walk(tree)
            ):
                raise ValueError("Use synchronous pytest tests with TestClient; this sandbox has no async pytest plugin")
        except (SyntaxError, ValueError) as exc:
            # The orchestrator includes this exact draft in the bounded repair retry.
            exc.failed_artifact = bundle
            raise
