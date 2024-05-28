
# steps:
#prep: make sure you have jq, aws-cli, kubectl, helm and argocd-cli installed
# 1. terraform files:
#create a dir for your terrafor files:
```
mkdir tf_files
cd ./tf_files
```
#data.tf (change ubuntu to another AMI if you don't plan to have the cluster being alive more than 30 min):
```
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

# ebs-csi.tf:
resource "aws_iam_policy" "eks_worknode_ebs_policy" {
  name = "Amazon_EBS_CSI_Driver"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AttachVolume",
        "ec2:CreateSnapshot",
        "ec2:CreateTags",
        "ec2:CreateVolume",
        "ec2:DeleteSnapshot",
        "ec2:DeleteTags",
        "ec2:DeleteVolume",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DetachVolume"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
}

# And attach the new policy
resource "aws_iam_role_policy_attachment" "worknode-AmazonEBSCSIDriver" {
  policy_arn = aws_iam_policy.eks_worknode_ebs_policy.arn
  role       = aws_iam_role.worker.name
}
```
#eks.tf:
```
#Creating EKS Cluster
resource "aws_eks_cluster" "eks" {
  name     = "pc-eks"
  role_arn = aws_iam_role.master.arn

  vpc_config {
    subnet_ids = [aws_subnet.Mysubnet01.id, aws_subnet.Mysubnet02.id]
  }

  tags = {
    "Name" = "MyEKS"
  }

  depends_on = [
    aws_iam_role_policy_attachment.AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.AmazonEKSServicePolicy,
    aws_iam_role_policy_attachment.AmazonEKSVPCResourceController,
  ]
}

resource "aws_eks_node_group" "node-grp" {
  cluster_name    = aws_eks_cluster.eks.name
  node_group_name = "pc-node-group"
  node_role_arn   = aws_iam_role.worker.arn
  subnet_ids      = [aws_subnet.Mysubnet01.id, aws_subnet.Mysubnet02.id]
  capacity_type   = "ON_DEMAND"
  disk_size       = 20
  instance_types  = ["t3.medium"]

  remote_access {
    ec2_ssh_key               = "kubernetes"
    source_security_group_ids = [aws_security_group.allow_tls.id]
  }

  labels = {
    env = "dev"
  }

  scaling_config {
    desired_size = 2
    max_size     = 2
    min_size     = 1
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.AmazonEC2ContainerRegistryReadOnly,
  ]
}
```
#provider.tf:
```
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.41"
    }
  }
}

#Adding Provider details
provider "aws" {
  region     = "eu-north-1"
}

# roles.tf:
#Creating IAM role for EKS
resource "aws_iam_role" "master" {
  name = "ed-eks-master"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "eks.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.master.name
}

resource "aws_iam_role_policy_attachment" "AmazonEKSServicePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.master.name
}

resource "aws_iam_role_policy_attachment" "AmazonEKSVPCResourceController" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.master.name
}

resource "aws_iam_role" "worker" {
  name = "ed-eks-worker"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "ec2.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "autoscaler" {
  name = "ed-eks-autoscaler-policy"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeTags",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup",
          "ec2:DescribeLaunchTemplateVersions"
        ],
        "Effect" : "Allow",
        "Resource" : "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "AmazonEKSWorkerNodePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "AmazonEKS_CNI_Policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "AmazonSSMManagedInstanceCore" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "x-ray" {
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "s3" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
  role       = aws_iam_role.worker.name
}

resource "aws_iam_role_policy_attachment" "autoscaler" {
  policy_arn = aws_iam_policy.autoscaler.arn
  role       = aws_iam_role.worker.name
}

resource "aws_iam_instance_profile" "worker" {
  depends_on = [aws_iam_role.worker]
  name       = "ed-eks-worker-new-profile"
  role       = aws_iam_role.worker.name
}
```
#security_group.tf:
```
#Adding security group
resource "aws_security_group" "allow_tls" {
  name_prefix = "allow_tls_"
  description = "Allow TLS inbound traffic"
  vpc_id      = aws_vpc.myvpc.id

  ingress {
    description = "TLS from VPC"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```
