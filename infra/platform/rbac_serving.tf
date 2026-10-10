# What the Jenkins agent may do in the serving namespace: deploy and check the inference service
resource "kubernetes_role_v1" "serving_deployer" {
  metadata {
    name      = "serving-deployer"
    namespace = kubernetes_namespace_v1.ns["serving"].metadata[0].name
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments"]
    verbs      = ["get", "list", "watch", "create", "update", "patch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["replicasets"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = [""]
    resources  = ["services"]
    verbs      = ["get", "list", "watch", "create", "update", "patch"]
  }

  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch", "create", "update", "patch"]
  }

  rule {
    api_groups = ["traefik.io"]
    resources  = ["middlewares"]
    verbs      = ["get", "list", "watch", "create", "update", "patch"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = [""]
    resources  = ["pods/log"]
    verbs      = ["get"]
  }

  # Needed to run the webhook registration inside the pod
  rule {
    api_groups = [""]
    resources  = ["pods/exec"]
    verbs      = ["create"]
  }
}

resource "kubernetes_role_binding_v1" "serving_deployer" {
  metadata {
    name      = "jenkins-agent-serving-deployer"
    namespace = kubernetes_namespace_v1.ns["serving"].metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.serving_deployer.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.jenkins_agent.metadata[0].name
    namespace = kubernetes_namespace_v1.ns["ci"].metadata[0].name
  }
}
