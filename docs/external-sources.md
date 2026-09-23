# External source assets

Retrieved 2026-09-22/23 UTC. These downloads remain outside the Site checkout. `external-summary.json` is safe aggregate output; UCI encounter records must not enter the website bundle. `summarize.mjs` derives the aggregate values, and `checksums.json` identifies downloaded assets.

## UCI Diabetes 130-US Hospitals

- Source: https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008
- Download: https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip
- Files: `uci-diabetes-130/diabetic_data.csv`, `uci-diabetes-130/IDS_mapping.csv`.
- License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.
- Attribution: Clore, J., Cios, K., DeShazo, J., and Strack, B. (2014). Diabetes 130-US Hospitals for Years 1999-2008. UCI Machine Learning Repository. https://doi.org/10.24432/C5230J.
- This is public, de-identified patient-level data, not an aggregate source. Keep isolated for external analysis. It is not synthetic and should never be described as such.
- The delivered CSV contains no actual admission dates, discharge dates, or feature observation timestamps. The encounter ID is an identifier, not proof of time. Real temporal splitting, censoring reconstruction, or time-availability audits cannot be established from this extract.
- Admission-time modeling must exclude discharge disposition, realized length of stay, and other post-admission variables. Synthea feature definitions cannot automatically be presumed equivalent. Training a second model on UCI is a separate benchmark, not external validation of the same locked Synthea model. Repeated patient IDs demand patient-group isolation for any holdout benchmark.

## CMS public hospital benchmarks

- Hospital unplanned visits: https://data.cms.gov/provider-data/dataset/632h-zaca
- National unplanned visits: https://data.cms.gov/provider-data/dataset/cvcs-xecj
- Hospital HCAHPS: https://data.cms.gov/provider-data/dataset/dgck-syfz
- National HCAHPS: https://data.cms.gov/provider-data/dataset/99ue-w85f
- Local CSVs: `CMS_Unplanned_Hospital_Visits-Hospital.csv`, `CMS_Unplanned_Hospital_Visits-National.csv`, `CMS_HCAHPS-Hospital.csv`, `CMS_HCAHPS-National.csv`.
- Exact immutable download URLs and modification/release dates are retained in four `cms-*-metadata.json` files.
- Current metadata: modified 2026-07-22; released 2026-08-13. Readmission measure windows and HCAHPS windows differ, and are retained per measure.
- U.S. government public domain data; cite CMS. CMS reuse guidance: https://data.cms.gov/sites/default/files/2022-12/API%20FAQ%20%20v1_1.pdf.
- `external-summary.json` includes both official national values and separately calculated unweighted hospital-score distributions. A median hospital score is not a national risk-standardized rate.
- Hybrid_HWR hospital-wide readmission is unavailable in this release. Missing or suppressed values remain null. Do not supply a fabricated all-cause national rate.
- CMS risk-standardized disease-specific measures and HCAHPS scores are contextual references, not directly comparable to a crude synthetic system rate or simulated satisfaction metric.

## CDC/ATSDR Social Vulnerability Index

- Official data download: https://svi.cdc.gov/dataDownloads/data-download.html
- Tracts: https://svi.cdc.gov/Documents/Data/2022/csv/states/Massachusetts.csv
- Counties: https://svi.cdc.gov/Documents/Data/2022/csv/states_counties/Massachusetts_county.csv
- Documentation: https://svi.cdc.gov/map25/data/docs/SVI2022Documentation_ZCTA.pdf
- Local files: `CDC_SVI_2022_Massachusetts_tract.csv`, `CDC_SVI_2022_Massachusetts_county.csv`.
- Attribution: CDC/ATSDR GRASP, Social Vulnerability Index 2022, Massachusetts. Source data are available free on the agency site. Use does not imply CDC, ATSDR, HHS, or U.S. government endorsement.
- Federal public domain guidance: https://www.cdc.gov/other/agencymaterials.html. No agency logo is included.
- These state downloads rank tracts against Massachusetts tracts and counties against Massachusetts counties. They are not nationally ranked values. Percentile ranks are relative and should not be compared across vintage years as change measures.
- Geography is an area-level characteristic, not an individual social-risk measurement. A synthetic patient coordinate-to-tract join needs the matching-vintage polygon boundary and point-in-polygon. County joins need county FIPS. Town labels cannot resolve a census tract, and postal ZIP is not identical to Census ZCTA. This task downloaded tabular data, not geometry; a choropleth requires an additional official geometry source.
- Values such as -999 are missing sentinels, not zero risk. No fabricated patient-to-tract assignments are provided.

## NEWS2 mathematical reference

- Official source: https://rcp.ac.uk/resources/national-early-warning-score-news-2/
- Score chart: https://rcp.ac.uk/media/alxev00t/news2-chart-1_the-news-scoring-system_0_0.pdf
- Trigger chart: https://rcp.ac.uk/media/2acdezkd/news2-chart-2_news-thresholds-and-triggers_0.pdf
- Additional guidance: https://rcp.ac.uk/resources/news2-additional-implementation-guidance/
- Local references: `NEWS2-score-chart-RCP.pdf`, `NEWS2-thresholds-RCP.pdf`.
- RCP permits reproduction if acknowledged, unchanged, in color, using the high-quality original chart. Link to the original rather than creating an altered chart with RCP branding.
- Scale 1: respiration <=8:3, 9-11:1, 12-20:0, 21-24:2, >=25:3; SpO2 <=91:3, 92-93:2, 94-95:1, >=96:0; supplemental oxygen adds 2; systolic BP <=90:3, 91-100:2, 101-110:1, 111-219:0, >=220:3; pulse <=40:3, 41-50:1, 51-90:0, 91-110:1, 111-130:2, >=131:3; consciousness alert:0, new confusion or voice/pain/unresponsive:3; temperature <=35.0:3, 35.1-36.0:1, 36.1-38.0:0, 38.1-39.0:1, >=39.1:2.
- Aggregate risk 0-4 low, 5-6 medium, >=7 high; any individual component of 3 is a separate escalation trigger. Do not hide it behind the total.
- Scale 2 is for appropriate patients with confirmed hypercapnic respiratory failure under clinical direction. Do not infer scale 2 from COPD alone. Its oxygen band logic differs.
- Missing oxygen status or consciousness cannot silently mean air or alert. Mark the score incomplete. A score computation does not establish a validated deterioration model or calibration.

## CKD-EPI 2021 creatinine equation

- Official NIDDK source: https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/adults
- Adults >=18 years. SCr in mg/dL; age in years; output mL/min/1.73m2.
- eGFR = 142 * min(SCr/kappa,1)^alpha * max(SCr/kappa,1)^(-1.200) * 0.9938^age * (1.012 if female).
- kappa: 0.7 female, 0.9 male. alpha: -0.241 female, -0.302 male. Convert micromol/L creatinine to mg/dL by dividing by 88.4. No race coefficient.
- This is an estimate. Avoid deriving clinical CKD diagnoses from a single result; missing sex, age, or standardized creatinine must produce unavailable output. The creatinine-cystatin C equation is preferred when available.

All clinical computations are a synthetic portfolio demonstration, not validated for clinical decisions.
