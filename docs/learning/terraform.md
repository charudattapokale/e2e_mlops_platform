# Terraform

## Two stages
`infra/cluster` creates the k3d cluster and registry. `infra/platform` deploys inside it.
The Kubernetes and Helm providers need a running cluster at plan time, so a flat single config cannot create both.
On EKS the cluster stage becomes an EKS module and the platform stage stays almost the same.

## variable, locals, output
`variable` = input from outside. `locals` = values computed inside. `output` = exported.
`locals` does nothing by itself. A resource must reference `local.<name>`.
Here, `locals` reads `jenkins/jobs/*.groovy` with `fileset`/`file` and builds the JCasC map.
`file()` content is not interpolated again, so `${...}` in Groovy needs no escaping. An inline heredoc would need `$${...}`.
`fileset` and `file` run at plan time, so a wrong path fails early. An empty folder gives no jobs, silently.

## State
- `terraform.tfstate` holds the generated Postgres password. Never commit it. Commit `.terraform.lock.hcl`.
- State lock error: another `terraform apply` is still running. `pgrep -a terraform`, stop it with `kill -INT <pid>`.
  A second interrupt skips saving state. `force-unlock` only if no process runs.
- Empty file by mistake: `cat > file <<'EOF' ... EOF` truncates the file. `terraform validate` accepts an empty file,
  and a plan would then destroy the resources it described. Read the plan before applying.

## Common errors
- `cannot re-use a name that is still in use`: an interrupted apply left a Helm release Terraform does not track.
  `helm uninstall <name> -n <ns>`, then apply.
- OOMKilled: raising limits with `kubectl set resources` is reverted by the next apply. Change the Terraform file.
- `Plan: 0 to add, 1 to change` on `helm_release` with only `values` changed is normal. `metadata -> (known after apply)` is Helm bookkeeping.

## Habits
`terraform plan` before `apply`. Never `-lock=false`. Do not use `kill -9` on Terraform.
