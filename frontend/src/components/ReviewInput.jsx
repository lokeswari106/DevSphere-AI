import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Upload, ScanLine, X, FileCode2 } from "lucide-react";
import { api, errorText } from "../api";

const languages = { JavaScript: ["app.js", "Node.js"], Python: ["app.py", "FastAPI"], Java: ["Main.java", "Java standard library"] };
const extensions = /\.(py|js|jsx|mjs|cjs|json|md|sql|java|css|html|txt|toml|yaml|yml|xml|properties|csv)$/i;
export function validateReviewFiles(files) {
  if (!files.length || files.length > 60) throw new Error("Choose between 1 and 60 source files.");
  let total = 0; const seen = new Set();
  for (const f of files) {
    if (!f.path || f.path.length > 240 || /[\\:\0]/.test(f.path) || f.path.split('/').some(p => !p || p.startsWith('.') || ['node_modules','dist','target','vendor','__pycache__'].includes(p)) || !extensions.test(f.path))
      throw new Error("Use a source filename such as app.js or src/service.py. Archives and dependency folders are not supported.");
    if (seen.has(f.path.toLowerCase())) throw new Error("Two files have the same path: " + f.path);
    seen.add(f.path.toLowerCase());
    const size = new TextEncoder().encode(f.content).length;
    if (size > 100000 || f.content.includes('\0')) throw new Error("Each source file must be text and at most 100 KB: " + f.path);
    total += size;
  }
  if (total > 750000) throw new Error("Choose at most 750 KB of source code.");
  if (!files.some(f => f.content.trim())) throw new Error("Paste code or choose a nonempty source file.");
  return files;
}

export default function ReviewInput() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("paste"), [language, setLanguage] = useState("JavaScript");
  const [path, setPath] = useState("app.js"), [code, setCode] = useState(""), [files, setFiles] = useState([]);
  const [name, setName] = useState(""), [goals, setGoals] = useState("");
  const [error, setError] = useState(""), [busy, setBusy] = useState(false), [savedId, setSavedId] = useState(null);
  async function upload(event) {
    const picked = [...event.target.files]; event.target.value = "";
    setError("");
    try {
      if (picked.length > 60 || picked.some(f => f.size > 100000)) throw new Error("Select at most 60 source files, each up to 100 KB.");
      const loaded = await Promise.all(picked.map(async f => ({path:f.webkitRelativePath || f.name, content:await f.text()})));
      setFiles(validateReviewFiles([...files, ...loaded]));
    } catch (e) { setError(e.message); }
  }
  async function submit(event) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const input = validateReviewFiles(mode === "paste" ? [{path:path.trim(),content:code}] : files);
      const description = "Review the supplied source for bugs, correctness, security and maintainability. Suggest concrete replacement code. " + goals;
      const {data:project} = await api.post('/projects', {
        project_name:(name.trim() || "Code review — " + input[0].path).slice(0,120),
        description, programming_language:language, framework:languages[language][1], application_type:"library",
      });
      setSavedId(project.id);
      const {data:proposal} = await api.post(`/projects/${project.id}/files/import`, {files:input,expected_revision:project.revision});
      // The button explicitly authorizes saving this initial snapshot in a NEW project.
      // Suggested fixes remain suggestions; existing projects are never overwritten.
      await api.post(`/projects/${project.id}/approvals/${proposal.id}/decision`, {
        decision:"approve", artifact_hash:proposal.artifact_hash, expected_revision:project.revision,
        comment:"Saved submitted source for analysis using Save & review code.",
      });
      await api.post(`/projects/${project.id}/execute`, {workflow_type:"quick_review",instructions:description});
      navigate(`/projects/${project.id}`, {state:{tab:"Code Review"}});
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  return <div className="page review-input-page">
    <span className="breadcrumb">Workspace / Code review</span>
    <header className="page-heading"><span className="eyebrow">A SECOND PAIR OF EYES</span><h1>Find the bug. See the fix.</h1><p>Paste a snippet or upload source files. Get file-level findings, explanations and suggested replacement code.</p></header>
    <form onSubmit={submit} className="review-input-form">
      <div className="review-method" role="tablist" aria-label="Source input method">
        {[["paste","Paste code"],["files","Upload files"]].map(([value,text]) => <button type="button" role="tab" key={value} aria-selected={mode===value} className={mode===value?'selected':''} onClick={()=>setMode(value)}>{text}</button>)}
      </div>
      <div className="form-row"><label>Language<select value={language} onChange={e=>{setLanguage(e.target.value); if (Object.values(languages).some(v=>v[0]===path)) setPath(languages[e.target.value][0]);}}>{Object.keys(languages).map(l=><option key={l}>{l}</option>)}</select></label>
      <label><span>Review name <small className="optional-label">Optional</small></span><input value={name} onChange={e=>setName(e.target.value)} maxLength={120} minLength={3} placeholder="e.g. Checkout service review" /></label></div>
      {mode==='paste' ? <><label>Filename<input value={path} onChange={e=>setPath(e.target.value)} required placeholder="src/checkout.js" /></label><label>Source code<textarea className="paste-code" value={code} onChange={e=>setCode(e.target.value)} rows={15} spellCheck={false} required placeholder="Paste the code you want to review…" maxLength={100000}/></label></> : <div className="review-upload-zone">
        <Upload size={24}/><h2>Choose your source files</h2><p>Python, JavaScript, Java and related text files. Up to 60 files, 100 KB each; 750 KB total.</p>
        <label className="secondary upload">Choose source files<input aria-label="Choose source files" type="file" multiple onChange={upload} accept=".py,.js,.jsx,.mjs,.cjs,.json,.md,.sql,.java,.css,.html,.txt,.toml,.yaml,.yml,.xml,.properties,.csv"/></label>
        {files.length>0 && <ul className="review-file-list">{files.map(f=><li key={f.path}><FileCode2 size={16}/><span>{f.path}</span><small>{new TextEncoder().encode(f.content).length.toLocaleString()} bytes</small><button type="button" aria-label={'Remove '+f.path} onClick={()=>setFiles(files.filter(x=>x.path!==f.path))}><X size={16}/></button></li>)}</ul>}
      </div>}
      <label><span>What should the review focus on? <small className="optional-label">Optional</small></span><textarea rows={2} value={goals} onChange={e=>setGoals(e.target.value)} maxLength={4000} placeholder="e.g. Checkout errors, validation and authorization"/></label>
      <p className="form-note">This saves a new review workspace. Your source is analyzed by the configured AI model; it is not executed. Remove secrets before submitting.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {savedId ? <p className="notice">Your workspace was created. <Link to={'/projects/'+savedId} state={{tab:'Code Review'}}>Open it to continue or retry the review.</Link></p> : null}
      <div className="form-actions"><button className="primary" disabled={busy || !!savedId}><ScanLine size={17}/>{busy?'Saving and starting review…':'Save & review code'}</button></div>
    </form>
  </div>;
}
