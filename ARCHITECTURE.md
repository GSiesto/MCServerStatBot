# MCServerStatBot - Target Architecture

> **Visual representation of the proposed AWS-ready architecture**

## High-Level Architecture Overview

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
│                  ┌────────────────────────┼────────────────────────┐       │
│                  │                        │                        │       │
│                  │  Application Load Balancer (ALB) - Alternative  │       │
│                  │  - Target Group Routing                         │       │
│                  │  - Health Checks                                │       │
│                  │  - Sticky Sessions (if needed)                  │       │
│                  └────────────────────────┬────────────────────────┘       │
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
│  │                Data & Caching Layer                │                  ││
│  │                        │                           │                  ││
│  │  ┌─────────────────────▼────┐        ┌────────────▼────────────────┐││
│  │  │    DynamoDB              │        │  ElastiCache (Redis)        │││
│  │  │                          │        │                             │││
│  │  │  Table: user_sessions    │        │  - Cluster Mode Enabled     │││
│  │  │  ┌──────────────────┐   │        │  - Multi-AZ                 │││
│  │  │  │ chat_id (PK)     │   │        │  - Automatic Failover       │││
│  │  │  │ last_url         │   │        │                             │││
│  │  │  │ last_query_time  │   │        │  Key Pattern:               │││
│  │  │  │ server_data      │   │        │  mc:server:{host}:status    │││
│  │  │  │ ttl              │   │        │  mc:server:{host}:players   │││
│  │  │  └──────────────────┘   │        │                             │││
│  │  │                          │        │  TTL: 30-60 seconds         │││
│  │  │  - On-Demand Billing     │        │  - In-Memory Performance    │││
│  │  │  - Point-in-Time Backup  │        │  - Pub/Sub (future)         │││
│  │  │  - DynamoDB Streams      │        └─────────────────────────────┘││
│  │  └──────────────────────────┘                                       ││
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

### User Command Flow: `/status minecraft.server.com`

```
1. User sends command
   │
   ▼
2. Telegram Platform
   │ (webhook POST)
   ▼
3. API Gateway / ALB
   │ (request validation, SSL termination)
   ▼
4. Bot Handler Service (ECS)
   │
   ├─▶ Parse command
   │   Extract URL: "minecraft.server.com"
   │
   ├─▶ Check DynamoDB for recent query
   │   Cache miss
   │
   ├─▶ HTTP POST to MC Query Service
   │   URL: http://mc-query-service/api/v1/status
   │   Body: {"server_url": "minecraft.server.com"}
   │   │
   │   ▼
   │   MC Query Service (ECS)
   │   │
   │   ├─▶ Check Redis cache
   │   │   Key: mc:server:minecraft.server.com:status
   │   │   Cache HIT → Return cached data (30s TTL)
   │   │
   │   └─▶ If cache MISS:
   │       ├─▶ Query Minecraft server (mcstatus)
   │       │   DNS lookup, TCP connection, protocol query
   │       │   Timeout: 5 seconds
   │       │
   │       ├─▶ Store result in Redis (TTL: 30-60s)
   │       │
   │       └─▶ Return response
   │
   ├─▶ Format response message
   │   "(ﾉ◕ヮ◕)ﾉ:･ﾟ✧\n✅ Online\nVersion: 1.20.1..."
   │
   ├─▶ Save to DynamoDB (chat state)
   │   {
   │     "chat_id": "12345",
   │     "last_url": "minecraft.server.com",
   │     "last_query_time": "2024-10-03T12:00:00Z",
   │     "server_data": {...}
   │   }
   │
   └─▶ Send formatted message to Telegram API
       │
       ▼
5. Telegram delivers to user
   With inline buttons: [Status] [Players] [About]
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
   ├─▶ Retrieve state from DynamoDB
   │   chat_id: "12345"
   │   → last_url: "minecraft.server.com"
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

### Scenario 3: DynamoDB Throttling
```
Bot Handler → DynamoDB Write (THROTTLED)
                ↓
           SDK Automatic Retry (exponential backoff)
                ↓
           If still failing after 3 retries:
                ↓
           Log error, continue without persistence
                ↓
           User still gets response (state lost)
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
   │ - Outbound: 443 (Telegram API), 6379 (Redis), 443 (DynamoDB)
   │
   ├─▶ ElastiCache (Security Group: 6379 from ECS only)
   └─▶ DynamoDB (VPC Endpoint, no internet)
```

### IAM Roles

**ECS Task Role (Bot Handler):**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "secretsmanager:GetSecretValue",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "xray:PutTraceSegments"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/user_sessions",
    "arn:aws:secretsmanager:*:*:secret/bot-token-*"
  ]
}
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

**Cost Optimization:**
- Use Fargate Spot for non-critical workloads: **-70% on compute**
- Reserved capacity for ElastiCache: **-30%**
- S3 for log archival: **-80% on storage**

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
