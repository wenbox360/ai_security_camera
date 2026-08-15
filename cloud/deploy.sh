#!/bin/bash

# AI Security Camera - Cloud Deployment Script
# This script builds and deploys the application to AWS ECS

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

for command in aws docker jq openssl; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "❌ Required command not found: $command" >&2
        exit 1
    fi
done

echo "🚀 AI Security Camera - Application Deployment"
echo "=============================================="

# Check if AWS infrastructure config exists
if [ ! -f "aws-config.json" ]; then
    echo "❌ AWS configuration not found!"
    echo "Please run './setup-aws-infrastructure.sh' first to create AWS resources"
    exit 1
fi

# Load configuration
PROJECT_NAME="security-camera"
AWS_REGION=$(jq -er '.region' aws-config.json)
ECS_CLUSTER=$(jq -er '.ecs_cluster' aws-config.json)
PUBLIC_SUBNETS=$(jq -er '[.public_subnets[]] | join(",")' aws-config.json)
ECS_SG=$(jq -er '.security_groups.ecs' aws-config.json)
S3_BUCKET=$(jq -er '.s3_bucket' aws-config.json)
ALB_DNS=$(jq -er '.alb_dns' aws-config.json)
TARGET_GROUP_ARN=$(jq -er '.target_group_arn' aws-config.json)
DB_SECRET_NAME=$(jq -er '.secrets.db_password_secret' aws-config.json)

echo "📋 Deployment Configuration:"
echo "  Region: $AWS_REGION"
echo "  Cluster: $ECS_CLUSTER"
echo "  S3 Bucket: $S3_BUCKET"
echo "  Load Balancer: $ALB_DNS"
echo ""

# Check environment variables
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "❌ OPENAI_API_KEY environment variable is required"
    echo "Please set it: export OPENAI_API_KEY=your_api_key"
    exit 1
fi

# Configuration
ECR_REPOSITORY_NAME="security-camera-api"
RUNTIME_SECRET_NAME="${PROJECT_NAME}-runtime"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "🔍 AWS Account: $AWS_ACCOUNT_ID"
echo ""

# Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names "$ECR_REPOSITORY_NAME" --region "$AWS_REGION" >/dev/null 2>&1 || \
aws ecr create-repository --repository-name "$ECR_REPOSITORY_NAME" --region "$AWS_REGION" >/dev/null

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URI"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t "$ECR_REPOSITORY_NAME" .

# Tag image
docker tag "$ECR_REPOSITORY_NAME:latest" "$ECR_URI/$ECR_REPOSITORY_NAME:latest"

# Push to ECR
echo "📤 Pushing image to ECR..."
docker push "$ECR_URI/$ECR_REPOSITORY_NAME:latest"

echo "✅ Image pushed successfully!"
echo ""

# Wait for RDS and ElastiCache to be ready
echo "⏳ Checking if RDS and ElastiCache are ready..."

# Check RDS status
RDS_STATUS=$(aws rds describe-db-instances --db-instance-identifier security-camera-db --region $AWS_REGION --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo "not-found")
if [ "$RDS_STATUS" != "available" ]; then
    echo "⏳ RDS database is not ready yet (status: $RDS_STATUS)"
    echo "Please wait for RDS to be available and run this script again"
    echo "Check status: aws rds describe-db-instances --db-instance-identifier security-camera-db --region $AWS_REGION"
    exit 1
fi

# Check ElastiCache status
REDIS_STATUS=$(aws elasticache describe-cache-clusters --cache-cluster-id security-camera-redis --region $AWS_REGION --query 'CacheClusters[0].CacheClusterStatus' --output text 2>/dev/null || echo "not-found")
if [ "$REDIS_STATUS" != "available" ]; then
    echo "⏳ ElastiCache Redis is not ready yet (status: $REDIS_STATUS)"
    echo "Please wait for ElastiCache to be available and run this script again"
    echo "Check status: aws elasticache describe-cache-clusters --cache-cluster-id security-camera-redis --region $AWS_REGION"
    exit 1
fi

echo "✅ RDS and ElastiCache are ready"

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier security-camera-db --region $AWS_REGION --query 'DBInstances[0].Endpoint.Address' --output text)

# Get ElastiCache endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id security-camera-redis --show-cache-node-info --region $AWS_REGION --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text)

# Assemble runtime settings in Secrets Manager. The ECS definitions below carry
# only ARN/key references, never credentials or secret values.
DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id "$DB_SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'SecretString' \
    --output text)
DB_PASSWORD_URLENCODED=$(printf '%s' "$DB_PASSWORD" | jq -sRr '@uri')

EXISTING_RUNTIME_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id "$RUNTIME_SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'SecretString' \
    --output text 2>/dev/null || true)
JWT_SECRET_KEY=$(printf '%s' "$EXISTING_RUNTIME_SECRET" | jq -r '.jwt_secret_key // empty' 2>/dev/null || true)
if [ -z "$JWT_SECRET_KEY" ]; then
    JWT_SECRET_KEY=$(openssl rand -base64 48)
