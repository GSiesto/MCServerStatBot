# MCServerStatBot - Refactoring Implementation Checklist

> **Quick reference checklist for implementing the 5-phase refactoring plan**
> 
> Full details in [../REFACTORING_PLAN.md](../REFACTORING_PLAN.md)

## ✅ Pre-Implementation Setup

- [ ] Review [REFACTORING_INDEX.md](../REFACTORING_INDEX.md)
- [ ] Read [REFACTORING_SUMMARY.md](../REFACTORING_SUMMARY.md)
- [ ] Review [REFACTORING_PLAN.md](../REFACTORING_PLAN.md)
- [ ] Set up development environment
  - [ ] Install Python 3.12
  - [ ] Install Docker Desktop
  - [ ] Install git, make, poetry/pdm
- [ ] Create feature branch: `git checkout -b refactor/milestone-1`

---

## 📋 Milestone 1: Foundation & Dependency Updates (1-2 weeks)

### 1.1 Python Version Upgrade
- [ ] Update `runtime.txt` to `python-3.12`
- [ ] Create `pyproject.toml` with Poetry/PDM
- [ ] Migrate from `requirements.txt` to `pyproject.toml`
- [ ] Test Python 3.12 compatibility locally

### 1.2 Dependency Modernization
- [ ] Upgrade `python-telegram-bot` 13.7 → 20.7+
  - [ ] Review breaking changes in PTB 20.x docs
  - [ ] Update all command handlers to async
  - [ ] Replace deprecated `pass_args`, `pass_chat_data`
  - [ ] Update callback handlers
- [ ] Upgrade `mcstatus` 6.4.0 → 11.x
- [ ] Add new dependencies:
  - [ ] `fastapi`
  - [ ] `pydantic`
  - [ ] `boto3`
  - [ ] `redis-py[async]`
  - [ ] `pytest` and plugins
  - [ ] Development tools: `ruff`, `mypy`, `pre-commit`

### 1.3 Code Quality Infrastructure
- [ ] Configure `ruff` for linting and formatting
  - [ ] Create `ruff.toml` or `pyproject.toml` config
  - [ ] Run `ruff check .` and fix issues
  - [ ] Run `ruff format .` to format code
- [ ] Configure `mypy` for type checking
  - [ ] Create `mypy.ini` config
  - [ ] Add `--strict` flag
- [ ] Set up `pre-commit` hooks
  - [ ] Create `.pre-commit-config.yaml`
  - [ ] Add hooks: ruff, mypy, trailing-whitespace, end-of-file
  - [ ] Run `pre-commit install`
- [ ] Create GitHub Actions CI pipeline
  - [ ] Create `.github/workflows/ci.yml`
  - [ ] Add jobs: lint, type-check, test
  - [ ] Badge in README

### 1.4 Type Annotations
- [ ] Add type hints to `utils.py`
- [ ] Add type hints to `main.py`
- [ ] Add type hints to `commands.py`
- [ ] Create Pydantic models for:
  - [ ] Server status response
  - [ ] Player query response
  - [ ] Chat session data
- [ ] Run `mypy` and resolve all errors

### 1.5 Basic Testing
- [ ] Set up pytest structure: `tests/unit/`, `tests/integration/`
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Write unit tests for `utils.validUrl()`
- [ ] Write unit tests for message formatting functions
- [ ] Mock Telegram API in handler tests
- [ ] Run tests: `pytest --cov`
- [ ] Achieve >70% code coverage

