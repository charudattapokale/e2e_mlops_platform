# Command cheat sheet

Run everything in WSL Ubuntu, from `~/projects/mlops-platform` unless noted.

## Cluster

```bash
k3d cluster list                  # list clusters (1/1 = running, 0/1 = stopped)
k3d cluster start mlops           # start the cluster, wait about a minute
k3d cluster stop mlops            # stop it (keeps all data)
k3d registry list                 # list local registries
kubectl config get-contexts       # contexts kubectl knows (* = active)
kubectl config current-context    # should print k3d-mlops
kubectl config use-context k3d-mlops
```

If `k3d` or `kubectl` cannot connect, start Docker first: `sudo systemctl start docker`.

## Nodes, pods, namespaces

```bash
kubectl get nodes                 # k3d-mlops-server-0 should be Ready
kubectl get nodes -o wide
kubectl get ns                    # ci, mlops, training, serving, monitoring + system ones
kubectl get pods -A               # pods in all namespaces
kubectl get pods -n mlops         # postgres-0, mlflow-...
kubectl get pods -n ci            # jenkins-0 (+ temporary agent pods during builds)
kubectl get pods -n training      # training Job pods
kubectl get pods -n mlops -w      # watch live, Ctrl+C to stop
kubectl get deploy,svc,pvc -n mlops
kubectl get jobs -n training
kubectl top pod -A                # memory and CPU use
```

## Debugging

```bash
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous      # logs of the crashed container
kubectl logs -n ci jenkins-0 -c jenkins --tail=50
kubectl logs -n training job/training-<build-number>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
kubectl delete job --all -n training              # remove finished training Jobs
free -m                                           # memory left in WSL
```

## Open the UIs (keep each terminal open)

```bash
kubectl port-forward -n mlops svc/mlflow 5000:80      # http://localhost:5000
kubectl port-forward -n ci svc/jenkins 8080:8080      # http://localhost:8080
kubectl get secret -n ci jenkins -o jsonpath='{.data.jenkins-admin-password}' | base64 -d; echo
pkill -f port-forward                                 # close all tunnels
```

Jenkins login: user `admin`, password from the command above.

## Build and destroy

```bash
./scripts/up.sh                   # cluster, registry, Postgres, MLflow, Jenkins
./scripts/down.sh                 # destroys everything, including the data
terraform -chdir=infra/platform plan
terraform -chdir=infra/platform apply
```

## Registry

```bash
curl -s http://localhost:5001/v2/training/tags/list   # image tags in the registry
docker images
docker image prune -f             # remove untagged images
docker system df                  # disk usage
```

Registry addresses: `localhost:5001` from the laptop, `mlops-registry.localhost:5000` inside the cluster.
Avoid `docker system prune -a`, it deletes the k3s, proxy and registry images.

## Local training

```bash
cd training
uv run python train.py                                            # needs the MLflow port-forward
uv run python -m unittest discover -s tests -t . -v
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml down
```

## Git

```bash
git branch --show-current
git status -sb
git switch -c feat/<name>
git add <files> && git commit -m "..." && git push -u origin feat/<name>
git switch main && git pull
```

## Finish for the day

```bash
git status -sb                    # nothing uncommitted
pkill -f port-forward
k3d cluster stop mlops
```

Optional, from Windows PowerShell: `wsl --shutdown` to free all memory.

## Pod logs

```bash
kubectl logs <pod> -n <ns>                         # one pod
kubectl logs deploy/inference -n serving           # a Deployment (kubectl picks ONE pod)
kubectl logs -l app=inference -n serving --prefix  # all pods with a label, prefixed with the pod name
kubectl logs jenkins-0 -n ci -c jenkins            # one container of a multi-container pod
kubectl logs <pod> -n <ns> -f                      # follow live, Ctrl+C to stop
kubectl logs <pod> -n <ns> --tail=50               # last 50 lines
kubectl logs <pod> -n <ns> --since=10m             # last 10 minutes
kubectl logs <pod> -n <ns> --timestamps            # add a time to every line
kubectl logs <pod> -n <ns> --previous              # the container before its last restart (crash, OOMKilled)
kubectl logs deploy/inference -n serving -f | grep -v "GET /health"   # hide readiness probe noise
```

Logs of this project:

