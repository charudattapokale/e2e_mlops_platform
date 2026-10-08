#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../infra"
terraform -chdir=cluster init -input=false
terraform -chdir=cluster apply -auto-approve
terraform -chdir=platform init -input=false
terraform -chdir=platform apply -auto-approve