### 1.6 Milestone 1 Completion
- [ ] All tests pass on Python 3.12
- [ ] CI pipeline green
- [ ] No mypy errors
- [ ] Code passes ruff linting
- [ ] Bot functional in dev mode (polling)
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v0.1.0-milestone-1`

---

## 📋 Milestone 2: Architectural Separation - Service Layer (2-3 weeks)

### 2.1 Project Structure Setup
- [ ] Create new directory structure:
  ```
  src/
  ├── bot/
  │   ├── handlers/
  │   ├── services/
  │   ├── repositories/
  │   └── models/
  └── common/
      ├── exceptions.py
      └── utils/
  ```

### 2.2 Extract Business Logic
- [ ] Create `MinecraftQueryService` class
  - [ ] Extract Minecraft server query logic from commands
  - [ ] Implement async query methods
  - [ ] Add connection pooling
  - [ ] Add retry logic with exponential backoff
- [ ] Create `SessionService` class
  - [ ] Extract session management logic
  - [ ] Handle chat_data operations
- [ ] Create `MessageFormatter` class
  - [ ] Extract all message formatting functions
  - [ ] Templates for status, players, errors

### 2.3 Dependency Injection
- [ ] Install `dependency-injector` or create simple DI
- [ ] Create DI container
- [ ] Register services in container
- [ ] Inject services into handlers
- [ ] Remove global state

### 2.4 Repository Pattern
- [ ] Create `SessionRepository` interface (Protocol)
- [ ] Implement `FileSessionRepository` (current behavior)
- [ ] Methods: `get()`, `save()`, `delete()`
- [ ] Design for Redis session storage (cost-optimized, no DynamoDB needed)

### 2.5 Error Handling Refactor
- [ ] Create custom exception hierarchy:
  - [ ] `McServerStatBotException` (base)
  - [ ] `ServerOfflineError`
  - [ ] `QueryTimeoutError`
  - [ ] `InvalidUrlError`
- [ ] Replace bare `except:` with specific exceptions
- [ ] Create centralized error handler middleware
- [ ] Add structured error logging

### 2.6 Async/Await Throughout
- [ ] Convert all I/O operations to async
  - [ ] Minecraft queries
  - [ ] File operations
  - [ ] Telegram API calls
- [ ] Use `asyncio.gather()` for concurrent operations
- [ ] Implement async connection pooling

### 2.7 Testing
- [ ] Unit tests for `MinecraftQueryService` (mocked mcstatus)
- [ ] Unit tests for `SessionService`
- [ ] Unit tests for `MessageFormatter`
- [ ] Unit tests for `SessionRepository`
- [ ] Integration tests with real mcstatus calls
- [ ] Handler tests with service mocks
- [ ] Achieve >80% coverage

### 2.8 Milestone 2 Completion
- [ ] Business logic decoupled from Telegram API
- [ ] All services unit tested (>80% coverage)
- [ ] No bare `except` blocks
- [ ] All I/O is non-blocking async
- [ ] Can swap persistence without touching handlers
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v0.2.0-milestone-2`

---

## 📋 Milestone 3: Containerization & Local Development (1-2 weeks)

### 3.1 Dockerfile Creation
- [ ] Create multi-stage `Dockerfile`
  - [ ] Stage 1: Builder (install dependencies)
  - [ ] Stage 2: Testing (run tests)
  - [ ] Stage 3: Production (minimal image)
- [ ] Use `python:3.12-slim` as base
- [ ] Create non-root user
- [ ] Copy only necessary files
- [ ] Build image: `docker build -t mcserverstatbot:latest .`

### 3.2 Docker Compose Setup
- [ ] Create `docker-compose.yml`
  - [ ] Bot service
  - [ ] Redis container (for MC cache + sessions)
- [ ] Configure environment variables
- [ ] Set up volume mounts for development
- [ ] Test: `docker-compose up`

### 3.3 Configuration Management
- [ ] Create `config.py` using Pydantic Settings
- [ ] Environment-based config (dev/staging/prod)
- [ ] Load from environment variables
- [ ] Validate required variables
- [ ] Document all variables in README

### 3.4 Health Check Endpoints
- [ ] Add `/health` endpoint (liveness probe)
- [ ] Add `/ready` endpoint (readiness probe)
- [ ] Check Redis connection

### 3.5 Local Development Scripts
- [ ] Create `scripts/local_dev.sh`
- [ ] Create `scripts/test.sh`
- [ ] Create `scripts/build.sh`
- [ ] Add hot reload for development

### 3.6 Documentation
- [ ] Update README with Docker instructions
- [ ] Document environment variables
- [ ] Add troubleshooting section
- [ ] Add architecture diagram

