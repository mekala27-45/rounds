export type Row = Record<string, string | number | boolean | null>;
export type Metric = {label:string;value:number|string|null;unit?:string;note?:string;definition?:string};
export type Department = {metrics:Metric[];chart:Row[];chart_title:string;callout:string;method:string;limitation:string;pushback:string;rows:Row[]};
export type Cohort = {id:string;name:string;count:number;definition:string;sql:string;codes:string[];attrition:{label:string;count:number}[]};
export type Measure = {id:string;name:string;numerator:number|null;denominator:number|null;value:number|null;unit:string;definition:string;exclusions:string;department:string};
export type Model = {id:string;name:string;department:string;prediction_time:string;status:string;method:string;limitation:string;metrics:Record<string,number|string|null>;baselines:Row[];calibration:{predicted:number;observed:number;n:number}[];decision_curve:{threshold:number;model:number;all:number;none:number}[];subgroups:Row[];gates:{name:string;passed:boolean;reason:string}[];contract:Record<string,boolean|string>;monitoring?:Row[]};
export type Bundle = {
 provenance:{source:string;population:string;patients:number;seed:number;as_of:string;version:string;encounters:number};
 overview:{metrics:Metric[];trend:Row[];insights:{title:string;text:string;route:string}[]};
 departments:Record<string,Department>;cohorts:Cohort[];measures:Measure[];
 quality:{checks:{name:string;category:string;checked:number;failed:number;status:string}[];summary:string;terminology:Row[];k_anonymity:Record<string,number|string>};
 schema:{table:string;columns:string[]}[];statement:string;models:Model[];memo?:{title:string;sections:{heading:string;text:string}[]};
 cohort_counts?:Row[];external?:Record<string,unknown>;benchmarks?:Row[];social_context?:Row[];validation?:{defect_challenge:{classes:Row[];method:string;limitations:string[]};fhir_reconciliation:{comparisons:Row[];method:string;population:string};dictionary_nlp:{by_entity:Row[];method:string;source:string;limitations:string[];negation_cases:number;negation_false_positive_cases:number}};uci?:{metrics:Row;method:string;limitations?:string[]};
};
