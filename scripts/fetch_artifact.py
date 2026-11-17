#!/usr/bin/env python3
"""Download a rendered Infrahub artifact into data/ for NAC.

Finds the artifact `ARTIFACT_NAME` whose target is `SDWAN_INSTANCE`, refuses
anything that is not `Ready`, verifies the stored checksum and writes the YAML
to `OUTPUT` (default data/sdwan.nac.yaml). Also writes data/.artifact.json with
the provenance (artifact id, checksum, branch) so the plan can be traced back
to the exact Infrahub render.

Stdlib only, so it runs in any python image.

Env:
  INFRAHUB_ADDRESS   e.g. http://infrahub-infrahub-server-1:8000
  INFRAHUB_API_TOKEN API token (CI variable, masked)
  INFRAHUB_BRANCH    default: main
  ARTIFACT_NAME      default: sdwan-nac
  SDWAN_INSTANCE     default: sdwan-manager
  OUTPUT             default: data/sdwan.nac.yaml
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

ADDRESS = os.environ["INFRAHUB_ADDRESS"].rstrip("/")
TOKEN = os.environ["INFRAHUB_API_TOKEN"]
BRANCH = os.environ.get("INFRAHUB_BRANCH", "main")
ARTIFACT = os.environ.get("ARTIFACT_NAME", "sdwan-nac")
INSTANCE = os.environ.get("SDWAN_INSTANCE", "sdwan-manager")
OUTPUT = os.environ.get("OUTPUT", "data/sdwan.nac.yaml")

QUERY = """
query ($name: String!) {
  CoreArtifact(name__value: $name) {
    edges { node {
      id
      status { value }
      checksum { value }
      storage_id { value }
      object { node { id display_label } }
    } }
  }
}
"""


def request(path: str, payload: dict | None = None) -> bytes:
    url = f"{ADDRESS}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "X-INFRAHUB-KEY": TOKEN,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> int:
    branch = urllib.parse.quote(BRANCH)
    body = json.loads(request(f"/graphql/{branch}", {"query": QUERY, "variables": {"name": ARTIFACT}}))
    if body.get("errors"):
        print(f"GraphQL error: {body['errors']}", file=sys.stderr)
        return 1

    matches = [
        e["node"] for e in body["data"]["CoreArtifact"]["edges"]
        if (e["node"]["object"]["node"] or {}).get("display_label") == INSTANCE
    ]
    if not matches:
        print(f"No artifact '{ARTIFACT}' for target '{INSTANCE}' on branch '{BRANCH}'", file=sys.stderr)
        return 1
    art = matches[0]

    status = art["status"]["value"]
    if status != "Ready":
        print(f"Artifact {art['id']} is '{status}', not Ready - refusing to deploy a stale or failed render",
              file=sys.stderr)
        return 1

    content = request(f"/api/storage/object/{art['storage_id']['value']}")
    checksum = hashlib.md5(content).hexdigest()  # noqa: S324 - Infrahub's own checksum scheme
    if checksum != art["checksum"]["value"]:
        print(f"Checksum mismatch: got {checksum}, Infrahub says {art['checksum']['value']}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "wb") as fh:
        fh.write(content)
    with open(os.path.join(os.path.dirname(OUTPUT) or ".", ".artifact.json"), "w") as fh:
        json.dump({"artifact_id": art["id"], "checksum": checksum, "branch": BRANCH,
                   "instance": INSTANCE, "name": ARTIFACT}, fh, indent=2)

    print(f"Wrote {OUTPUT} ({len(content)} bytes) from artifact {art['id']} checksum {checksum}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