### 3.7 Milestone 3 Completion
- [ ] Bot runs in Docker container
- [ ] `docker-compose up` starts all services
- [ ] Redis functional for caching and sessions
- [ ] Health check endpoints return 200 OK
- [ ] Hot reload works in development
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v0.3.0-milestone-3`

---

## 📋 Milestone 4: Serverless Lambda Functions (1-2 weeks) ⭐ RECOMMENDED

**Goal:** Deploy to AWS Lambda for near-zero cost (~$0.93/month)

### 4.1 Lambda Function Setup
- [ ] Create Lambda project structure:
  - [ ] `lambda/bot_handler/`
  - [ ] `lambda/mc_query/`
  - [ ] `lambda/layers/dependencies/`
- [ ] Set up AWS SAM or Terraform for IaC

### 4.2 Bot Handler Lambda
- [ ] Create Lambda handler function (`handler.py`)
- [ ] Integrate python-telegram-bot library
- [ ] Parse API Gateway event (webhook payload)
- [ ] Implement command routing logic
- [ ] Invoke MC Query Lambda (boto3 lambda.invoke())
- [ ] Format responses for Telegram
- [ ] Session caching in environment variables (ephemeral)
- [ ] Unit tests for handler

### 4.3 MC Query Lambda
- [ ] Create Lambda handler function (`handler.py`)
- [ ] Implement mcstatus server query logic
- [ ] In-memory caching (module-level globals)
- [ ] Timeout handling (5 seconds)
- [ ] Error handling and retry logic
- [ ] Return structured JSON response
- [ ] Unit tests for handler

### 4.4 Lambda Layers
- [ ] Create shared dependencies layer:
  - [ ] python-telegram-bot
  - [ ] mcstatus
  - [ ] requests
  - [ ] pydantic
- [ ] Build layer package (requirements.txt → ZIP)
- [ ] Deploy layer to AWS
- [ ] Attach layer to both Lambda functions

### 4.5 API Gateway Setup
- [ ] Create REST API in API Gateway
- [ ] Create POST /webhook endpoint
- [ ] Configure Lambda proxy integration
- [ ] Set up request validation
- [ ] Configure rate limiting (10 req/sec per IP)
- [ ] Test webhook with curl

### 4.6 Local Testing
- [ ] Install AWS SAM CLI
- [ ] Test Lambdas locally: `sam local invoke`
- [ ] Test API Gateway locally: `sam local start-api`
- [ ] Create test events for webhook payloads
- [ ] Verify cold start time (<1 second)

### 4.7 Deployment & Testing
- [ ] Deploy both Lambda functions to AWS
- [ ] Deploy API Gateway
- [ ] Configure Telegram webhook URL
- [ ] Integration test with real Telegram bot
- [ ] Load test to verify free tier coverage
- [ ] Monitor CloudWatch Logs

### 4.8 Milestone 4 Completion
- [ ] Both Lambda functions deployed
- [ ] API Gateway triggers Bot Handler Lambda
- [ ] MC Query Lambda invoked successfully
- [ ] In-memory caching functional
- [ ] CloudWatch Logs show invocations
- [ ] Cost within free tier (~$0.93/month)
- [ ] Cold start <1 second, warm <100ms
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v0.4.0-milestone-4-lambda`

---

## 📋 Alternative Milestone 4: Container-Based Microservices (2-3 weeks)

**Use only if:** Lambda limits exceeded (>1M req/month) or specific container needs

**Cost:** ~$39/month vs. $0.93/month for Lambda

### 4.1 Service Separation
- [ ] Define OpenAPI spec for MC Query Service
- [ ] Create two separate service directories:
  - [ ] `services/bot_handler/`
  - [ ] `services/mc_query_service/`

### 4.2 Bot Handler Service
- [ ] Set up FastAPI application
- [ ] Create webhook endpoint: `POST /webhook`
- [ ] Integrate python-telegram-bot with FastAPI
- [ ] Create HTTP client for MC Query Service
- [ ] Implement retry logic and circuit breaker
- [ ] Add health check: `GET /health`
- [ ] Dockerfile for bot handler
- [ ] Tests for webhook endpoint

