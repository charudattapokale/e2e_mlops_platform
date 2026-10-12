# Image tags and skipping builds

## The rule
Tag = first 12 characters of a SHA-256 over the contents of the files that go into the image:

    FILES=$(git ls-files <project> | grep -v -E '<excluded>')
    echo "$FILES" | xargs sha256sum | sha256sum | cut -c1-12

| Pipeline | Hashed | Excluded |
| --- | --- | --- |
| training | tracked files under `training/` | `training/k8s/`, `training/docker/docker-compose.yml` |
| inference | tracked files under `inference/` | `inference/k8s/`, `inference/scripts/` |

The pipeline asks the registry whether `<image>:<tag>` exists (`/v2/<image>/tags/list`). Yes: skip Kaniko. No: build and push.
Same content gives the same tag, so reverting code brings the old tag and the old image back. It is not the commit hash.
Parameters (learning rate and so on) are env vars on the Job, so they never change the tag.

## One tag, one image
- A forced rebuild under an existing tag (a FORCE_BUILD checkbox) overwrote the image. Two images shared one name, a rollout saw an
  identical pod template and did nothing, and a node with the tag cached kept the old image (`imagePullPolicy: IfNotPresent`).
  The checkbox was removed. If a rebuild is needed, change an input of the hash.
- Base images are not in the hash (`python:3.12-slim`, `uv:latest`). Pin exact versions so a base update is a visible edit.
- Registries such as ECR can enforce tag immutability. `registry:2` cannot, so the rule lives in the pipeline.

## The empty-hash bug
Symptom: the inference registry held the tag `abcfa6a9d4df`, the same tag the training pipeline had produced earlier.
Two different projects cannot share a content hash, so the hash input was empty: `git ls-files` printed nothing, `xargs` still ran
`sha256sum` once on empty input, and every build got the same constant tag. After the first build the check said
"already in registry: true" forever, so changed code was never built.

Why it hid: a pipeline reports the exit status of its last command, so the failed `git ls-files` was swallowed and the build stayed green.
Suspected cause: git refusing the workspace ("dubious ownership"), because the kubectl container runs as another user than the checkout.
Not confirmed from the console. Check the diagnosis with
`git ls-files does-not-exist | xargs sha256sum | sha256sum | cut -c1-12` (unverified: expected to print the constant).

Fix: `git config --global --add safe.directory "$WORKSPACE"`, fail loudly when the file list is empty, and print how many files were hashed.

Lessons:
- A check that cannot fail is worse than no check. Guard against empty input.
- Every "the second build skips the image build" result before the fix was a false pass. Test the negative path too: change a file and expect a new tag.
- Compare the pipeline's value with the same computation on a laptop, from a clean working tree.

## Other pitfalls found
- `curl` treats every `*.localhost` name as loopback without asking DNS. Inside a pod, `mlops-registry.localhost` pointed at the pod itself.
  Cluster DNS and the container runtime resolve it fine. Fix: `getent hosts` for the IP, then `curl --resolve host:port:ip`.
- Jenkins read the Jenkinsfile from an old branch for hours. The job definition's branch and the `GIT_BRANCH` parameter are separate things.
- The same variable declared twice in one Groovy scope (`def regIp`) is a compile error.
- `kubectl apply` of an unchanged manifest restarts nothing. Use `kubectl rollout restart` (it writes a restartedAt annotation into the pod template).
- A restart does not pull a changed image under the same tag. A new tag is the only reliable way.

## Registry addresses
| From | Address |
| --- | --- |
| Laptop (`docker push`) | `localhost:5001/<image>:<tag>` |
| Pods (Kaniko, Jobs, the node) | `mlops-registry.localhost:5000/<image>:<tag>` |

5000 is the registry's port inside the Docker network, 5001 only the host port. The registry is plain HTTP, so Kaniko needs `--insecure --skip-tls-verify`.
