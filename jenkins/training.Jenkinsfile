pipeline {
  agent {
    kubernetes {
      namespace 'ci'
      yamlFile 'jenkins/agent-pod.yaml'
    }
  }

  options {
    disableConcurrentBuilds()
    timeout(time: 30, unit: 'MINUTES')
  }

  parameters {
    string(name: 'GIT_BRANCH',        defaultValue: 'main',           description: 'Branch to build')
    string(name: 'LEARNING_RATE',     defaultValue: '0.1',            description: 'Learning rate')
    string(name: 'MAX_ITER',          defaultValue: '200',            description: 'Boosting iterations')
    string(name: 'MAX_DEPTH',         defaultValue: '6',              description: 'Max tree depth')
    string(name: 'MLFLOW_EXPERIMENT', defaultValue: 'bank-marketing', description: 'MLflow experiment name')
  }

  environment {
    REGISTRY = 'mlops-registry.localhost:5000'
  }

  stages {
    stage('Checkout') {
      steps {
        git url: 'https://github.com/charudattapokale/e2e_mlops_platform.git',
            branch: params.GIT_BRANCH
      }
    }

    stage('Check image') {
      steps {
        container('kubectl') {
          script {
            env.TAG = sh(returnStdout: true, script:
              "git ls-files training | grep -v -E '^training/(k8s|docker/docker-compose.yml)' | xargs sha256sum | sha256sum | cut -c1-12").trim()
            def rc = sh(returnStatus: true, script:
              "curl -sf -o /dev/null -H 'Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json' http://${env.REGISTRY}/v2/training/manifests/${env.TAG}")
            env.IMAGE_EXISTS = (rc == 0) ? 'true' : 'false'
            echo "Image tag ${env.TAG}, already in registry: ${env.IMAGE_EXISTS}"
          }
        }
      }
    }

    stage('Build and push image') {
      when { expression { env.IMAGE_EXISTS == 'false' } }
      steps {
        container('kaniko') {
          sh """
            /kaniko/executor \
              --context=dir://\$WORKSPACE/training \
              --dockerfile=\$WORKSPACE/training/docker/Dockerfile \
              --target=runtime \
              --destination=${env.REGISTRY}/training:${env.TAG} \
              --insecure --skip-tls-verify
          """
        }
      }
    }

    stage('Run training job') {
      steps {
        container('kubectl') {
          sh """
            export IMAGE=${env.REGISTRY}/training:${env.TAG}
            export BUILD_NUMBER=${env.BUILD_NUMBER}
            export LEARNING_RATE=${params.LEARNING_RATE}
            export MAX_ITER=${params.MAX_ITER}
            export MAX_DEPTH=${params.MAX_DEPTH}
            export MLFLOW_EXPERIMENT=${params.MLFLOW_EXPERIMENT}
            envsubst < training/k8s/job.yaml | kubectl apply -f -
          """
        }
      }
    }

    stage('Wait and logs') {
      steps {
        container('kubectl') {
          sh """
            kubectl wait --for=condition=complete job/training-${env.BUILD_NUMBER} -n training --timeout=20m &
            kubectl wait --for=condition=failed   job/training-${env.BUILD_NUMBER} -n training --timeout=20m &
            wait -n
            kubectl logs -n training job/training-${env.BUILD_NUMBER}
            kubectl get job training-${env.BUILD_NUMBER} -n training -o jsonpath='{.status.succeeded}' | grep -q 1
          """
        }
      }
    }
  }

  post {
    always {
      container('kubectl') {
        sh "kubectl delete job training-${env.BUILD_NUMBER} -n training --ignore-not-found"
      }
    }
  }
}
