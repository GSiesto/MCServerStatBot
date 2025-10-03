# MCServerStatBot - Target Architecture

> **Visual representation of the proposed AWS-ready architecture**

## High-Level Architecture Overview

### **Serverless Architecture (RECOMMENDED - ~$0.93/month)**

```
                                    ┌─────────────────────────┐
                                    │   Telegram Platform     │
                                    │   (External Service)    │
                                    └───────────┬─────────────┘
                                                │
                                                │ HTTPS Webhooks
                                                │
                                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                     │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                            API Gateway                               │ │
│  │                            (REST API)                                │ │
│  │  - Webhook endpoint: POST /webhook                                  │ │
│  │  - Rate limiting: 10 req/sec per IP                                 │ │
│  │  - Request validation & throttling                                  │ │
│  │  - SSL/TLS termination                                              │ │
│  │  - Lambda integration (direct invocation)                           │ │
│  └────────────────────────────────┬─────────────────────────────────────┘ │
│                                   │                                       │
│                                   ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Serverless Compute Layer                        │ │
│  │                                                                      │ │
│  │  ┌────────────────────────────────┐    ┌──────────────────────────┐│ │
│  │  │   Bot Handler Lambda           │    │  MC Query Lambda         ││ │
│  │  │   Runtime: Python 3.12         │    │  Runtime: Python 3.12    ││ │
│  │  │   Memory: 512 MB               │    │  Memory: 512 MB          ││ │
│  │  │   Timeout: 30 seconds          │    │  Timeout: 10 seconds     ││ │
│  │  │                                │    │                          ││ │
│  │  │  ┌──────────────────────────┐ │    │  ┌────────────────────┐  ││ │
│  │  │  │ Python-Telegram-Bot 20.x │ │    │  │  mcstatus Library  │  ││ │
│  │  │  │ - Command Handlers       │ │    │  │  - Server Query    │  ││ │
│  │  │  │ - Callback Handlers      │ │    │  │  - Retry Logic     │  ││ │
│  │  │  │ - Message Formatting     │ │    │  └────────────────────┘  ││ │
│  │  │  └──────────────────────────┘ │    │                          ││ │
│  │  │                                │    │  ┌────────────────────┐  ││ │
│  │  │  ┌──────────────────────────┐ │    │  │  In-Memory Cache   │  ││ │
│  │  │  │ Lambda Layer:            │ │    │  │  - MC query cache  │  ││ │
│  │  │  │ - Shared dependencies    │ │    │  │  - TTL: 30-60s     │  ││ │
│  │  │  │ - python-telegram-bot    │ │    │  │  - Ephemeral       │  ││ │
│  │  │  │ - requests, pydantic     │ │    │  └────────────────────┘  ││ │
│  │  │  └──────────────────────────┘ │    │                          ││ │
│  │  │                                │    │  Session Cache:          ││ │
│  │  │  Session Cache:                │    │  - Environment vars      ││ │
│  │  │  - Lambda env variables        │    │  - 5-min warmup window   ││ │
│  │  │  - 5-min function warmup       │    │                          ││ │
│  │  │                                │    │                          ││ │
│  │  │  Invocation: Event-driven     │    │  Invocation: HTTP/invoke ││ │
│  │  │  Concurrency: Auto-scale 0-1K │    │  Concurrency: Auto-scale ││ │
│  │  └────────────────────────────────┘    └──────────────────────────┘│ │
│  │                                                                      │ │
│  │  Key Benefits:                                                       │ │
│  │  ✅ Near-zero cost (~$0.93/month within free tier)                  │ │
│  │  ✅ Auto-scaling from 0 to 1000+ concurrent executions              │ │
│  │  ✅ No idle costs - pay only for actual requests                    │ │
│  │  ✅ No container management or server maintenance                   │ │
│  │  ✅ Built-in HA and fault tolerance across AZs                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Security & Secrets                              │ │
│  │                                                                      │ │
│  │  ┌──────────────────┐  ┌──────────────┐                            │ │
│  │  │ Secrets Manager  │  │ IAM Roles    │                            │ │
│  │  │ - Bot Token      │  │ - Lambda     │                            │ │
│  │  │ - API Keys       │  │ - Execute    │                            │ │
│  │  │ Auto-Rotation    │  │ - Logs       │                            │ │
│  │  └──────────────────┘  └──────────────┘                            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Observability Layer                               │ │
│  │                                                                      │ │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐      │ │
│  │  │ CloudWatch Logs  │  │ CloudWatch   │  │ AWS X-Ray       │      │ │
│  │  │ - Auto-created   │  │ Metrics      │  │ - Optional      │      │ │
│  │  │ - 7-day retain   │  │ - Built-in   │  │ - Tracing       │      │ │
│  │  └──────────────────┘  └──────────────┘  └─────────────────┘      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

### **Alternative: ECS Fargate Architecture (~$39/month)**
**For higher traffic or specific container requirements**

```
                                    ┌─────────────────────────┐
                                    │   Telegram Platform     │
                                    │   (External Service)    │
                                    └───────────┬─────────────┘
                                                │
                                                │ HTTPS Webhooks
                                                │
                                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                     │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                        Edge Layer                                    │ │
