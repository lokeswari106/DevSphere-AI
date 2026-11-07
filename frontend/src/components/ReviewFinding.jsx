import { useState } from "react";
import { Status } from "./Artifacts";
import { label } from "../api";

export default function ReviewFinding({ finding:r, source }) {
  const [message,setMessage]=useState("");
  const lines = source?.file_content.split('\n') || [];
  const start = Math.max(0,(r.line_number || 1)-3);
  const context = lines.slice(start,start+7).map((line,i)=>`${start+i+1}  ${line}`).join('\n');
  async function copy() {
    try { await navigator.clipboard.writeText(r.improved_code); setMessage("Replacement copied."); }
    catch { setMessage("Clipboard is unavailable here. Select the code or download the suggestion."); }
  }
  function save() {
    const url=URL.createObjectURL(new Blob([r.improved_code],{type:'text/plain'}));
    const a=document.createElement('a'); a.href=url; a.download='suggested-fix-'+r.file_path.split('/').pop(); a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <article className="finding">
    <div className="section-line"><strong>{r.file_path}{r.line_number && `:${r.line_number}`}</strong><Status value={r.severity}/></div>
    <p>{r.issue_description}</p>
    <p><strong>How to fix it:</strong> {r.suggested_fix}</p>
    <small>{label(r.evidence_status)} · {r.issue_type}{r.source_current===false && " · Earlier source version"}</small>
    {context && <details className="source-context"><summary>Source context</summary><pre>{context}</pre></details>}
    {r.improved_code ? <section className="replacement-code"><div className="section-line"><h3>Suggested replacement code</h3><div className="button-row"><button className="text-button" onClick={copy}>Copy code</button><button className="text-button" onClick={save}>Download suggestion</button></div></div><pre>{r.improved_code}</pre><small>Replace the function or block described above. This suggestion has not been applied or tested.</small>{message && <p role="status">{message}</p>}</section> : <p className="muted">No safe replacement block was provided for this finding. Follow the explanation above and review the wider context.</p>}
  </article>;
}
