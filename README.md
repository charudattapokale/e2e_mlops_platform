# mlops-platform

An end-to-end MLOps platform that runs locally on Kubernetes (k3d) and is built entirely from code: Terraform, Jenkins, MLflow, and later FastAPI serving, monitoring and drift-triggered retraining.

## Architecture

| Namespace | Purpose |
| --- | --- |
| `ci` | Jenkins controller and temporary build agents |
| `mlops` | MLflow and its Postgres backend |
| `training` | Training Jobs (run once, then finish) |
| `serving` | FastAPI model service and Streamlit UI |
| `monitoring` | Prometheus, Grafana, drift detection |

## Quick start

1. Install the tools on WSL2 Ubuntu: see [bootstrap.md](bootstrap.md).
2. Build everything with one command:

```bash
./scripts/up.sh      # k3d cluster, registry, Postgres, MLflow, Jenkins
./scripts/down.sh    # destroy everything (deletes the data)
```

3. Open the UIs:

```bash
kubectl port-forward -n mlops svc/mlflow 5000:80     # http://localhost:5000
kubectl port-forward -n ci svc/jenkins 8080:8080     # http://localhost:8080
```

## Repository layout

| Folder | Contents |
| --- | --- |
| `infra/` | Terraform: `cluster/` (k3d + registry) and `platform/` (everything inside the cluster). See [infra/README.md](infra/README.md) |
| `scripts/` | `up.sh` and `down.sh` |
| `training/` | Training code, Dockerfile and Kubernetes Job template |
| `dataset/` | Data loading and preparation code |
| `inference/` | FastAPI service, Streamlit UI and their Kubernetes manifests |
| `jenkins/` | Jenkinsfiles for the training and serving pipelines |

## Registry addresses

- From your laptop: `localhost:5001/<image>:<tag>`
- From pods in the cluster: `mlops-registry.localhost:5000/<image>:<tag>`

## Status

Done: cluster, registry, Postgres, MLflow, Jenkins.
Next: training pipeline (build, push, run as a Job), then model registry promotion, serving, monitoring.
