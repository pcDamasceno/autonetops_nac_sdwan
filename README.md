# autonetops_nac_sdwan

Deploys Catalyst SD-WAN configuration with Cisco **Network-as-Code**
([`netascode/nac-sdwan/sdwan`](https://registry.terraform.io/modules/netascode/nac-sdwan/sdwan))
using the data model **rendered by Infrahub**. Nothing in `data/` is written by hand.

```
Infrahub (SdwanInstance "sdwan-manager")
  └─ transform sdwan_nac_export ─► artifact "sdwan-nac" (NAC YAML)
        └─ GitLab CI: fetch ─► validate ─► plan ─► deploy (manual) ─► SD-WAN Manager
```

## Pipeline

| Job | What it does |
|---|---|
| `fetch:artifact` | `scripts/fetch_artifact.py`: finds the `sdwan-nac` artifact for `SDWAN_INSTANCE`, refuses anything not `Ready`, verifies the checksum, writes `data/sdwan.nac.yaml` + `data/.artifact.json` (provenance) |
| `validate:refs` | `scripts/check_refs.py`: refuses an empty model; every profile, configuration group and policy group referenced is defined (the module would otherwise fail in `plan` with "Invalid index") |
| `validate:terraform` | `terraform fmt -check` + `terraform validate` |
| `plan` | `terraform plan` against the Manager; `plan.txt` kept as a job artifact for review |
| `deploy` | manual, default branch only: applies **that exact plan file** |

State is GitLab-managed (Operate > Terraform states), one state per `SDWAN_INSTANCE`.
`plan` and `deploy` share a `resource_group`, so two pipelines never touch the Manager at once.

> `deploy` pushes to devices: the module defaults `configuration_group_deploy: true`,
> so every router under `sites[].routers` is attached to its configuration group and deployed.

## CI/CD variables

| Variable | Flags | Value |
|---|---|---|
| `INFRAHUB_API_TOKEN` | masked | Infrahub API token |
| `SDWAN_URL` | | `https://<manager>` |
| `SDWAN_USERNAME` | | Manager user |
| `SDWAN_PASSWORD` | masked | Manager password |

Defaults set in `.gitlab-ci.yml` (override as variables if needed):
`INFRAHUB_ADDRESS=http://infrahub-infrahub-server-1:8000`, `INFRAHUB_BRANCH=main`,
`SDWAN_INSTANCE=sdwan-manager`, `ARTIFACT_NAME=sdwan-nac`, `SDWAN_INSECURE=true`.

The runner's Docker executor attaches jobs to the `bootcamp` network, which is where
`infrahub-infrahub-server-1` resolves.

## Local run

```bash
export INFRAHUB_ADDRESS=http://localhost:8000 INFRAHUB_API_TOKEN=...
python3 scripts/fetch_artifact.py && python3 scripts/check_refs.py data/*.yaml
terraform init -backend=false && terraform validate
```

`plan` needs the GitLab state, so run it in the pipeline. To plan locally, also set the
`SDWAN_*` credentials and the `TF_HTTP_*` variables from `.gitlab-ci.yml`
(`TF_HTTP_USERNAME`/`TF_HTTP_PASSWORD`: your GitLab user and an access token), then run
`terraform init -reconfigure`. Never plan against an empty local state: it proposes to
create objects that already exist.
