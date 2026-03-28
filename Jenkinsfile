pipeline {
    agent any

    environment {
        IMAGE_NAME = "network-monitor"
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
                sh "docker build -t ${IMAGE_NAME}:latest ."
            }
        }

        stage('Health Check') {
            steps {
                script {
                    sh "docker rm -f temp-${IMAGE_NAME} || true"
                    sh "docker run -d --name temp-${IMAGE_NAME} -p 8081:8000 ${IMAGE_NAME}:latest"
                    sleep 25
                    def result = sh(script: "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/health", returnStdout: true).trim()
                    if (result != '200') {
                        error "Health check failed: HTTP ${result}"
                    }
                    sh "docker stop temp-${IMAGE_NAME} && docker rm temp-${IMAGE_NAME}"
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