fi

RUNTIME_SECRET_FILE="$TEMP_DIR/runtime-secret.json"
umask 077
jq -n \
    --arg database_url "mysql+pymysql://admin:${DB_PASSWORD_URLENCODED}@${RDS_ENDPOINT}:3306/security_camera_db" \
    --arg redis_url "redis://${REDIS_ENDPOINT}:6379/0" \
    --arg openai_api_key "$OPENAI_API_KEY" \
    --arg jwt_secret_key "$JWT_SECRET_KEY" \
    '{database_url: $database_url, redis_url: $redis_url, openai_api_key: $openai_api_key, jwt_secret_key: $jwt_secret_key}' \
    > "$RUNTIME_SECRET_FILE"

if [ -n "$EXISTING_RUNTIME_SECRET" ]; then
    aws secretsmanager put-secret-value \
        --secret-id "$RUNTIME_SECRET_NAME" \
        --secret-string "file://$RUNTIME_SECRET_FILE" \
        --region "$AWS_REGION" >/dev/null
else
    aws secretsmanager create-secret \
        --name "$RUNTIME_SECRET_NAME" \
        --description "Runtime configuration for $PROJECT_NAME ECS tasks" \
        --secret-string "file://$RUNTIME_SECRET_FILE" \
        --region "$AWS_REGION" >/dev/null
