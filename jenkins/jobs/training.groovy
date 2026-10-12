pipelineJob('training_jenkins_pipeline') {
  description('Train the bank marketing model and log it to MLflow')
  parameters {
    stringParam('GIT_BRANCH', 'main', 'Branch to build')
    stringParam('LEARNING_RATE', '0.1', 'Learning rate')
    stringParam('MAX_ITER', '200', 'Boosting iterations')
    choiceParam('MAX_DEPTH', ['6', '4', '8', '10'], 'Max tree depth')
    stringParam('MLFLOW_EXPERIMENT', 'bank-marketing', 'MLflow experiment name')
    booleanParam('PROMOTE', true, 'Register the model and move champion if it beats the current champion')
    choiceParam('PROMOTION_MIN_DELTA', ['0.002', '0', '0.001', '0.005', '0.01'], 'Minimum pr_auc gain over the champion (0 also accepts a tie)')
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
