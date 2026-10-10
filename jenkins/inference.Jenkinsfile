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

  environment {
    REGISTRY = 'mlops-registry.localhost:5000'
    APP      = 'inference'
    NS       = 'serving'
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
            env.TAG = sh(returnStdout: true, script: '''
              git ls-files inference | grep -v -E '^inference/(k8s|scripts)/' | xargs sha256sum | sha256sum | cut -c1-12
            ''').trim()
            def exists = sh(returnStatus: true, script: '''
              REG_IP=$(getent hosts mlops-registry.localhost | cut -d' ' -f1)
              curl -sf --resolve mlops-registry.localhost:5000:$REG_IP http://$REGISTRY/v2/$APP/tags/list | grep -qF "\\"$TAG\\""
            ''') == 0
            env.BUILD_IMAGE = (!exists || params.FORCE_BUILD) ? 'true' : 'false'
            echo "Image tag ${env.TAG}, already in registry: ${exists}"
          }
        }
      }
    }

    stage('Build and push image') {
      when { expression { env.BUILD_IMAGE == 'true' } }
      steps {
        container('kaniko') {
          sh '''
            /kaniko/executor \
              --context=dir://$WORKSPACE/inference \
              --dockerfile=$WORKSPACE/inference/docker/Dockerfile \
              --target=runtime \
              --destination=$REGISTRY/$APP:$TAG \
              --insecure --skip-tls-verify
          '''
        }
      }
    }

    stage('Deploy') {
      steps {
        script { env.DEPLOY_STARTED = 'true' }
        container('kubectl') {
          sh '''
            export IMAGE=$REGISTRY/$APP:$TAG
            envsubst '${IMAGE}' < inference/k8s/app.yaml > /tmp/app.yaml
            kubectl apply --dry-run=server -f /tmp/app.yaml
            kubectl apply -f /tmp/app.yaml
            kubectl rollout status deployment/$APP -n $NS --timeout=240s
          '''
        }
      }
    }

    stage('Smoke test') {
      steps {
        container('kubectl') {
          sh '''
            URL=http://$APP.$NS.svc.cluster.local
            curl -sf $URL/health
            echo
            curl -sf -X POST $URL/predict -H 'Content-Type: application/json' \
              -d '{"age":40,"job":"blue-collar","marital":"married","education":"primary","default":"no","balance":640,"housing":"yes","loan":"no","contact":"unknown","day":8,"month":"may","duration":347,"campaign":2,"pdays":-1,"previous":0,"poutcome":"unknown"}' \
              | tee /tmp/predict.json
            echo
            grep -q '"probability"' /tmp/predict.json
          '''
        }
        script { env.DEPLOY_VERIFIED = 'true' }
      }
    }

    stage('Register webhook') {
      steps {
        container('kubectl') {
          // Idempotent: prints "already exists, nothing to do" when the webhook is registered
          sh 'kubectl exec -i -n $NS deploy/$APP -- python - < inference/scripts/register_webhook.py'
        }
      }
    }
  }

  post {
    failure {
      script {
        // Roll back only if the new version was deployed but did not pass the smoke test.
        // A failure before the deploy changed nothing, and a failed registration is not an image problem.
        if (env.DEPLOY_STARTED == 'true' && env.DEPLOY_VERIFIED != 'true') {
          container('kubectl') {
            sh 'kubectl rollout undo deployment/$APP -n $NS || true'
          }
        }
      }
    }
  }
}
