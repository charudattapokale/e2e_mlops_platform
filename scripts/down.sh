#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../infra"
terraform -chdir=platform destroy -auto-approve
terraform -chdir=cluster destroy -auto-approve