### 4.3 MC Query Service
- [ ] Set up FastAPI application
- [ ] Create REST endpoints:
  - [ ] `POST /api/v1/status` - Get server status
  - [ ] `POST /api/v1/players` - Get player list
  - [ ] `GET /health` - Health check
- [ ] Implement Redis caching layer
  - [ ] Cache key pattern: `mc:server:{hostname}:status`
  - [ ] TTL: 30-60 seconds
- [ ] Connection pooling for Minecraft queries
- [ ] Add timeout and retry logic
- [ ] Dockerfile for MC query service
- [ ] Tests for all endpoints

### 4.4 Inter-Service Communication
- [ ] HTTP client with automatic retries (tenacity)
- [ ] Request/response schemas with Pydantic
- [ ] Circuit breaker pattern (optional)
- [ ] Correlation IDs for tracing

### 4.5 Observability
- [ ] Structured JSON logging
- [ ] Log correlation IDs across services
- [ ] Custom metrics endpoints (Prometheus format)
- [ ] OpenTelemetry instrumentation (optional)

### 4.6 Testing
- [ ] Unit tests for each service
- [ ] Integration tests with both services
- [ ] Contract tests for API
- [ ] Load testing with locust or k6
- [ ] Test caching behavior

### 4.7 Update Docker Compose
- [ ] Add bot_handler service
- [ ] Add mc_query_service
- [ ] Configure service networking
- [ ] Test inter-service communication

