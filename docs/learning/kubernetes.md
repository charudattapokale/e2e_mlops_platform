# Kubernetes

## Workload types
| Type | Use | Behavior |
| --- | --- | --- |
| Deployment | Servers (FastAPI, Streamlit) | Always running, restarted on exit |
| StatefulSet | Postgres | Stable identity, own volume |
| Job | One training run | Runs to completion, no restart |
| CronJob | A schedule | Creates a Job on a schedule from a template |

## Jobs
- `backoffLimit: 0`: no retries for a failed run.
- `ttlSecondsAfterFinished`: removes the pod later. Finished pods are kept on purpose, for logs.
- A Job's pod template is immutable, so use a new name per build (`training-<build>`). `apply` on a changed template fails.
- `apply` on an existing object also needs `patch` in RBAC. `create` is more honest for one-shot objects.
- `kubectl apply` returns when the API server accepts the Job. Image pull errors and crashes show up later.

## Running is not Ready
`Running` means the process started. `READY 1/1` follows the readiness probe. `Completed` is healthy for Jobs.
RESTARTS goes up by one after a cluster stop and start. A count that keeps growing is a crash loop.

## RBAC
Service account `jenkins-agent` (namespace `ci`) with a Role in `training`: create/get/list/watch/delete jobs, read pods and logs.
Pods use their service account token automatically (in-cluster config). No kubeconfig is stored.
`kubectl auth can-i create jobs -n training --as=system:serviceaccount:ci:jenkins-agent` checks it.

## Namespaces
`ci` Jenkins, `mlops` MLflow and Postgres, `training` Jobs, `serving` API and UI, `monitoring` Prometheus and Grafana.
`default`, `kube-system`, `kube-public`, `kube-node-lease` are created by k3s itself. Terraform must not manage them.

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

## Hierarchy

    cluster
    ├── nodes                      machines that run pods (cluster-wide, not in a namespace)
    └── namespaces                 logical partitions (ci, mlops, training, serving, monitoring)
        └── workloads              Deployment, StatefulSet, Job, CronJob (the controllers)
            └── pods               the smallest thing Kubernetes schedules
                └── containers     the actual processes (images)

| Level | What it is | In this project |
| --- | --- | --- |
| Cluster | The whole Kubernetes system: control plane plus nodes | k3d cluster `mlops` |
| Node | A machine (VM or server) that runs pods | `k3d-mlops-server-0`, which is itself a Docker container |
| Namespace | A logical partition for names, access rules and quotas. It does not separate machines | `ci`, `mlops`, `training`, `serving`, `monitoring` |
| Workload | A controller that creates and manages pods | `postgres` StatefulSet, `mlflow` Deployment, `training-<n>` Job |
| Pod | One or more containers sharing network and volumes, scheduled together on one node | `postgres-0`, `jenkins-0`, a Jenkins agent pod |
| Container | A running image | `train`, `kaniko`, `kubectl`, `jenkins` |

Nuances:
- Namespaces and nodes are separate dimensions. A pod has a namespace (where it is defined) and a node (where it runs). Namespaces do not map to machines.
- Some objects are cluster-scoped, not namespaced: nodes, namespaces, PersistentVolumes, ClusterRoles. Pods, Deployments, Services, Roles and PVCs are namespaced.
- Workload controllers own pods. A Deployment owns a ReplicaSet, which owns the pods, so deleting a pod makes the controller create a new one. A Job owns a pod and stops when it succeeds.
- A pod can hold several containers. `jenkins-0` shows `2/2`: the `jenkins` container plus a `config-reload` sidecar. The agent pod has `jnlp`, `kaniko` and `kubectl`. The containers share the pod's network (`localhost`) and its volumes, which is why `kubectl` sees the files `git` checked out.
- Init containers run first and must finish before the main containers start (the MLflow pod waits on `dbchecker` and `mlflow-db-migration`).
- Services, Ingresses, ConfigMaps and Secrets are not workloads. They do not run anything. A Service gives pods a stable name and address, and an Ingress routes outside traffic to a Service.
- Resource limits apply per container. The scheduler sums the requests of all containers in a pod to pick a node.
- A single-node cluster still has this structure: one node, many namespaces, many pods.
