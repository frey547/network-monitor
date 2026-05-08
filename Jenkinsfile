pipeline {
    agent any

    environment {
        HARBOR_URL    = '192.168.207.129:8088'
        IMAGE_NAME    = '192.168.207.129:8088/network-monitor/app'
        DEPLOY_DIR    = '/workspace/network-monitor'
        COMPOSE_FILE  = 'docker-compose.deploy.yml'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
        skipDefaultCheckout()
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                sh 'git clone --depth 1 --branch main git@github.com:frey547/network-monitor.git .'
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
                    sh '''
                        for i in $(seq 1 30); do
                            docker exec test-network-monitor curl -sf http://127.0.0.1:8000/health && exit 0
                            sleep 2
                        done
                        echo "Health check failed after 60s"
                        docker logs test-network-monitor || true
                        exit 1
                    '''
                    echo "Test health check passed"
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

                    sleep 20

                    def health = sh(
                        script: "docker inspect --format='{{.State.Health.Status}}' network-monitor",
                        returnStdout: true
                    ).trim()
                    echo "Deploy health: ${health}"

                    if (health != 'healthy') {
                        echo "=== DEPLOY FAILED - collecting logs ==="
                        sh "cd ${DEPLOY_DIR} && docker compose -f ${COMPOSE_FILE} logs --tail=50 network-monitor || true"

                        echo "=== ROLLING BACK to build #${prevBuild} ==="
                        sh """
                            docker tag ${IMAGE_NAME}:${prevBuild} ${IMAGE_NAME}:latest || true
                            cd ${DEPLOY_DIR}
                            docker compose -f ${COMPOSE_FILE} up -d network-monitor || true
                        """
                        sleep 15

                        def rollbackHealth = sh(
                            script: "docker inspect --format='{{.State.Health.Status}}' network-monitor",
                            returnStdout: true
                        ).trim()
                        if (rollbackHealth != 'healthy') {
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
