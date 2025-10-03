# MCServerStatBot - Refactoring Summary

> **Full details in [REFACTORING_PLAN.md](./REFACTORING_PLAN.md)**

## 🎯 Project Purpose

A **Telegram bot** that checks Minecraft server status and shows connected players.

## 📊 Current State (Critical Issues)

1. **🔴 CRITICAL: Outdated Stack**
   - Python 3.6.14 (EOL since Dec 2021)
   - python-telegram-bot 13.7 (now at 20.x)
   - Security vulnerabilities, no patches

2. **🟡 HIGH: Monolithic Design**
   - No separation of concerns
   - Hard to test, scale, or maintain
   - Bare exception handling

3. **🟡 HIGH: Heroku Lock-in**
   - Hard-coded Heroku URLs
   - File-based persistence (no horizontal scaling)
   - No containerization

## 🏗️ Target Architecture (AWS-Ready)

```
Telegram Users
     ↓
API Gateway
     ↓
┌────────────────────────────────────────┐
│    AWS Lambda (Serverless)             │
│  ┌──────────────┐  ┌────────────────┐ │
│  │ Bot Handler  │→ │ MC Query       │ │
│  │   Lambda     │  │   Lambda       │ │
│  └──────────────┘  └────────────────┘ │
│  (Event-driven, auto-scale, $0 idle)  │
└────────────────────────────────────────┘
       In-memory cache (ephemeral)
```

### Key AWS Services (Serverless - RECOMMENDED)
- **AWS Lambda**: Compute (2 functions) - $0 within free tier (1M req/month)
- **Lambda Function URL**: Native HTTPS webhook endpoint - $0 (always free)
- **Encrypted Environment Variables**: Bot tokens via KMS - $0 within free tier (20K req/month)
- **CloudWatch**: Logs, metrics - $0 within free tier (5GB/month)

**Total Cost: $0/month** 💰🎉

**Cost Breakdown:**
- Lambda: $0 (within 1M request/month free tier)
- Lambda Function URL: $0 (always free, no API Gateway needed)
- KMS encryption: $0 (within 20K request/month free tier)
- CloudWatch: $0 (within 5GB free tier)
- Data Transfer: $0 (within 100GB free tier)

**Long-term cost if exceeding free tier:** ~$0.20/month at 2M requests/month

**Ultra-Optimizations Applied:**
- ✅ **Lambda Function URL** replaces API Gateway (saves $0.50-$5/month)
- ✅ **Encrypted env variables** replace Secrets Manager (saves $0.43/month)
- ✅ **ECS Fargate removed**: Lambda replaces containers (-$15/month)
- ✅ **ElastiCache removed**: Lambda in-memory cache sufficient (-$8/month)
- ✅ **DynamoDB removed**: Stateless operation (-$5/month)
- ✅ **ALB removed**: Lambda Function URL handles routing (-$25/month)

**Alternative: ECS Fargate (~$39/month)**
- Use if traffic consistently exceeds 1M requests/month
- Or if specific container requirements exist

## 🚀 Modernized Tech Stack

| Component | Current | Proposed |
|-----------|---------|----------|
| **Python** | 3.6.14 (EOL) | **3.12** (2028 support) |
| **Bot Framework** | PTB 13.7 | **PTB 20.7+** (async) |
| **MC Client** | mcstatus 6.4.0 | **mcstatus 11.x** |
| **Web Framework** | - | **FastAPI 0.109+** |
| **Data Validation** | - | **Pydantic 2.x** |
| **Redis** | - | **redis-py 5.x** (async) |
| **AWS SDK** | - | **boto3** |
| **Testing** | None | **pytest 8.x + pytest-asyncio** |
| **Linting** | None | **ruff + mypy** |
| **Container** | None | **Docker** (multi-stage) |
| **Dependency Mgmt** | requirements.txt | **Poetry** or **PDM** |

## 📅 5-Phase Refactoring Plan

### Phase 1: Foundation (1-2 weeks) - **MEDIUM**
- ✅ Upgrade to Python 3.12
- ✅ Update all dependencies
- ✅ Add type hints + mypy
- ✅ Set up CI/CD (GitHub Actions)
- ✅ Basic test suite (pytest)

