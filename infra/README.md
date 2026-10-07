# infra: Terraform for the local platform

Creates the platform pieces inside the local k3d cluster. The cluster itself is created by hand once (see `../bootstrap.md`, step 14).

## Prerequisites

- WSL2 Ubuntu with Docker, kubectl, helm, terraform and k3d installed (see `../bootstrap.md`)
- The cluster `mlops` is running, with kubectl context `k3d-mlops`

```bash
k3d cluster list                  # the cluster named mlops should be listed
kubectl config current-context    # should print k3d-mlops
kubectl get nodes                 # one node in Ready state
```

## Files

| File | Purpose |
| --- | --- |
| `main.tf` | Terraform settings, the Kubernetes provider connection, and the namespaces |
| `variables.tf` | Inputs, for example the list of namespaces |
| `.terraform.lock.hcl` | Pins provider versions (created by `init`, commit it) |
| `terraform.tfstate`, `.terraform/` | Terraform's state and downloaded plugins (never commit) |

## Commands

Run these inside the `infra` folder.

```bash
terraform init       # download the Kubernetes provider, creates .terraform.lock.hcl
terraform fmt        # format the .tf files
terraform validate   # check the syntax and settings, changes nothing
terraform plan       # show what would be created, changes nothing
terraform apply      # create it for real, type yes to confirm
```

## Check the result

```bash
kubectl get ns       # ci, mlops, training, serving, monitoring should be listed
terraform plan       # should say: No changes. Your infrastructure matches the configuration.
```

## Rebuild from code

```bash
terraform destroy    # remove everything Terraform created, type yes
kubectl get ns       # the five namespaces are gone
terraform apply      # create them again, type yes
```

## Change the namespaces

Edit the `namespaces` default in `variables.tf`, then run:

```bash
terraform plan
terraform apply
```

## Notes

- Never commit the state file or the `.terraform/` folder (they are in `.gitignore`).
- Commit `.terraform.lock.hcl`.
- If `plan` says the context does not exist, check the name with `kubectl config get-contexts` and fix `config_context` in `main.tf`.
- Next steps: Postgres, MinIO and MLflow through the Helm provider.