│  │                                                                      │ │
│  │  ┌────────────────────┐         ┌──────────────────────┐           │ │
│  │  │  Route 53 (DNS)    │────────▶│  CloudFront (CDN)    │           │ │
│  │  │                    │         │  Optional            │           │ │
│  │  └────────────────────┘         └───────────┬──────────┘           │ │
│  │                                              │                      │ │
│  │                                              ▼                      │ │
│  │                            ┌──────────────────────────┐            │ │
│  │                            │   API Gateway (REST)     │            │ │
│  │                            │   - Webhook Endpoint     │            │ │
│  │                            │   - Rate Limiting        │            │ │
│  │                            │   - Request Validation   │            │ │
│  │                            │   - SSL/TLS Termination  │            │ │
│  │                            └──────────┬───────────────┘            │ │
│  └───────────────────────────────────────┼──────────────────────────────┘ │
│                                           │                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Compute Layer (ECS Fargate)                     │ │
│  │                                                                      │ │
│  │  ┌────────────────────────────────┐    ┌──────────────────────────┐│ │
│  │  │   Bot Handler Service          │    │  MC Query Service        ││ │
│  │  │   (Container)                  │    │  (Container)             ││ │
│  │  │                                │    │                          ││ │
│  │  │  ┌──────────────────────────┐ │    │  ┌────────────────────┐  ││ │
│  │  │  │  FastAPI Application     │ │    │  │  FastAPI App       │  ││ │
│  │  │  │  - Webhook Handler       │ │    │  │  - /status API     │  ││ │
│  │  │  │  - Health Check: /health │ │    │  │  - /players API    │  ││ │
│  │  │  └──────────────────────────┘ │    │  │  - /health         │  ││ │
│  │  │                                │    │  └────────────────────┘  ││ │
│  │  │  ┌──────────────────────────┐ │    │                          ││ │
│  │  │  │ Python-Telegram-Bot 20.x │ │    │  ┌────────────────────┐  ││ │
│  │  │  │ - Command Handlers       │ │    │  │  mcstatus Library  │  ││ │
│  │  │  │ - Callback Handlers      │ │    │  │  - Server Query    │  ││ │
│  │  │  │ - Message Formatting     │ │    │  │  - Connection Pool │  ││ │
│  │  │  └──────────────────────────┘ │    │  │  - Retry Logic     │  ││ │
│  │  │                                │    │  └────────────────────┘  ││ │
│  │  │  ┌──────────────────────────┐ │    │                          ││ │
│  │  │  │ HTTP Client              │◀┼────┼──┤  Cache Layer         │  ││ │
│  │  │  │ - Calls MC Query Service │ │    │  │  - Redis Client      │  ││ │
│  │  │  │ - Circuit Breaker        │ │    │  │  - TTL: 30-60s       │  ││ │
│  │  │  │ - Retry Logic            │ │    │  └────────────────────┘  ││ │
│  │  │  └──────────────────────────┘ │    │                          ││ │
│  │  │                                │    │                          ││ │
│  │  │  Auto-scaling: 1-10 instances │    │  Auto-scaling: 1-5 inst. ││ │
│  │  └────────────────────────────────┘    └──────────────────────────┘│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                           │                           │                    │
│                           │                           │                    │
│  ┌────────────────────────┼───────────────────────────┼──────────────────┐│
│  │            Caching Layer (Cost-Optimized)          │                  ││
│  │                        │                           │                  ││
│  │                        │          ┌────────────────▼────────────────┐││
│  │                        │          │  ElastiCache (Redis)            │││
│  │                        │          │  Single-AZ for cost savings     │││
│  │                        │          │  cache.t4g.micro (ARM, 0.5GB)   │││
│  │                        │          │                                 │││
│  │                        │          │  MC Query Cache (Primary):      │││
│  │                        │          │    mc:server:{host}:status      │││
│  │                        │          │    mc:server:{host}:players     │││
│  │                        │          │    TTL: 30-60 seconds           │││
│  │                        │          │                                 │││
│  │                        │          │  Session Cache (Optional):      │││
│  │                        │          │    session:{chat_id}            │││
│  │                        │          │    TTL: 300 seconds (5 min)     │││
│  │                        │          │                                 │││
│  │                        │          │  Benefits:                      │││
│  │                        │          │  - 80% query reduction          │││
│  │                        │          │  - No DynamoDB needed           │││
│  │                        │          │  - Stateless architecture       │││
│  │                        │          └─────────────────────────────────┘││
│  │                        │                                             ││
│  │  Note: DynamoDB eliminated for cost optimization.                   ││
│  │  Session state stored in Redis with 5-min TTL (acceptable tradeoff).││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Messaging Layer (Future)                          │ │
│  │                                                                      │ │
│  │  ┌──────────────────┐        ┌────────────────┐                    │ │
│  │  │  SQS Queue       │        │  SNS Topics    │                    │ │
│  │  │  - Async Jobs    │        │  - Notifications│                   │ │
│  │  │  - Dead Letter Q │        │  - Fan-out     │                    │ │
│  │  └──────────────────┘        └────────────────┘                    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      Security & Secrets                              │ │
│  │                                                                      │ │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐      │ │
│  │  │ Secrets Manager  │  │ IAM Roles    │  │ Security Groups │      │ │
│  │  │ - Bot Token      │  │ - ECS Task   │  │ - VPC Firewall  │      │ │
│  │  │ - API Keys       │  │ - Lambda     │  │ - Port Control  │      │ │
│  │  │ Auto-Rotation    │  │ - Read-Only  │  │ - Ingress Rules │      │ │
│  │  └──────────────────┘  └──────────────┘  └─────────────────┘      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Observability Layer                               │ │
│  │                                                                      │ │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐      │ │
│  │  │ CloudWatch Logs  │  │ CloudWatch   │  │ AWS X-Ray       │      │ │
│  │  │                  │  │ Metrics      │  │                 │      │ │
│  │  │ - Log Groups     │  │ - Custom     │  │ - Tracing       │      │ │
│  │  │ - Log Streams    │  │ - Alarms     │  │ - Service Map   │      │ │
│  │  │ - Log Insights   │  │ - Dashboards │  │ - Latency View  │      │ │
│  │  │ - Retention: 30d │  │              │  │                 │      │ │
│  │  └──────────────────┘  └──────────────┘  └─────────────────┘      │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────┐          │ │
│  │  │           CloudWatch Dashboard Example                │          │ │
│  │  │  - Total commands/hour                                │          │ │
│  │  │  - MC query success rate                              │          │ │
│  │  │  - Cache hit ratio                                    │          │ │
│  │  │  - Average response time                              │          │ │
│  │  │  - Error rate by type                                 │          │ │
│  │  │  - Container CPU/Memory                               │          │ │
│  │  └──────────────────────────────────────────────────────┘          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                        Network Layer                                 │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │  VPC (Virtual Private Cloud)                                 │  │ │
│  │  │                                                              │  │ │
│  │  │  ┌───────────────┐         ┌───────────────┐               │  │ │
│  │  │  │ Public Subnet │         │ Public Subnet │               │  │ │
│  │  │  │  AZ-1         │         │  AZ-2         │               │  │ │
│  │  │  │  - ALB        │         │  - ALB        │               │  │ │
│  │  │  │  - NAT GW     │         │  - NAT GW     │               │  │ │
│  │  │  └───────┬───────┘         └───────┬───────┘               │  │ │
│  │  │          │                         │                       │  │ │
│  │  │  ┌───────▼───────┐         ┌───────▼───────┐               │  │ │
│  │  │  │ Private       │         │ Private       │               │  │ │
│  │  │  │ Subnet AZ-1   │         │ Subnet AZ-2   │               │  │ │
│  │  │  │ - ECS Tasks   │         │ - ECS Tasks   │               │  │ │
│  │  │  │ - ElastiCache │         │ - ElastiCache │               │  │ │
│  │  │  └───────────────┘         └───────────────┘               │  │ │
│  │  │                                                              │  │ │
│  │  │  Benefits:                                                  │  │ │
│  │  │  - Multi-AZ for High Availability                           │  │ │
│  │  │  - Private subnets for secure services                      │  │ │
│  │  │  - NAT Gateway for outbound internet (MC queries)           │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

