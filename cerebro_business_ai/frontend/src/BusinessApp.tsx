import { useEffect, useRef, useState } from 'react';
import './business.css';

const API=import.meta.env.VITE_API_URL || 'http://127.0.0.1:8900';
type Obj=Record<string,any>;
type Module='hiring'|'demand'|'fraud'|'product';
type Row={date:string;sales:number;price:number|null;visitors:number|null;promotion:boolean;stockout:boolean};
const names: Record<Module,string>={hiring:'Hiring assistant',demand:'Sales & inventory',fraud:'Job verification',product:'Product copy studio'};
const routes: Record<Module,string>={hiring:'/api/ai/jobs/brief',demand:'/api/ai/demand/plan',fraud:'/api/ai/jobs/review',product:'/api/ai/products/brief'};
const examples: Record<Module,string>={hiring:'We need a senior ML engineer to turn our retail forecasting prototype into reliable APIs. Python, XGBoost and FastAPI. 5000/month, meals and housing. Help me define the role and evaluate candidates.',fraud:'Work from home 1 hour a day. Earn $500/day. No experience required. Contact us on Telegram and pay a registration fee.',product:'Wireless over-ear headphones. USB-C charging, foldable design, 3.5 mm wired connection. Black. For students commuting to campus. Brand: Northline. I have not verified battery life or noise cancellation.',demand:''};
function sample(pattern='seasonal'):Row[]{return Array.from({length:84},(_,i)=>({date:new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10),sales:pattern==='intermittent'?(i%9===0?6:0):Math.max(0,Math.round(8+[0,1,2,1,3,7,5][i%7]+i*.05)),price:20,visitors:null,promotion:false,stockout:false}));}
function readable(value:any):string{if(Array.isArray(value))return value.map(v=>typeof v==='object'?Object.entries(v).map(([k,x])=>`${k.replaceAll('_',' ')}: ${x}`).join('\n'):`• ${v}`).join('\n\n'); return typeof value==='object'?JSON.stringify(value,null,2):String(value??'');}
function download(name:string,content:string){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type:'text/plain;charset=utf-8'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function parseCSV(text:string):Row[]{
  const lines:string[][]=[];let row:string[]=[],cell='',quoted=false;
  for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\\n'||c==='\\r')&&!quoted){if(c==='\\r'&&text[i+1]==='\\n')i++;row.push(cell);if(row.some(x=>x.trim()))lines.push(row);row=[];cell='';}else cell+=c;}
  if(quoted)throw new Error('CSV has an unclosed quote.');row.push(cell);if(row.some(x=>x.trim()))lines.push(row);
  const header=lines.shift()?.map(x=>x.trim().replace(/^\\uFEFF/,'').toLowerCase())||[];
  const find=(names:string[])=>names.map(n=>header.indexOf(n)).find(i=>i>=0)??-1;
  const ix={date:find(['date','day','timestamp','sale date']),sales:find(['sales','units sold','units','quantity','demand']),price:find(['price','unit price']),visitors:find(['visitors','traffic']),promotion:find(['promotion','promo','on promotion']),stockout:find(['stockout','stock out','out of stock'])};
  if(ix.date<0||ix.sales<0)throw new Error('Cerebro could not map the file. Need a date column and a sales/units sold column.');
  if(lines.length>730)throw new Error('Please use at most 730 daily rows.');
  const bool=(value:string, row:number, key:string)=>{if(!value||['0','false','no','n'].includes(value.toLowerCase()))return false;if(['1','true','yes','y'].includes(value.toLowerCase()))return true;throw new Error(`Row ${row}: ${key} must be true/false.`);};
  const out=lines.map((cells,i)=>{const get=(k:keyof typeof ix)=>ix[k]>=0?(cells[ix[k]]||'').trim():'';const rawDate=get('date');const parsed=new Date(rawDate);if(!rawDate||Number.isNaN(parsed.getTime()))throw new Error(`Row ${i+2}: invalid date "${rawDate}".`);const rawSales=get('sales');const sales=Number(rawSales);if(!rawSales||!Number.isFinite(sales)||sales<0)throw new Error(`Row ${i+2}: sales must be a nonnegative number.`);const optional=(k:keyof typeof ix)=>{const v=get(k);if(!v)return null;const n=Number(v);if(!Number.isFinite(n)||n<0)throw new Error(`Row ${i+2}: ${k} must be a nonnegative number.`);return n;};return {date:parsed.toISOString().slice(0,10),sales,price:optional('price'),visitors:optional('visitors'),promotion:bool(get('promotion'),i+2,'promotion'),stockout:bool(get('stockout'),i+2,'stockout')};});
  const seen=new Set<string>();for(const r of out){if(seen.has(r.date))throw new Error(`Duplicate date found: ${r.date}. Remove or combine duplicate rows.`);seen.add(r.date);}return out.sort((a,b)=>a.date.localeCompare(b.date));
}
