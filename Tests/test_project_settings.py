import importlib.util
from pathlib import Path
import unittest


path = Path(__file__).resolve().parents[1] / 'scripts/check_project_settings.py'
spec = importlib.util.spec_from_file_location('project_settings', path)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ProjectSettingsTests(unittest.TestCase):
    def settings(self):
        return [{'target': target, 'buildSettings': {'PRODUCT_BUNDLE_IDENTIFIER': bundle_id}}
                for target, bundle_id in checker.EXPECTED.items()]

    def test_valid_identifiers(self):
        checker.validate(self.settings())

    def test_empty_identifier_rejected(self):
        settings = self.settings()
        settings[1]['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'] = ''
        with self.assertRaises(ValueError):
            checker.validate(settings)

    def test_missing_extension_rejected(self):
        with self.assertRaises(ValueError):
            checker.validate(self.settings()[:-1])