## Request Flow Diagram

### Serverless Flow: `/status minecraft.server.com`

```
1. User sends command
   │
   ▼
2. Telegram Platform
   │ (webhook POST)
   ▼
3. API Gateway
   │ (request validation, SSL termination, rate limiting)
   ▼
4. Bot Handler Lambda (invoked)
   │ Cold start: <1 second (first invocation)
   │ Warm: <10ms (subsequent invocations)
   │
   ├─▶ Parse command
   │   Extract URL: "minecraft.server.com"
   │
   ├─▶ Invoke MC Query Lambda (synchronous)
   │   Payload: {"server_url": "minecraft.server.com"}
   │   │
   │   ▼
   │   MC Query Lambda (invoked)
   │   │
   │   ├─▶ Check in-memory cache (Lambda container warmup)
   │   │   Key: minecraft.server.com:status
   │   │   Cache HIT → Return cached data (if Lambda warm + <30s old)
   │   │
   │   └─▶ If cache MISS or Lambda cold:
   │       ├─▶ Query Minecraft server (mcstatus)
   │       │   DNS lookup, TCP connection, protocol query
   │       │   Timeout: 5 seconds
   │       │
   │       ├─▶ Store result in Lambda memory (ephemeral cache)
   │       │   TTL: 30-60s (expires when Lambda container recycles)
   │       │
   │       └─▶ Return response to Bot Handler Lambda
   │
   ├─▶ Format response message
   │   "(ﾉ◕ヮ◕)ﾉ:･ﾟ✧\n✅ Online\nVersion: 1.20.1..."
   │
   ├─▶ Cache session in Lambda environment variable (for callbacks)
   │   Stored in warm Lambda container memory
   │   Available for ~5-15 minutes while Lambda stays warm
   │   Expires when Lambda container is recycled
   │
   └─▶ Send formatted message to Telegram API
       │
       ▼
5. Telegram delivers to user
   With inline buttons: [Status] [Players] [About]
   
**Note:** Lambda execution time: ~1-3 seconds total
**Cost per request:** ~$0.00002 (within free tier for first 1M requests)
```

