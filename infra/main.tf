# Settings for Terraform itself
terraform {
  # Refuse to run with a Terraform older than 1.5
  required_version = ">= 1.5"

  # Providers are plugins that let Terraform talk to a system
  required_providers {
    kubernetes = {
      # Where to download the plugin from (the Terraform Registry)
      source  = "hashicorp/kubernetes"
      # Allowed versions: 2.30 or newer, but below 4.0
      version = ">= 2.30, < 4.0"
    }
  }
}

# How the Kubernetes plugin connects to the cluster
provider "kubernetes" {
  # The kubeconfig file that k3d wrote when it created the cluster
  config_path    = "~/.kube/config"
  # Which cluster inside that file to use (k3d names it k3d-<cluster name>)
  config_context = "k3d-mlops"
}

# A resource is one thing Terraform creates and manages.
# "kubernetes_namespace_v1" is the type, "ns" is our own label for it
resource "kubernetes_namespace_v1" "ns" {
  # Create one namespace for each name in the list from variables.tf.
  # toset() turns the list into a set, which for_each needs
  for_each = toset(var.namespaces)

  metadata {
    # each.value is the current name from the list (ci, mlops, ...)
    name = each.value

    # Labels are tags; this one marks everything as part of this project
    labels = {
      "app.kubernetes.io/part-of" = "mlops-platform"
    }
  }
}
