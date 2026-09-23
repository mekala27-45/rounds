"""Known-answer challenge tests; no external service or actual patient text."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

import build_validation as build


def fixture():
    return {
        "persons": {"fixture-person"},
        "conditions": [{"PATIENT": "fixture-person", "SYSTEM": "SNOMED-CT", "CODE": "x"}],
        "observations": [{"PATIENT": "fixture-person", "TYPE": "numeric", "CODE": "8867-4", "VALUE": "80", "UNITS": "/min"} for _ in range(2)],
        "encounters": [{"Id": "fixture-visit-"+str(i), "PATIENT": "fixture-person", "START": "2020-01-01T00:00:00Z", "STOP": "2020-01-02T00:00:00Z"} for i in range(2)],
        "medications": [{"PATIENT": "fixture-person"}],
        "notes": [{"text": "A synthetic fixture with no identifiers."}],
    }


class ChallengeTests(unittest.TestCase):
    def test_clean_pass(self):
        self.assertEqual(build.audit_challenge(fixture()), [])

    def test_each_deliberate_violation(self):
        for defect, expected_rule in build.RULES.items():
            with self.subTest(defect=defect):
                findings = build.audit_challenge(build.inject(fixture(), defect))
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["rule"], expected_rule)

    def test_empty_refuses(self):
        for empty in [{}, {"persons": set()}, {**fixture(), "conditions": []}]:
            with self.assertRaises(ValueError):
                build.audit_challenge(empty)

    def test_injection_does_not_modify_source_copy(self):
        clean = fixture()
        original = copy.deepcopy(clean)
        build.inject(clean, "missing_encounter_end")
        self.assertEqual(clean, original)

    def test_combined_quarantine_removes_every_challenge(self):
        data = fixture()
        for defect in build.RULES:
            data = build.inject(data, defect)
        # Add clean rows so the post-quarantine fixture has nonempty tables.
        for table in ["conditions", "observations", "medications"]:
            data[table].extend(fixture()[table])
        findings = build.audit_challenge(data)
        self.assertEqual(len(findings), len(build.RULES))
        self.assertFalse(build.audit_challenge(build.quarantine(data, findings)))

    def test_each_identifier_form_detected_independently(self):
        for text in ["VALIDATION_"+"PERSON_SENTINEL", "202-555-0149", "MRN 987654321"]:
            data = fixture()
            data["notes"][0]["text"] = text
            self.assertEqual(build.audit_challenge(data)[0]["rule"], build.RULES["planted_identifiers"])

    def test_units_only_required_for_numeric_measurement(self):
        data = fixture()
        data["observations"][0] = {"TYPE": "text", "CODE": "fixture-text", "UNITS": "", "VALUE": "normal"}
        self.assertFalse(build.audit_challenge(data))


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def paired_fixture(root):
    (root / "csv").mkdir()
    (root / "fhir").mkdir()
    write_csv(root / "csv/patients.csv", [{"Id": "fixture-person"}])
    write_csv(root / "csv/encounters.csv", [{"Id": "fixture-visit", "PATIENT": "fixture-person"}])
    conditions = [{"PATIENT": "fixture-person", "ENCOUNTER": "fixture-visit", "CODE": "fixture-code", "START": "2020-01-01", "STOP": ""}] * 2
    write_csv(root / "csv/conditions.csv", conditions)
    condition = {"resourceType": "Condition", "subject": {"reference": "urn:uuid:fixture-person"},
                 "encounter": {"reference": "urn:uuid:fixture-visit"},
                 "code": {"coding": [{"system": "http://snomed.info/sct", "code": "fixture-code"}]},
                 "onsetDateTime": "2020-01-01T12:00:00Z"}
    resources = [{"resourceType": "Patient", "id": "fixture-person"},
                 {"resourceType": "Encounter", "id": "fixture-visit", "subject": {"reference": "urn:uuid:fixture-person"}},
                 condition, copy.deepcopy(condition)]
    path = root / "fhir/fixture.json"
    path.write_text(json.dumps({"resourceType": "Bundle", "entry": [{"resource": r} for r in resources]}), encoding="utf-8")
    return path


class ReconcileTests(unittest.TestCase):
    def test_equal_multisets_and_day_precision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paired_fixture(root)
            report = build.reconcile(root, 1, seed=20260923)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["comparisons"][2]["fhir_rows"], 2)
            self.assertEqual(report["seed"], 20260923)
            self.assertIn("seed 20260923", report["population"])

    def test_record_count_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = paired_fixture(root)
            bundle = json.loads(path.read_text())
            bundle["entry"].pop()
            path.write_text(json.dumps(bundle))
            report = build.reconcile(root, 1)
            self.assertEqual(report["status"], "mismatch")
            self.assertEqual(report["comparisons"][2]["csv_only"], 1)

    def test_code_identity_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = paired_fixture(root)
            bundle = json.loads(path.read_text())
            bundle["entry"][-1]["resource"]["code"]["coding"][0]["code"] = "different-code"
            path.write_text(json.dumps(bundle))
            result = build.reconcile(root, 1)["comparisons"][2]
            self.assertEqual(result["csv_only"], 1)
            self.assertEqual(result["fhir_only"], 1)

    def test_empty_bundles_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fhir").mkdir()
            with self.assertRaises(ValueError):
                build.reconcile(root, 1)


class NLPTests(unittest.TestCase):
    lexicon = {"condition": [{"description": "Example disorder", "code": "example"},
                              {"description": "Secondary disease", "code": "secondary"}]}

    def test_positive_known_label(self):
        self.assertEqual(build.extract("Documented Example disorder.", self.lexicon), {("condition", "example")})

    def test_twenty_negation_cases(self):
        prefixes = ["No evidence of", "Patient denies", "Without", "Negative for", "Ruled out"]
        for i in range(20):
            self.assertFalse(build.extract(prefixes[i % 5] + " Example disorder.", self.lexicon))

    def test_negation_scope_stops_at_sentence_boundary(self):
        text = "No Example disorder. Secondary disease is documented."
        self.assertEqual(build.extract(text, self.lexicon), {("condition", "secondary")})

    def test_negation_scope_stops_at_but(self):
        text = "No Example disorder but Secondary disease is documented."
        self.assertEqual(build.extract(text, self.lexicon), {("condition", "secondary")})

    def test_empty_text_is_not_a_positive(self):
        self.assertFalse(build.extract("", self.lexicon))

    def test_dictionary_boundaries(self):
        self.assertFalse(build.extract("Example disorders", self.lexicon))

    def test_longest_same_entity_mention_wins(self):
        lexicon = {"condition": [{"description": "disease", "code": "short"},
                                 {"description": "Example disease", "code": "long"}]}
        self.assertEqual(build.extract("Example disease", lexicon), {("condition", "long")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
