export default function JobReviewResult({result:r}:{result:any}){
  const evidence=[...(r.evidence||[])].sort((a:any,b:any)=>(a.severity==='high'?0:1)-(b.severity==='high'?0:1));
  const categories=new Set(evidence.map((e:any)=>e.category));
  const spans=evidence.map((e:any)=>({start:e.start,end:e.end})).sort((a:any,b:any)=>a.start-b.start);
  const merged:{start:number;end:number}[]=[];
  for(const s of spans){const prev=merged[merged.length-1];if(prev&&s.start<=prev.end)prev.end=Math.max(prev.end,s.end);else merged.push({...s});}
  const chunks:any[]=[];let offset=0;
  for(const s of merged){chunks.push(r.text.slice(offset,s.start));chunks.push(<mark key={s.start}>{r.text.slice(s.start,s.end)}</mark>);offset=s.end;}
  chunks.push(r.text.slice(offset));
  return <><div className={'b-review-verdict '+(r.risk_tier==='high'?'b-review-high':'')}><span className="b-pill">{r.risk_tier==='high'?'High concern':r.risk_tier==='needs_review'?'More checks needed':'Limited warning signals'}</span><h2>{r.advisory}</h2><p>{r.decision_basis||'Review evidence and verify the employer independently.'}</p></div>
    <div className="b-stats"><b>{categories.size}<small>Warning categories</small></b><b>{evidence.filter((e:any)=>e.severity==='high').length}<small>High-concern findings</small></b></div>
    {evidence.length>0?<><h3>Why this needs attention</h3><div className="b-evidence-list">{evidence.map((e:any)=><article className="b-evidence" data-severity={e.severity} key={`${e.start}-${e.category}`}><small>{e.severity==='high'?'PRIORITY CHECK':'CHECK IN CONTEXT'}</small><h3>{e.category}</h3><blockquote>“{e.text}”</blockquote><p>{e.action}</p></article>)}</div></>:<p className="b-help">No explicit rule warnings were found. This does not verify the company or establish that the offer is safe.</p>}
    <details open><summary>Posting with highlighted evidence</summary><div className="b-posting">{chunks}</div></details>
    <details open><summary>Extracted pay, hours and contact</summary><div className="b-fact-grid">{Object.entries(r.extracted||{}).map(([key,values])=><div key={key}><small>{({pay:'Stated compensation',payment_requests:'Requested payments',hours:'Working hours',domains:'Domains',emails:'Email contacts'} as Record<string,string>)[key]||key}</small><p>{(values as string[]).join(' · ')||'Not found in the posting'}</p></div>)}</div>{r.compensation_details?.some((p:any)=>p.currency_ambiguous)&&<p className="b-help">A currency name is ambiguous. “Dinars” alone does not identify the country, and “dollars” alone does not identify the dollar currency.</p>}</details>
    <h3>Before applying</h3><ul>{(r.next_actions||[]).map((s:string)=><li key={s}>{s}</li>)}</ul>
    {(r.missing_information||[]).map((s:string)=><p className="b-warning" key={s}>{s}</p>)}
    <details><summary>Classifier details and limitations</summary><p><b>{(r.model_probability*100).toFixed(1)}%</b> raw classifier output.</p><p>{r.calibration}</p><p>Evidence warnings can require investigation even when this classifier value is below 50%. It is not a verified fraud probability.</p>{(r.limitations||[]).map((s:string)=><p key={s}>{s}</p>)}</details>
  </>;
}
