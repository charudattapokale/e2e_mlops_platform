pipelineJob('training_jenkins_pipeline') {
  description('Train the bank marketing model and log it to MLflow')
  parameters {
    stringParam('GIT_BRANCH', 'main', 'Branch to build')
    stringParam('LEARNING_RATE', '0.1', 'Learning rate')
    stringParam('MAX_ITER', '200', 'Boosting iterations')
    choiceParam('MAX_DEPTH', ['6', '4', '8', '10'], 'Max tree depth')
    stringParam('MLFLOW_EXPERIMENT', 'bank-marketing', 'MLflow experiment name')
  }
  definition {
    cpsScm {
      scm {
        git {
          remote { url('https://github.com/charudattapokale/e2e_mlops_platform.git') }
          branch('*/main')
        }
      }
      scriptPath('jenkins/training.Jenkinsfile')
      lightweight(true)
    }
  }
}
