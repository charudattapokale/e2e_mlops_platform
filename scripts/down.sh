#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../infra"

# The platform destroy needs a running cluster. Everything inside the cluster disappears with it anyway.
if kubectl --context k3d-mlops get nodes >/dev/null 2>&1; then
  terraform -chdir=platform destroy -auto-approve || echo "platform destroy failed, deleting the cluster anyway"
else
  echo "cluster is not reachable, skipping the platform destroy"
fi

k3d cluster delete mlops || true
k3d registry delete mlops-registry.localhost 2>/dev/null || true
rm -f cluster/terraform.tfstate* cluster/terraform.tfstate.backup platform/terraform.tfstate* platform/terraform.tfstate.backup
echo "done"
