"""Reproduce bounded Synthea challenge, interoperability, and lexical evidence.

Only aggregate evidence is published. Raw identities and planted text stay in
memory. This is not a claim of clinical validation or production de-identification.
"""
from __future__ import annotations

import argparse
import os
import copy
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("ROUNDS_SOURCE_ROOT",HERE.parent/"data"/"source"))
STATEMENT = (
    "This is a portfolio demonstration on synthetic data. It is not a medical "
    "device, has not been validated for clinical use, and must not be used to "
    "make decisions about real patients."
)
RULES = {
    "local_condition_code": "condition_standard_system",
    "missing_measurement_unit": "measurement_numeric_unit_required",
    "implausible_heart_rate": "measurement_heart_rate_range_20_250",
    "duplicate_encounter": "encounter_unique_id",
    "orphan_medication": "medication_person_foreign_key",
    "missing_encounter_end": "encounter_end_required",
    "planted_identifiers": "free_text_identifier_pattern",
}


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.DictReader(handle)


def digest(value: str) -> str:
    return hashlib.sha256(("rounds-private-validation:" + value).encode()).hexdigest()[:24]


def baseline_slice(root: Path) -> dict:
    """Copy a bounded, valid slice; never edit the original Synthea exports."""
    patient_ids = {r["Id"] for r in csv_rows(root / "patients.csv")}
    persons = {digest(p) for p in patient_ids}
    selected = {}
    for table, limit in [("conditions", 80), ("encounters", 80), ("medications", 80), ("observations", 80)]:
        rows = []
        for row in csv_rows(root / (table + ".csv")):
            if row["PATIENT"] not in patient_ids:
                continue
            if table == "conditions" and row["SYSTEM"] != "SNOMED-CT":
                continue
            if table == "encounters" and not row["STOP"]:
                continue
            if table == "observations":
                if row["CODE"] != "8867-4" or not row["UNITS"]:
                    continue
                try:
                    if not 20 <= float(row["VALUE"]) <= 250:
                        continue
                except ValueError:
                    continue
            allowed = {"Id", "PATIENT", "SYSTEM", "CODE", "START", "STOP", "VALUE", "UNITS", "TYPE"}
            clean = {k: v for k, v in row.items() if k in allowed}
            clean["PATIENT"] = digest(row["PATIENT"])
            if "Id" in clean:
                clean["Id"] = digest(clean["Id"])
            rows.append(clean)
            if len(rows) == limit:
                break
        if len(rows) < limit:
            raise ValueError("Insufficient source rows for bounded challenge: " + table)
        selected[table] = rows
    selected["persons"] = persons
    selected["notes"] = [{"text": "Synthetic validation fixture. No identifiers present."}]
    return selected


def identifier_patterns():
    # Planted names are constructed, not copied from records. This is an exact
    # sentinel challenge, not an open-ended name recognition/privacy guarantee.
    planted_name = "VALIDATION_" + "PERSON_SENTINEL"
    return [re.compile(re.escape(planted_name), re.I),
            re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b"),
            re.compile(r"\bMRN[- :]*\d{6,}\b", re.I)]


def audit_challenge(data: dict) -> list[dict]:
    if not data or not data.get("persons") or not all(data.get(k) for k in ["conditions", "observations", "encounters", "medications"]):
        raise ValueError("Challenge refuses empty or missing required input tables")
    findings = []

    def flag(table, index, rule):
        findings.append({"table": table, "row_index": index, "rule": rule})

    for i, row in enumerate(data["conditions"]):
        if row.get("SYSTEM") != "SNOMED-CT":
            flag("conditions", i, RULES["local_condition_code"])
    for i, row in enumerate(data["observations"]):
        if row.get("TYPE") == "numeric" and not row.get("UNITS"):
            flag("observations", i, RULES["missing_measurement_unit"])
        if row.get("CODE") == "8867-4":
            try:
                valid = 20 <= float(row["VALUE"]) <= 250
            except (ValueError, KeyError):
                valid = False
            if not valid:
                flag("observations", i, RULES["implausible_heart_rate"])
    seen = set()
    for i, row in enumerate(data["encounters"]):
        if row.get("Id") in seen:
            flag("encounters", i, RULES["duplicate_encounter"])
        seen.add(row.get("Id"))
        if not row.get("STOP"):
            flag("encounters", i, RULES["missing_encounter_end"])
    for i, row in enumerate(data["medications"]):
        if row.get("PATIENT") not in data["persons"]:
            flag("medications", i, RULES["orphan_medication"])
    for i, row in enumerate(data.get("notes", [])):
        if any(pattern.search(row["text"]) for pattern in identifier_patterns()):
            flag("notes", i, RULES["planted_identifiers"])
    return findings


