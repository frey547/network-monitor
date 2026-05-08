pipeline {
    agent any

    environment {
        HARBOR_URL    = '192.168.207.129:8088'
        IMAGE_NAME    = '192.168.207.129:8088/network-monitor/app'
        DEPLOY_DIR    = '/home/s/network-monitor'
        COMPOSE_FILE  = 'docker-compose.deploy.yml'
        HEALTH_URL    = 'http://127.0.0.1:8001/health'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                git url: 'git@github.com:frey547/network-monitor.git',
                    branch: 'main',
                    credentialsId: 'github-ssh'
            }
        }

        stage('Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest ."
            }
        }

        stage('Test') {
            steps {
                script {
                    sh 'docker rm -f test-network-monitor || true'
                    sh "docker run -d --name test-network-monitor ${IMAGE_NAME}:${BUILD_NUMBER}"
                    sleep 10
                    def code = sh(
                        script: "docker exec test-network-monitor curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health",
                        returnStdout: true
                    ).trim()
                    echo "Health check: HTTP ${code}"
                    if (code != '200') {
                        sh 'docker logs test-network-monitor || true'
                        error "Health check failed with HTTP ${code}"
                    }
                }
            }
            post {
                always {
                    sh 'docker rm -f test-network-monitor || true'
                }
            }
        }

        stage('Push Harbor') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'harbor',
                    usernameVariable: 'HARBOR_USER',
                    passwordVariable: 'HARBOR_PASS'
                )]) {
                    sh 'echo $HARBOR_PASS | docker login $HARBOR_URL -u $HARBOR_USER --password-stdin'
                }
                sh "docker push ${IMAGE_NAME}:${BUILD_NUMBER}"
                sh "docker push ${IMAGE_NAME}:latest"
            }
        }

        stage('Deploy') {
            steps {
                script {
                    def prevBuild = "${BUILD_NUMBER.toInteger() - 1}"

                    sh """
                        cd ${DEPLOY_DIR}
                        docker compose -f ${COMPOSE_FILE} pull network-monitor
                        docker compose -f ${COMPOSE_FILE} up -d network-monitor
                    """

                    sleep 15

                    def code = sh(
                        script: "curl -sf -o /dev/null -w '%{http_code}' ${HEALTH_URL}",
                        returnStatus: true
                    )

                    if (code != 0) {
                        echo "=== DEPLOY FAILED - collecting logs ==="
                        sh "cd ${DEPLOY_DIR} && docker compose -f ${COMPOSE_FILE} logs --tail=50 network-monitor || true"

                        echo "=== ROLLING BACK to build #${prevBuild} ==="
                        sh """
                            docker tag ${IMAGE_NAME}:${prevBuild} ${IMAGE_NAME}:latest || true
                            cd ${DEPLOY_DIR}
                            docker compose -f ${COMPOSE_FILE} up -d network-monitor || true
                        """
                        sleep 10

                        def rollbackCode = sh(
                            script: "curl -sf -o /dev/null -w '%{http_code}' ${HEALTH_URL}",
                            returnStatus: true
                        )
                        if (rollbackCode != 0) {
                            error "Rollback also failed. Manual intervention required."
                        }
                        error "Deploy failed. Rolled back to build #${prevBuild}."
                    }

                    echo "Deploy successful - build #${BUILD_NUMBER} is live."
                }
            }
        }
    }

    post {
        always {
            sh "docker rmi ${IMAGE_NAME}:${BUILD_NUMBER} || true"
            cleanWs()
        }
        success {
            echo "Pipeline #${BUILD_NUMBER} completed successfully."
        }
        failure {
            echo "Pipeline #${BUILD_NUMBER} failed. Check logs above."
        }
    }
}
