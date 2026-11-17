#!/usr/bin/env python3
"""Referential pre-flight for the NAC SD-WAN model.

The nac-sdwan module resolves names with map lookups, so a configuration group
that points at a profile missing from the model fails deep inside `plan` with
an opaque "Invalid index" error. Catch those here with a readable message.

Usage: check_refs.py data/sdwan.nac.yaml [more.yaml ...]
"""

from __future__ import annotations

import sys

import yaml

# configuration_group key -> feature_profiles key
PROFILE_REFS = {
    "cli_profile": "cli_profiles",
    "other_profile": "other_profiles",
    "service_profile": "service_profiles",
    "system_profile": "system_profiles",
    "transport_profile": "transport_profiles",
    "application_priority_profile": "application_priority_profiles",
}


def main(paths: list[str]) -> int:
    sdwan: dict = {}
    for p in paths:
        with open(p) as fh:
            sdwan.update((yaml.safe_load(fh) or {}).get("sdwan", {}))

    profiles = sdwan.get("feature_profiles", {})
    known = {k: {p["name"] for p in profiles.get(k, [])} for k in PROFILE_REFS.values()}
    groups = {g["name"] for g in sdwan.get("configuration_groups", [])}
    errors: list[str] = []

    for g in sdwan.get("configuration_groups", []):
        for ref, coll in PROFILE_REFS.items():
            if ref in g and g[ref] not in known[coll]:
                errors.append(f"configuration_group '{g['name']}': {ref} '{g[ref]}' "
                              f"is not defined in feature_profiles.{coll}")
        # policy_object_profile is a single object, not a list
        if "policy_object_profile" in g and "policy_object_profile" not in profiles:
            errors.append(f"configuration_group '{g['name']}': policy_object_profile "
                          f"'{g['policy_object_profile']}' but feature_profiles.policy_object_profile is not defined")

    for site in sdwan.get("sites", []):
        for r in site.get("routers", []):
            cg = r.get("configuration_group")
            if cg and cg not in groups:
                errors.append(f"site {site.get('id')} router {r.get('chassis_id')}: "
                              f"configuration_group '{cg}' is not defined")

    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} unresolved reference(s). Fix the data in Infrahub and regenerate "
              f"the artifact.", file=sys.stderr)
        return 1

    print(f"OK: {len(groups)} configuration group(s), "
          f"{sum(len(v) for v in known.values())} feature profile(s), "
          f"{sum(len(s.get('routers', [])) for s in sdwan.get('sites', []))} router(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["data/sdwan.nac.yaml"]))
