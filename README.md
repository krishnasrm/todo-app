# End-to-end CI/CD Pipeline: Jenkins + Docker Hub + Kubernetes

A Python Flask To-Do API deployed on a self-managed 3-node Kubernetes cluster
with a fully automated CI/CD pipeline. Every push to GitHub automatically builds
a Docker image, pushes it to Docker Hub with a versioned tag, and performs a
zero-downtime rolling update on Kubernetes.

//![Architecture](screenshots/architecture.png)

## Tech stack
| Area | Tool |
|------|------|
| Application | Python, Flask |
| Version control | Git, GitHub |
| CI/CD | Jenkins declarative pipeline (configured in Jenkins dashboard) |
| Containerization | Docker |
| Image registry | Docker Hub: krishnasrm1423/todo-app |
| Orchestration | Kubernetes v1.37 (kubeadm), containerd, Calico |
| OS | Red Hat Enterprise Linux 9 |

## Infrastructure
| Node | Role | IP |
|------|------|----|
| k8s-master | Control plane + Jenkins | 192.168.119.134 |
| k8s-worker1 | Worker | 192.168.119.135 |
| k8s-worker2 | Worker | 192.168.119.136 |

## How it works
1. Developer pushes code to the `main` branch on GitHub
2. Jenkins detects the change (Poll SCM every 2 minutes)
3. Checkout: Jenkins clones the repo
4. Build: builds a Docker image tagged `v<BUILD_NUMBER>`
5. Push: logs in to Docker Hub using Jenkins Credentials and pushes the image
6. Deploy: updates the image in the Kubernetes manifest, applies it and waits for the rollout
7. Kubernetes performs a rolling update across 2 replicas with readiness and liveness probes

## Project structure
| File | Purpose |
|------|---------|
| app.py | Flask REST API with health endpoint |
| requirements.txt | Pinned Python dependencies |
| Dockerfile | Builds the container image using layer caching |
| .dockerignore | Keeps unnecessary files out of the image |
| .gitignore | Keeps cache and secret files out of Git |
| k8s/deployment.yaml | Kubernetes Deployment (2 replicas, probes) and NodePort Service |

## Jenkins pipeline
~~~groovy
pipeline {
  agent any
  environment {
    IMAGE = "krishnasrm1423/todo-app"
    TAG   = "v${BUILD_NUMBER}"
  }
  stages {
    stage('Checkout') {
      steps {
        git branch: 'main', credentialsId: 'github-creds',
            url: 'https://github.com/krishnasrm/todo-app.git'
      }
    }
    stage('Build') {
      steps { sh 'docker build -t $IMAGE:$TAG .' }
    }
    stage('Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
          usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
          sh 'docker push $IMAGE:$TAG'
        }
      }
    }
    stage('Deploy') {
      steps {
        sh 'sed -i "s|image: .*|image: $IMAGE:$TAG|" k8s/deployment.yaml'
        sh 'kubectl apply -f k8s/deployment.yaml'
        sh 'kubectl rollout status deployment/todo-app --timeout=120s'
      }
    }
  }
  post {
    always { sh 'docker logout || true' }
  }
}
~~~

## Screenshots
### Jenkins pipeline
//![Jenkins](screenshots/jenkins-pipeline.png)

### Docker Hub versioned images
//![Docker Hub](screenshots/dockerhub-tags.png)

### Kubernetes cluster
//![Pods](screenshots/kubectl-pods.png)

### Live application
//![App](screenshots/app-output.png)

## API endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | App status and version |
| GET | /health | Health check used by Kubernetes probes |
| GET | /todos | List all todos |
| POST | /todos | Add a todo: {"task": "learn devops"} |

## Run locally
//~~~bash
//docker build -t krishnasrm1423/todo-app:v1.0 .
//docker run -d -p 5000:5000 krishnasrm1423/todo-app:v1.0
//curl http://localhost:5000
//~~~

## Deploy manually to Kubernetes
//~~~bash
//kubectl apply -f k8s/deployment.yaml
//kubectl get pods -o wide
//curl http://<worker-node-ip>:30007
//~~~

## Challenges faced and solutions
| Problem | Cause | Solution |
|---------|-------|----------|
| curl returned "connection reset" right after docker run | Flask had not finished starting | Waited for startup, checked docker logs |
| Jenkins could not run docker/kubectl | Jenkins runs as the jenkins user | Added user to docker group and copied kubeconfig to /var/lib/jenkins/.kube |
| NodePort refused on localhost | Pods run on worker nodes; NodePort not served on localhost | Accessed the app via worker node IP |
| NodePort blocked | RHEL 9 firewalld | Opened ports 30000-32767/tcp on all nodes |

## Security practices
- Docker Hub and GitHub tokens stored in Jenkins Credentials, never in code
- Credentials masked in Jenkins console output
- docker logout after every build

## Future improvements
- Trivy image vulnerability scanning stage
- SonarQube code quality analysis
- Helm chart packaging
- Prometheus and Grafana monitoring
- Server provisioning with Ansible