#subnets.tf:
```
#Create Subnets
resource "aws_subnet" "Mysubnet01" {
  vpc_id                  = aws_vpc.myvpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "eu-north-1a"
  map_public_ip_on_launch = true
  tags = {
    "Name" = "MyPublicSubnet01"
  }
}

resource "aws_subnet" "Mysubnet02" {
  vpc_id                  = aws_vpc.myvpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "eu-north-1b"
  map_public_ip_on_launch = true
  tags = {
    "Name" = "MyPublicSubnet02"
  }
}

# Associate Subnets with the Route Table
resource "aws_route_table_association" "Mysubnet01_association" {
  route_table_id = aws_route_table.myroutetable.id
  subnet_id      = aws_subnet.Mysubnet01.id
}

resource "aws_route_table_association" "Mysubnet02_association" {
  route_table_id = aws_route_table.myroutetable.id
  subnet_id      = aws_subnet.Mysubnet02.id
}
```
#vpc.tf:
```
#Create a custom VPC
resource "aws_vpc" "myvpc" {
  cidr_block = "10.0.0.0/16"
  tags = {
    "Name" = "MyProjectVPC"
  }
}

# Creating Internet Gateway IGW
resource "aws_internet_gateway" "myigw" {
  vpc_id = aws_vpc.myvpc.id
  tags = {
    "Name" = "MyIGW"
  }
}

# Creating Route Table
resource "aws_route_table" "myroutetable" {
  vpc_id = aws_vpc.myvpc.id
  tags = {
    "Name" = "MyPublicRouteTable"
  }
}

# Create a Route in the Route Table with a route to IGW
resource "aws_route" "myigw_route" {
  route_table_id         = aws_route_table.myroutetable.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.myigw.id
}
```
#once all files are created:
```
terraform init
terraform apply --auto-approve
```
the setup should take about 10-15 minutes
# 2. setup kubectl context:
```
aws eks --region <your_region> update-kubeconfig --name <your_eks_name>
```
# 3. install MongoDB
#(make sure it is installed and has proper data prior to pipelines)
```
helm install mongodb-release oci://registry-1.docker.io/bitnamicharts/mongodb
```
# 3.1 insert data into mongodb:
#to get the mongodb password:
```
kubectl get secret --namespace default mongodb-release -o jsonpath="{.data.mongodb-root-password}" | base64 -d
```
#and login into the pod
```
kubectl exec -it <mongodb-pod-number> bash
mongosh -u <user_name> -p <password>
```
#once inside run the following:
```
show dbs
use shop_db

db.users.insertMany([
    {
        "userID": "user1",
        "userName": "Alice",
        "purchases": ["item1", "item3", "item5"]
    },
    {
        "userID": "user2",
        "userName": "Bob",
        "purchases": ["item2", "item4"]
    },
    {
        "userID": "user3",
        "userName": "Charlie",
        "purchases": ["item1", "item4", "item6"]
    },
    {
        "userID": "user4",
        "userName": "Diana",
        "purchases": ["item3", "item5"]
    },
    {
        "userID": "user5",
        "userName": "Eve",
        "purchases": ["item2", "item6"]
    }
])

db.items.insertMany([
     {
        "itemID": "item1",
        "name": "Xbox",
        "price": 299.99
    },
    {
        "itemID": "item2",
        "name": "PlayStation",
        "price": 499.99
    },
    {
        "itemID": "item3",
        "name": "PC",
        "price": 999.99
    },
    {
        "itemID": "item4",
        "name": "Camera",
        "price": 199.99
    },
    {
        "itemID": "item5",
        "name": "Headphones",
        "price": 89.99
    },
    {
        "itemID": "item6",
        "name": "Smartphone",
        "price": 799.99
    }
])
```
#to make sure it worked run
```
db.users.find()
db.items.find()
```
# 4.1 install nginx nlb ingress controller:
```
helm upgrade --install ingress-nginx ingress-nginx --repo https://kubernetes.github.io/ingress-nginx  --namespace ingress-nginx --create-namespace \
  --set-string controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"
```
# 4.2 Create ignress object ingress.yaml:
#(you can also create this object as part of your helm/yaml deployment)
```
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  labels:
    app: <your app label>
  name: kafka-app-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: <your nlb dns, or /etc/hosts dns>
      http:
        paths:
          - backend:
              service:
                name: <name of your frontend cluster ip service>
                port:
                  number: <your frontend's service's port>
            path: /
            pathType: Prefix
```
#and apply:
```
kubectl apply -f ingress.yaml
```

