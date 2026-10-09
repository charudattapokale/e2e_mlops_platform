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
