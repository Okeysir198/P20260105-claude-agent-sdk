# Deployment Guide

## Production Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured for production
- [ ] API keys rotated and secured
- [ ] TLS certificates installed and validated
- [ ] LiveKit server scaled and tested
- [ ] Agent worker instances provisioned
- [ ] Monitoring and logging infrastructure ready
- [ ] Backup and disaster recovery plan documented
- [ ] Security audit completed
- [ ] Load testing performed
- [ ] Documentation updated and accessible

### Deployment Steps

- [ ] Deploy LiveKit server cluster
- [ ] Configure load balancer
- [ ] Deploy agent worker instances
- [ ] Verify health checks passing
- [ ] Enable monitoring dashboards
- [ ] Configure alerting rules
- [ ] Perform smoke tests
- [ ] Enable traffic routing
- [ ] Monitor initial production traffic
- [ ] Document deployment artifacts and configuration

### Post-Deployment

- [ ] Verify all metrics within acceptable ranges
- [ ] Confirm audit logging operational
- [ ] Review error logs for anomalies
- [ ] Validate POPI compliance mechanisms
- [ ] Schedule post-deployment review meeting
- [ ] Update runbooks with lessons learned

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the agent directory with the following variables:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key-here
LIVEKIT_API_SECRET=your-api-secret-here

# AI Service API Keys
OPENAI_API_KEY=sk-your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key

# Agent Configuration
AGENT_PORT=8083

# Logging Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Observability (Optional)
PHOENIX_ENDPOINT=http://your-phoenix-server:6006
TRACING_ENABLED=true
```

### Environment-Specific Configurations

#### Development

```bash
LIVEKIT_URL=ws://localhost:18003
LOG_LEVEL=DEBUG
TRACING_ENABLED=true
```

#### Staging

```bash
LIVEKIT_URL=wss://staging-livekit.yourcompany.com
LOG_LEVEL=INFO
TRACING_ENABLED=true
```

#### Production

```bash
LIVEKIT_URL=wss://livekit.yourcompany.com
LOG_LEVEL=WARNING
TRACING_ENABLED=false  # Or point to production observability
```

### Secrets Management

**AWS Secrets Manager Example:**

```python
import boto3
import json

def load_secrets_from_aws():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='debt-collection/agent')
    secrets = json.loads(response['SecretString'])

    os.environ['LIVEKIT_API_KEY'] = secrets['livekit_api_key']
    os.environ['LIVEKIT_API_SECRET'] = secrets['livekit_api_secret']
    os.environ['OPENAI_API_KEY'] = secrets['openai_api_key']
    # ... etc
```

**HashiCorp Vault Example:**

```python
import hvac

def load_secrets_from_vault():
    client = hvac.Client(url='https://vault.yourcompany.com')
    client.auth.approle.login(role_id='...', secret_id='...')

    secrets = client.secrets.kv.v2.read_secret_version(path='debt-collection/agent')
    data = secrets['data']['data']

    os.environ.update(data)
```

---

## Monitoring and Logging Setup

### Application Logging

**Structured Logging Configuration:**

```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
```

### Metrics Collection

**Prometheus Metrics Example:**

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
calls_total = Counter('debt_collection_calls_total', 'Total number of calls', ['outcome'])
call_duration = Histogram('debt_collection_call_duration_seconds', 'Call duration in seconds')
active_sessions = Gauge('debt_collection_active_sessions', 'Number of active sessions')
agent_handoffs = Counter('debt_collection_handoffs_total', 'Agent handoffs', ['from_agent', 'to_agent'])
verification_success = Counter('debt_collection_verification_success_total', 'Successful verifications')
payment_captured = Counter('debt_collection_payment_captured_total', 'Payments captured', ['method'])

# Start metrics server
start_http_server(9090)
```

**Integration in Code:**

```python
# In agents.py
@server.rtc_session(agent_name=get_agent_id())
async def entrypoint(ctx: JobContext):
    active_sessions.inc()
    start_time = time.time()

    try:
        # ... session logic
        calls_total.labels(outcome='success').inc()
    except Exception as e:
        calls_total.labels(outcome='error').inc()
        raise
    finally:
        duration = time.time() - start_time
        call_duration.observe(duration)
        active_sessions.dec()
```

### Log Aggregation

**ELK Stack (Elasticsearch, Logstash, Kibana):**

```yaml
# logstash.conf
input {
  file {
    path => "/var/log/debt-collection/*.log"
    codec => json
  }
}

filter {
  if [level] == "ERROR" {
    mutate {
      add_tag => ["error"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "debt-collection-%{+YYYY.MM.dd}"
  }
}
```

**CloudWatch Logs (AWS):**

