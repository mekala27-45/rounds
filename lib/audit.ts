import {env} from 'cloudflare:workers';
import {STATEMENT} from './constants';
export function db(){if(!env.DB)throw new Error('Audit storage is unavailable. Patient data remains locked.');return env.DB;}
export function response(data:Record<string,unknown>,status=200){return Response.json({...data,statement:STATEMENT},{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
export async function digest(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
export function purposeOf(body:Record<string,unknown>){const p=typeof body.purpose==='string'?body.purpose.trim():'';if(p.length<10||p.length>300)throw new Error('Provide a purpose between 10 and 300 characters.');return p;}
export async function authenticate(request:Request){const token=request.headers.get('Authorization')?.match(/^Bearer ([A-Za-z0-9-]+)$/)?.[1];if(!token)throw Error('AUTH: A short-lived access token is required.');const record=await db().prepare('SELECT subject, expires FROM access_tokens WHERE token_hash = ?').bind(await digest(token)).first<{subject:string;expires:number}>();if(!record||record.expires<=Date.now())throw Error('AUTH: This access session has expired. Start a new session.');return record.subject;}
export async function recordAccess(subject:string,personIds:string[],route:string,purpose:string,action='view'){
 const batchId=crypto.randomUUID(),at=new Date().toISOString();const statements=personIds.map((person,i)=>db().prepare('INSERT INTO audit_events (id, subject, created_at, person_id, route, purpose, action) VALUES (?, ?, ?, ?, ?, ?, ?)').bind(`${batchId}:${i}`,subject,at,person,route,purpose,action));const result=await db().batch(statements);if(result.some(r=>!r.success))throw Error('Audit persistence failed. Patient data remains locked.');
 const observed=await db().prepare('SELECT COUNT(*) AS n FROM audit_events WHERE id LIKE ?').bind(batchId+':%').first<{n:number}>();if(observed?.n!==personIds.length)throw Error('Audit verification failed. Patient data remains locked.');return {id:batchId,at,records:personIds.length};
}
