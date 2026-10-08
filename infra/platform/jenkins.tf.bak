# Jenkins controller in the ci namespace (official chart).
# Builds will run in temporary agent pods, so the controller stays small.
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
    }

    # Jenkins home (jobs, plugins, settings) survives pod restarts
    persistence = {
      enabled = true
      size    = "5Gi"
    }
  })]
}