# 5.1 install ebs-csi driver for stateful sets (for kafka and zookeeper):
```
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"
```
#might also need the following storageclass.yaml:
```
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
    type: gp2
mountOptions:
  - debug
volumeBindingMode: Immediate
```
#apply
```
kubectl apply -f storageclass.yaml
```
# 5.2 setup and apply kafka yaml files:
#kafka-network-policy.yaml:
```
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kafka-network
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              network/kafka-network: "true"
  podSelector:
    matchLabels:
      network/kafka-network: "true"
```
#kafka-stateful-set.yaml:
```
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    service: kafka
  name: kafka
spec:
  serviceName: kafka
  replicas: 3
  selector:
    matchLabels:
      service: kafka
  template:
    metadata:
      labels:
        network/kafka-network: "true"
        service: kafka
    spec:
      securityContext:
        fsGroup: 1000
      enableServiceLinks: false
      containers:
      - name: kafka
        imagePullPolicy: IfNotPresent
        image: bitnami/kafka:latest
        ports:
          - containerPort: 29092
          - containerPort: 9092
        env:
          - name: KAFKA_ADVERTISED_LISTENERS
            value: "INTERNAL://:29092,LISTENER_EXTERNAL://:9092"
          - name: KAFKA_AUTO_CREATE_TOPICS_ENABLE
            value: "true"
          - name: KAFKA_INTER_BROKER_LISTENER_NAME
            value: "INTERNAL"
          - name: KAFKA_LISTENERS
            value: "INTERNAL://:29092,LISTENER_EXTERNAL://:9092"
          - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
            value: "INTERNAL:PLAINTEXT,LISTENER_EXTERNAL:PLAINTEXT"
          - name: KAFKA_ZOOKEEPER_CONNECT
            value: "zookeeper:2181"
        resources: {}
        volumeMounts:
          - mountPath: /var/lib/kafka/
            name: kafka-data
      hostname: kafka
      restartPolicy: Always
  volumeClaimTemplates:
    - metadata:
        name: kafka-data
      spec:
        accessModes:
          - ReadWriteOnce
        storageClassName: gp2
        resources:
          requests:
            storage: 1Gi
```
#kafka-service.yaml:
```
apiVersion: v1
kind: Service
metadata:
  labels:
    service: kafka
  name: kafka
spec:
  clusterIP: None
  selector:
    service: kafka
  ports:
    - name: internal
      port: 29092
      targetPort: 29092
    - name: external
      port: 30092
      targetPort: 9092
```
#zookeeper-stateful-set:
```
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    service: zookeeper
  name: zookeeper
spec:
  serviceName: zookeeper
  replicas: 1
  selector:
    matchLabels:
      service: zookeeper
  template:
    metadata:
      labels:
        network/kafka-network: "true"
        service: zookeeper
    spec:
      securityContext:
        fsGroup: 1000
      enableServiceLinks: false
      containers:
        - name: zookeeper
          imagePullPolicy: Always
          image: zookeeper
          ports:
            - containerPort: 2181
          env:
            - name: ZOOKEEPER_CLIENT_PORT
              value: "2181"
            - name: ZOOKEEPER_DATA_DIR
              value: "/var/lib/zookeeper/data"
            - name: ZOOKEEPER_LOG_DIR
              value: "/var/lib/zookeeper/log"
            - name: ZOOKEEPER_SERVER_ID
              value: "1"
          resources: {}
          volumeMounts:
            - mountPath: /var/lib/zookeeper/data
              name: zookeeper-data
            - mountPath: /var/lib/zookeeper/log
              name: zookeeper-log
      hostname: zookeeper
      restartPolicy: Always
  volumeClaimTemplates:
    - metadata:
        name: zookeeper-data
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1024Mi
        storageClassName: gp2
    - metadata:
        name: zookeeper-log
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1024Mi
        storageClassName: gp2
```
#kafka-service.yaml:
```
apiVersion: v1
kind: Service
metadata:
  labels:
    service: zookeeper
  name: zookeeper
spec:
  ports:
    - name: "2181"
      port: 2181
      targetPort: 2181
  selector:
    service: zookeeper
```
#install kafka files:
```
kubectl apply -f /path/to/kafka.yamls/.
```
# 6 install argocd in the cluster:
```
# create a namespace for argo
kubectl create namespace argocd

# install usint manifest into cluster
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.5.8/manifests/install.yaml

# patch the service to become a load balancer
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# set up ENV_VARS to be used in argocd-cli login:
# might need: sudo apt install jq

export ARGOCD_SERVER=`kubectl get svc argocd-server -n argocd -o json | jq --raw-output '.status.loadBalancer.ingress[0].hostname'`
export ARGO_PWD=`kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

