import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "capability_scan", Path(__file__).resolve().parents[1] / "scripts/inspect_xcode_capabilities.py")
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)


class CapabilityScanTests(unittest.TestCase):
    def test_xcode27_snapshot_retains_supported_team_and_profile_requirements(self):
        path = Path(__file__).parent / "fixtures/xcode27-accessory-capabilities.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        records = list(SCAN.matching_records(snapshot))
        self.assertEqual(len(records), 3)
        for record in records:
            attributes = record["definition"]["attributes"]
            self.assertEqual(set(attributes["validTeamTypes"]), {
                "APPLE_DEVELOPER_PROGRAM", "APPLE_DEVELOPER_ENTERPRISE_PROGRAM"})
            self.assertTrue(attributes["entitlements"][0]["isRequiredInPlist"])
            self.assertFalse(attributes["enabledByDefault"])

    def test_keeps_capability_identifier_and_eligibility_conditions(self):
        capability = {"id": "EXAMPLE_ACCESSORY", "type": "capabilities", "attributes": {
            "supportedSDKs": ["ios"], "entitlements": [
                {"profileKey": "com.apple.developer.accessory-data-provider", "isRequiredInPlist": True}]}}
        records = list(SCAN.matching_records({"data": [capability]}))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["definition"], capability)

    def test_preserves_signing_rules_for_a_matching_entitlement(self):
        metadata = {"items": [{"Entitlement": "com.apple.developer.accessory-data-provider",
                               "RequiresProfile": False, "Supported": True}]}
        records = list(SCAN.matching_records(metadata))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["key_path"], ["items", "0"])
        self.assertIs(records[0]["definition"]["RequiresProfile"], False)

    def test_matches_dictionary_keys(self):
        metadata = {"rules": {"com.apple.developer.accessory-transport-security": {"type": "bool"}}}
        self.assertEqual(list(SCAN.matching_records(metadata))[0]["key_path"], ["rules"])

    def test_ignores_unrelated_definitions(self):
        self.assertEqual(list(SCAN.matching_records({"application-identifier": "example"})), [])