### Callback Flow: User clicks [Players] button

```
1. User clicks inline button
   │
   ▼
2. Telegram Platform
   │ (webhook POST with callback_query)
   ▼
3. API Gateway / ALB
   │
   ▼
4. Bot Handler Service
   │
   ├─▶ Parse callback: "pattern_players"
   │
   ├─▶ Retrieve session from Redis
   │   Key: session:{chat_id}
   │   → last_url: "minecraft.server.com" (if not expired)
   │   Note: Works for queries in last 5 minutes
   │
   ├─▶ HTTP POST to MC Query Service
   │   URL: /api/v1/players
   │   Body: {"server_url": "minecraft.server.com"}
   │   │
   │   ▼
   │   MC Query Service
   │   │
   │   ├─▶ Check Redis cache
   │   │   Key: mc:server:minecraft.server.com:players
   │   │   Cache HIT → Return
   │   │
   │   └─▶ If MISS: Query server, cache, return
   │
   ├─▶ Format player list
   │   "Players (3): Steve, Alex, Notch"
   │
   └─▶ Edit message via Telegram API
       (updates existing message, not new one)
```

## Scaling & Performance

### Auto-Scaling Configuration

**Bot Handler Service:**
```yaml
Min Tasks: 1
Max Tasks: 10
Scale Up: CPU > 70% OR Request Count > 100/min
Scale Down: CPU < 30% AND Request Count < 20/min
Cooldown: 60 seconds
```

**MC Query Service:**
```yaml
Min Tasks: 1
Max Tasks: 5
Scale Up: CPU > 60% OR Queue Depth > 50
Scale Down: CPU < 25% AND Queue Depth < 5
Cooldown: 120 seconds
```

### Performance Metrics (Expected)

