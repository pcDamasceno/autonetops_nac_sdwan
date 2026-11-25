#!/usr/bin/env python3
"""Self-check for fetch_artifact.py. Usage: python scripts/test_fetch_artifact.py"""

import hashlib
import json
import os
import tempfile
import unittest
from unittest import mock

with mock.patch.dict(os.environ, {"INFRAHUB_ADDRESS": "http://infrahub.invalid", "INFRAHUB_API_TOKEN": "x"}):
    import fetch_artifact

CONTENT = b"sdwan: {}\n"
MD5 = hashlib.md5(CONTENT).hexdigest()


class FetchArtifact(unittest.TestCase):
    def run_main(self, status="Ready", checksum=MD5, target=None, errors=None):
        """Return (exit code, files written) for a fake Infrahub answer."""
        node = {"id": "a1", "status": {"value": status}, "checksum": {"value": checksum},
                "storage_id": {"value": "s1"},
                "object": {"node": {"id": "t1", "display_label": target or fetch_artifact.INSTANCE}}}
        body = {"errors": errors, "data": {"CoreArtifact": {"edges": [{"node": node}]}}}

        def request(path, payload=None):
            return json.dumps(body).encode() if path.startswith("/graphql/") else CONTENT

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(fetch_artifact, "OUTPUT", os.path.join(d, "m.yaml")), \
                mock.patch.object(fetch_artifact, "request", request):
            code = fetch_artifact.main()
            written = {}
            for name in os.listdir(d):
                with open(os.path.join(d, name), "rb") as fh:
                    written[name] = fh.read()
            return code, written

    def test_good(self):
        code, written = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(written["m.yaml"], CONTENT)
        self.assertEqual(json.loads(written[".artifact.json"])["checksum"], MD5)

    def test_refusals_write_nothing(self):
        for case in ({"status": "Error"}, {"checksum": "bad"}, {"target": "other"},
                     {"errors": [{"message": "no"}]}):
            with self.subTest(**case):
                self.assertEqual(self.run_main(**case), (1, {}))


if __name__ == "__main__":
    unittest.main()
