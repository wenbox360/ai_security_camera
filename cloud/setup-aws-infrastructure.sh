#!/bin/bash

# AI Security Camera - Complete AWS Infrastructure Setup
# This script creates all necessary AWS resources for the security camera system

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

for command in aws openssl; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

echo "🚀 AI Security Camera - AWS Infrastructure Setup"
echo "================================================"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="security-camera"
VPC_CIDR="10.0.0.0/16"
PUBLIC_SUBNET_1_CIDR="10.0.1.0/24"
PUBLIC_SUBNET_2_CIDR="10.0.2.0/24"
PRIVATE_SUBNET_1_CIDR="10.0.3.0/24"
PRIVATE_SUBNET_2_CIDR="10.0.4.0/24"

# Get availability zones
AZ1=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[0].ZoneName' --output text)
AZ2=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[1].ZoneName' --output text)

echo "📍 Deploying to region: $AWS_REGION"
echo "📍 Availability zones: $AZ1, $AZ2"
echo ""

# Check if user is authenticated
echo "🔐 Checking AWS authentication..."
aws sts get-caller-identity > /dev/null
echo "✅ AWS authentication successful"
echo ""

# Create VPC
echo "🏗️  Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block $VPC_CIDR \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${PROJECT_NAME}-vpc}]" \
    --query 'Vpc.VpcId' \
    --output text \
    --region $AWS_REGION)

echo "✅ VPC created: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $AWS_REGION

# Create Internet Gateway
echo "🌐 Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${PROJECT_NAME}-igw}]" \
    --query 'InternetGateway.InternetGatewayId' \
    --output text \
    --region $AWS_REGION)

# Attach Internet Gateway to VPC
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID --region $AWS_REGION
echo "✅ Internet Gateway created and attached: $IGW_ID"

# Create Public Subnets
echo "🏢 Creating public subnets..."
PUBLIC_SUBNET_1_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block $PUBLIC_SUBNET_1_CIDR \
    --availability-zone $AZ1 \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-public-subnet-1}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

PUBLIC_SUBNET_2_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block $PUBLIC_SUBNET_2_CIDR \
    --availability-zone $AZ2 \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-public-subnet-2}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

echo "✅ Public subnets created: $PUBLIC_SUBNET_1_ID, $PUBLIC_SUBNET_2_ID"

# Create Private Subnets
echo "🔒 Creating private subnets..."
PRIVATE_SUBNET_1_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block $PRIVATE_SUBNET_1_CIDR \
    --availability-zone $AZ1 \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-private-subnet-1}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block $PRIVATE_SUBNET_2_CIDR \
    --availability-zone $AZ2 \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-private-subnet-2}]" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

echo "✅ Private subnets created: $PRIVATE_SUBNET_1_ID, $PRIVATE_SUBNET_2_ID"

# Create Route Table for Public Subnets
echo "🛣️  Creating route tables..."
PUBLIC_RT_ID=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-public-rt}]" \
    --query 'RouteTable.RouteTableId' \
    --output text \
    --region $AWS_REGION)

# Add route to Internet Gateway
aws ec2 create-route --route-table-id $PUBLIC_RT_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID --region $AWS_REGION

# Associate public subnets with public route table
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_1_ID --route-table-id $PUBLIC_RT_ID --region $AWS_REGION
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_2_ID --route-table-id $PUBLIC_RT_ID --region $AWS_REGION

echo "✅ Route tables configured"

# Create Security Groups
echo "🔐 Creating security groups..."

# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-alb-sg \
    --description "Security group for Application Load Balancer" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${PROJECT_NAME}-alb-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

# Allow HTTP and HTTPS from anywhere
aws ec2 authorize-security-group-ingress --group-id $ALB_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $AWS_REGION
aws ec2 authorize-security-group-ingress --group-id $ALB_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $AWS_REGION

# ECS Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-ecs-sg \
    --description "Security group for ECS tasks" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${PROJECT_NAME}-ecs-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress --group-id $ECS_SG_ID --protocol tcp --port 8000 --source-group $ALB_SG_ID --region $AWS_REGION

# RDS Security Group
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-rds-sg \
    --description "Security group for RDS database" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${PROJECT_NAME}-rds-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

# Allow MySQL from ECS
aws ec2 authorize-security-group-ingress --group-id $RDS_SG_ID --protocol tcp --port 3306 --source-group $ECS_SG_ID --region $AWS_REGION

# ElastiCache Security Group
REDIS_SG_ID=$(aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-redis-sg \
    --description "Security group for ElastiCache Redis" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${PROJECT_NAME}-redis-sg}]" \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

# Allow Redis from ECS
aws ec2 authorize-security-group-ingress --group-id $REDIS_SG_ID --protocol tcp --port 6379 --source-group $ECS_SG_ID --region $AWS_REGION

echo "✅ Security groups created"

# Create S3 Bucket
echo "📦 Creating S3 bucket..."
BUCKET_NAME="${PROJECT_NAME}-storage-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled

# Configure lifecycle policy
cat > lifecycle.json << EOF
{
    "Rules": [
        {
            "ID": "SecurityCameraRetention",
            "Status": "Enabled",
            "Filter": {"Prefix": "events/"},
            "Expiration": {"Days": 7}
        }
    ]
}
EOF

aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET_NAME --lifecycle-configuration file://lifecycle.json
rm lifecycle.json

echo "✅ S3 bucket created: $BUCKET_NAME"