def inject(base: dict, defect: str) -> dict:
    data = copy.deepcopy(base)
    if defect == "local_condition_code":
        data["conditions"][0]["SYSTEM"] = "LOCAL-CHALLENGE"
    elif defect == "missing_measurement_unit":
        data["observations"][0]["UNITS"] = ""
    elif defect == "implausible_heart_rate":
        data["observations"][1]["VALUE"] = "400"
    elif defect == "duplicate_encounter":
        duplicate = copy.deepcopy(data["encounters"][0])
        duplicate["START"] = duplicate["START"][:10] + "T01:00:00Z"
        data["encounters"].append(duplicate)
    elif defect == "orphan_medication":
        data["medications"][0]["PATIENT"] = "private-orphan-sentinel"
    elif defect == "missing_encounter_end":
        data["encounters"][1]["STOP"] = ""
    elif defect == "planted_identifiers":
        data["notes"][0]["text"] = "VALIDATION_" + "PERSON_SENTINEL; " + "202-555-0149; MRN 987654321"
    else:
        raise ValueError("Unknown challenge class")
    return data


def quarantine(data: dict, findings: list[dict]) -> dict:
    rejected = {(f["table"], f["row_index"]) for f in findings}
    return {table: ([row for i, row in enumerate(rows) if (table, i) not in rejected]
                    if isinstance(rows, list) else copy.deepcopy(rows))
            for table, rows in data.items()}


def defect_evidence(root: Path) -> dict:
    baseline = baseline_slice(root)
    if audit_challenge(baseline):
        raise AssertionError("Selected clean baseline does not pass")
    rows = []
    combined = baseline
    for defect, rule in RULES.items():
        findings = audit_challenge(inject(baseline, defect))
        detected = any(f["rule"] == rule for f in findings)
        rows.append({"class": defect, "rule": rule, "injected_rows": 1,
                     "detected_rows": sum(f["rule"] == rule for f in findings),
                     "passed": detected})
        combined = inject(combined, defect)
    findings = audit_challenge(combined)
    sanitized = quarantine(combined, findings)
    empty_refused = False
    try:
        audit_challenge({})
    except ValueError:
        empty_refused = True
    return {
        "status": "passed" if all(r["passed"] for r in rows) and not audit_challenge(sanitized) and empty_refused else "failed",
        "kind": "deliberately_injected_challenge_not_source_quality_rate",
        "source": "Synthea population-2000 CSV copied slices",
        "baseline_rows": {k: len(v) for k, v in baseline.items() if k != "persons"},
        "classes": rows, "class_count": len(rows),
        "detected_class_count": sum(r["passed"] for r in rows),
        "combined_quarantined_rows": len({(f["table"], f["row_index"]) for f in findings}),
        "clean_baseline_findings": 0, "post_quarantine_findings": len(audit_challenge(sanitized)),
        "empty_input_refused": empty_refused,
        "method": "Seven independent one-row challenges plus a combined challenge. Duplicate IDs are quarantined on the subsequent occurrence. Identifier class contains a planted name sentinel, phone and MRN. Source exports are not modified.",
        "limitations": ["The selected clean baseline is not an estimate of original source quality.", "Seven classes include three identifier forms within one text class.", "Exact planted-name matching does not establish general name removal or HIPAA compliance.", "Heart-rate bounds are challenge thresholds, not clinical alerting thresholds."],
    }


def reference_id(value: str) -> str:
    return value.rsplit("/", 1)[-1].removeprefix("urn:uuid:")


def normalized_date(value: str | None) -> str:
    return (value or "")[:10]


