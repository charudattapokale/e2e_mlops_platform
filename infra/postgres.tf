# Random password for the MLflow database user.
# It is stored in the Terraform state, which is not committed to git
resource "random_password" "postgres" {
  length  = 24
  special = false
}

# Kubernetes Secret holding the database name, user and password
resource "kubernetes_secret_v1" "postgres" {
  metadata {
    name = "postgres"
    # Referencing the namespace resource makes Terraform create the namespace first
    namespace = kubernetes_namespace_v1.ns["mlops"].metadata[0].name
  }

  data = {
    POSTGRES_DB       = "mlflow"
    POSTGRES_USER     = "mlflow"
    POSTGRES_PASSWORD = random_password.postgres.result
  }
}

# Headless Service: gives the pod a stable DNS name, postgres.mlops.svc.cluster.local
resource "kubernetes_service_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace_v1.ns["mlops"].metadata[0].name
  }

  spec {
    cluster_ip = "None"
    selector = {
      app = "postgres"
    }
    port {
      name        = "postgres"
      port        = 5432
      target_port = 5432
    }
  }
}

# StatefulSet: runs one Postgres pod with its own persistent disk
resource "kubernetes_stateful_set_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = kubernetes_namespace_v1.ns["mlops"].metadata[0].name
  }

  spec {
    service_name = kubernetes_service_v1.postgres.metadata[0].name
    replicas     = 1

    selector {
      match_labels = {
        app = "postgres"
      }
    }

    template {
      metadata {
        labels = {
          app = "postgres"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:17"

          port {
            container_port = 5432
          }

          # Load POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD from the Secret
          env_from {
            secret_ref {
              name = kubernetes_secret_v1.postgres.metadata[0].name
            }
          }

          # Use a sub-folder of the volume as the data directory
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }

          # Small limits, because the laptop has 16 GB in total
          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              memory = "512Mi"
            }
          }

          # The pod counts as ready only when the database accepts connections
          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "mlflow", "-d", "mlflow"]
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
        }
      }
    }

    # Creates a 2 GB persistent volume for the pod (k3s local-path storage by default)
    volume_claim_template {
      metadata {
        name = "data"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = {
            storage = "2Gi"
          }
        }
      }
    }
  }
}