```python
import boto3
import json
from datetime import datetime

def send_to_cloudwatch(log_group, log_stream, message):
    client = boto3.client('logs')

    client.put_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        logEvents=[{
            'timestamp': int(datetime.now().timestamp() * 1000),
            'message': json.dumps(message)
        }]
    )
```

### Health Checks

**Agent Worker Health Endpoint:**

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

health_status = {
    'status': 'healthy',
    'last_check': datetime.now().isoformat(),
    'active_sessions': 0,
    'total_calls': 0,
}

@app.get('/health')
def health_check():
    return health_status

@app.get('/ready')
def readiness_check():
    # Check dependencies
    if not check_livekit_connection():
        return {'status': 'not_ready', 'reason': 'livekit_unavailable'}, 503
    if not check_openai_api():
        return {'status': 'not_ready', 'reason': 'openai_unavailable'}, 503
    return {'status': 'ready'}
```

### Alerting Rules

**Prometheus Alerting:**

```yaml
# alerts.yml
groups:
  - name: debt_collection
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(debt_collection_calls_total{outcome="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} calls/sec"

      - alert: LowVerificationRate
        expr: rate(debt_collection_verification_success_total[10m]) / rate(debt_collection_calls_total[10m]) < 0.5
        for: 10m
        annotations:
          summary: "Verification success rate below 50%"

      - alert: AgentWorkerDown
        expr: up{job="debt_collection_agent"} == 0
        for: 2m
        annotations:
          summary: "Agent worker instance down"
```

---

## Performance Tuning Guidelines

### LLM Optimization

**1. Prompt Engineering:**
- Keep prompts concise (under 1000 tokens)
- Use structured formats (YAML, JSON) for context
- Avoid redundant information in system messages
- Pre-compute dynamic prompt sections during initialization

**2. Response Streaming:**
```python
llm = openai.LLM(
    model="gpt-4o-mini",
    temperature=0.7,
    stream=True  # Enable streaming for faster perceived response
)
```

**3. Context Window Management:**
```python
# Limit chat context size
CHAT_CONTEXT_MAX_ITEMS = 6  # Last 6 messages only

# Truncate on handoff
truncated_chat_ctx = prev_agent.chat_ctx.copy().truncate(max_items=6)
```

### TTS Optimization

**1. Voice Selection:**
- Use faster voices in production (cartesia has low latency)
- Avoid overly complex voice synthesis
- Pre-generate common phrases (greetings, closings)

**2. Chunking Strategy:**
```python
# Stream TTS in chunks for faster playback
tts = cartesia.TTS(
    voice="79a125e8-cd45-4c13-8a67-188112f4dd22",
    chunk_length_seconds=0.5  # Smaller chunks for lower latency
)
```

### Network Optimization

**1. Connection Pooling:**
```python
import aiohttp

# Reuse HTTP sessions
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=100, limit_per_host=30)
)
```

**2. Regional Deployment:**
- Deploy agent workers in same region as LiveKit server
- Use CDN for static assets
- Minimize inter-region network hops

### Resource Limits

**Docker Container Limits:**

```yaml
# docker-compose.yml
services:
  agent-worker:
    image: debt-collection-agent:latest
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 2G
        reservations:
          cpus: '2'
          memory: 512M
    environment:
      - MAX_CONCURRENT_SESSIONS=15
```

**Process Limits:**

```python
# In agents.py
import asyncio

# Limit concurrent sessions per worker
semaphore = asyncio.Semaphore(15)

@server.rtc_session(agent_name=get_agent_id())
async def entrypoint(ctx: JobContext):
    async with semaphore:
        # ... session logic
```

---

## Security Hardening Steps

### 1. Network Security

**Firewall Rules:**
```bash
# Allow only necessary ports
ufw allow 8083/tcp  # Agent worker port
ufw allow 443/tcp   # HTTPS
ufw deny 22/tcp     # Disable SSH from public internet
ufw enable
```

**IP Whitelisting:**
```python
# In agents.py
ALLOWED_IPS = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']

def check_ip_allowed(ip: str) -> bool:
    import ipaddress
    ip_obj = ipaddress.ip_address(ip)
    return any(ip_obj in ipaddress.ip_network(net) for net in ALLOWED_IPS)
```

### 2. API Key Rotation

**Rotation Schedule:**
- LiveKit API keys: Every 90 days
- OpenAI API keys: Every 90 days
- Deepgram/Cartesia keys: Every 90 days

**Automated Rotation Script:**
```python
import boto3
from datetime import datetime, timedelta

def rotate_api_keys():
    sm = boto3.client('secretsmanager')

    # Get current secret
    response = sm.get_secret_value(SecretId='debt-collection/agent')
    current = json.loads(response['SecretString'])

    # Check if rotation needed
    last_rotation = datetime.fromisoformat(current.get('last_rotation', '2000-01-01'))
    if datetime.now() - last_rotation < timedelta(days=90):
        return

    # Generate new keys (implementation specific to each service)
    new_keys = {
        'livekit_api_key': generate_new_livekit_key(),
        'openai_api_key': generate_new_openai_key(),
        'last_rotation': datetime.now().isoformat()
    }

    # Update secret
    sm.update_secret(SecretId='debt-collection/agent', SecretString=json.dumps(new_keys))

    # Notify deployment to restart workers
    notify_restart_required()