def reconcile(root: Path, patient_limit: int, seed: int | None = None) -> dict:
    fhir = {"Patient": Counter(), "Encounter": Counter(), "Condition": Counter()}
    selected = set()
    patient_files = 0
    files_read = 0
    for path in sorted((root / "fhir").glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        resources = [entry.get("resource", {}) for entry in bundle.get("entry", [])]
        patients = [r for r in resources if r.get("resourceType") == "Patient"]
        files_read += 1
        if not patients:
            continue
        patient_files += 1
        for patient in patients:
            selected.add(patient["id"])
            fhir["Patient"][patient["id"]] += 1
        for resource in resources:
            kind = resource.get("resourceType")
            if kind == "Encounter":
                fhir[kind][(resource["id"], reference_id(resource["subject"]["reference"]))] += 1
            elif kind == "Condition":
                coding = [c for c in resource.get("code", {}).get("coding", []) if c.get("system") == "http://snomed.info/sct"]
                for code in coding:
                    key = (reference_id(resource["subject"]["reference"]),
                           reference_id(resource.get("encounter", {}).get("reference", "")),
                           code["code"], normalized_date(resource.get("onsetDateTime")),
                           normalized_date(resource.get("abatementDateTime")))
                    fhir[kind][key] += 1
        if patient_files >= patient_limit:
            break
    if not selected:
        raise ValueError("No patient-bearing FHIR bundles found")
    csv_data = {"Patient": Counter(), "Encounter": Counter(), "Condition": Counter()}
    total_csv_patients = 0
    for row in csv_rows(root / "csv" / "patients.csv"):
        total_csv_patients += 1
        if row["Id"] in selected:
            csv_data["Patient"][row["Id"]] += 1
    for row in csv_rows(root / "csv" / "encounters.csv"):
        if row["PATIENT"] in selected:
            csv_data["Encounter"][(row["Id"], row["PATIENT"])] += 1
    for row in csv_rows(root / "csv" / "conditions.csv"):
        if row["PATIENT"] in selected:
            key = (row["PATIENT"], row["ENCOUNTER"], row["CODE"], normalized_date(row["START"]), normalized_date(row["STOP"]))
            csv_data["Condition"][key] += 1
    comparisons = []
    for kind in fhir:
        a, b = fhir[kind], csv_data[kind]
        comparisons.append({"resource": kind, "fhir_rows": sum(a.values()),
                            "csv_rows": sum(b.values()), "fhir_only": sum((a-b).values()),
                            "csv_only": sum((b-a).values()), "exact_multiset_match": a == b})
    return {
        "status": "passed" if all(r["exact_multiset_match"] for r in comparisons) else "mismatch",
        "population": "Synthea sample-300 paired exporter run" + (f", seed {seed}" if seed is not None else ""),
        "seed": seed,
        "source_csv_patients": total_csv_patients, "patient_bundles_evaluated": patient_files,
        "patients_evaluated": len(selected), "resource_scope": list(fhir), "comparisons": comparisons,
        "coverage": "all_csv_patients" if len(selected) == total_csv_patients else "bounded_slice",
        "method": ("All patient-bearing bundles in the paired run. " if len(selected) == total_csv_patients else "Deterministic first patient-bearing bundles sorted by source filename. ") + "Multiset reconciliation: Patient ID; Encounter ID and patient; Condition patient, encounter, SNOMED code, onset date and abatement date. Timestamps are normalized to calendar date for Condition because CSV dates have day precision.",
        "limitations": ([] if len(selected) == total_csv_patients else ["This bounded slice is not a random or representative sample."]) + ["This checks source-export identities and record counts; it does not validate complete FHIR schemas or certify an OMOP transformation.", "Observation, medications, procedures, claims and other resource types are not included.", "No raw identifiers or source filenames are published in this report."],
    }


def terminology(root: Path, maximum: int = 100) -> dict:
    lexicon = {}
    for entity, table in [("condition", "conditions"), ("medication", "medications"), ("procedure", "procedures")]:
        seen = set()
        entries = []
        for row in csv_rows(root / (table + ".csv")):
            description = row["DESCRIPTION"].strip()
            key = description.casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            entries.append({"entity": entity, "code": row["CODE"], "description": description})
            if len(entries) >= maximum:
                break
        lexicon[entity] = entries
    return lexicon


def extract(text: str, lexicon: dict) -> set[tuple[str, str]]:
    candidates = []
    for entity, entries in lexicon.items():
        for entry in entries:
            pattern = r"(?<!\w)" + re.escape(entry["description"]) + r"(?!\w)"
            for match in re.finditer(pattern, text, re.I):
                prefix = text[max(0, match.start()-100):match.start()].lower()
                scope = re.split(r"[.;!?]|\bbut\b|\bhowever\b", prefix)[-1]
                negated = bool(re.search(r"\b(no|denies|without|negative for|ruled out|absence of)\b", scope))
                if not negated:
                    candidates.append((match.start(), match.end(), entity, entry["code"]))
    # Prefer the longest overlapping dictionary mention of the same entity type.
    kept = []
    for candidate in sorted(candidates, key=lambda c: c[1]-c[0], reverse=True):
        if not any(candidate[2] == old[2] and candidate[0] < old[1] and old[0] < candidate[1] for old in kept):
            kept.append(candidate)
    return {(c[2], c[3]) for c in kept}


def nlp_evidence(root: Path) -> dict:
    lexicon = terminology(root)
    positive = []
    for entity, entries in lexicon.items():
        for entry in entries[:40]:
            text = "Structured record describes " + entry["description"] + "."
            positive.append((text, {(entity, entry["code"])}))
    patterns = ["No evidence of {}.", "Patient denies {}.", "Without {}.", "Negative for {}.", "Ruled out {}."]
    negative = [(patterns[i % len(patterns)].format(entry["description"]), set())
                for i, entry in enumerate(lexicon["condition"][:20])]
    scores = []
    for entity in lexicon:
        tp = fp = fn = 0
        for text, expected in positive + negative:
            truth = {key for key in expected if key[0] == entity}
            predicted = {key for key in extract(text, lexicon) if key[0] == entity}
            tp += len(truth & predicted)
            fp += len(predicted - truth)
            fn += len(truth - predicted)
        precision = tp / (tp+fp) if tp+fp else 0.0
        recall = tp / (tp+fn) if tp+fn else 0.0
        scores.append({"entity": entity, "true_positive": tp, "false_positive": fp, "false_negative": fn,
                       "precision": round(precision, 6), "recall": round(recall, 6),
                       "f1": round(2*precision*recall/(precision+recall), 6) if precision+recall else 0.0})
    neg_fp = sum(bool(extract(text, lexicon)) for text, _ in negative)
    return {
        "status": "evaluated", "path": "dictionary_and_rules",
        "source": "Synthea CSV structured descriptions, not actual clinical notes",
        "lexicon_entries": {k: len(v) for k,v in lexicon.items()},
        "positive_cases": len(positive), "negation_cases": len(negative),
        "negation_false_positive_cases": neg_fp,
        "negation_false_positive_rate": neg_fp / len(negative), "by_entity": scores,
        "method": "Exact dictionary mentions and longest overlapping spans, with sentence-local negation triggers. Labels are the source table type and structured code, never an LLM assessment. Positive sentences and twenty planted negative sentences are generated from structured descriptions.",
        "limitations": ["This is a lexical extraction sanity check on exact source descriptions, not independent clinical NLP validation.", "The evaluation vocabulary is present in the dictionary; no held-out vocabulary generalization is claimed.", "Templated sentence scores cannot estimate accuracy on real notes, abbreviations, spelling variation, uncertainty or complex negation."],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fhir-patients", type=int, default=300)
    args = parser.parse_args()
    if args.fhir_patients < 1:
        parser.error("--fhir-patients must be positive")
    csv_root = DATA / "population-2000" / "csv"
    source_provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    seed = int(source_provenance["seed"])
    report = {"schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
              "statement": STATEMENT, "synthetic": True,
              "defect_challenge": defect_evidence(csv_root),
              "fhir_reconciliation": reconcile(DATA / "sample-300", args.fhir_patients, seed=seed),
              "dictionary_nlp": nlp_evidence(csv_root)}
    target = HERE / "validation.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(target), "defect_challenge": report["defect_challenge"]["status"],
                      "fhir_reconciliation": report["fhir_reconciliation"]["status"],
                      "fhir_patients": report["fhir_reconciliation"]["patients_evaluated"],
                      "nlp_positive_cases": report["dictionary_nlp"]["positive_cases"],
                      "nlp_negation_cases": report["dictionary_nlp"]["negation_cases"]}))


if __name__ == "__main__":
    main()