| Metric | Without Cache | With Cache | Improvement |
|--------|--------------|------------|-------------|
| **Avg Response Time** | 800-1200ms | 150-300ms | **75% faster** |
| **MC Server Load** | 100% queries hit server | ~20% queries hit server | **80% reduction** |
| **Bot Throughput** | ~50 cmd/min | ~500 cmd/min | **10x increase** |
| **Cost per 1M requests** | $50 | $15 | **70% savings** |

### Cache Strategy

**Redis TTL Strategy:**
- **Status queries**: 60 seconds (changes infrequently)
- **Player list**: 30 seconds (changes frequently)
- **Server offline**: 10 seconds (quick retry)

**Cache Key Patterns:**
```
mc:server:{hostname}:status     → Status object (JSON)
mc:server:{hostname}:players    → Player list (JSON)
mc:server:{hostname}:error      → Error state (string)
```

## Failure Scenarios & Resilience

### Scenario 1: MC Query Service Down
```
Bot Handler → HTTP request → MC Query Service (DOWN)
                ↓
           Timeout (3s)
                ↓
           Retry #1 (exponential backoff)
                ↓
           Timeout (3s)
                ↓
           Circuit Breaker OPEN
                ↓
           Return cached data from DynamoDB (if available)
                OR
           Return friendly error: "Service temporarily unavailable"
```

### Scenario 2: Redis Cache Unavailable
```
MC Query Service → Redis (DOWN)
                ↓
           Cache Miss (treat as miss)
                ↓
           Query Minecraft server directly
                ↓
           Log warning to CloudWatch
                ↓
           Continue without cache (degraded mode)
```

### Scenario 3: Session Cache Unavailable (Redis Down for Sessions)
```
Bot Handler → Redis Write (session) (FAILED)
                ↓
           Continue without session storage
                ↓
           User gets response immediately
                ↓
           Tradeoff: Callback buttons won't work
                ↓
           User can re-run command if needed
                ↓
           No impact on core /status and /players commands
```

## Security Architecture

### Network Security
```
Internet
   │ HTTPS (443)
   ▼
API Gateway (WAF enabled)
   │ - Rate limiting: 10 req/sec per IP
   │ - Bot detection
   │ - SQL injection filtering
   ▼
ALB (Security Group: 443 from API Gateway only)
   │
   ▼
ECS Tasks (Private Subnet)
   │ Security Group:
   │ - Inbound: 8080 from ALB only
   │ - Outbound: 443 (Telegram API), 6379 (Redis)
   │
   └─▶ ElastiCache (Security Group: 6379 from ECS only)
```

### IAM Roles

**ECS Task Role (Bot Handler) - Cost-Optimized:**
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "xray:PutTraceSegments"
  ],
  "Resource": [
    "arn:aws:secretsmanager:*:*:secret/bot-token-*"
  ]
}
```
Note: DynamoDB permissions removed - no persistent storage needed
```

