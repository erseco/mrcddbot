#!/usr/bin/env groovy

pipeline {
  options {
    timeout(time: 20, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  parameters {
    string (name: 'GIT_REVISION', defaultValue: 'HEAD', description: 'Git revision to build')
    string (name: 'ENV', defaultValue: 'dev', description: 'env to deploy to')
    string (name: 'TAG', defaultValue: '', description: 'for tracking build to stage or prod')
    booleanParam (name: 'FORCE_DEPLOY', defaultValue: false, description: 'deploy irrespective of branch')
  }
  agent {
    node {
      label 'master'
      customWorkspace './exobot'
    }
  } // single node jenkins
  environment {
    ENV = "${params.ENV}"
    AWS_DEFAULT_REGION = 'us-east-1'
  }
  stages {
    stage('Git clone and setup') {
      steps {
        echo 'Checkout code'
        script {
          if (params.GIT_REVISION == 'HEAD') {
            checkout scm
          } else {
            checkout([$class: 'GitSCM',
              branches: [[name: "${params.GIT_REVISION}"]],
              userRemoteConfigs: scm.userRemoteConfigs,
              submoduleCfg: []
            ])
          }
        }
        echo 'Setup Helm'
        sh 'helm init --client-only || :'
        sh 'helm plugin install https://github.com/hypnoglow/helm-s3.git --version 0.6.0 || :'
        sh 'helm repo add machaao-helm s3://machaao-helm/charts || :'
      }
    }
    stage('Build and test') {
      steps {
        echo 'Build docker image and run unit tests'
        sh "ENV=${params.ENV} make build"
      }
    }
    stage('release') {
      when {
         expression {
          return env.BRANCH_NAME == 'main' || params.FORCE_DEPLOY
        }
      }
      steps {
        echo 'Package and push image and chart artifacts'
        sh 'make release'
      }
    }
    stage('deploy') {
      when {
         expression {
          return env.BRANCH_NAME == 'main' || params.FORCE_DEPLOY
        }
      }
      steps {
        echo 'Package and push image and chart artifacts'
        echo "Deploy to ${params.ENV}"
        withCredentials([file(credentialsId: "${params.ENV}-kubecfg", variable:'KUBECONFIG')]) {
          sh "ENV=${params.ENV} make deploy"
        }
      }
    }
  }
  post {
    always {
        echo 'Cleaning Workspace'
        cleanWs()
    }
  }
}
