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

# group kind -> {group key -> feature_profiles key}
PROFILE_REFS = {
    "configuration_group": {
        "cli_profile": "cli_profiles",
        "other_profile": "other_profiles",
        "service_profile": "service_profiles",
        "system_profile": "system_profiles",
        "transport_profile": "transport_profiles",
    },
    "policy_group": {
        "application_priority": "application_priority_profiles",
        "ngfw_security": "ngfw_security_profiles",
        "sse": "sse_profiles",
    },
    "topology_group": {
        "topology_profile": "topology_profiles",
    },
}


def main(paths: list[str]) -> int:
    sdwan: dict = {}
    for p in paths:
        with open(p) as fh:
            sdwan.update((yaml.safe_load(fh) or {}).get("sdwan") or {})

    profiles = sdwan.get("feature_profiles") or {}
    known = {k: {p["name"] for p in profiles.get(k) or []}
             for refs in PROFILE_REFS.values() for k in refs.values()}
    groups = {kind: {g["name"] for g in sdwan.get(f"{kind}s") or []} for kind in PROFILE_REFS}
    sites = sdwan.get("sites") or []
    routers = sum(len(s.get("routers") or []) for s in sites)
    errors: list[str] = []

    # An empty model is valid to Terraform: it would plan to destroy everything.
    if not groups["configuration_group"] or not routers:
        errors.append(f"model has {len(groups['configuration_group'])} configuration group(s) and "
                      f"{routers} router(s); refusing an empty model")

    for kind, refs in PROFILE_REFS.items():
        for g in sdwan.get(f"{kind}s") or []:
            for ref, coll in refs.items():
                if g.get(ref) is not None and g[ref] not in known[coll]:
                    errors.append(f"{kind} '{g['name']}': {ref} '{g[ref]}' "
                                  f"is not defined in feature_profiles.{coll}")

    for g in sdwan.get("configuration_groups") or []:
        # policy_object_profile is a single object, not a list
        if g.get("policy_object_profile") is not None and "policy_object_profile" not in profiles:
            errors.append(f"configuration_group '{g['name']}': policy_object_profile "
                          f"'{g['policy_object_profile']}' but feature_profiles.policy_object_profile is not defined")

    for site in sites:
        for r in site.get("routers") or []:
            for kind in ("configuration_group", "policy_group"):
                if r.get(kind) is not None and r[kind] not in groups[kind]:
                    errors.append(f"site {site.get('id')} router {r.get('chassis_id')}: "
                                  f"{kind} '{r[kind]}' is not defined")

    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} error(s). Fix the data in Infrahub and regenerate "
              f"the artifact.", file=sys.stderr)
        return 1

    print(f"OK: {len(groups['configuration_group'])} configuration group(s), "
          f"{sum(len(v) for v in known.values())} feature profile(s), "
          f"{routers} router(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["data/sdwan.nac.yaml"]))