| What | Command |
| --- | --- |
| Inference API | `kubectl logs -n serving deploy/inference --tail=50` |
| MLflow | `kubectl logs -n mlops deploy/mlflow -c mlflow --tail=50` |
| Postgres | `kubectl logs -n mlops postgres-0 --tail=50` |
| Jenkins controller | `kubectl logs -n ci jenkins-0 -c jenkins --tail=80` |
| Jenkins config reload | `kubectl logs -n ci jenkins-0 -c config-reload --tail=20` |
| Training Job | `kubectl logs -n training job/training-<build>` |
| Jenkins agent during a build | `kubectl logs -n ci <agent-pod> -c kaniko` (or `-c kubectl`, `-c jnlp`) |

Notes:
- List the containers of a pod: `kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].name}'`. Init containers are separate (`-c mlflow-db-migration`).
- Logs belong to the pod. A deleted pod has none, so the training Job and agent pods lose theirs when they are cleaned up. The pipeline prints the training logs into the Jenkins console first.
- `--previous` works only if the same pod restarted its container. If the Deployment replaced the whole pod, the old logs are gone.
- A pod that never started (`ImagePullBackOff`, `ContainerCreating`) has no app logs. Read the events instead:
  `kubectl describe pod <pod> -n <ns> | tail -20` or `kubectl get events -n <ns> --sort-by=.lastTimestamp | tail`.
- Triage order for a broken pod: `get pods`, `describe`, `logs`, `logs --previous`.

## Stopping and starting pods

A single pod cannot be stopped and started. The workload that owns it (Deployment, StatefulSet, Job) keeps the desired state,
so the way to "stop" a pod is to change the owner's replica count, and to "restart" it is to let the owner replace it.

```bash
# Restart: a new pod replaces the old one (rolling, no gap for Deployments)
kubectl rollout restart deployment/inference -n serving
kubectl rollout restart deployment/mlflow -n mlops
kubectl rollout restart statefulset/jenkins -n ci
kubectl rollout status deployment/inference -n serving      # wait until it is done

# Restart one pod: delete it, the owner creates a new one
kubectl delete pod <pod> -n <ns>

# Stop: scale to zero (the object, its config and its volumes stay)
kubectl scale deployment/inference -n serving --replicas=0
kubectl scale deployment/mlflow -n mlops --replicas=0
kubectl scale statefulset/jenkins -n ci --replicas=0

# Start again
kubectl scale deployment/inference -n serving --replicas=1
kubectl scale deployment/mlflow -n mlops --replicas=1
kubectl scale statefulset/jenkins -n ci --replicas=1

# Jobs and CronJobs
kubectl delete job <name> -n training                       # stop and remove a Job and its pod
kubectl delete job --all -n training                        # remove all finished training Jobs
kubectl patch cronjob <name> -n <ns> -p '{"spec":{"suspend":true}}'    # pause a schedule
kubectl patch cronjob <name> -n <ns> -p '{"spec":{"suspend":false}}'   # resume it
```

Free memory when you are not working (the cluster keeps running):

```bash
kubectl scale statefulset/jenkins -n ci --replicas=0
kubectl scale deployment/mlflow -n mlops --replicas=0
kubectl scale deployment/inference -n serving --replicas=0
```

Start in dependency order: Postgres first (it stays running), then MLflow, then inference, then Jenkins.

Notes:
- `scale --replicas=0` keeps the volumes, so data survives. `kubectl delete` of a Deployment or StatefulSet removes the workload, and the next
  `terraform apply` or `up.sh` creates it again. Deleting a PersistentVolumeClaim removes the data.
- `rollout restart` is the right tool after changing a ConfigMap, a Secret or an environment variable. It does not pull a new image if the tag is
  the same: the default pull policy `IfNotPresent` reuses the cached image. Use a new tag, as the pipeline does with the content hash.
- A restarted pod gets a new IP. A running `kubectl port-forward` stays bound to the old pod, so close it (`pkill -f port-forward`) and open it again.
- A pod that is `Running` but `0/1` is still alive. The readiness probe fails, and the Service sends it no traffic. Look at `kubectl describe pod`.
- Scaling by hand is a change outside Terraform. A StatefulSet managed as a Terraform resource (Postgres) shows up as a difference in the next
  `terraform plan`. Helm releases (MLflow, Jenkins) keep the manual replica count until the chart values change. Put it back before you apply.
- Stop everything at once: `k3d cluster stop mlops`. Start it again with `k3d cluster start mlops`. All data stays.
