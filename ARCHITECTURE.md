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
   ├─▶ Cache session in Redis (optional, for callbacks)
   │   Key: session:{chat_id}
   │   Value: {last_url, query_time}
   │   TTL: 300 seconds (5 minutes)
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

### **Cost-Optimized Architecture (Recommended)** 💰
**Eliminates unnecessary storage, stateless operation**

| Service | Usage | Cost | Savings |
|---------|-------|------|---------|
| **ECS Fargate (Spot)** | 2 services, avg 2 tasks (0.25 vCPU, 0.5GB RAM) | $15 | -70% |
| **ALB** | Removed - API Gateway only | $0 | -100% |
| **DynamoDB** | **Eliminated** - stateless callbacks | $0 | -100% |
| **ElastiCache** | cache.t4g.micro (0.5GB) ARM | $8 | -33% |
| **API Gateway** | 1.5M requests | $5 | - |
| **CloudWatch** | Logs (5GB, 7-day retention), basic metrics | $5 | -67% |
| **Data Transfer** | 50GB outbound | $5 | - |
| **Secrets Manager** | 2 secrets, 50K API calls | $1 | - |
| **Total** | | **~$39/month** | **-67% savings** |

### Cost Optimization Strategies

**Immediate (Implemented in Cost-Optimized Architecture):**
- ✅ **Remove DynamoDB**: Use in-memory session cache (Redis) with TTL - callbacks work for recent queries only
- ✅ **Remove ALB**: API Gateway is sufficient for webhook traffic
- ✅ **Use Fargate Spot**: 70% discount for non-critical workloads
- ✅ **Reduce CloudWatch retention**: 7 days instead of 30 days
- ✅ **Right-size instances**: 0.25 vCPU instead of 0.5 vCPU per task
- ✅ **Use ARM processors**: T4g instances are 20-30% cheaper than T3

**Additional Savings (Optional):**
- Use Lambda instead of Fargate for Bot Handler: **-50% on compute** (~$25/mo total)
- Reduce ElastiCache to cache.t4g.nano (0.25GB): **-50% on cache** (~$32/mo total)
- Move to free tier services if under 1M requests/month: **$0/month**

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
