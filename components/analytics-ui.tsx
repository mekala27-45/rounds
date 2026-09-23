"use client";
import { useId, useState } from "react";
import { ArrowUpRight, Info, Table2, ChartNoAxesCombined, CheckCircle2, CircleAlert } from "lucide-react";
import { Table,TableHeader,TableBody,TableRow,TableHead,TableCell } from "@/components/ui/table";
import type {Metric,Row} from "@/lib/types";

export function fmt(value:unknown,digits=1):string {
 if (value===null||value===undefined) return "Not available";
 if(typeof value==="number") return Number.isFinite(value)?value.toLocaleString("en-US",{maximumFractionDigits:digits}):"Not available";
 if(typeof value==="object") return JSON.stringify(value);
 return String(value);
}
export function human(value:string){return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());}
export function DataTable({rows,limit=100,columns}:{rows:Row[];limit?:number;columns?:string[]}) {
 if(!rows?.length) return <div className="empty">No records meet this definition.</div>;
 const keys=columns??Object.keys(rows[0]);
 return <Table className="data-table"><TableHeader><TableRow>{keys.map(k=><TableHead key={k}>{human(k)}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.slice(0,limit).map((r,i)=><TableRow key={i}>{keys.map(k=><TableCell className={typeof r[k]==="number"?"numeric":""} key={k}>{fmt(r[k],3)}</TableCell>)}</TableRow>)}</TableBody></Table>;
}
export function Sparkline({values}:{values:number[]}){
 if(values.length<2)return null; const min=Math.min(...values),max=Math.max(...values); const points=values.map((v,i)=>`${i/(values.length-1)*70+1},${23-(v-min)/(max-min||1)*20}`).join(" ");
 return <svg className="sparkline" viewBox="0 0 72 26" role="img" aria-label="Monthly trend"><polyline points={points} fill="none" stroke="var(--series)" strokeWidth="2"/><circle cx="71" cy={23-(values.at(-1)!-min)/(max-min||1)*20} r="2" fill="var(--series)"/></svg>;
}
export function MetricCards({metrics,trend}:{metrics:Metric[];trend?:number[]}){
 return <div className="metrics" style={metrics.length<4?{gridTemplateColumns:`repeat(${Math.max(metrics.length,1)},minmax(0,1fr))`}:undefined}>{metrics.slice(0,4).map((m,i)=><div className="metric" key={m.label}><div className="metric-label"><span>{m.label}</span><Info size={13} aria-label={m.definition??m.note??m.label}/></div><div className="metric-value">{typeof m.value === "number" && Math.abs(m.value)>=1000000 ? new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:1}).format(m.value) : fmt(m.value)}{m.unit&&<small> {m.unit}</small>}</div><div className="flex items-end justify-between gap-2"><div className="metric-meta">{m.note??"Synthetic population"}</div>{i===0&&trend&&<Sparkline values={trend}/>}</div></div>)}</div>;
}
export function Status({pass,children}:{pass?:boolean;children:React.ReactNode}){return <span className={`status ${pass===true?"good":pass===false?"warning":""}`}>{pass===true?<CheckCircle2 size={12}/>:pass===false?<CircleAlert size={12}/>:null}{children}</span>;}
type Series = {key:string;label:string;color?:string};
export function Chart({title,subtitle,rows,series,callout,bar=false,yMax,reference,defaultTable=false}:{title:string;subtitle?:string;rows:Row[];series:Series[];callout:string;bar?:boolean;yMax?:number;reference?:boolean;defaultTable?:boolean}){
 const [table,setTable]=useState(defaultTable),id=useId().replaceAll(":","");
 const valid=rows.filter(r=>series.some(s=>typeof r[s.key]==="number"));
 const nums=valid.flatMap(r=>series.map(s=>Number(r[s.key]??0))).filter(Number.isFinite);
 const max=yMax??Math.max(1,...nums)*1.15,min=Math.min(0,...nums); const x=(i:number)=>54+i/Math.max(1,valid.length-1)*560;const y=(v:number)=>195-(v-min)/(max-min)*168;
 return <section className="panel"><div className="panel-head"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div><button className="btn icon" onClick={()=>setTable(!table)} aria-label={table?`Show chart for ${title}`:`Show table for ${title}`} title={table?"Chart view":"Table view"}>{table?<ChartNoAxesCombined size={15}/>:<Table2 size={15}/>}</button></div>{table?<div className="panel-body"><DataTable rows={rows}/></div>:valid.length?<><div className="legend">{series.map((s,i)=><span key={s.key}><i className={i?"second":""} style={{borderColor:s.color}}/>{s.label}</span>)}</div><div className="chart-wrap"><svg className="chart-svg" viewBox="0 0 650 230" role="img" aria-labelledby={id}><title id={id}>{title}. {callout}</title><defs><linearGradient id={`fill-${id}`} x1="0" x2="0" y1="0" y2="1"><stop stopColor="var(--series)" stopOpacity=".14"/><stop offset="1" stopColor="var(--series)" stopOpacity=".01"/></linearGradient></defs>{Array.from({length:5},(_,i)=>min+(max-min)*i/4).map((v,i)=><g key={i}><line className="gridline" x1="54" x2="618" y1={y(v)} y2={y(v)}/><text x="44" y={y(v)+4} textAnchor="end">{fmt(v,1)}</text></g>)}{reference&&<line x1="54" x2="614" y1={y(0)} y2={y(max)} stroke="var(--muted-foreground)" strokeDasharray="3 5"/>}{valid.map((r,i)=>i%Math.max(1,Math.ceil(valid.length/6))===0||i===valid.length-1?<text key={i} x={x(i)} y="221" textAnchor="middle">{String(r.label??r.month??i).slice(0,12)}</text>:null)}{series.map((s,si)=>{const points=valid.map((r,i)=>`${x(i)},${y(Number(r[s.key]??0))}`).join(" "),color=s.color??(si?"var(--series2)":"var(--series)");return <g key={s.key}>{!bar&&si===0&&<polygon points={`54,${y(0)} ${points} 614,${y(0)}`} fill={`url(#fill-${id})`}/>} {!bar&&<polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeDasharray={si?"5 4":undefined}/>} {valid.map((r,i)=>bar?<rect key={i} x={x(i)-10+si*12} y={y(Number(r[s.key]??0))} width={Math.min(18,480/valid.length/series.length)} height={Math.max(0,y(0)-y(Number(r[s.key]??0)))} fill={color} rx="3" tabIndex={0}><title>{fmt(r.label)}: {s.label} {fmt(r[s.key])}</title></rect>:<circle key={i} cx={x(i)} cy={y(Number(r[s.key]??0))} r="4" fill="var(--card)" stroke={color} strokeWidth="2" tabIndex={0}><title>{fmt(r.label)}: {s.label} {fmt(r[s.key])}</title></circle>)}</g>})}</svg></div></>:<div className="empty">This measure has no eligible observations.</div>}<div className="panel-footer"><Info size={13}/><span>{callout}</span></div></section>;
}
export function SectionHeader({title,text,href,action}:{title:string;text?:string;href?:string;action?:string}){return <div className="section-row"><div><h2>{title}</h2>{text&&<p>{text}</p>}</div>{href&&<a className="text-link" href={href}>{action??"View details"}<ArrowUpRight size={14}/></a>}</div>;}
