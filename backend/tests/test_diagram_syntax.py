from app.diagram_syntax import normalize_er_diagram
from app.schemas import DatabaseDraft, DatabaseDesign


def test_er_notation_is_repaired_without_changing_relationships():
    source = 'erDiagram\n User ||--o{ Order : "has"\n User {\n id: UUID PK\n email: string "Contact"\n amount: decimal(10,2)\n }'
    fixed = normalize_er_diagram(source)
    assert 'User ||--o{ Order : "has"' in fixed
    assert 'UUID id PK' in fixed
    assert 'string email "Contact"' in fixed
    assert 'decimal(10,2) amount' in fixed
    assert normalize_er_diagram(fixed) == fixed
    assert normalize_er_diagram('classDiagram\nclass User {\n+id: UUID\n}') == 'classDiagram\nclass User {\n+id: UUID\n}'


def test_both_generated_and_edited_database_contracts_normalize_er_fields():
    shared = dict(summary='Design', entities=[], migration_sql='', performance_notes=[], er_diagram='```mermaid\nerDiagram\nUser {\nid: UUID\n}\n```')
    endpoint = dict(path='/users', method='get', summary='List users', request_fields=[], response_fields=[], response_is_array=True, success_status=200)
    draft = DatabaseDraft(**shared, endpoints=[endpoint])
    approved = DatabaseDesign(**shared, openapi_json='{}')
    assert draft.er_diagram == approved.er_diagram == 'erDiagram\nUser {\nUUID id\n}'
