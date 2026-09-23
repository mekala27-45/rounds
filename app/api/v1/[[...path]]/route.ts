import {getChatGPTUser} from '@/app/chatgpt-auth';
import {authenticate,db,digest,purposeOf,recordAccess,response} from '@/lib/audit';
import {scoreLinear,type LinearModel} from '@/lib/scoring';
import patientData from '@/data/private/patients.json';
import modelData from '@/data/private/models.json';
import inputData from '@/data/private/inputs.json';

export const dynamic='force-dynamic';
type Patient={id:string;age_band:string;sex:string;index_admission:string;[key:string]:unknown};
type ModelInput={features:Record<string,number>;prediction_time:string;index_id:string};
const patients=patientData.patients as Patient[];
const models=Object.fromEntries((modelData as unknown as (LinearModel&{id:string})[]).map(m=>[m.id,m]));
const inputs=inputData as unknown as Record<string,Record<string,ModelInput>>;
function score(personId:string,id:string){const model=models[id],input=inputs[personId]?.[id];if(!model||!input)throw Error('No evaluated model input is available for this record.');return {...scoreLinear(model,input.features),model:id,prediction_time:input.prediction_time,status:'Research demonstration only',explanation_method:'Exact linear feature contributions; not causal effects.'};}
async function handle(request:Request,parts:string[]){try{
 const action=parts[0]??'health';
 if(action==='health')return response({status:'ok',data:'synthetic',audit_backend:'D1',patient_count:patients.length});
 if(request.method==='GET'&&action!=='audit')return response({error:'Use POST with an access purpose.'},405);
 if(request.headers.get('sec-fetch-site')==='cross-site')return response({error:'Cross-site access is not allowed.'},403);
 if(Number(request.headers.get('content-length')??0)>8000)return response({error:'Request is too large.'},413);
 const body=request.method==='POST'?await request.json() as Record<string,unknown>:{};
 if(action==='session'){
  const user=await getChatGPTUser();if(!user)return response({error:'Sign in to start an audited access session.',signin:'/signin-with-chatgpt?return_to=/patients'},401);
  const token=crypto.randomUUID()+crypto.randomUUID(),expires=Date.now()+3600000;
  await db().prepare('INSERT INTO access_tokens (token_hash, subject, expires) VALUES (?, ?, ?)').bind(await digest(token),user.userId,expires).run();
  return response({token,expires,subject:user.displayName});
 }
 const subject=await authenticate(request);
 if(action==='audit'){
  const rows=await db().prepare('SELECT id, created_at, person_id, route, purpose, action FROM audit_events WHERE subject = ? ORDER BY created_at DESC LIMIT 200').bind(subject).all();return response({events:rows.results});
 }
 const purpose=purposeOf(body);
 if(action==='score'&&parts[1]==='ed_arrivals'){
  const horizon=body.horizon===undefined?14:Number(body.horizon);if(!Number.isInteger(horizon)||horizon<1||horizon>56)return response({error:'Forecast horizon must be an integer from 1 to 56 days.'},400);
  const model=models.ed_arrivals,history=[...(model.last_28_counts as number[])];const forecast=[];const date=new Date(String(model.last_date)+'T00:00:00Z');
  for(let i=0;i<horizon;i++){const prediction=[7,14,21,28].reduce((sum,lag)=>sum+history[history.length-lag],0)/4;history.push(prediction);date.setUTCDate(date.getUTCDate()+1);forecast.push({date:date.toISOString().slice(0,10),arrivals:prediction})}
  const audit=await recordAccess(subject,['aggregate'],'/v1/score/ed_arrivals',purpose,'forecast');return response({model:'ed_arrivals',forecast,audit,method:'Mean of the previous four matching weekdays, recursively extended. Original synthetic calendar.',interval:'No prospective interval guarantee is claimed.'});
 }
 if(action==='patients'&&!parts[1]){
  const audit=await recordAccess(subject,patients.map(p=>p.id),'/v1/patients',purpose);
  const contacts=await db().prepare('SELECT person_id, contacted FROM care_contacts').all<{person_id:string;contacted:number}>();const contact=new Map(contacts.results.map(r=>[r.person_id,r.contacted===1]));
  const rows=patients.map(p=>{let risk:number|null=null,risk_as_of:string|null=null;try{const s=score(p.id,'readmit30');risk=s.prediction;risk_as_of=s.prediction_time}catch{}return {id:p.id,age_band:p.age_band,sex:p.sex,index_admission:p.index_admission,risk,risk_as_of,contacted:contact.get(p.id)??false}}).sort((a,b)=>(b.risk??-1)-(a.risk??-1));return response({patients:rows,audit});
 }
 const personId=action==='patients'?parts[1]:String(body.person_id??'');const person=patients.find(p=>p.id===personId);if(!person)return response({error:'Patient is not in the deployed synthetic sample.'},404);
 if(action==='patients'){
  const audit=await recordAccess(subject,[person.id],'/v1/patients/'+person.id,purpose);
  const scores=Object.keys(models).flatMap(id=>{try{return [score(person.id,id)]}catch{return []}});
  return response({patient:person,scores,audit});
 }
 if(action==='score'){
  const id=parts[1]??'';const prediction=score(person.id,id);const audit=await recordAccess(subject,[person.id],'/v1/score/'+id,purpose,'score');return response({score:prediction,audit});
 }
 if(action==='contact'){
  if(typeof body.contacted!=='boolean')return response({error:'Contacted must be a boolean.'},400);
  const auditId=crypto.randomUUID(),at=new Date().toISOString();const result=await db().batch([
   db().prepare('INSERT INTO audit_events (id,subject,created_at,person_id,route,purpose,action) VALUES (?,?,?,?,?,?,?)').bind(auditId,subject,at,person.id,'/v1/contact',purpose,body.contacted?'mark_contacted':'mark_not_contacted'),
   db().prepare('INSERT INTO care_contacts (person_id,contacted,updated_at,subject) VALUES (?,?,?,?) ON CONFLICT(person_id) DO UPDATE SET contacted=excluded.contacted,updated_at=excluded.updated_at,subject=excluded.subject').bind(person.id,body.contacted?1:0,at,subject)
  ]);if(result.some(r=>!r.success))throw Error('Could not save the audited contact update.');return response({saved:true,contacted:body.contacted,audit:{id:auditId,at}});
 }
 return response({error:'Endpoint not found.'},404);
 }catch(error){const message=error instanceof Error?error.message:'Request could not be completed.';const status=message.startsWith('AUTH:')?401:message.includes('purpose')?400:503;return response({error:message.replace('AUTH: ',''),patient_data_withheld:true},status)}}
export async function POST(request:Request,context:{params:Promise<{path?:string[]}>}){return handle(request,(await context.params).path??[])}
export async function GET(request:Request,context:{params:Promise<{path?:string[]}>}){return handle(request,(await context.params).path??[])}
