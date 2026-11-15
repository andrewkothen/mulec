"use client";
import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { Play, Pause, Repeat2 } from "lucide-react";
import { Project, clock } from "@/lib/model";

export default function Player({project,seek,onTime}:{project:Project;seek:{time:number;nonce:number}|null;onTime:(t:number)=>void}) {
  const container=useRef<HTMLDivElement>(null), wave=useRef<WaveSurfer|null>(null);
  const callback=useRef(onTime); callback.current=onTime;
  const [playing,setPlaying]=useState(false), [time,setTime]=useState(0), [ready,setReady]=useState(false);
  const [error,setError]=useState(""), [speed,setSpeed]=useState(1), [loop,setLoop]=useState(false);
  const [start,setStart]=useState(0), [end,setEnd]=useState(project.source.duration);
  const region=useRef({start,end,loop}); region.current={start,end,loop};
  useEffect(()=>{
    if(!container.current)return;
    setReady(false);setError("");setTime(0);setPlaying(false);setSpeed(1);setStart(0);setEnd(project.source.duration);setLoop(false);
    const ws=WaveSurfer.create({container:container.current,height:100,waveColor:"#a2b8b0",progressColor:"#246557",cursorColor:"#da6a49",barWidth:2,barGap:2,barRadius:2,
      url:`/api/projects/${project.id}/audio`,peaks:[project.waveform],duration:project.source.duration,normalize:true});
    wave.current=ws;
    ws.on("ready",()=>setReady(true));
    ws.on("play",()=>setPlaying(true));ws.on("pause",()=>setPlaying(false));
    ws.on("timeupdate",(t)=>{const r=region.current;if(r.loop&&r.end>r.start&&t>=r.end){ws.setTime(r.start);return;}setTime(t);callback.current(t);});
    ws.on("finish",()=>{if(region.current.loop){ws.setTime(region.current.start);void ws.play().catch(e=>setError(String(e)));}});
    ws.on("error",()=>setError("Audio unavailable. JSON imports contain notation only."));
    return ()=>{ws.destroy();wave.current=null;};
  },[project.id]);
  useEffect(()=>{if(seek&&ready)wave.current?.setTime(Math.min(seek.time,project.source.duration));},[seek,ready,project.source.duration]);
  return <div className="player">
    <div className="eyebrow">SOURCE RECORDING</div><h3 title={project.source.filename}>{project.source.filename}</h3>
    <div ref={container} className="waveform"/>
    <div className="transport"><button className="play" aria-label={playing?"Pause":"Play"} disabled={!ready} onClick={()=>void wave.current?.playPause().catch(e=>setError(String(e)))}>{playing?<Pause size={20}/>:<Play size={20}/>}</button><span className="time">{clock(time)} <span>/ {clock(project.source.duration)}</span></span><select aria-label="Playback speed" value={speed} onChange={e=>{const v=Number(e.target.value);setSpeed(v);wave.current?.setPlaybackRate(v,true);}}>{[0.5,0.75,1,1.25,1.5].map(n=><option key={n} value={n}>{n}×</option>)}</select></div>
    <div className="loop-fields"><label>Loop from (s)<input type="number" min="0" max={end} step="0.1" value={start} onChange={e=>setStart(Math.max(0,Math.min(end,Number(e.target.value))))}/></label><label>To (s)<input type="number" min={start} max={project.source.duration} step="0.1" value={end} onChange={e=>setEnd(Math.min(project.source.duration,Math.max(start,Number(e.target.value))))}/></label><button className={loop?"icon active":"icon"} title="Loop selected region" aria-label="Loop selected region" aria-pressed={loop} onClick={()=>{setLoop(!loop);if(!loop)wave.current?.setTime(start);}}><Repeat2 size={19}/></button></div>
    {error&&<p className="error-inline">{error}</p>}
    {project.source.reference_url&&<a className="source-link" href={project.source.reference_url} target="_blank" rel="noreferrer">Open source reference ↗</a>}
  </div>;
}