```

### 3. Input Validation

**Already Implemented:**
- Prompt sanitization (removes control characters, truncates length)
- Bank details validation (whitelist, format checks)
- Amount validation (positive, max limits)

**Additional Hardening:**
```python
def validate_metadata(metadata: dict) -> dict:
    """Validate and sanitize job metadata before processing."""
    required_fields = ['debtor', 'script_type']
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    # Sanitize all string fields
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_for_prompt(value, max_length=500)
        elif isinstance(value, dict):
            sanitized[key] = validate_metadata(value)  # Recursive
        else:
            sanitized[key] = value

    return sanitized
```

### 4. Audit Log Protection

**Tamper-Proof Logging:**
```python
import hashlib
import hmac

class TamperProofAuditLog:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.events = []
        self.last_hash = None

    def log_event(self, event: AuditEvent):
        # Serialize event
        event_data = json.dumps({
            'type': event.event_type.value,
            'timestamp': event.timestamp,
            'agent_id': event.agent_id,
            'details': event.details,
            'prev_hash': self.last_hash
        })

        # Compute HMAC
        event_hash = hmac.new(
            self.secret_key.encode(),
            event_data.encode(),
            hashlib.sha256
        ).hexdigest()

        # Store event with hash
        self.events.append({
            'data': event_data,
            'hash': event_hash
        })
        self.last_hash = event_hash

    def verify_integrity(self) -> bool:
        """Verify entire audit log hasn't been tampered with."""
        prev_hash = None
        for entry in self.events:
            event_data = json.loads(entry['data'])
            if event_data['prev_hash'] != prev_hash:
                return False
            # Recompute HMAC and verify
            expected_hash = hmac.new(
                self.secret_key.encode(),
                entry['data'].encode(),
                hashlib.sha256
            ).hexdigest()
            if expected_hash != entry['hash']:
                return False
            prev_hash = entry['hash']
        return True
```

### 5. Rate Limiting

**Per-User Rate Limiting:**
```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_calls: int, window: timedelta):
        self.max_calls = max_calls
        self.window = window
        self.calls = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        cutoff = now - self.window

        # Remove old calls
        self.calls[user_id] = [
            timestamp for timestamp in self.calls[user_id]
            if timestamp > cutoff
        ]

        # Check limit
        if len(self.calls[user_id]) >= self.max_calls:
            return False

        self.calls[user_id].append(now)
        return True

# Usage
rate_limiter = RateLimiter(max_calls=5, window=timedelta(hours=1))

@server.rtc_session(agent_name=get_agent_id())
async def entrypoint(ctx: JobContext):
    user_id = ctx.job.metadata.get('debtor', {}).get('user_id')
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return  # Reject session
```

---

## Docker/Kubernetes Considerations

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY debt_collection/ ./debt_collection/
COPY livekit_custom_plugins/ ./livekit_custom_plugins/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV AGENT_PORT=8083

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run agent
WORKDIR /app/debt_collection
CMD ["python", "agents.py", "dev"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  agent-worker-1:
    build: .
    container_name: debt-collection-agent-1
    restart: unless-stopped
    environment:
      - LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}
      - CARTESIA_API_KEY=${CARTESIA_API_KEY}
      - AGENT_PORT=8083
    ports:
      - "8083:8083"
      - "9090:9090"  # Metrics
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 2G
        reservations:
          cpus: '2'
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  agent-worker-2:
    extends: agent-worker-1
    container_name: debt-collection-agent-2
    ports:
      - "8084:8083"
      - "9091:9090"

  agent-worker-3:
    extends: agent-worker-1
    container_name: debt-collection-agent-3
    ports:
      - "8085:8083"
      - "9092:9090"
```

### Kubernetes Deployment

**deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: debt-collection-agent
  namespace: voice-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: debt-collection-agent
  template:
    metadata:
      labels:
        app: debt-collection-agent
    spec:
      containers:
      - name: agent
        image: your-registry/debt-collection-agent:latest
        ports:
        - containerPort: 8083
          name: agent
        - containerPort: 9090
          name: metrics
        env:
        - name: LIVEKIT_URL
          valueFrom:
            secretKeyRef:
              name: debt-collection-secrets
              key: livekit-url
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: debt-collection-secrets
              key: livekit-api-key
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: debt-collection-secrets
              key: livekit-api-secret
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: debt-collection-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "2"
          limits:
            memory: "2Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 9090
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 9090
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: debt-collection-agent
  namespace: voice-agents
