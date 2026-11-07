"""Create a portable source archive without credentials, databases or dependencies."""

from pathlib import Path
import zipfile, hashlib, json

root = Path(__file__).resolve().parents[1]
out = root / "output"
out.mkdir(exist_ok=True)
excluded = {
    ".git",
    ".local",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "playwright-report",
    "output",
    ".DS_Store",
}
files = []
for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(root)
    if any(x in excluded for x in rel.parts):
        continue
    if rel.parts[:2] == ("frontend", "test-results"):
        continue
    if p.name.startswith(".env") and p.name != ".env.example":
        continue
    if p.suffix in {".log", ".pyc", ".zip"}:
        continue
    files.append(p)
archive = out / "DevSphere-AI-Source.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in files:
        z.write(p, "DevSphereAI/" + str(p.relative_to(root)))
    for name in ("DevSphere-AI-Project-Report.docx", "DevSphere-AI-Project-Report.pdf", "DevSphere-AI-UML-Handbook.docx", "DevSphere-AI-UML-Handbook.pdf"):
        artifact = out / name
        if artifact.is_file():
            z.write(artifact, "DevSphereAI/output/" + name)
            files.append(artifact)
manifest = {
    "archive": archive.name,
    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "file_count": len(files),
    "excludes": ["credentials", "databases", "dependencies", "runtime logs"],
}
(out / "source-manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
