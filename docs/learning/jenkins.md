# Jenkins

## The layers
| Layer | Language | Role | Runs |
| --- | --- | --- | --- |
| Terraform `locals` | HCL | Reads `jenkins/jobs/*.groovy`, wraps each in JCasC YAML | `terraform apply` |
| JCasC | YAML | Configures Jenkins, hands scripts to Job DSL | on reload |
| Job DSL (`jenkins/jobs/*.groovy`) | Groovy | Creates the job: name, form, pointer to the pipeline | once per apply |
| Jenkinsfile (`jenkins/*.Jenkinsfile`) | Groovy (declarative) | The stages that run | every build |

`locals` is glue only. It holds no UI information. The form lives in the `.groovy` file.

## How the files connect

    jenkins/jobs/training.groovy      (Job DSL: what exists)
      - job name, the parameter form (UI)
      - scriptPath -> jenkins/training.Jenkinsfile
            |
            v
    jenkins/training.Jenkinsfile      (pipeline: what runs, every build)
      - stages: checkout, check image, Kaniko build, run job, wait and logs, cleanup
      - run stage: envsubst < training/k8s/job.yaml | kubectl apply -f -
            |
            v
    training/k8s/job.yaml             (Kubernetes manifest: the workload)
      - one Job in namespace training, runs the image, then finishes

The training manifest contains only a Job. Deployment, Service and Ingress belong to serving
(`inference/k8s/app.yaml`), applied by a serving pipeline.

Flow of one build:
1. Terraform and Job DSL created the job with its form (once per apply).
2. You click Build with Parameters. Jenkins fetches the Jenkinsfile named by `scriptPath`.
3. The Jenkinsfile starts an agent pod, builds or reuses the image, fills `job.yaml` with `envsubst`, applies it.
4. Kubernetes creates the Job and its pod in `training`. The pod runs `train.py`, logs to MLflow, exits.
5. The pipeline waits, prints the logs, deletes the Job.

## Where changes go
- Pipeline steps: edit the Jenkinsfile, `git push`. Jenkins reads it from GitHub at build time.
- The form, name, repo, branch, `scriptPath`: edit `jenkins/jobs/*.groovy`, run `terraform apply`.
  Terraform reads the file from the working tree, not from GitHub.

## Checklist: adding a new pipeline
A new pipeline always needs a `terraform apply`. Until you apply, Jenkins does not know the job exists.
1. Write `jenkins/<name>.Jenkinsfile` (the stages).
2. Write `jenkins/jobs/<name>.groovy` (name, form, `scriptPath('jenkins/<name>.Jenkinsfile')`).
3. Add RBAC if it touches a new namespace (`infra/platform/rbac.tf`), and any manifests it applies.
4. Commit and `git push`. The Jenkinsfile must be on GitHub before the first build.
5. `cd infra/platform && terraform plan`. Only `helm_release.jenkins` should change.
6. `terraform apply`. The config-reload sidecar applies it without restarting the pod.
7. Check `kubectl logs -n ci jenkins-0 -c jenkins --tail=80 | grep -i -E 'casc|dsl|error|exception'`, then open the job.

| Change | Needs `terraform apply`? | Why |
| --- | --- | --- |
| New pipeline (new `jenkins/jobs/*.groovy`) | Yes | The job definition is delivered by Terraform |
| Form, job name, repo, branch or `scriptPath` | Yes | Same, it lives in the `.groovy` file |
| Stages in an existing Jenkinsfile | No, `git push` only | Read from GitHub at build time |
| `training/k8s/job.yaml` | No, `git push` only | Applied from the checkout |
| New plugin | Yes | `installPlugins` is in `jenkins.tf` |
| New namespace or permission for the agent | Yes | RBAC is in `rbac.tf` |

`jenkins.tf` is not edited for a new pipeline: `fileset` finds the new file. Apply from `main` with a clean tree.
Not applying is silent: the old definition keeps running.

## Parameters
- Jenkins learns Jenkinsfile parameters by running the Jenkinsfile, so that form is one build behind.
- A JCasC reload regenerates the job and can wipe a form that came from the Jenkinsfile.
- Define the form in ONE place. If both the DSL and the Jenkinsfile define it, they overwrite each other.
- Scheduled and API-triggered builds use the defaults, not the form.
- Parameters are strings. Validate them. Groovy `"""${params.X}"""` is expanded before the shell runs,
  so a crafted value can inject shell code. Pass values as environment variables instead.

## Two checkouts
Loading the Jenkinsfile (branch in the job definition) and the `Checkout` stage (`GIT_BRANCH`) are independent.
They can be different branches, even different commits. `checkout scm` ties them together.

## Pitfalls
- A typo in `scriptPath` is only caught at build time ("Unable to find ...").
- One broken `.groovy` file can stop the whole JCasC reload. Check the Jenkins log.
- Deleting a `.groovy` file does not delete the job.
- `installPlugins` replaces the chart's defaults. Plugins installed by hand are removed on the next apply.
- In YAML, `>` folds lines together and `|` keeps newlines. Use `|` for scripts.
- Agent pods share one workspace volume across containers, so `kubectl` sees the files `git` checked out.
