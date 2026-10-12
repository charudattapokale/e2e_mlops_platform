# Terraform

## Two stages
`infra/cluster` creates the k3d cluster and the registry. `infra/platform` deploys inside it. They are separate because the Kubernetes
and Helm providers need a running cluster at plan time. On EKS the cluster stage becomes an EKS module and the platform stage stays almost the same.
`up.sh` refreshes the kubeconfig (`k3d kubeconfig merge`) and waits for the API server and the node before the second stage.
Without the wait, the first namespace calls failed with `EOF`, because k3d reports the cluster as created before the API answers.

## variable, locals, output
`variable` is an input, `locals` are values computed inside, `output` is exported. A `locals` value does nothing until a resource refers to it.
Here `locals` reads `jenkins/jobs/*.groovy` with `fileset` and `file`, and builds the JCasC map. `file()` content is not interpolated again,
so `${...}` in Groovy needs no escaping (an inline heredoc would need `$${...}`). `fileset` runs at plan time, so a wrong path fails early.
An empty folder gives no jobs, silently.

## State
- `terraform.tfstate` holds the generated Postgres password. Never commit it. Commit `.terraform.lock.hcl`.
- State lock error: another `terraform apply` is still running (`pgrep -a terraform`). Stop it with `kill -INT <pid>`.
  A second interrupt skips saving state. `force-unlock` only when no Terraform process runs.
- `cat > file <<'EOF' ... EOF` truncates the file. `terraform validate` accepts an empty file, and a plan would destroy what it described. Read the plan.

## Errors and what they meant
- `cannot re-use a name that is still in use`: an interrupted apply left a Helm release that Terraform no longer tracks.
  `helm uninstall <name> -n <ns>`, then apply.
- OOMKilled after raising a limit with `kubectl set resources`: the next apply reverts it. Change the Terraform file.
- `kubectl set env` has the same problem. The webhook settings on MLflow worked through `set env` and would have been removed by the next apply.
  They belong in `extraEnvVars`.
- `down.sh` failed on a stopped cluster: `terraform destroy` needs the API (`connection refused`). The script now skips the destroy when the
  API does not answer, and deletes the cluster directly. Everything inside it disappears with it.
- `Plan: 0 to add, 1 to change` on a `helm_release` with only `values` changed is normal. `metadata -> (known after apply)` is Helm bookkeeping.

## What goes where
| Change | Needs `terraform apply`? |
| --- | --- |
| New or changed `jenkins/jobs/*.groovy` (name, form, repo, path) | Yes |
| Stages in a Jenkinsfile | No, `git push` |
| Kubernetes manifests applied by a pipeline | No, the pipeline applies them |
| Plugins, RBAC, chart values | Yes |

RBAC for a namespace went into its own file (`rbac_serving.tf`): a separate file is safe to recreate, while appending to an existing file added a second copy when a paste was repeated.

## Habits
`terraform plan` before `apply`. Never `-lock=false`. Never `kill -9` on Terraform.
Apply from `main` with a clean tree, so the cluster matches Git.
