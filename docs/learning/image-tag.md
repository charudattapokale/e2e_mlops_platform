# Image tag and skipping builds

## The rule
Tag = first 12 characters of a SHA-256 over the contents of the image files:

    git ls-files training | grep -v -E '^training/(k8s|docker/docker-compose.yml)' | xargs sha256sum | sha256sum | cut -c1-12

The pipeline asks the registry whether `training:<tag>` exists. Yes: skip Kaniko. No: build and push.
There is no "latest image" comparison. Same content gives the same tag, so reverting code reuses the old image.

## Which files count
In: `train.py`, `pyproject.toml`, `uv.lock`, `.python-version`, `.dockerignore`, `docker/Dockerfile`, `tests/*`.
Out: `training/k8s/`, the compose file, `jenkins/`, `infra/`, `docs/`, `dataset/`, `inference/`.
Any change to an included file, even a comment, gives a new tag.
Parameters (learning rate etc.) are env vars on the Job, so they never change the image.

## Not the git commit hash
A commit hash changes on any change in the repo. The content tag changes only when the image inputs change.
Add the commit as metadata (image label, MLflow tag) if you need traceability.

## Pitfalls found here
- `curl` treats any `*.localhost` name as loopback (127.0.0.1), without asking DNS. Inside a pod,
  `mlops-registry.localhost` is therefore unreachable for curl, although cluster DNS resolves it for other tools.
  Fix: `getent hosts` to get the IP, then `curl --resolve host:port:ip`.
- Jenkins was reading the Jenkinsfile from an old branch, so fixes on `main` never ran.
- `def` of the same variable twice in one Groovy scope is a compile error.
- The hash does not cover base images (`python:3.12-slim`, `uv:latest`). Pin them, or the image can change under the same tag.
- Registry data lives in the cluster. After `down.sh` and `up.sh` the first build rebuilds.

## Registry addresses
| From | Address |
| --- | --- |
| Laptop (docker push) | `localhost:5001/<image>:<tag>` |
| Pods (Kaniko, Jobs) | `mlops-registry.localhost:5000/<image>:<tag>` |
The registry listens on 5000 inside the Docker network. 5001 is only the host port.
Registry is plain HTTP, so Kaniko needs `--insecure --skip-tls-verify`.
