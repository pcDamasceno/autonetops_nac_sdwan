#!/usr/bin/env python3
"""Self-check for check_refs.py. Usage: python scripts/test_check_refs.py"""

import copy
import os
import tempfile
import unittest

import yaml

from check_refs import main

GOOD = {
    "feature_profiles": {
        "system_profiles": [{"name": "sys"}],
        "application_priority_profiles": [{"name": "ap"}],
        "ngfw_security_profiles": [{"name": "fw"}],
        "sse_profiles": [{"name": "sse"}],
        "topology_profiles": [{"name": "topo"}],
    },
    "configuration_groups": [{"name": "cg", "system_profile": "sys"}],
    "policy_groups": [{"name": "pg", "application_priority": "ap", "ngfw_security": "fw", "sse": "sse"}],
    "topology_groups": [{"name": "tg", "topology_profile": "topo"}],
    "sites": [{"id": 1, "routers": [{"chassis_id": "r1", "configuration_group": "cg", "policy_group": "pg"}]}],
}


def check(doc) -> int:
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.yaml")
        with open(path, "w") as fh:
            yaml.safe_dump(doc, fh)
        return main([path])


class CheckRefs(unittest.TestCase):
    def test_good(self):
        self.assertEqual(check({"sdwan": GOOD}), 0)

    def test_empty(self):
        for doc in (None, {}, {"sdwan": None}, {"sdwan": {}}):
            with self.subTest(doc=doc):
                self.assertEqual(check(doc), 1)
        for key in ("configuration_groups", "sites"):
            with self.subTest(missing=key):
                model = copy.deepcopy(GOOD)
                model[key] = []
                if key == "configuration_groups":
                    del model["sites"][0]["routers"][0]["configuration_group"]
                self.assertEqual(check({"sdwan": model}), 1)

    def test_bad_refs(self):
        for coll, ref in (("configuration_groups", "system_profile"), ("policy_groups", "application_priority"),
                          ("policy_groups", "ngfw_security"), ("policy_groups", "sse"),
                          ("topology_groups", "topology_profile")):
            with self.subTest(ref=ref):
                model = copy.deepcopy(GOOD)
                model[coll][0][ref] = "gone"
                self.assertEqual(check({"sdwan": model}), 1)
        for ref in ("configuration_group", "policy_group"):
            with self.subTest(router=ref):
                model = copy.deepcopy(GOOD)
                model["sites"][0]["routers"][0][ref] = "gone"
                self.assertEqual(check({"sdwan": model}), 1)

    def test_nulls(self):
        model = copy.deepcopy(GOOD)
        model["configuration_groups"][0].update(cli_profile=None, policy_object_profile=None)
        model["sites"].append({"id": 2, "routers": None})
        self.assertEqual(check({"sdwan": model}), 0)
        for key in GOOD:
            with self.subTest(null=key):
                model = copy.deepcopy(GOOD)
                model[key] = None
                self.assertEqual(check({"sdwan": model}), 1 if key != "topology_groups" else 0)


if __name__ == "__main__":
    unittest.main()
