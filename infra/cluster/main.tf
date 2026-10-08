terraform {
  required_version = ">= 1.5"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# The local k3d cluster and its image registry.
# On EKS this stage becomes an EKS module; the platform stage stays the same.
resource "null_resource" "k3d_cluster" {
  triggers = {
    name        = "mlops"
    config      = "${path.module}/k3d-config.yaml"
    config_hash = filemd5("${path.module}/k3d-config.yaml")
  }

  provisioner "local-exec" {
    command = "k3d cluster create --config ${self.triggers.config}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "k3d cluster delete ${self.triggers.name}"
  }
}
