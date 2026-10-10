# Jenkins

## The layers
| Layer | Language | Role | Runs |
| --- | --- | --- | --- |
| Terraform `locals` | HCL | Reads `jenkins/jobs/*.groovy`, wraps each in JCasC YAML | `terraform apply` |
| JCasC | YAML | Configures Jenkins, hands scripts to Job DSL | on reload |
| Job DSL (`jenkins/jobs/*.groovy`) | Groovy | Creates the job: name, form, pointer to the pipeline | once per apply |
| Jenkinsfile (`jenkins/*.Jenkinsfile`) | Groovy (declarative) | The stages that run | every build |

Job definition = what should exist (declarative, once per apply).
Jenkinsfile = what to do (imperative, every build). Keep them in separate files.

## Where changes go
- Pipeline steps: edit the Jenkinsfile, `git push`. Jenkins reads it from GitHub at build time.
- The form, name, repo, branch, `scriptPath`: edit `jenkins/jobs/*.groovy`, run `terraform apply`.
  Terraform reads the file from the working tree, not from GitHub.

## Parameters
- Jenkins learns Jenkinsfile parameters by running the Jenkinsfile, so the form is one build behind.
- A JCasC reload regenerates the job and can wipe a form that came from the Jenkinsfile.
- Define the form in ONE place. If both the DSL and the Jenkinsfile define it, they overwrite each other.
- Scheduled and API-triggered builds use the defaults, not the form.
- Parameters are strings. Validate them. Groovy `"""${params.X}"""` is expanded before the shell runs,
  so a crafted value can inject shell code. Pass values as environment variables instead.

## Two checkouts
Loading the Jenkinsfile (branch in the job definition) and the `Checkout` stage (`GIT_BRANCH`) are independent.
They can be different branches, even different commits. `checkout scm` ties them together.

## Adding a pipeline
1. `jenkins/<name>.Jenkinsfile`
2. `jenkins/jobs/<name>.groovy` with `scriptPath('jenkins/<name>.Jenkinsfile')`
3. `git push`, then `terraform apply`
4. RBAC for the namespaces it touches (`infra/platform/rbac.tf`), or `kubectl` fails with `forbidden`

No change to `jenkins.tf`: `fileset` picks up new files.

## Pitfalls
- A typo in `scriptPath` is only caught at build time ("Unable to find ...").
- One broken `.groovy` file can stop the whole JCasC reload. Check `kubectl logs -n ci jenkins-0 -c jenkins`.
- Deleting a `.groovy` file does not delete the job.
- `installPlugins` replaces the chart's defaults. Plugins installed by hand are removed on the next apply.
- `>` in YAML folds lines together, `|` keeps newlines. Use `|` for scripts.
- The `config-reload` sidecar applies a changed ConfigMap without restarting the pod.
- Agent pods share one workspace volume across containers, so `kubectl` sees the files `git` checked out.
