import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("launcher",Path(__file__).resolve().parents[2]/"devsphere.py")
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_launcher_preserves_credentials_and_updates_ports(tmp_path):
    path=tmp_path/".env.localhost"
    first=launcher.prepare_config(path,"personal-local")
    second=launcher.prepare_config(path,"personal-local",port=8019,database_port=55439)
    assert second["JWT_SECRET"]==first["JWT_SECRET"]
    assert second["POSTGRES_PASSWORD"]==first["POSTGRES_PASSWORD"]
    assert len(second["JWT_SECRET"])>=32
    assert second["APP_ORIGIN"]=="http://localhost:8019"
    assert second["DATABASE_PORT"]=="55439"
    assert second["REGISTRATION_ENABLED"]=="true"


def test_launcher_uses_explicit_context_config_and_project(tmp_path):
    config=tmp_path/"folder with spaces"/".env.localhost"
    command=launcher.compose_command("personal-context",config,"devsphere-local")
    assert command[:4]==["docker","--context","personal-context","compose"]
    assert command[command.index("--env-file")+1]==str(config)
    assert command[command.index("--project-name")+1]=="devsphere-local"


def test_launcher_supports_external_model_without_changing_source_env(tmp_path):
    cfg=launcher.prepare_config(tmp_path/".env.localhost","personal",model="qwen3:4b",ollama_url="http://host.docker.internal:11434")
    assert cfg["OLLAMA_MODEL"]=="qwen3:4b"
    assert cfg["OLLAMA_BASE_URL"]=="http://host.docker.internal:11434"
    assert not (tmp_path/".env").exists()
