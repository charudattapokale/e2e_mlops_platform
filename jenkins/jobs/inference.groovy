pipelineJob('inference_jenkins_pipeline') {
  description('Build the inference image (skipped when unchanged), deploy it to the serving namespace and register the MLflow webhook')
  parameters {
    stringParam('GIT_BRANCH', 'main', 'Branch to build')
  }
  definition {
    cpsScm {
      scm {
        git {
          remote { url('https://github.com/charudattapokale/e2e_mlops_platform.git') }
          branch('*/main')
        }
      }
      scriptPath('jenkins/inference.Jenkinsfile')
      lightweight(true)
    }
  }
}
