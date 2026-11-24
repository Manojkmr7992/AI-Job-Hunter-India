
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

        POSTGRES_CONTAINER = 'ai-job-hunter-postgres'
        APP_NETWORK = 'ai-job-hunter-network'

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

                    export JOB_HUNTER_DB=sqlite
                    unset DATABASE_URL

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
                        .
                '''
            }
        }

        stage('Validate Deployment Prerequisites') {
            steps {
                sh '''
                    set -eu

                    docker network inspect "${APP_NETWORK}" >/dev/null

                    test "$(docker inspect \
                        --format '{{.State.Health.Status}}' \
                        "${POSTGRES_CONTAINER}")" = "healthy"

                    test "$(docker inspect \
                        --format '{{.State.Health.Status}}' \
                        "${APP_NAME}")" = "healthy"

                    docker run --rm \
                        --entrypoint /bin/sh \
                        --mount "type=bind,source=${PROFILE_FILE},target=/data/candidate_profile.json,readonly" \
                        "${IMAGE_NAME}:${BUILD_NUMBER}" \
                        -c 'test -f /data/candidate_profile.json && test -r /data/candidate_profile.json'

                    echo "PASS: Deployment prerequisites verified."
                '''
            }
        }

        stage('Validate PostgreSQL Connectivity') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'ai-job-hunter-postgres-env',
                        variable: 'PG_ENV_FILE'
                    )
                ]) {
                    sh '''
                        set +x
                        set -eu

                        docker run --rm -i \
                            --network "${APP_NETWORK}" \
                            --env-file "${PG_ENV_FILE}" \
                            --entrypoint python \
                            "${IMAGE_NAME}:${BUILD_NUMBER}" - <<'PY'
from postgres_store import postgres_enabled, engine
from sqlalchemy import text

assert postgres_enabled(), "PostgreSQL backend disabled"

with engine().connect() as conn:
    database = conn.execute(
        text("SELECT current_database()")
    ).scalar_one()

    user = conn.execute(
        text("SELECT current_user")
    ).scalar_one()

    assert database == "ai_job_hunter"
    assert user == "job_hunter_user"

    count = conn.execute(
        text("SELECT COUNT(*) FROM public.jobs")
    ).scalar_one()

    print("Database:", database)
    print("Connected user:", user)
    print("Job records:", count)

print("PASS: PostgreSQL connectivity verified.")
PY
                    '''
                }
            }
        }

        stage('Deploy and Verify Application') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'ai-job-hunter-postgres-env',
                        variable: 'PG_ENV_FILE'
                    )
                ]) {
                    sh '''
                        set +x
                        set -eu

                        rollback_name="${APP_NAME}-rollback-${BUILD_NUMBER}"

                        test "$(docker inspect \
                            --format '{{.State.Health.Status}}' \
                            "${APP_NAME}")" = "healthy"

                        if docker container inspect "$rollback_name" >/dev/null 2>&1; then
                            echo "Rollback container already exists."
                            exit 1
                        fi

                        old_id=$(docker inspect \
                            --format '{{.Id}}' "${APP_NAME}")

                        rollback() {
                            rc=$?

                            trap - EXIT
                            set +e

                            if [ "$rc" -eq 0 ]; then
                                exit 0
                            fi

                            echo "Deployment failed. Attempting rollback."

                            if docker container inspect "$rollback_name" >/dev/null 2>&1; then

                                current_id=$(docker inspect \
                                    --format '{{.Id}}' "${APP_NAME}" 2>/dev/null || true)

                                if [ -n "$current_id" ] && [ "$current_id" != "$old_id" ]; then
                                    docker rm -f "${APP_NAME}"
                                fi

                                docker rename "$rollback_name" "${APP_NAME}" &&
                                docker start "${APP_NAME}"

                            else
                                docker start "$old_id"
                            fi

                            restored=0

                            for attempt in $(seq 1 45); do

                                status=$(docker inspect \
                                    --format '{{.State.Health.Status}}' \
                                    "${APP_NAME}" 2>/dev/null || true)

                                if [ "$status" = "healthy" ]; then
                                    restored=1
                                    break
                                fi

                                sleep 2
                            done

                            if [ "$restored" -eq 1 ]; then
                                echo "Previous application restored and healthy."
                            else
                                echo "ERROR: Rollback requires manual intervention."
                            fi

                            exit "$rc"
                        }

                        trap rollback EXIT
                        trap 'exit 130' INT
                        trap 'exit 143' TERM

                        echo "Preserving existing application."

                        docker stop "${APP_NAME}"
                        docker rename "${APP_NAME}" "$rollback_name"

                        echo "Deploying PostgreSQL-enabled application."

                        docker run -d \
                            --name "${APP_NAME}" \
                            --restart unless-stopped \
                            --network "${APP_NETWORK}" \
                            --publish 127.0.0.1:8501:8501 \
                            --env-file "${PG_ENV_FILE}" \
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

                        test "$healthy" -eq 1

                        echo "Validating deployed PostgreSQL backend."

                        docker exec -i "${APP_NAME}" python - <<'PY'
from core import list_jobs
from postgres_store import postgres_enabled, engine
from sqlalchemy import text

assert postgres_enabled(), "PostgreSQL backend disabled"

with engine().connect() as conn:

    database = conn.execute(
        text("SELECT current_database()")
    ).scalar_one()

    user = conn.execute(
        text("SELECT current_user")
    ).scalar_one()

    assert database == "ai_job_hunter"
    assert user == "job_hunter_user"

    print("Database:", database)
    print("Connected user:", user)

print("Application job count:", len(list_jobs()))
print("PASS: Application PostgreSQL backend verified.")
PY

                        docker tag \
                            "${IMAGE_NAME}:${BUILD_NUMBER}" \
                            "${IMAGE_NAME}:latest"

                        trap - EXIT INT TERM

                        echo "Application deployed successfully."
                        echo "Rollback container: $rollback_name"
                    '''
                }
            }
        }
    }

    post {

        success {
            echo 'SUCCESS: CI/CD pipeline completed.'
            echo 'Python regression tests passed.'
            echo 'Docker image built successfully.'
            echo 'PostgreSQL connectivity verified.'
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
