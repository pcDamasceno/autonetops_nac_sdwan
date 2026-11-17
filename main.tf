# Cisco Network-as-Code for Catalyst SD-WAN.
#
# The data model is NOT written by hand here: it is the `sdwan-nac` artifact
# rendered by Infrahub (transform `sdwan_nac_export`), downloaded into data/ by
# the CI `fetch` job (scripts/fetch_artifact.py).
#
# Provider credentials come from the environment (GitLab CI variables):
#   SDWAN_URL, SDWAN_USERNAME, SDWAN_PASSWORD   (SDWAN_INSECURE defaults to true)

terraform {
  required_version = ">= 1.8.0"

  # GitLab-managed Terraform state; configured entirely through TF_HTTP_*
  # variables in .gitlab-ci.yml. For a local run use `-backend=false`.
  backend "http" {}

  required_providers {
    sdwan = {
      source  = "CiscoDevNet/sdwan"
      version = "0.11.7"
    }
    utils = {
      source  = "netascode/utils"
      version = ">= 2.0.1, < 3.0.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.3.0"
    }
  }
}

provider "sdwan" {}

module "sdwan" {
  source  = "netascode/nac-sdwan/sdwan"
  version = "1.5.1"

  yaml_directories = ["data"]
}