### Phase 2: Service Layer (2-3 weeks) - **HIGH**
- ✅ Extract business logic from handlers
- ✅ Dependency injection
- ✅ Repository pattern
- ✅ Async/await throughout
- ✅ Proper error handling

### Phase 3: Containerization (1-2 weeks) - **MEDIUM**
- ✅ Dockerfile + docker-compose
- ✅ Local dev environment (Redis for caching + sessions)
- ✅ Configuration management
- ✅ Health check endpoints

### Phase 4: Serverless Lambda Functions (1-2 weeks) - **MEDIUM** ⭐ RECOMMENDED
- ✅ Bot Handler Lambda + MC Query Lambda
- ✅ Lambda Function URL (native HTTPS endpoint)
- ✅ Lambda layers for dependencies
- ✅ In-memory caching (ephemeral)
- ✅ CloudWatch Logs integration
- ✅ **Cost: $0/month** (completely within free tier) 💰

**Alternative:** Container-based microservices (2-3 weeks, ~$39/month) if Lambda limits exceeded

### Phase 5: AWS Integration (1-2 weeks) - **MEDIUM**
- ✅ Encrypted environment variables (KMS) for bot token
- ✅ CloudWatch Logs + custom metrics
- ✅ Lambda Function URL webhook setup
- ✅ Lambda deployment automation (SAM/Terraform)
- ✅ ECS task definitions
- ✅ Deployment documentation

**Total Estimated Effort**: 6-10 weeks (1.5-2.5 months) for serverless architecture
*Alternative: 8-13 weeks for container-based architecture*

## 📁 New Directory Structure

```
MCServerStatBot/
├── services/
│   ├── bot_handler/          # Telegram webhook + routing
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/bot_handler/
│   │   │   ├── main.py       # FastAPI app
│   │   │   ├── handlers/     # Commands, callbacks
│   │   │   ├── services/     # Business logic
│   │   │   └── models/       # Pydantic schemas
│   │   └── tests/
│   └── mc_query_service/     # MC server queries
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── src/mc_query/
│       │   ├── main.py       # FastAPI app
│       │   ├── api/          # REST endpoints
│       │   └── services/     # Query logic + cache
│       └── tests/
├── shared/common/            # Shared utilities
│   └── aws/                  # Secrets Manager, CloudWatch
├── docker-compose.yml
├── .github/workflows/        # CI/CD
└── REFACTORING_PLAN.md       # Full details
```

## ✨ Key Improvements

### Performance
- ⚡ **80% cache hit rate** (Redis caching)
- ⚡ **Non-blocking async** (no thread blocking)
- ⚡ **Horizontal scaling** (stateless services)

### Reliability
- 🛡️ **Service isolation** (failures don't cascade)
- 🛡️ **Retry logic + circuit breakers**
- 🛡️ **Health checks** (auto-recovery)

### Observability
- 📊 **Centralized logging** (CloudWatch)
- 📊 **Custom metrics** (command counts, latency)
- 📊 **Distributed tracing** (X-Ray ready)

### Security
- 🔒 **Secrets Manager** (no hard-coded tokens)
- 🔒 **IAM roles** (no access keys)
- 🔒 **VPC isolation**

### Maintainability
- 🧪 **80%+ test coverage**
- 🧪 **Type safety** (mypy strict mode)
- 🧪 **Dependency injection** (easy mocking)
- 🧪 **CI/CD pipeline** (automated quality checks)

## 🎓 Architecture Principles

1. **Cloud-Native**: Designed for AWS from the ground up
2. **Microservices**: Independent, scalable services
3. **Event-Driven**: Async communication (future: SQS)
4. **Managed Services First**: Leverage AWS, reduce ops overhead
5. **Infrastructure as Code**: Reproducible deployments (future)
6. **Observability First**: Logs, metrics, traces by default

## 🚧 What's NOT Included (Future Work)

- ❌ Actual AWS infrastructure deployment (CDK/Terraform)
- ❌ Web dashboard (React/Vue.js)
- ❌ Multi-region deployment
- ❌ Kubernetes migration
- ❌ gRPC between services

## 📖 Next Steps

1. Read the [full refactoring plan](./REFACTORING_PLAN.md)
2. Review and approve the approach
3. Start with Phase 1 (Foundation)
4. Deploy to AWS after Phase 5

---

**Questions?** See [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) for complete details on architecture, tech stack, and implementation strategy.
