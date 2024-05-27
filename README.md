#steps:
# terraform files:
# data.tf:
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

# eks.tf:

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

# provider.tf:
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

# security_group.tf:
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

# subnets.tf:
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

# vpc.tf:
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

# once all files are created:

terraform init
terraform apply --auto-approve

# once cluster is up run the following command to use the correct context with kubectl
aws eks --region eu-north-1 update-kubeconfig --name pc-eks

# install nginx nlb ingress controller:

helm upgrade --install ingress-nginx ingress-nginx --repo https://kubernetes.github.io/ingress-nginx  --namespace ingress-nginx --create-namespace \
  --set-string controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"


#make sure mongodb is installed prior to pipelines:
helm install mongodb-release oci://registry-1.docker.io/bitnamicharts/mongodb

# insert data into mongodb:
kubectl exec -it <mongodb-pod-number> bash
mongosh -u <user_name> -p <password>

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

# install ebs csi driver for stateful sets:
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"

#install kafka files:
kubectl apply -f /path/to/kafka.yamls/.
# !!important!!: might need to add storageClassName: gp2 to volumeClaimTemplates.spec


# create ignress object ingress.yaml:
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
                  number: 8000
            path: /
            pathType: Prefix

# and apply:
kubectl apply -f ingress.yaml
