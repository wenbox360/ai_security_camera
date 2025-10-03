# AI Security Camera System

A complete cloud-based AI security camera system with Raspberry Pi edge devices, featuring face recognition, behavior analysis, and intelligent cloud processing.

![alt text](/images/image.png)

## Architecture

```
Pi Device → Cloud API → LLM Analysis → Mobile Notifications
    ↓           ↓           ↓              ↓
  Local AI   FastAPI    OpenAI GPT    Push Alerts
 Processing  + MySQL   + Celery       + Dashboard
```

### System Components

**Pi Device (Edge)**:
- PIR motion detection
- Camera capture (photo/video)
- Local YOLO person detection
- Face recognition against known faces
- Smart filtering before cloud upload

**Cloud Backend**:
- FastAPI REST API
- MySQL database (AWS RDS)
- Redis + Celery for async processing
- OpenAI GPT-4 for intelligent event analysis
- AWS S3 for media storage
- JWT authentication for mobile
- API key authentication for Pi devices

**Mobile App** (Future):
- Real-time event notifications
- Live camera feeds
- Device management
- Settings configuration

## Quick Deployment

### Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed
- OpenAI API key
- jq (JSON processor): `brew install jq`

### 1. Deploy Cloud Infrastructure

```bash
# Configure AWS credentials
aws configure

# Deploy cloud infrastructure (creates VPC, RDS, Redis, ECS, ALB)
cd cloud
./setup-aws-infrastructure.sh
```

This creates:
- VPC with public/private subnets
- MySQL database (AWS RDS)
- Redis cluster (AWS ElastiCache)
- ECS cluster with Fargate
- Application Load Balancer
- Security groups and IAM roles

### 2. Deploy Application

```bash
# Deploy containers to ECS (requires OpenAI API key)
./deploy.sh sk-your-openai-api-key-here
```

This will:
- Build Docker containers
- Push to AWS ECR
- Create ECS task definitions
- Deploy API and worker services
- Configure load balancer

### 3. Initialize Database

```bash
# Initialize database and create admin user
./init-database.sh
```

Follow prompts to:
- Create database tables
- Create admin user account
- Create Pi device with API key

### 4. Configure Pi Device

```bash
# Back to project root
cd ..

# Configure Pi with cloud endpoint
./setup-pi.sh
```

Enter the API key from step 3 when prompted.

### 5. Start Security System

On your Raspberry Pi:

```bash
cd pi

# Install dependencies (one-time)
pip install -r requirements.txt

# Add known faces to known_faces/ directory

# Start the security system
python main.py
```

## System Flow

### Settings Configuration
1. **Mobile App** → Updates device settings via cloud API
2. **Cloud** → Stores settings in database
3. **Pi Device** → Polls for settings updates periodically

### Event Processing
1. **PIR Sensor** → Detects motion
2. **Camera** → Captures photo/video
3. **YOLO** → Detects persons in image
4. **Face Recognition** → Identifies known vs unknown persons
5. **Smart Filtering** → Only uploads significant events:
   - Unknown persons
   - Known persons dwelling (>10 seconds)
   - Suspicious behavior patterns
6. **Cloud Upload** → Sends event data + media to cloud
7. **LLM Analysis** → GPT-4 analyzes context and determines alert necessity
8. **Mobile Notification** → Sends push notification if alert warranted

## Configuration

### Pi Configuration

Key files:
- `pi/config/settings.py` - Main configuration
- `pi/config/cloud_config.py` - Cloud API settings (auto-generated)
- `pi/known_faces/` - Directory for known face images

### Cloud Configuration

Environment variables (set in ECS):
- `DATABASE_URL` - MySQL connection string
- `REDIS_URL` - Redis connection string
- `AWS_S3_BUCKET` - S3 bucket name
- `OPENAI_API_KEY` - OpenAI API key
- `JWT_SECRET_KEY` - JWT signing key

## Monitoring

### View Logs

```bash
# Cloud logs
aws logs tail /ecs/security-camera-api --follow --region us-east-1

# Pi logs
tail -f pi/captures/logs/security_*.log
```

### Database Management

```bash
# Connect to running container
aws ecs execute-command \
  --cluster security-camera-cluster \
  --task <task-arn> \
  --container api \
  --interactive \
  --command "/bin/bash"

# Inside container
python manage.py list-users
python manage.py list-devices
```

## Security Features

### Authentication
- **Mobile Apps**: JWT tokens with refresh mechanism
- **Pi Devices**: API keys with device-specific permissions
- **Cloud API**: Rate limiting and request validation

### Privacy
- **Face Data**: Stored as embeddings, not raw images
- **Media Files**: 7-day retention policy with automatic cleanup
- **Encryption**: TLS in transit, encrypted storage at rest

### Cost Optimization
- **Smart Filtering**: Only sends significant events to cloud
- **Local Processing**: YOLO and face recognition run on Pi
- **Efficient Storage**: S3 lifecycle policies for automatic cleanup

## Development

### Local Testing

```bash
cd cloud

# Start local services
docker-compose up -d

# Run API locally
python main.py

# Run worker locally
celery -A celery_app worker --loglevel=info
```

### Testing Components

```bash
# Test Pi camera + YOLO
cd pi
python test/camera_yolo_test.py

# Test PIR sensor
python test/pir_test.py

# Test cloud communication
python test_system.py
```

## Dependencies

### Pi Requirements
- OpenCV
- YOLO (ultralytics)
- face-recognition
- RPi.GPIO
- requests

### Cloud Requirements
- FastAPI
- SQLAlchemy
- Celery
- Redis
- OpenAI
- boto3 (AWS SDK)

## Key Features

### Smart Event Detection
- Motion-triggered recording
- Person detection with YOLO
- Face recognition for known vs unknown persons
- Behavior analysis (dwelling, loitering patterns)

### Intelligent Cloud Processing
- Context-aware LLM analysis
- Cost-effective filtering (only sends significant events)
- Automatic threat assessment
- Smart notification decisions

### Scalable Architecture
- Containerized deployment with ECS
- Auto-scaling based on load
- Load-balanced API endpoints
- Managed database and cache services

### Mobile Integration Ready
- RESTful API for mobile apps
- JWT authentication
- Real-time event streaming
- Device management endpoints

## Troubleshooting

### Common Issues

**Pi can't connect to cloud**:
- Check internet connection
- Verify API key is correct
- Check cloud deployment status: `aws ecs describe-services --cluster security-camera-cluster --services security-camera-api-service`

**No motion detection**:
- Check PIR sensor wiring (pin 18)
- Test PIR: `python test/pir_test.py`
- Check sensitivity settings

**Face recognition not working**:
- Ensure known faces are in `known_faces/` directory
- Check image quality and lighting
- Verify face_recognition library installation

**Cloud deployment fails**:
- Check AWS credentials and permissions
- Verify region settings
- Check for resource limits or conflicts

### Support

For issues or questions:
1. Check the logs first (Pi and cloud)
2. Verify network connectivity
3. Test individual components
4. Check AWS service status if cloud issues


**Your AI security camera system is now ready!**