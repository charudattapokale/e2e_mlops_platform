locals {
  # Job definitions live in the repo: jenkins/jobs/*.groovy (path is relative to this folder)
  job_dir   = "${path.module}/../../jenkins/jobs"
  job_files = fileset(local.job_dir, "*.groovy")

  # One JCasC config script per file: YAML wrapper around the raw Job DSL (Groovy).
  # file() is not re-interpreted by Terraform, so ${...} inside the Groovy needs no escaping.
  job_scripts = {
    for f in local.job_files :
    trimsuffix(f, ".groovy") => "jobs:\n  - script: |\n      ${indent(6, file("${local.job_dir}/${f}"))}\n"
  }
}

# Jenkins controller in the ci namespace (official chart).
# Builds run in temporary agent pods, so the controller stays small.
resource "helm_release" "jenkins" {
  name       = "jenkins"
  namespace  = kubernetes_namespace_v1.ns["ci"].metadata[0].name
  repository = "https://charts.jenkins.io"
  chart      = "jenkins"
  version    = "5.9.68"
  timeout    = 900 # seconds, the first start downloads the plugins

  values = [yamlencode({
    controller = {
      serviceType = "ClusterIP"
      # Keep the JVM below the container limit
      javaOpts = "-Xms256m -Xmx1g"
      resources = {
        requests = {
          cpu    = "200m"
          memory = "768Mi"
        }
        limits = {
          memory = "2Gi"
        }
      }

      # Replaces the chart's default plugin list, so the defaults are repeated here
      installPlugins = [
        "kubernetes:latest",
        "workflow-aggregator:latest",
        "git:latest",
        "configuration-as-code:latest",
        "job-dsl:latest",
        "pipeline-stage-view:latest",
        "pipeline-graph-view:latest",
      ]

      JCasC = {
        defaultConfig = true
        configScripts = local.job_scripts
      }
    }

    # Jenkins home (jobs, plugins, settings) survives pod restarts
    persistence = {
      enabled = true
      size    = "5Gi"
    }
  })]
}
