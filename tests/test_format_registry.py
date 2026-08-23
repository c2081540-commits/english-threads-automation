import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threads_automation.formats import (CANONICAL_FORMATS, COMMON_SYNC_FIELDS,
    FORMAT_REGISTRY, FormatDefinition, FormatValidationError, adapt_dryrun_record,
    build_threads_reply, validate_format_master)
from threads_automation.validation import (ValidationError, validate,
    validate_current_production, validate_historical)

EXPECTED = {"text": True, "visual": True, "difference": True, "pattern": True,
            "error_hunt": False, "save_list": True}


class FormatRegistryTests(unittest.TestCase):
    def test_registry_conformance_and_snapshot_routing(self):
        self.assertEqual(tuple(FORMAT_REGISTRY), CANONICAL_FORMATS)
        self.assertEqual(set(FORMAT_REGISTRY), set(EXPECTED))
        self.assertEqual(len({d.name for d in FORMAT_REGISTRY.values()}), 6)
        for key, definition in FORMAT_REGISTRY.items():
            self.assertIsInstance(definition, FormatDefinition)
            self.assertEqual(key, definition.name)
            self.assertTrue(callable(definition.master_validator))
            self.assertEqual(definition.uses_choices, EXPECTED[key])
            self.assertTrue(definition.sync_fields)
            self.assertTrue(callable(definition.dryrun_adapter))
            self.assertTrue(callable(definition.reply_builder))
            self.assertTrue(callable(definition.reply_validator))
        self.assertTrue(COMMON_SYNC_FIELDS)

    def test_current_and_historical_entry_points_fail_closed(self):
        historical=json.loads((ROOT/"data/master/ENG-000001.json").read_text())
        validate_historical(historical)
        with self.assertRaises(ValidationError): validate_current_production(historical)
        with self.assertRaises(ValidationError): validate_historical(dict(historical,format="unknown_format"))
        with self.assertRaises(ValidationError): validate(dict(historical,format="Text"))
        with self.assertRaises(ValidationError): validate(dict(historical,format="unknown_format"))

    def test_registered_invalid_schema_fails(self):
        invalid={"content_id":"ENG-900001","format":"text"}
        with self.assertRaises((ValidationError,FormatValidationError)):
            validate_current_production(invalid)

    def test_cross_repo_registry_contract_when_workspace_sibling_exists(self):
        sibling=ROOT.parent/"english-instagram-automation/src/instagram_automation/formats.py"
        if not sibling.is_file():
            self.assertEqual(set(FORMAT_REGISTRY), set(EXPECTED))
            return
        spec=importlib.util.spec_from_file_location("instagram_registry_contract", sibling)
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
        self.assertEqual(COMMON_SYNC_FIELDS,module.COMMON_SYNC_FIELDS)
        self.assertEqual({k:(v.uses_choices,v.sync_fields) for k,v in FORMAT_REGISTRY.items()},
                         {k:(v.uses_choices,v.sync_fields) for k,v in module.FORMAT_REGISTRY.items()})

    def test_dummy_format_routes_without_central_code_changes(self):
        calls=[]
        def master(record): calls.append("master")
        def adapter(record,item): record["dummy_value"]=item["dummy_value"]; record["threads_reply"]="yes routed"; calls.append("dryrun")
        def builder(record): calls.append("builder"); return record["threads_reply"]
        def reply(record,text):
            if record["dummy_value"] not in text: raise FormatValidationError("dummy mismatch")
            calls.append("reply")
        definition=FormatDefinition("dummy_format",master,False,("dummy_value",),adapter,builder,reply)
        FORMAT_REGISTRY["dummy_format"]=definition
        try:
            item={"content_id":"ENG-999999","difficulty":"L2","learning_point":"dummy","question":"Dummy?",
                  "correct_answer":"yes","dummy_value":"routed"}
            record=adapt_dryrun_record(item,"2026-08-24T07:00:00+09:00","dummy_format")
            validate_format_master(record)
            self.assertEqual(build_threads_reply(record),"yes routed")
            self.assertEqual(calls,["dryrun","master","builder","reply"])
        finally:
            FORMAT_REGISTRY.pop("dummy_format",None)
        self.assertNotIn("dummy_format",FORMAT_REGISTRY)


if __name__ == "__main__": unittest.main()
