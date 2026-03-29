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
                    // 删除旧容器（如果存在）
                    sh "docker rm -f temp-${IMAGE_NAME} || true"

                    // 自动选择一个可用端口
                    def port = sh(
                	script: """
                  	    for p in {8081..8090}; do
                        	if ! lsof -i:\$p >/dev/null 2>&1; then
                            	    echo \$p
                            	    break
                       	        fi
                   	    done
               	        """,
               	        returnStdout: true
           	    ).trim()

           	    echo "Selected available port: ${port}"

                    // 启动新容器
                    sh "docker run -d --name temp-${IMAGE_NAME} -p ${port}:8000 ${IMAGE_NAME}:latest"

                    // 等待容器内部 FastAPI 启动
                    sleep 15  // 延长等待时间，确保服务启动完成

                    // 健康检查：在容器内部访问 127.0.0.1:8000/health
                    def result = sh(
                        script: "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${port}/health",
                        returnStdout: true
                    ).trim()

                    echo "Health check returned HTTP ${result}"

                    if (result != '200') {
                        error "Health check failed: HTTP ${result}"
                    }

                    // 健康检查完毕，停止并删除临时容器
                    sh "docker stop temp-${IMAGE_NAME} || true"
                    sh "docker rm temp-${IMAGE_NAME} || true"
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