fi
RUNTIME_SECRET_ARN=$(aws secretsmanager describe-secret \
    --secret-id "$RUNTIME_SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'ARN' \
    --output text)

echo "🔗 Endpoints:"
echo "  RDS: $RDS_ENDPOINT"
echo "  Redis: $REDIS_ENDPOINT"
echo ""

# Create IAM roles if they do not exist. Temporary policy files are confined to
# the private temp directory and removed by the EXIT trap.
echo "🔐 Setting up IAM roles..."
TRUST_POLICY_FILE="$TEMP_DIR/trust-policy.json"
jq -n '{Version: "2012-10-17", Statement: [{Effect: "Allow", Principal: {Service: "ecs-tasks.amazonaws.com"}, Action: "sts:AssumeRole"}]}' > "$TRUST_POLICY_FILE"

TASK_ROLE_ARN=$(aws iam get-role --role-name "${PROJECT_NAME}-task-role" --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$TASK_ROLE_ARN" ]; then
    aws iam create-role --role-name "${PROJECT_NAME}-task-role" --assume-role-policy-document "file://$TRUST_POLICY_FILE" >/dev/null

    # Attach S3 policy
    S3_POLICY_FILE="$TEMP_DIR/s3-policy.json"
    jq -n --arg bucket "$S3_BUCKET" '{Version: "2012-10-17", Statement: [{Effect: "Allow", Action: ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource: ("arn:aws:s3:::" + $bucket + "/*")}, {Effect: "Allow", Action: ["s3:ListBucket"], Resource: ("arn:aws:s3:::" + $bucket)}]}' > "$S3_POLICY_FILE"
    aws iam put-role-policy --role-name "${PROJECT_NAME}-task-role" --policy-name S3Access --policy-document "file://$S3_POLICY_FILE"
    
    TASK_ROLE_ARN=$(aws iam get-role --role-name "${PROJECT_NAME}-task-role" --query 'Role.Arn' --output text)
fi

# Get execution role ARN
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$EXECUTION_ROLE_ARN" ]; then
    echo "Creating ecsTaskExecutionRole..."
    aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document "file://$TRUST_POLICY_FILE" >/dev/null
    aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
fi

SECRETS_POLICY_FILE="$TEMP_DIR/read-runtime-secret-policy.json"
jq -n --arg secret_arn "$RUNTIME_SECRET_ARN" '{Version: "2012-10-17", Statement: [{Effect: "Allow", Action: ["secretsmanager:GetSecretValue"], Resource: $secret_arn}]}' > "$SECRETS_POLICY_FILE"
aws iam put-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-name ReadSecurityCameraRuntimeSecret \
    --policy-document "file://$SECRETS_POLICY_FILE"

echo "✅ IAM roles configured"
echo ""

# Create API task definition
echo "🐳 Creating ECS task definitions..."
cat > api-task-definition.json << EOF
{
    "family": "${PROJECT_NAME}-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "$EXECUTION_ROLE_ARN",
    "taskRoleArn": "$TASK_ROLE_ARN",
    "containerDefinitions": [
        {
            "name": "api",
            "image": "$ECR_URI/$ECR_REPOSITORY_NAME:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "AWS_REGION", "value": "$AWS_REGION"},
                {"name": "S3_BUCKET_NAME", "value": "$S3_BUCKET"},
                {"name": "DEBUG", "value": "False"}
            ],
            "secrets": [
                {"name": "DATABASE_URL", "valueFrom": "${RUNTIME_SECRET_ARN}:database_url::"},
                {"name": "REDIS_URL", "valueFrom": "${RUNTIME_SECRET_ARN}:redis_url::"},
                {"name": "OPENAI_API_KEY", "valueFrom": "${RUNTIME_SECRET_ARN}:openai_api_key::"},
                {"name": "JWT_SECRET_KEY", "valueFrom": "${RUNTIME_SECRET_ARN}:jwt_secret_key::"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/${PROJECT_NAME}-api",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs",
                    "awslogs-create-group": "true"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
EOF

# Register API task definition
aws ecs register-task-definition --cli-input-json file://api-task-definition.json --region "$AWS_REGION"

# Create Worker task definition
cat > worker-task-definition.json << EOF
{
    "family": "${PROJECT_NAME}-worker",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "$EXECUTION_ROLE_ARN",
    "taskRoleArn": "$TASK_ROLE_ARN",
    "containerDefinitions": [
        {
            "name": "worker",
            "image": "$ECR_URI/$ECR_REPOSITORY_NAME:latest",
            "command": ["celery", "-A", "cloud.celery_app", "worker", "--loglevel=info"],
            "environment": [
                {"name": "AWS_REGION", "value": "$AWS_REGION"},
                {"name": "S3_BUCKET_NAME", "value": "$S3_BUCKET"}
            ],
            "secrets": [
                {"name": "DATABASE_URL", "valueFrom": "${RUNTIME_SECRET_ARN}:database_url::"},
                {"name": "REDIS_URL", "valueFrom": "${RUNTIME_SECRET_ARN}:redis_url::"},
                {"name": "OPENAI_API_KEY", "valueFrom": "${RUNTIME_SECRET_ARN}:openai_api_key::"},
                {"name": "JWT_SECRET_KEY", "valueFrom": "${RUNTIME_SECRET_ARN}:jwt_secret_key::"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/${PROJECT_NAME}-worker",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs",
                    "awslogs-create-group": "true"
                }
            }
        }
    ]
}
EOF

# Register Worker task definition
aws ecs register-task-definition --cli-input-json file://worker-task-definition.json --region "$AWS_REGION"

echo "✅ Task definitions registered"

# Create/update API service
echo "🚀 Deploying API service..."
API_SERVICE_EXISTS=$(aws ecs describe-services --cluster $ECS_CLUSTER --services ${PROJECT_NAME}-api-service --region $AWS_REGION --query 'services[0].serviceName' --output text 2>/dev/null || echo "None")

if [ "$API_SERVICE_EXISTS" = "None" ]; then
    # Create new service
    aws ecs create-service \
        --cluster $ECS_CLUSTER \
        --service-name ${PROJECT_NAME}-api-service \
        --task-definition ${PROJECT_NAME}-api \
        --desired-count 2 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=api,containerPort=8000" \
        --region $AWS_REGION
else
    # Update existing service
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service ${PROJECT_NAME}-api-service \
        --task-definition ${PROJECT_NAME}-api \
        --region $AWS_REGION
fi

# Create/update Worker service  
echo "⚙️  Deploying worker service..."
WORKER_SERVICE_EXISTS=$(aws ecs describe-services --cluster $ECS_CLUSTER --services ${PROJECT_NAME}-worker-service --region $AWS_REGION --query 'services[0].serviceName' --output text 2>/dev/null || echo "None")

if [ "$WORKER_SERVICE_EXISTS" = "None" ]; then
    # Create new service
    aws ecs create-service \
        --cluster $ECS_CLUSTER \
        --service-name ${PROJECT_NAME}-worker-service \
        --task-definition ${PROJECT_NAME}-worker \
        --desired-count 2 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
        --region $AWS_REGION
else
    # Update existing service
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service ${PROJECT_NAME}-worker-service \
        --task-definition ${PROJECT_NAME}-worker \
        --region $AWS_REGION
fi

echo "✅ Services deployed"

# Clean up temporary files
rm -f api-task-definition.json worker-task-definition.json

echo ""
echo "🎉 Deployment Complete!"
echo "====================="
echo ""
echo "🌐 Your API is available at: http://$ALB_DNS"
echo "📊 Health check: http://$ALB_DNS/health"
echo "📖 API docs: http://$ALB_DNS/docs"
echo ""
echo "⏳ Services are starting up (this may take 2-3 minutes)"
echo ""
echo "🔍 Monitor deployment:"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services ${PROJECT_NAME}-api-service --region $AWS_REGION"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services ${PROJECT_NAME}-worker-service --region $AWS_REGION"
echo ""
echo "📝 Next steps:"
echo "1. Wait for services to become stable"
echo "2. Initialize database: run './init-database.sh' or execute 'python -m cloud.manage init-db' in an API task"
echo "3. Create admin user and Pi device"
echo "4. Configure your Pi with the API URL: http://$ALB_DNS"
