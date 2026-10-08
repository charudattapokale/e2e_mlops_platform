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

      # Agent pods run in the ci namespace with the jenkins-agent service account
      # (rbac.tf), so they may create Jobs in the training namespace.
      JCasC = {
        defaultConfig = true
        configScripts = {
          training-job = <<-EOT
            jobs:
              - script: >
                  pipelineJob('training_jenkins_pipeline') {
                    description('Train the bank marketing model and log it to MLflow')
                    definition {
                      cpsScm {
                        scm {
                          git {
                            remote { url('https://github.com/charudattapokale/e2e_mlops_platform.git') }
                            branch('*/main')
                          }
                        }
                        scriptPath('jenkins/training.Jenkinsfile')
                        lightweight(true)
                      }
                    }
                  }
          EOT
        }
      }
    }

    # Jenkins home (jobs, plugins, settings) survives pod restarts
    persistence = {
      enabled = true
      size    = "5Gi"
    }
  })]
}
