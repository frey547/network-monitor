pipeline {
    agent any

    stages {
        stage('拉取代码') {
            steps {
                git 'https://github.com/frey547/network-monitor.git'
            }
        }

        stage('构建镜像') {
            steps {
                sh 'docker build -t network-monitor:latest .'
            }
        }

        stage('运行容器') {
            steps {
                sh '''
                docker rm -f network-monitor || true
                docker run -d -p 8080:8000 --name network-monitor network-monitor:latest
                '''
            }
        }
    }
}
