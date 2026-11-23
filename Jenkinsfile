pipeline {
    agent { label 'python-agent' }

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    environment {
        JOB_HUNTER_DB = 'sqlite'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .jenkins-venv
                    .jenkins-venv/bin/python -m pip install --upgrade pip
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    .jenkins-venv/bin/python -m pip install -r requirements.txt
                    .jenkins-venv/bin/python -m pip install pytest
                '''
            }
        }

        stage('Run Python Tests') {
            steps {
                sh '''
                    .jenkins-venv/bin/python -m pytest -q
                '''
            }
        }
    }

    post {
        success {
            echo 'AI Job Hunter CI pipeline passed.'
        }
        failure {
            echo 'AI Job Hunter CI pipeline failed.'
        }
        always {
            deleteDir()
        }
    }
}
