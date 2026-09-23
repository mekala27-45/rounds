# Rounds synthetic source data

All patient records here were generated locally by the official open-source Synthea simulator. No real patient data was used.

- `population-2000/csv/`: 2,000 Massachusetts patients, complete exported lifetimes; 1,825 alive and 175 deceased at the fixed end date.
- `sample-300/csv/` and `sample-300/fhir/`: 300 patients generated with the same seed, complete CSV and FHIR R4 transaction bundles; 276 alive and 24 deceased. Practitioner and hospital bundles are included.
- `provenance.json`: exact source, versions, checksums, record counts, date ranges, and CSV/FHIR identity checks.
- `population-2000.log`, `sample-300.log`: complete simulator output.
- `audit-data.mjs`: streaming CSV audit and FHIR identity/resource audit.

The 2,000-patient CSV export is approximately 3 GB; the 300-patient FHIR export is approximately 2.9 GB. Build compact derived analytics and patient timelines for a web deployment instead of bundling these complete raw histories.

## Pinned inputs

- Official [Synthea release](https://github.com/synthetichealth/synthea/releases/tag/master-branch-latest), published 2026-08-18, build `d9d07a6`.
- Synthea SHA-256: `018ad7f04f7aacb995804d7d4781c76d5fc714f7f23257ba50daa9eefae224ac`.
- Official [Temurin JRE 17.0.20.1+1](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.20.1%2B1).
- Temurin ZIP SHA-256: `bc21a93923103cdaac93ee337b0ae4365e739fde36df823dd456bc67c8a9d352`.
- Both binary checksums were verified against official release metadata.
- Patient and clinician seeds: `20260923`; reference and simulation end: `2026-09-22`; state: Massachusetts.
- `-o false` avoids excess patients from replacement generation; the output includes living and deceased records.
- `exporter.years_of_history=0` preserves all available history, as documented in [Synthea configuration](https://github.com/synthetichealth/synthea/wiki/Common-Configuration).

## Generation commands (PowerShell)

Run from this directory. Re-running may replace output files in the configured output folders.

```powershell
& '.\java\jdk-17.0.20.1+1-jre\bin\java.exe' -Xmx4g -jar '.\synthea-with-dependencies.jar' -s 20260923 -cs 20260923 -p 2000 -r 20260922 -e 20260922 -o false --exporter.baseDirectory=./population-2000 --exporter.years_of_history=0 --exporter.csv.export=true --exporter.fhir.export=false --exporter.hospital.fhir.export=false --exporter.practitioner.fhir.export=false --generate.thread_pool_size=4 Massachusetts

& '.\java\jdk-17.0.20.1+1-jre\bin\java.exe' -Xmx3g -jar '.\synthea-with-dependencies.jar' -s 20260923 -cs 20260923 -p 300 -r 20260922 -e 20260922 -o false --exporter.baseDirectory=./sample-300 --exporter.years_of_history=0 --exporter.csv.export=true --exporter.fhir.export=true --exporter.hospital.fhir.export=true --exporter.practitioner.fhir.export=true --generate.thread_pool_size=2 Massachusetts

node .\audit-data.mjs
```

Use [Synthea's CSV data dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary) for field definitions. The main run produces a warning about excluded organization and practitioner FHIR bundles even though patient FHIR is disabled there; the separate FHIR run includes all three bundle types.
