#!/bin/bash

# AI Security Camera - Database Initialization Script
# This script initializes the database and creates initial users/devices

set -e

echo "🗄️  AI Security Camera - Database Initialization"
echo "==============================================="

# Check if AWS config exists
if [ ! -f "aws-config.json" ]; then
    echo "❌ AWS configuration not found!"
    echo "Please run './setup-aws-infrastructure.sh' first"
    exit 1
fi

# Load configuration
AWS_REGION=$(jq -r '.region' aws-config.json)
ECS_CLUSTER=$(jq -r '.ecs_cluster' aws-config.json)
PROJECT_NAME="security-camera"

echo "📋 Configuration:"
echo "  Region: $AWS_REGION"
echo "  Cluster: $ECS_CLUSTER"
echo ""

# Get running API task
echo "🔍 Finding running API task..."
TASK_ARN=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name ${PROJECT_NAME}-api-service --region $AWS_REGION --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" = "None" ] || [ -z "$TASK_ARN" ]; then
    echo "❌ No running API tasks found!"
    echo "Please make sure the API service is deployed and running"
    echo "Check status: aws ecs describe-services --cluster $ECS_CLUSTER --services ${PROJECT_NAME}-api-service --region $AWS_REGION"
    exit 1
fi

echo "✅ Found API task: $TASK_ARN"
echo ""

# Initialize database
echo "🔧 Initializing database tables..."
aws ecs execute-command \
    --cluster $ECS_CLUSTER \
    --task $TASK_ARN \
    --container api \
    --interactive \
    --command "python manage.py init-db" \
    --region $AWS_REGION

echo "✅ Database initialized"
echo ""

# Create admin user
echo "👤 Creating admin user..."
echo "Please enter admin credentials:"
read -p "Username: " ADMIN_USERNAME
read -p "Email: " ADMIN_EMAIL

aws ecs execute-command \
    --cluster $ECS_CLUSTER \
    --task $TASK_ARN \
    --container api \
    --interactive \
    --command "python manage.py create-user $ADMIN_USERNAME $ADMIN_EMAIL" \
    --region $AWS_REGION

echo "✅ Admin user created"
echo ""

# Create Pi device
echo "🔧 Creating Pi device..."
read -p "Device name (e.g., 'Living Room Pi'): " DEVICE_NAME

echo "Creating device for user ID 1..."
aws ecs execute-command \
    --cluster $ECS_CLUSTER \
    --task $TASK_ARN \
    --container api \
    --interactive \
    --command "python manage.py create-device 1 \"$DEVICE_NAME\"" \
    --region $AWS_REGION

echo ""
echo "✅ Database initialization complete!"
echo ""
echo "📋 Important:"
echo "1. Save the API key from the device creation output"
echo "2. Use this API key to configure your Pi device"
echo "3. Your cloud API URL is: http://$(jq -r '.alb_dns' aws-config.json)"
echo ""
echo "🔍 Verify setup:"
echo "  List users: aws ecs execute-command --cluster $ECS_CLUSTER --task $TASK_ARN --container api --interactive --command \"python manage.py list-users\" --region $AWS_REGION"
echo "  List devices: aws ecs execute-command --cluster $ECS_CLUSTER --task $TASK_ARN --container api --interactive --command \"python manage.py list-devices\" --region $AWS_REGION"
