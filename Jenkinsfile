pipeline {
    agent any

    environment {
        IMAGE_NAME = "fre547/network-monitor"
        DOCKER_CREDENTIALS = "fre-docker-hub"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest ."
            }
        }

        stage('Health Check') {
            steps {
                script {
                    sh "docker rm -f temp-network-monitor || true"
                    sh "docker run -d --name temp-network-monitor ${IMAGE_NAME}:latest"
                    sleep 15
                    def result = sh(
                        script: "docker exec temp-network-monitor curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health",
                        returnStdout: true
                    ).trim()
                    echo "Health check returned HTTP ${result}"
                    if (result != '200') {
                        sh "docker logs temp-network-monitor || true"
                        sh "docker rm -f temp-network-monitor || true"
                        error "Health check failed"
                    }
                    sh "docker rm -f temp-network-monitor || true"
                }
            }
        }

        stage('Docker Login & Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${DOCKER_CREDENTIALS}",
                                                  usernameVariable: 'DOCKER_USER',
                                                  passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                    echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                    '''
                }
                sh """
                docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                docker push ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Deploy') {
            steps {
                sh "docker rm -f network-monitor || true"
                sh """
                docker run -d \
                  -p 8001:8000 \
                  --name network-monitor \
                  --restart unless-stopped \
                  ${IMAGE_NAME}:latest
                """
            }
        }
    }

    post {
        always {
            sh "docker system prune -f || true"
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check logs.'
        }
    }
}
