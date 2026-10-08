# ServiceAccount used by the Jenkins build agent pods (in the ci namespace)
resource "kubernetes_service_account_v1" "jenkins_agent" {
  metadata {
    name      = "jenkins-agent"
    namespace = kubernetes_namespace_v1.ns["ci"].metadata[0].name
  }
}

# What the agent may do in the training namespace: run Jobs, read their pods and logs
resource "kubernetes_role_v1" "training_runner" {
  metadata {
    name      = "training-runner"
    namespace = kubernetes_namespace_v1.ns["training"].metadata[0].name
  }

  rule {
    api_groups = ["batch"]
    resources  = ["jobs"]
    verbs      = ["create", "get", "list", "watch", "delete"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log"]
    verbs      = ["get", "list", "watch"]
  }
}

resource "kubernetes_role_binding_v1" "training_runner" {
  metadata {
    name      = "jenkins-agent-training-runner"
    namespace = kubernetes_namespace_v1.ns["training"].metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.training_runner.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.jenkins_agent.metadata[0].name
    namespace = kubernetes_namespace_v1.ns["ci"].metadata[0].name
  }
}
