# Kubernetes

## Hierarchy

    cluster
    ├── nodes                      machines that run pods (cluster-wide, not in a namespace)
    └── namespaces                 logical partitions (ci, mlops, training, serving, monitoring)
        └── workloads              Deployment, StatefulSet, Job, CronJob (the controllers)
            └── pods               the smallest thing Kubernetes schedules
                └── containers     the actual processes (images)

| Level | What it is | In this project |
| --- | --- | --- |
| Cluster | The whole system: control plane plus nodes | k3d cluster `mlops` |
| Node | A machine that runs pods | `k3d-mlops-server-0` (itself a Docker container) |
| Namespace | Logical partition for names, access rules, quotas. Not a machine boundary | `ci`, `mlops`, `training`, `serving`, `monitoring` |
| Workload | A controller that creates and manages pods | `postgres` StatefulSet, `mlflow` Deployment, `training-<n>` Job |
| Pod | One or more containers sharing network and volumes, scheduled on one node | `postgres-0`, `jenkins-0`, a Jenkins agent pod |
| Container | A running image | `train`, `kaniko`, `kubectl`, `jenkins` |

Nuances:
- Namespaces and nodes are separate dimensions. A pod has a namespace (where it is defined) and a node (where it runs).
- Cluster-scoped objects (no namespace): nodes, namespaces, PersistentVolumes, ClusterRoles.
  Namespaced: pods, Deployments, Services, Roles, PVCs.
- Controllers own pods. A Deployment owns a ReplicaSet, which owns the pods, so deleting a pod makes a new one appear.
  A Job owns a pod and stops when it succeeds.
- A pod can hold several containers. `jenkins-0` is `2/2`: `jenkins` plus a `config-reload` sidecar.
  The agent pod has `jnlp`, `kaniko` and `kubectl`. They share `localhost` and the volumes, which is why `kubectl` sees the files `git` checked out.
- Init containers run first and must finish (MLflow waits on `dbchecker` and `mlflow-db-migration`).
- Services, Ingresses, ConfigMaps and Secrets run nothing. A Service gives pods a stable name, an Ingress routes outside traffic to a Service.
- Limits apply per container. The scheduler sums the requests of all containers in a pod.

## Workload types
| Type | Use | Behavior |
| --- | --- | --- |
| Deployment | Servers (FastAPI, Streamlit) | Always running, restarted on exit |
| StatefulSet | Postgres | Stable identity, own volume |
| Job | One training run | Runs to completion, no restart |
| CronJob | A schedule | Creates a Job from a template on a schedule |

## Jobs
- `backoffLimit: 0`: no retries for a failed run.
- `ttlSecondsAfterFinished` removes the pod later. Finished pods are kept on purpose, for logs.
- A Job's pod template is immutable: use a new name per build (`training-<build>`).
- `apply` on an existing object also needs `patch` in RBAC. `create` fits one-shot objects better.
- `kubectl apply` returns when the API server accepts the Job. Image pull errors and crashes appear later.

## Running is not Ready
`Running` means the process started. `READY 1/1` follows the readiness probe. `Completed` is healthy for Jobs.
RESTARTS goes up by one after a cluster stop and start. A count that keeps growing is a crash loop.

## RBAC
Service account `jenkins-agent` (namespace `ci`) with a Role in `training`: create/get/list/watch/delete jobs, read pods and logs.
Pods use their service account token automatically (in-cluster config). No kubeconfig is stored.
Check: `kubectl auth can-i create jobs -n training --as=system:serviceaccount:ci:jenkins-agent`.

## Namespaces in this project
`ci` Jenkins, `mlops` MLflow and Postgres, `training` Jobs, `serving` API and UI, `monitoring` Prometheus and Grafana.
`default`, `kube-system`, `kube-public`, `kube-node-lease` are created by k3s. Terraform must not manage them.

## Is the cluster up? Layers
Docker daemon, node container (`k3d cluster list`), API server, node (`kubectl get nodes`), system pods, workloads.
`1/1` in `k3d cluster list` only means the container runs. Right after a start, kubectl may still refuse connections.
Not-healthy pods only: `kubectl get pods -A | grep -v -E 'Running|Completed'`.

## Look-alike failures
- Stale kubeconfig: `k3d kubeconfig merge mlops --kubeconfig-merge-default --kubeconfig-switch-context`.
- Wrong context: must be `k3d-mlops`.
- WSL2 clock drift after sleep: `x509: certificate has expired`. `sudo hwclock -s` or `wsl --shutdown`.
- Docker not running after a WSL restart: `sudo systemctl start docker`.
- Memory pressure: OOMKilled pods, node NotReady. `free -m`, `kubectl top node`.

## Data
`k3d cluster stop/start` keeps volumes. `k3d cluster delete` (and `down.sh`) removes them.