spec:
  selector:
    app: debt-collection-agent
  ports:
  - name: agent
    port: 8083
    targetPort: 8083
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: debt-collection-agent-hpa
  namespace: voice-agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: debt-collection-agent
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**secrets.yaml:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: debt-collection-secrets
  namespace: voice-agents
type: Opaque
stringData:
  livekit-url: "wss://your-livekit-server.com"
  livekit-api-key: "your-api-key"
  livekit-api-secret: "your-api-secret"
  openai-api-key: "sk-your-openai-key"
  deepgram-api-key: "your-deepgram-key"
  cartesia-api-key: "your-cartesia-key"
```

### Deployment Commands

**Docker:**
```bash
# Build image
docker build -t debt-collection-agent:latest .

# Run container
docker run -d \
  --name debt-collection-agent \
  -p 8083:8083 \
  --env-file .env \
  debt-collection-agent:latest

# View logs
docker logs -f debt-collection-agent

# Stop container
docker stop debt-collection-agent
```

**Kubernetes:**
```bash
# Apply secrets
kubectl apply -f secrets.yaml

# Deploy application
kubectl apply -f deployment.yaml

# Check status
kubectl get pods -n voice-agents
kubectl describe deployment debt-collection-agent -n voice-agents

# View logs
kubectl logs -f deployment/debt-collection-agent -n voice-agents

# Scale manually
kubectl scale deployment debt-collection-agent --replicas=5 -n voice-agents

# Delete deployment
kubectl delete -f deployment.yaml
```

---

## Disaster Recovery

### Backup Strategy

**What to Backup:**
1. Configuration files (agent.yaml, prompt YAMLs)
2. Audit logs (export to S3/persistent storage)
3. Call transcripts (if enabled)
4. Environment configurations

**Backup Script:**
```bash
#!/bin/bash

BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r debt_collection/*.yaml "$BACKUP_DIR/"

# Backup audit logs (if persisted)
cp -r /var/log/debt-collection "$BACKUP_DIR/"

# Compress
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"

# Upload to S3
aws s3 cp "$BACKUP_DIR.tar.gz" s3://your-backup-bucket/debt-collection/

# Clean old backups (keep 30 days)
find /backups -name "*.tar.gz" -mtime +30 -delete
```

### Recovery Procedures

**Scenario 1: Agent Worker Failure**
1. Kubernetes will automatically restart failed pods (if using K8s)
2. Docker Compose will restart containers (if `restart: unless-stopped`)
3. Manual restart: `docker restart debt-collection-agent`

**Scenario 2: LiveKit Server Failure**
1. Agent workers will disconnect and retry connection
2. Monitor LiveKit server health
3. Restore LiveKit server from backup
4. Agent workers will automatically reconnect

**Scenario 3: Complete Infrastructure Failure**
1. Restore from infrastructure-as-code (Terraform, CloudFormation)
2. Deploy LiveKit server cluster
3. Deploy agent workers
4. Restore configuration from backups
5. Verify health checks passing
6. Resume traffic

---

## Troubleshooting Guide

### Common Issues

**Issue: Agent not connecting to LiveKit**
```
Solution:
1. Check LIVEKIT_URL is correct (ws:// for local, wss:// for production)
2. Verify LIVEKIT_API_KEY and LIVEKIT_API_SECRET match server
3. Check network connectivity: ping livekit-server
4. Review agent logs for connection errors
5. Verify LiveKit server is running and accessible
```

**Issue: High latency in responses**
```
Solution:
1. Check LLM API latency (OpenAI status page)
2. Verify network latency to AI services
3. Review prompt length (keep under 1000 tokens)
4. Enable response streaming
5. Optimize TTS voice selection
6. Check CPU/memory usage on agent workers
```

**Issue: Verification failures**
```
Solution:
1. Review fuzzy matching threshold (currently 0.8)
2. Check voice input normalization (spoken_digits.py)
3. Verify debtor data quality in job metadata
4. Review audit logs for verification attempts
5. Adjust MAX_FIELD_ATTEMPTS if needed
```

**Issue: Memory leak**
```
Solution:
1. Monitor memory usage: docker stats
2. Check for unclosed connections or streams
3. Review chat context truncation settings
4. Ensure proper cleanup on session end
5. Restart worker instances periodically
```

### Debug Mode

**Enable Debug Logging:**
```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env
LOG_LEVEL=DEBUG
```

**Trace Specific Sessions:**
```python
# In agents.py
@server.rtc_session(agent_name=get_agent_id())
async def entrypoint(ctx: JobContext):
    user_id = metadata.get('debtor', {}).get('user_id')
    logger.info(f"Starting session for user_id: {user_id}")

    # Enable trace for specific user
    if user_id == "debug_user_123":
        logging.getLogger().setLevel(logging.DEBUG)
```
