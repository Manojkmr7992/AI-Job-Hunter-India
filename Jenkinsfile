
pipeline {
    agent { label 'python-agent' }

    options {
        timestamps()
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }

    environment {
        JOB_HUNTER_DB = 'sqlite'

        APP_NAME = 'ai-job-hunter-app'
        IMAGE_NAME = 'ai-job-hunter-india'

        DB_FILE = '/Users/manojkavuluru/.local/share/ai-job-hunter-india/jobs.sqlite3'

        PROFILE_FILE = '/Users/manojkavuluru/Documents/AI-Job-Hunter-India/ai_job_hunter_step1/candidate_profile.json'
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
                    set -eu

                    python3 --version
                    python3 -m venv .jenkins-venv

                    .jenkins-venv/bin/python -m pip install --upgrade pip
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -eu

                    .jenkins-venv/bin/python -m pip install -r requirements.txt

                    .jenkins-venv/bin/python -m pip install pytest
                '''
            }
        }

        stage('Run Python Tests') {
            steps {
                sh '''
                    set -eu

                    .jenkins-venv/bin/python -m pytest -q
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    docker build \
                        -t "${IMAGE_NAME}:${BUILD_NUMBER}" \
                        -t "${IMAGE_NAME}:latest" \
                        .
                '''
            }
        }

        stage('Validate Deployment Prerequisites') {
            steps {
                sh '''
                    set -eu

                    # Confirm both host files exist and are readable.
                    # Docker resolves these paths on the Docker host.
                    docker run --rm \
                        --entrypoint /bin/sh \
                        --mount "type=bind,source=${DB_FILE},target=/data/jobs.sqlite3,readonly" \
                        --mount "type=bind,source=${PROFILE_FILE},target=/data/candidate_profile.json,readonly" \
                        "${IMAGE_NAME}:${BUILD_NUMBER}" \
                        -c 'test -f /data/jobs.sqlite3 && test -r /data/jobs.sqlite3 && test -f /data/candidate_profile.json && test -r /data/candidate_profile.json'

                    # Require an existing healthy application before
                    # the first automated replacement.
                    test "$(docker inspect \
                        --format '{{.State.Health.Status}}' \
                        "${APP_NAME}")" = "healthy"

                    echo "Deployment prerequisites verified."
                '''
            }
        }

        stage('Deploy and Verify Application') {
            steps {
                sh '''
                    set -eu

                    rollback_name="${APP_NAME}-rollback"

                    # Ensure the existing application is healthy.
                    old_status=$(docker inspect \
                        --format '{{.State.Health.Status}}' \
                        "${APP_NAME}")

                    if [ "$old_status" != "healthy" ]; then
                        echo "Existing application is not healthy."
                        exit 1
                    fi

                    # Clear a previous rollback container only after
                    # verifying the current application is healthy.
                    if docker container inspect "$rollback_name" >/dev/null 2>&1; then
                        docker rm -f "$rollback_name"
                    fi

                    # Save the current application as rollback.
                    docker stop "${APP_NAME}"
                    docker rename "${APP_NAME}" "$rollback_name"

                    # Any failure after this point restores the old app.
                    rollback() {
                        echo "Deployment failed. Restoring previous application."

                        docker rm -f "${APP_NAME}" 2>/dev/null || true

                        if docker container inspect "$rollback_name" >/dev/null 2>&1; then
                            docker rename "$rollback_name" "${APP_NAME}"
                            docker start "${APP_NAME}"

                            echo "Previous application restarted."
                        else
                            echo "ERROR: Rollback container missing."
                        fi
                    }

                    trap 'rollback' EXIT

                    # Start the newly built application.
                    docker run -d \
                        --name "${APP_NAME}" \
                        --restart unless-stopped \
                        --network bridge \
                        --publish 127.0.0.1:8501:8501 \
                        --env JOB_HUNTER_DB=sqlite \
                        --mount "type=bind,source=${DB_FILE},target=/app/jobs.sqlite3" \
                        --mount "type=bind,source=${PROFILE_FILE},target=/app/candidate_profile.json,readonly" \
                        "${IMAGE_NAME}:${BUILD_NUMBER}"

                    echo "Waiting for application health check."

                    healthy=0

                    for attempt in $(seq 1 45); do
                        status=$(docker inspect \
                            --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
                            "${APP_NAME}")

                        echo "Health check ${attempt}: ${status}"

                        if [ "$status" = "healthy" ]; then
                            healthy=1
                            break
                        fi

                        if [ "$status" = "unhealthy" ] || \
                           [ "$status" = "no-healthcheck" ]; then
                            break
                        fi

                        sleep 2
                    done

                    if [ "$healthy" -ne 1 ]; then
                        echo "New application failed its health check."
                        exit 1
                    fi

                    # New deployment succeeded.
                    # Disable automatic rollback.
                    trap - EXIT

                    echo "Application deployed successfully."
                    echo "Previous container retained for rollback."
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: CI/CD pipeline completed.'
            echo 'Python tests passed.'
            echo 'Docker image built.'
            echo 'Application deployed and healthy.'
            echo 'Application URL: http://localhost:8501'
        }

        failure {
            echo 'FAILURE: CI/CD pipeline failed.'
            echo 'Check the console output for the failing stage.'
        }

        always {
            deleteDir()
        }
    }
}