# login to argocd-cli
argocd login $ARGOCD_SERVER --username admin --password $ARGO_PWD --insecure
```
# 7 create CI pipeline in GitHub:
#make 2 github repos, 1 to contain your source-code and ci-pipeline for github actions
and one to contain your app's yaml/helm manifest files for argocd to monitor

#in the first repo add the following ci_pipeline yaml \
#(should be placed in .github/workflows/ci_pipeline.yaml if you intend to update it by pushing and not editing manually from github) \
\
#!!remember to edit the pipeline to fit your needs!!
```
name: Docker Image CI

on:
  push:
    branches: [ "master" ]
  pull_request:
    branches: [ "master" ]

jobs:

  build:

    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4
    
    - name: Build the Docker image
      run: |
        docker build ./backend --file backend/Dockerfile --tag ${{ secrets.DOCKER_USER }}/argocd_backend:${{ github.run_number }}
        docker build ./frontend --file frontend/Dockerfile --tag ${{ secrets.DOCKER_USER }}/argocd_frontend:${{ github.run_number }}
      
    - name: Docker Login
      uses: docker/login-action@v3.1.0
      with:
        username: ${{ secrets.DOCKER_USER }}
        password: ${{ secrets.DOCKER_TOKEN }}

    - name: push to dockerhub
      run: |
        docker push ${{ secrets.DOCKER_USER }}/argocd_backend:${{ github.run_number }}
        docker push ${{ secrets.DOCKER_USER }}/argocd_frontend:${{ github.run_number }}
        
    - name: Check out my other private repo
      uses: actions/checkout@master
      with:
        repository: Evgeny-Nik/argocd_helm
        token: ${{ secrets.GIT_TOKEN }}

    - name: Install YQ
      uses: dcarbone/install-yq-action@v1.1.1

    - name: Update the image name
      run: |
        yq  '.backend.backend.image.tag="${{ github.run_number }}"' -i kafka-app/values.yaml
        yq  '.frontend.frontend.image.tag="${{ github.run_number }}"' -i kafka-app/values.yaml

    - name: Commit changes
      uses: EndBug/add-and-commit@v9
      with:
        add: kafka-app/values.yaml
        message: "changed version of shop app to ${{ github.run_number }}"
        pathspec_error_handling: exitImmediately
        token: ${{ secrets.GIT_TOKEN }}
```
#for this to work your need to create 3 github secrets: \
#DOCKER_USER, DOCKER_TOKEN, GITHUB_TOKEN (a personal access token) \
#to do so go to: \
your repo->settings->secrets and variables->actions->new repo secret \
\
#to create the secrets go to: \
your dockerhub acc->my-account->security->new access token \
\
#for the github TOKEN go to: \
your github user->settings->developer-settings->personal-access-tokens->classic->generate new token

# 8 create ArgoCD app:
#the next step can be done with either argocd-cli, yaml files or gui, i do it via yaml manifest files \
#argo_app.yaml:
```
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: <app_name>
  namespace: argocd
spec:
  project: default
  source:
    repoURL: <url_for_your_yaml/helm_git_repo>
    targetRevision: HEAD
    path: <path_to_yaml/helm_dir_in_repo>
  destination: 
    server: https://kubernetes.default.svc
    namespace: default  
  syncPolicy:
    syncOptions:
    - CreateNamespace=true
    automated:
      selfHeal: true
      prune: true
```
#apply the yaml:
```
kubectl apply -f argo_app.yaml
```
#if you want to login using the gui, use the following command to get the load balancer dns:
```
kubectl get svc -n argocd argocd-server
```
#to get the password:
```
# username should be admin
echo $ARGOCD_PWD
```