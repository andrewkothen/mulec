"use client";
import {Plus, Trash2, Scissors, X} from "lucide-react";
import {Measure, quarters} from "@/lib/model";

export function TextField({label,value,onChange,maxLength=160}:{label:string;value:string;onChange:(v:string)=>void;maxLength?:number}) {
  return <label>{label}<input key={value} defaultValue={value} maxLength={maxLength} onBlur={e=>{if(e.target.value!==value)onChange(e.target.value);}} onKeyDown={e=>{if(e.key==="Enter")e.currentTarget.blur();}}/></label>;
}

export default function MeasureEditor({measure,index,onChange,onDelete,onSplit,onClose}:{measure:Measure;index:number;onChange:(m:Measure)=>void;onDelete:()=>void;onSplit:()=>void;onClose:()=>void}) {
  const q=quarters(measure.meter);
  function update(fn:(m:Measure)=>void){const copy=structuredClone(measure);fn(copy);onChange(copy);}
  return <section className="measure-editor">
    <div className="panel-heading"><div><div className="eyebrow">MAKE IT YOURS</div><h3>Bar {index+1}</h3></div><button className="icon" aria-label="Close bar editor" onClick={onClose}><X size={18}/></button></div>
    <TextField label="Section / rehearsal mark" value={measure.section} maxLength={60} onChange={v=>update(m=>{m.section=v;})}/>
    <TextField label="Rehearsal cue" value={measure.cue} onChange={v=>update(m=>{m.cue=v;})}/>
    <div className="field-pair"><label>Start (seconds)<input type="number" key={`s${measure.start}`} min="0" step="0.01" defaultValue={measure.start.toFixed(2)} onBlur={e=>update(m=>{m.start=Number(e.target.value);})}/></label><label>End (seconds)<input type="number" key={`e${measure.end}`} min="0" step="0.01" defaultValue={measure.end.toFixed(2)} onBlur={e=>update(m=>{m.end=Number(e.target.value);})}/></label></div>
    <h4>Harmony <span>quarter-note beats</span></h4>
    {[...measure.chords].sort((a,b)=>a.beat-b.beat).map(c=><div className="event-row" key={c.id}>
      <label className="beat-input"><span className="sr-only">Chord beat</span><input aria-label={`Chord beat ${c.symbol}`} type="number" min="1" max={q+0.5} step="0.5" key={`${c.id}${c.beat}`} defaultValue={c.beat+1} onBlur={e=>update(m=>{const item=m.chords.find(v=>v.id===c.id)!;item.beat=Number(e.target.value)-1;item.manual=true;})}/></label>
      <label className="symbol-input"><span className="sr-only">Chord symbol</span><input aria-label="Chord symbol" key={c.symbol} defaultValue={c.symbol} placeholder="Dm7" maxLength={48} onBlur={e=>update(m=>{const item=m.chords.find(v=>v.id===c.id)!;item.symbol=e.target.value.trim();item.manual=true;})} onKeyDown={e=>{if(e.key==="Enter")e.currentTarget.blur();}}/></label>
      <button className="icon" aria-label={`Remove ${c.symbol}`} onClick={()=>update(m=>{m.chords=m.chords.filter(v=>v.id!==c.id);})}><Trash2 size={15}/></button>
    </div>)}
    <button className="text-button" onClick={()=>update(m=>{const beat=Array.from({length:Math.ceil(q*2)},(_,i)=>i/2).find(b=>!m.chords.some(c=>c.beat===b));if(beat!==undefined)m.chords.push({id:crypto.randomUUID(),beat,symbol:"C",confidence:1,manual:true});})}><Plus size={14}/> Add chord change</button>
    <p className="hint">Examples: Cmaj7 · Dm7 · G7b9 · Bb/F · N.C. Beat 1.5 is the offbeat after beat 1.</p>
    <details><summary>Melody notes ({measure.notes.length})</summary><p className="hint">MIDI pitch: C4 = 60. Durations use quarter-note beats. Gaps become rests.</p>
      {measure.notes.map(n=><div className="note-row" key={n.id}>{(["beat","midi","duration"] as const).map(field=><label key={field}>{field==="midi"?"Pitch":field==="beat"?"Beat":"Length"}<input type="number" step={field==="midi"?1:0.5} key={n[field]} defaultValue={n[field]+(field==="beat"?1:0)} onBlur={e=>update(m=>{const item=m.notes.find(v=>v.id===n.id)!;item[field]=Number(e.target.value)-(field==="beat"?1:0);item.manual=true;})}/></label>)}<button className="icon" aria-label="Remove note" onClick={()=>update(m=>{m.notes=m.notes.filter(v=>v.id!==n.id);})}><Trash2 size={14}/></button></div>)}
      <button className="text-button" onClick={()=>update(m=>{const beat=Math.max(0,...m.notes.map(n=>n.beat+n.duration));if(beat<q)m.notes.push({id:crypto.randomUUID(),beat,duration:Math.min(1,q-beat),midi:60,confidence:1,manual:true});})}><Plus size={14}/> Add note</button>
    </details>
    <div className="repeat-options"><label><input type="checkbox" checked={measure.repeat_start} onChange={e=>update(m=>{m.repeat_start=e.target.checked;})}/> Repeat start</label><label><input type="checkbox" checked={measure.repeat_end} onChange={e=>update(m=>{m.repeat_end=e.target.checked;})}/> Repeat end</label></div>
    <div className="editor-actions"><button className="secondary small" onClick={onSplit}><Scissors size={14}/> Split bar</button><button className="danger small" onClick={onDelete}><Trash2 size={14}/> Delete bar</button></div>
  </section>;
}