**ECS Task Role (MC Query Service):**
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "xray:PutTraceSegments"
  ],
  "Resource": "*"
}
```

## Cost Estimation (Monthly)

### Standard Architecture (With Session Storage)
**Assumptions:** 10,000 users, 50,000 commands/day

| Service | Usage | Cost |
|---------|-------|------|
| **ECS Fargate** | 2 services, avg 3 tasks (0.5 vCPU, 1GB RAM) | $50 |
| **ALB** | 1 ALB, 500 LCU-hours | $25 |
| **DynamoDB** | On-Demand, 1.5M reads, 500K writes | $5 |
| **ElastiCache** | cache.t3.micro (0.5GB) | $12 |
| **API Gateway** | 1.5M requests | $5 |
| **CloudWatch** | Logs (10GB), Metrics, Alarms | $15 |
| **Data Transfer** | 50GB outbound | $5 |
| **Secrets Manager** | 2 secrets, 50K API calls | $1 |
| **Total** | | **~$118/month** |

### **Serverless Architecture with AWS Lambda (RECOMMENDED)** 🎯
**Near-zero cost using AWS Free Tier for low-traffic scenarios**

| Service | Free Tier | Typical Usage (50K cmd/day) | Cost |
|---------|-----------|------------------------------|------|
| **Lambda** | 1M requests/mo, 400K GB-sec/mo | ~1.5M requests/mo (50K×30 days) | **$0** (within free tier) |
| **API Gateway** | 1M requests/mo (12 months) | 1.5M requests/mo | **$0.50** (500K × $0.001) |
| **ElastiCache** | None | **ELIMINATED** - Use Lambda caching | **$0** |
| **CloudWatch Logs** | 5GB ingestion/mo | ~2GB/mo | **$0** (within free tier) |
| **Secrets Manager** | First 30 days free | 2 secrets, 50K API calls | **$0.43** ($0.40 + $0.03) |
| **Data Transfer** | 100GB/mo | ~5GB/mo | **$0** (within free tier) |
| **Total** | | | **~$0.93/month** 💰 |

**After 12-month Free Tier expires (API Gateway):**
- API Gateway: $5/month
- **Total: ~$5.43/month** (still 95% cheaper than ECS)

### **Alternative: ECS Fargate Architecture** (For comparison)
**For higher traffic or if Lambda limits become a constraint**

| Service | Usage | Cost |
|---------|-------|------|
| **ECS Fargate (Spot)** | 2 services, 2 tasks (0.25 vCPU, 0.5GB) | $15 |
| **ElastiCache** | cache.t4g.micro (0.5GB) ARM | $8 |
| **API Gateway** | 1.5M requests | $5 |
| **CloudWatch** | Logs (5GB, 7-day retention) | $5 |
| **Data Transfer** | 50GB outbound | $5 |
| **Secrets Manager** | 2 secrets, 50K API calls | $1 |
| **Total** | | **~$39/month** |

### Cost Optimization Strategy: Serverless-First

**Why Lambda is Perfect for This Bot:**
1. ✅ **Intermittent traffic** - Bot responds only when users send commands (not 24/7 load)
2. ✅ **Low request volume** - 50K commands/day = ~1.5M requests/month (within Lambda free tier)
3. ✅ **Short execution time** - Minecraft queries typically complete in 1-3 seconds
4. ✅ **No cold start impact** - Telegram webhooks have 30+ second timeout, Lambda cold start (<1s) is acceptable
5. ✅ **Built-in caching** - Lambda can cache Minecraft query results in memory between invocations
6. ✅ **Auto-scaling** - Scales from 0 to 1000s of concurrent executions automatically
7. ✅ **No idle costs** - Pay only for actual requests, not for 24/7 running containers

**Lambda Free Tier Coverage:**
- **1M requests/month**: Covers up to ~33K commands/day
- **400,000 GB-seconds/month**: With 512MB memory and 2s avg execution = 800K requests/month
- For 50K commands/day (1.5M/month), cost is minimal even beyond free tier

**Eliminated Services (Serverless Benefits):**
- ❌ **ElastiCache removed**: Lambda's ephemeral storage + in-memory caching sufficient
- ❌ **ECS Fargate removed**: Lambda replaces container orchestration
- ❌ **ALB removed**: API Gateway handles all routing
- ❌ **DynamoDB removed**: Stateless operation with optional Lambda environment variables for short-term caching

## Deployment Strategy (Future)

### Blue-Green Deployment
```
Current (Blue):  Task Definition v5 → 100% traffic
New (Green):     Task Definition v6 → 0% traffic
                                    ↓
                            Deploy v6 (green)
                                    ↓
                            Health checks pass
                                    ↓
                            Shift 10% traffic
                                    ↓
                            Monitor for 5 minutes
                                    ↓
                            Shift 50% traffic
                                    ↓
                            Monitor for 5 minutes
                                    ↓
                            Shift 100% traffic
                                    ↓
                            Keep blue for 1 hour (rollback)
                                    ↓
                            Decommission blue
```

### Rollback Procedure
```
1. Detect issue (error rate > 5%, latency > 2s)
2. CloudWatch Alarm triggers
3. Shift 100% traffic back to blue
4. Investigate issue in logs
5. Fix and redeploy green
```

---

## Summary

This architecture provides:
- ✅ **High Availability**: Multi-AZ, auto-scaling, failover
- ✅ **Performance**: Caching, async I/O, optimized queries
- ✅ **Security**: VPC isolation, IAM roles, secrets management
- ✅ **Observability**: Logs, metrics, tracing, alarms
- ✅ **Cost-Effective**: Serverless where possible, auto-scaling
- ✅ **Maintainable**: Microservices, IaC, CI/CD

**Next Steps:** See [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) for implementation details.