### 4.8 Milestone 4 Completion
- [ ] Two independent services in separate containers
- [ ] Services communicate via HTTP API
- [ ] Redis caching reduces queries by >80%
- [ ] Each service has health check
- [ ] Logs include correlation IDs
- [ ] Services deployable independently
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v0.4.0-milestone-4`

---

## 📋 Milestone 5: AWS Integration & Production Readiness (2-3 weeks)

### 5.1 AWS SDK Integration
- [ ] Add boto3 dependencies
- [ ] Configure IAM role-based auth (not credentials)
- [ ] Test locally with AWS credentials

### 5.2 Redis Session Storage (Cost-Optimized)
- [ ] Implement session caching in Redis:
  - [ ] Key pattern: `session:{chat_id}`
  - [ ] Value: `{last_url, query_time}`
  - [ ] TTL: 300 seconds (5 minutes)
- [ ] Test session storage locally
- [ ] Test with ElastiCache (dev account)
- [ ] Verify callback buttons work for recent queries

**Note:** DynamoDB skipped for cost optimization (-$5+/month savings)

### 5.3 Redis/ElastiCache Integration
- [ ] Update cache client for ElastiCache compatibility
- [ ] Connection pooling and failover handling
- [ ] Cache invalidation strategies
- [ ] Test with Redis locally
- [ ] Test with ElastiCache (dev account)

### 5.4 Secrets Management
- [ ] Move bot token to AWS Secrets Manager
- [ ] Update config to fetch secrets at startup
- [ ] Test secret rotation
- [ ] Document secret naming convention

### 5.5 CloudWatch Integration
- [ ] Configure CloudWatch Logs handler
- [ ] Add custom metrics:
  - [ ] Command counts by type
  - [ ] Query latency (p50, p95, p99)
  - [ ] Cache hit rate
  - [ ] Error rate by type
- [ ] Create CloudWatch Alarms:
  - [ ] Error rate > 5%
  - [ ] Average latency > 2s
- [ ] AWS X-Ray tracing (optional)

### 5.6 Webhook Configuration
- [ ] Update webhook endpoint to use API Gateway/ALB URL
- [ ] SSL/TLS certificate setup
- [ ] Remove Heroku-specific code
- [ ] Test webhook with Telegram

### 5.7 Production Configuration
- [ ] Create environment-specific configs
  - [ ] `config/dev.yaml`
  - [ ] `config/staging.yaml`
  - [ ] `config/prod.yaml`
- [ ] Configure resource limits
- [ ] Configure auto-scaling parameters
- [ ] Security hardening:
  - [ ] Non-root user
  - [ ] Read-only filesystem
  - [ ] Minimal base image

### 5.8 ECS Task Definitions
- [ ] Create ECS task definition for bot handler
- [ ] Create ECS task definition for MC query service
- [ ] Define CPU/memory requirements
- [ ] Configure health checks
- [ ] Set environment variables

### 5.9 Deployment Documentation
- [ ] Write step-by-step AWS deployment guide
- [ ] Document required IAM policies
- [ ] Create deployment checklist
- [ ] Document rollback procedures
- [ ] Create runbook for common issues

### 5.10 Testing
- [ ] Integration tests against real AWS services
- [ ] Chaos engineering: test service failures
- [ ] Performance testing under load
- [ ] Test auto-scaling behavior
- [ ] Test failover scenarios

### 5.11 Milestone 5 Completion
- [ ] Session state cached in Redis (5-min TTL)
- [ ] MC queries cached in Redis (30-60s TTL)
- [ ] All secrets from Secrets Manager
- [ ] Logs flow to CloudWatch Logs
- [ ] Custom metrics in CloudWatch
- [ ] Webhook mode functional with HTTPS
- [ ] Documentation complete
- [ ] Production-ready Docker images
- [ ] Cost-optimized: ~$39/month achieved
- [ ] Create PR and merge to main
- [ ] Tag release: `git tag v1.0.0-aws-ready`

---

## 🎉 Post-Refactoring Tasks

### Documentation
- [ ] Update main README.md
- [ ] Remove deprecated documentation
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Create operations runbook

### CI/CD Enhancement
- [ ] Add staging deployment pipeline
- [ ] Add production deployment pipeline
- [ ] Implement blue-green deployment
- [ ] Add automatic rollback on failure

### Monitoring & Alerts
- [ ] Create CloudWatch dashboard
- [ ] Set up PagerDuty/Opsgenie alerts
- [ ] Configure log-based metrics
- [ ] Test alert notification flow

### Security
- [ ] Set up Dependabot for dependency updates
- [ ] Configure Snyk for vulnerability scanning
- [ ] Enable AWS Security Hub
- [ ] Conduct security review

### Performance
- [ ] Run load tests
- [ ] Optimize slow queries
- [ ] Review CloudWatch metrics
- [ ] Implement additional caching if needed

---

## 📊 Success Criteria Checklist

### Technical
- [ ] Python 3.12 deployed
- [ ] All dependencies updated
- [ ] Test coverage >80%
- [ ] No critical security vulnerabilities
- [ ] CI/CD pipeline functional
- [ ] Docker images building successfully

### Architecture
- [ ] Microservices deployed independently
- [ ] Services communicate via HTTP/REST
- [ ] Session state and MC cache in Redis (cost-optimized, no DynamoDB)
- [ ] Caching reduces MC queries by >80%
- [ ] Secrets managed in AWS Secrets Manager

### Operations
- [ ] Logs centralized in CloudWatch
- [ ] Custom metrics tracked
- [ ] Alarms configured
- [ ] Health checks passing
- [ ] Auto-scaling functional

### Performance
- [ ] Response time <300ms (avg)
- [ ] Cache hit rate >80%
- [ ] Throughput >500 commands/min
- [ ] Zero downtime deployments

### Documentation
- [ ] Architecture documented
- [ ] API documented
- [ ] Deployment guide written
- [ ] Runbook created

---

## 🔍 Review Checklist (Before Each Milestone)

- [ ] All tasks in milestone completed
- [ ] All tests passing
- [ ] Code reviewed by peer
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance benchmarks met
- [ ] Successfully deployed to staging
- [ ] Stakeholder approval received

---

## 📝 Notes Section

Use this space to track blockers, decisions, and important context:

### Decisions Log
- [ ] **Date:** _____  **Decision:** _____  **Rationale:** _____

### Blockers
- [ ] **Blocker:** _____  **Owner:** _____  **Status:** _____

### Risks
- [ ] **Risk:** _____  **Mitigation:** _____  **Probability:** _____

---

**Last Updated:** 2024-10-03  
**Current Milestone:** Pre-Implementation  
**Progress:** 0/5 milestones complete
