pipeline {
    agent any

    environment {
        IMAGE_NAME = "network-monitor"
        IMAGE_TAG  = "${BUILD_NUMBER}"
        DOCKER_REGISTRY = "fre-docker-hub"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10')) // 保留最近10个构建
        timestamps()                                  // 日志带时间戳
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm  // 自动从 Jenkins Job 配置的 SCM 拉取代码
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install --upgrade pip'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh '. venv/bin/activate && pytest -v || true'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Health Check') {
            steps {
                script {
                    // 删除旧容器（如果存在）
                    sh "docker rm -f temp-${IMAGE_NAME} || true"
                    // 启动容器
                    sh "docker run -d --name temp-${IMAGE_NAME} ${IMAGE_NAME}:latest"


                    // 等待容器内 FastAPI 启动完成
                    sleep 15  // 可根据服务启动时间调整

                    // 健康检查
                    def result = sh(
                        script: "docker exec temp-${IMAGE_NAME} curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health",
                        returnStdout: true
                    ).trim()

                    echo "Health check returned HTTP ${result}"

                    if (result != '200') {
                        
                        sh "docker logs temp-${IMAGE_NAME} || true"
                        sh "docker rm -f temp-${IMAGE_NAME} || true"
                        error "Health check failed"
                    }

                    // 健康检查成功，停止并删除临时容器
                    //sh "docker stop temp-${IMAGE_NAME} || true"
                    sh "docker rm -f temp-${IMAGE_NAME} || true"
                }
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'docker-hub-creds', 
                                                  usernameVariable: 'DOCKER_USER', 
                                                  passwordVariable: 'DOCKER_PASS')]) {
                    sh 'docker login -u $DOCKER_USER -p $DOCKER_PASS'
                }
            }
        }
        stage('Push Image') {
            steps {
                sh """
                docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                docker tag ${IMAGE_NAME}:latest ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                """
            }
        }

        stage('Deploy') {
            steps {
                script {
                    sh "docker rm -f ${IMAGE_NAME} || true"
                    sh "docker pull ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
                    sh """
                    docker run -d \
                      -p 8082:8000 \
                      --name ${IMAGE_NAME} \
                      ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                    """
                }
            }
        }
    }

    post {
        always {
            echo 'Cleaning up temporary resources...'
            sh "docker system prune -f || true"
        }
        success {
            echo 'Build and CI pipeline completed successfully!'
        }
        failure {
            echo 'Build failed. Check logs for details.'
        }
    }
}
