# Settings for Terraform itself
terraform {
  required_version = ">= 1.5"

  # Providers are plugins that let Terraform talk to a system
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.30, < 4.0"
    }
    # Generates random values, used here for the database password
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6"
    }
  }
}

# How the Kubernetes plugin connects to the cluster
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "k3d-mlops"
}

# One namespace for each name in var.namespaces (see variables.tf)
resource "kubernetes_namespace_v1" "ns" {
  for_each = toset(var.namespaces)

  metadata {
    name = each.value
    labels = {
      "app.kubernetes.io/part-of" = "mlops-platform"
    }
  }
}
