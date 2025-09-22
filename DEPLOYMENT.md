# AI Security Camera - Deployment Checklist

## ✅ Pre-Deployment Checklist

### AWS Prerequisites
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS credentials with sufficient permissions:
  - [ ] EC2 (VPC, security groups)
  - [ ] RDS (database creation)
  - [ ] ElastiCache (Redis)
  - [ ] ECS (container orchestration)
  - [ ] ECR (container registry)
  - [ ] ELB (load balancer)
  - [ ] IAM (roles and policies)
  - [ ] S3 (storage bucket)
- [ ] Docker installed locally
- [ ] jq installed (`brew install jq`)

### API Keys
- [ ] OpenAI API key ready (starts with `sk-`)
- [ ] Sufficient OpenAI credits for GPT-4 usage

## 🚀 Deployment Steps

### 1. Cloud Infrastructure Setup
```bash
cd cloud
./setup-aws-infrastructure.sh
```

**Expected outputs**:
- [ ] VPC created with public/private subnets
- [ ] RDS MySQL database provisioned
- [ ] ElastiCache Redis cluster created
- [ ] ECS cluster with Fargate ready
- [ ] Application Load Balancer configured
- [ ] S3 bucket created with lifecycle policies
- [ ] aws-config.json file generated

**Verification**:
```bash
# Check if config file exists
ls -la aws-config.json

# Verify key resources
aws ecs describe-clusters --cluster security-camera-cluster
aws rds describe-db-instances --db-instance-identifier security-camera-db
```

### 2. Application Deployment
```bash
./deploy.sh sk-your-openai-api-key-here
```

**Expected outputs**:
- [ ] Docker images built successfully
- [ ] Images pushed to ECR
- [ ] ECS task definitions created
- [ ] API service deployed and running
- [ ] Worker service deployed and running
- [ ] Load balancer health checks passing

**Verification**:
```bash
# Check service status
aws ecs describe-services --cluster security-camera-cluster --services security-camera-api-service

# Test API endpoint
curl -f http://$(jq -r '.alb_dns' aws-config.json)/health
```

### 3. Database Initialization
```bash
./init-database.sh
```

**Steps to complete**:
- [ ] Database tables created
- [ ] Admin user created (save credentials)
- [ ] Pi device created (save API key)

**Verification**:
```bash
# List database tables
aws ecs execute-command \
  --cluster security-camera-cluster \
  --task $(aws ecs list-tasks --cluster security-camera-cluster --service-name security-camera-api-service --query 'taskArns[0]' --output text) \
  --container api \
  --interactive \
  --command "python manage.py list-users"
```

### 4. Pi Configuration
```bash
cd ..  # Back to project root
./setup-pi.sh
```

**Information needed**:
- [ ] API key from step 3
- [ ] Cloud API URL (automatically detected)

**Expected outputs**:
- [ ] `pi/config/cloud_config.py` created
- [ ] `pi/config/settings.py` updated
- [ ] Cloud connection test successful

## 🔧 Post-Deployment Configuration

### Pi Device Setup
On your Raspberry Pi:

```bash
# Install Python dependencies
cd pi
pip install -r requirements.txt

# Add known faces
# Copy face images to pi/known_faces/ directory
# Use clear, well-lit photos of faces
mkdir -p known_faces
# Copy your face images here: cp /path/to/face.jpg known_faces/person_name.jpg
```

### Test Pi Components
```bash
# Test PIR sensor
python test/pir_test.py

# Test camera + YOLO
python test/camera_yolo_test.py

# Test cloud communication
python test_system.py
```

### Start Security System
```bash
# Run the main security system
python main.py
```

## 📊 Verification & Monitoring

### Cloud Services Health Check
```bash
# API health
curl http://$(jq -r '.alb_dns' cloud/aws-config.json)/health

# Check running services
aws ecs describe-services \
  --cluster security-camera-cluster \
  --services security-camera-api-service security-camera-worker-service

# View logs
aws logs tail /ecs/security-camera-api --follow
```

### Pi System Status
```bash
# Check system logs
tail -f pi/captures/logs/security_*.log

# Test motion detection
# Walk in front of Pi - should see detection logs

# Verify cloud uploads
# Check captures/ directory for files
# Monitor cloud API logs for upload requests
```

## 🚨 Troubleshooting

### Common Issues

**Infrastructure script fails**:
- Check AWS permissions
- Verify region settings (default: us-east-1)
- Check for existing resources with same names
- Review CloudFormation events for specific errors

**Deployment script fails**:
- Verify OpenAI API key format
- Check Docker daemon is running
- Ensure sufficient ECR permissions
- Review ECS task definition for errors

**Pi can't connect to cloud**:
- Verify internet connectivity
- Check API key is correct
- Test cloud endpoint manually: `curl http://your-alb-dns/health`
- Review Pi logs for connection errors

**No motion detection**:
- Check PIR sensor wiring (GPIO pin 18)
- Test sensor independently
- Verify camera permissions

### Resource Cleanup (if needed)
```bash
# Delete ECS services
aws ecs update-service --cluster security-camera-cluster --service security-camera-api-service --desired-count 0
aws ecs delete-service --cluster security-camera-cluster --service security-camera-api-service

# Delete other resources
aws rds delete-db-instance --db-instance-identifier security-camera-db --skip-final-snapshot
aws elasticache delete-cache-cluster --cache-cluster-id security-camera-redis

# Note: Manual cleanup may be required for VPC, security groups, etc.
```

## 📋 Success Criteria

- [ ] Cloud API responding to health checks
- [ ] Database contains users and devices
- [ ] Pi successfully connects to cloud
- [ ] Motion detection triggers camera capture
- [ ] YOLO detects persons in images
- [ ] Face recognition identifies known/unknown faces
- [ ] Events upload to cloud successfully
- [ ] LLM analysis processes events
- [ ] Logs show successful end-to-end operation

## 🎉 Next Steps

After successful deployment:

1. **Add Known Faces**: Copy face images to `pi/known_faces/`
2. **Configure Settings**: Adjust sensitivity, thresholds via API
3. **Monitor System**: Set up CloudWatch alerts
4. **Mobile App**: Integrate mobile app using the REST API
5. **Scale**: Add more Pi devices using same cloud infrastructure

---

**🔧 Support**: Check logs first, verify network connectivity, test components individually.