# Create RDS Subnet Group
echo "🗄️  Creating RDS subnet group..."
aws rds create-db-subnet-group \
    --db-subnet-group-name ${PROJECT_NAME}-db-subnet-group \
    --db-subnet-group-description "Subnet group for security camera database" \
    --subnet-ids $PRIVATE_SUBNET_1_ID $PRIVATE_SUBNET_2_ID \
    --region $AWS_REGION

# Create RDS Instance
echo "🗄️  Creating RDS MySQL database..."
# Generate a strong password for the RDS instance
DB_PASSWORD=$(openssl rand -hex 32)

# Store the database password securely in AWS Secrets Manager
SECRET_NAME="${PROJECT_NAME}-db-password"
echo "🔒 Storing database password securely in AWS Secrets Manager..."
aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "RDS master password for $PROJECT_NAME" \
    --secret-string "$DB_PASSWORD" \
    --region $AWS_REGION

echo "🔒 Database password stored securely in AWS Secrets Manager as secret: $SECRET_NAME"

aws rds create-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --master-username admin \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name ${PROJECT_NAME}-db-subnet-group \
    --db-name security_camera_db \
    --backup-retention-period 7 \
    --storage-encrypted \
    --region $AWS_REGION

echo "✅ RDS database creation initiated (this takes 5-10 minutes)"

# Create ElastiCache Subnet Group
echo "⚡ Creating ElastiCache subnet group..."
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name ${PROJECT_NAME}-redis-subnet-group \
    --cache-subnet-group-description "Subnet group for security camera Redis" \
    --subnet-ids $PRIVATE_SUBNET_1_ID $PRIVATE_SUBNET_2_ID \
    --region $AWS_REGION

# Create ElastiCache Redis
echo "⚡ Creating ElastiCache Redis..."
aws elasticache create-cache-cluster \
    --cache-cluster-id ${PROJECT_NAME}-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids $REDIS_SG_ID \
    --cache-subnet-group-name ${PROJECT_NAME}-redis-subnet-group \
    --region $AWS_REGION

echo "✅ ElastiCache Redis creation initiated"

# Create ECS Cluster
echo "🐳 Creating ECS cluster..."
aws ecs create-cluster \
    --cluster-name ${PROJECT_NAME}-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --region $AWS_REGION

echo "✅ ECS cluster created"

# Create Application Load Balancer
echo "⚖️  Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name ${PROJECT_NAME}-alb \
    --subnets $PUBLIC_SUBNET_1_ID $PUBLIC_SUBNET_2_ID \
    --security-groups $ALB_SG_ID \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo "✅ Application Load Balancer created: $ALB_DNS"

# Create Target Group
echo "🎯 Creating target group..."
TG_ARN=$(aws elbv2 create-target-group \
    --name ${PROJECT_NAME}-targets \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Create Listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $AWS_REGION

echo "✅ Target group and listener created"

# Save configuration to file
echo "💾 Saving configuration..."
cat > aws-config.json << EOF
{
    "region": "$AWS_REGION",
    "vpc_id": "$VPC_ID",
    "public_subnets": ["$PUBLIC_SUBNET_1_ID", "$PUBLIC_SUBNET_2_ID"],
    "private_subnets": ["$PRIVATE_SUBNET_1_ID", "$PRIVATE_SUBNET_2_ID"],
    "security_groups": {
        "alb": "$ALB_SG_ID",
        "ecs": "$ECS_SG_ID",
        "rds": "$RDS_SG_ID",
        "redis": "$REDIS_SG_ID"
    },
    "s3_bucket": "$BUCKET_NAME",
    "rds_instance": "${PROJECT_NAME}-db",
    "redis_cluster": "${PROJECT_NAME}-redis",
    "ecs_cluster": "${PROJECT_NAME}-cluster",
    "alb_arn": "$ALB_ARN",
    "alb_dns": "$ALB_DNS",
    "target_group_arn": "$TG_ARN",
    "secrets": {
        "db_password_secret": "$SECRET_NAME"
    }
}
EOF

echo ""
echo "🎉 AWS Infrastructure Setup Complete!"
echo "===================================="
echo ""
echo "📋 Resources Created:"
echo "  🌐 VPC: $VPC_ID"
echo "  📦 S3 Bucket: $BUCKET_NAME"
echo "  🗄️  RDS Database: ${PROJECT_NAME}-db"
echo "  ⚡ Redis Cache: ${PROJECT_NAME}-redis"
echo "  🐳 ECS Cluster: ${PROJECT_NAME}-cluster"
echo "  ⚖️  Load Balancer: $ALB_DNS"
echo ""
echo "📝 Configuration saved to: aws-config.json"
echo "🔑 Database password saved in AWS Secrets Manager: $SECRET_NAME"
echo ""
echo "⏳ Note: RDS and ElastiCache are still being created (5-10 minutes)"
echo ""
echo "🔗 Next steps:"
echo "1. Wait for RDS and ElastiCache to be available"
echo "2. Run './deploy.sh' to deploy your application"
echo "3. Your API will be available at: http://$ALB_DNS"
echo ""
echo "🔍 Monitor creation status:"
echo "  aws rds describe-db-instances --db-instance-identifier ${PROJECT_NAME}-db --region $AWS_REGION"
echo "  aws elasticache describe-cache-clusters --cache-cluster-id ${PROJECT_NAME}-redis --region $AWS_REGION"
