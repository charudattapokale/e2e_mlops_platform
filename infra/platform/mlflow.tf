# Persistent disk where MLflow stores artifacts (models, plots, files)
resource "kubernetes_persistent_volume_claim_v1" "mlflow_artifacts" {
  metadata {
    name      = "mlflow-artifacts"
    namespace = kubernetes_namespace_v1.ns["mlops"].metadata[0].name
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "5Gi"
      }
    }
  }

  # k3s binds the disk only when a pod uses it, so do not wait for it here
  wait_until_bound = false
}

# Installs MLflow from the community Helm chart
resource "helm_release" "mlflow" {
  name       = "mlflow"
  namespace  = kubernetes_namespace_v1.ns["mlops"].metadata[0].name
  repository = "https://community-charts.github.io/helm-charts"
  chart      = "mlflow"
  version    = "1.10.0"
  timeout    = 600 # seconds, the first image pull can be slow

  # Start only after Postgres and the artifact disk exist
  depends_on = [
    kubernetes_stateful_set_v1.postgres,
    kubernetes_persistent_volume_claim_v1.mlflow_artifacts,
  ]

  # The database password comes from the same random value as the Postgres secret
  set_sensitive {
    name  = "backendStore.postgres.password"
    value = random_password.postgres.result
  }

  # Chart settings; the keys are documented in the chart's values.yaml
  values = [yamlencode({
    # Database for experiments, runs and the model registry
    backendStore = {
      databaseMigration       = true # create or update the tables on start
      databaseConnectionCheck = true # wait until Postgres answers
      postgres = {
        enabled  = true
        host     = "postgres.mlops.svc.cluster.local"
        port     = 5432
        database = "mlflow"
        user     = "mlflow"
        driver   = "psycopg2"
      }
    }

    # Clients upload artifacts through the MLflow server, which writes to the disk
    artifactRoot = {
      proxiedArtifactStorage      = true
      defaultArtifactsDestination = "/mlartifacts"
    }

    # One server worker keeps memory low on a laptop (the default is 4)
    extraArgs = {
      workers = "1"
    }

    # Host names MLflow accepts; "*" allows in-cluster names like
    # mlflow.mlops.svc.cluster.local. Fine locally, tighten it for real deployments
    serverAllowedHosts = ["*"]

    # Mount the persistent disk into the MLflow pod
    extraVolumes = [{
      name = "artifacts"
      persistentVolumeClaim = {
        claimName = "mlflow-artifacts"
      }
    }]
    extraVolumeMounts = [{
      name      = "artifacts"
      mountPath = "/mlartifacts"
    }]

    # Small limits, the laptop has 16 GB in total
    resources = {
      requests = {
        cpu    = "100m"
        memory = "256Mi"
      }
      limits = {
        memory = "3Gi"
      }
    }
  })]
}
