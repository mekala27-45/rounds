import type {Bundle,Row} from './types';
let connection:Promise<import('@duckdb/duckdb-wasm').AsyncDuckDBConnection>|undefined;
export function aggregateTables(bundle:Bundle):Record<string,Row[]>{return {
 monthly_activity:bundle.overview.trend,
 department_metrics:Object.entries(bundle.departments).flatMap(([department,d])=>d.metrics.map(m=>({department,measure:m.label,value:m.value,unit:m.unit??'',note:m.note??''}))),
 cohort_counts:bundle.cohort_counts??bundle.cohorts.map(c=>({cohort_id:c.id,name:c.name,count:c.count})),
 quality_measures:bundle.measures.map(m=>({id:m.id,name:m.name,numerator:m.numerator,denominator:m.denominator,value:m.value,unit:m.unit,department:m.department})),
 quality_checks:bundle.quality.checks.map(c=>({...c})),
};}
export async function queryWarehouse(bundle:Bundle,sql:string):Promise<Row[]>{
 const query=sql.trim().replace(/;$/,'');if(!/^(select|with)\s/i.test(query)||query.includes(';'))throw new Error('Use one SELECT query over the aggregate tables.');
 if(!connection)connection=(async()=>{const d=await import('@duckdb/duckdb-wasm');const selected=await d.selectBundle(d.getJsDelivrBundles());if(!selected.mainWorker)throw Error('This browser cannot start the SQL engine.');
  const workerURL=URL.createObjectURL(new Blob([`importScripts(${JSON.stringify(selected.mainWorker)});`],{type:'text/javascript'}));const worker=new Worker(workerURL);const db=new d.AsyncDuckDB(new d.VoidLogger(),worker);await db.instantiate(selected.mainModule,selected.pthreadWorker);URL.revokeObjectURL(workerURL);const conn=await db.connect();
  for(const [name,rows] of Object.entries(aggregateTables(bundle))){if(!rows.length)continue;await db.registerFileText(name+'.json',JSON.stringify(rows));await conn.query(`CREATE TABLE ${name} AS SELECT * FROM read_json_auto('${name}.json')`)}
  await conn.query('SET enable_external_access = false');return conn;
 })().catch(e=>{connection=undefined;throw e});
 const conn=await connection;const result=await conn.query(`SELECT * FROM (${query}) AS result LIMIT 500`);return result.toArray().map(row=>JSON.parse(JSON.stringify(row.toJSON(),(_,v)=>typeof v==='bigint'?Number(v):v))) as Row[];
}
