# MCServerStatBot - Complete Refactoring Plan

## Current State Summary

### Project Intention
MCServerStatBot is a **Telegram bot** that allows users to check the status of Minecraft game servers. The bot provides two main features:
1. **Server Status Check** (`/status` command): Queries a Minecraft server URL to determine if it's online, displaying server description, version, ping latency, and player count
2. **Active Players List** (`/players` command): Shows which players are currently connected to the server (if the server allows query requests)

The bot uses inline callback buttons for easy navigation between status/players views and includes persistent data storage to remember the last queried server URL.

### Current Architecture
The application follows a **monolithic architecture** with three Python modules:
- **`main.py`**: Entry point that configures the Telegram bot updater, registers command/callback handlers, and manages deployment mode (dev polling vs. prod webhook)
- **`commands.py`**: Contains all command handlers (`cmd_start`, `cmd_status`, `cmd_players`), callback handlers (`cb_status`, `cb_players`, `cb_about`), and formatting functions for messages and errors
- **`utils.py`**: Basic URL validation utility (currently only checks length)

**Deployment Model:**
- Originally designed for **Heroku** deployment (webhook mode)
- Supports local development via polling mode
- Uses `PicklePersistence` for state management (file-based storage)
- Configured via environment variables (`MODE`, `TOKEN`, `HEROKU_APP_NAME`, `PORT`)

### Three Most Significant Limitations

#### 1. **Critically Outdated Technology Stack** (Priority: CRITICAL)
- **Python 3.6.14**: End-of-life since December 2021, no security patches
- **python-telegram-bot 13.7**: Multiple major versions behind (current is 20.x with breaking changes)
- **mcstatus 6.4.0**: Several versions behind (current is 11.x)
- **Security Vulnerabilities**: No dependency scanning, likely multiple CVEs in outdated packages
- **Impact**: Security risks, incompatibility with modern Python features, difficult maintenance

#### 2. **Tightly Coupled Monolithic Design** (Priority: HIGH)
- **No separation of concerns**: Business logic, presentation, and infrastructure are mixed in command handlers
- **Hard-coded dependencies**: Direct imports of `telegram` and `mcstatus` throughout, making testing impossible
- **No abstraction layers**: No service layer, repository pattern, or dependency injection
- **State management issues**: Relies on bot framework's `chat_data` dict for persistence without validation or typing
- **Error handling**: Bare `except` blocks that catch all exceptions, poor observability
- **Impact**: Extremely difficult to test, refactor, or scale; impossible to swap dependencies

#### 3. **Heroku-Specific Configuration & Limited Scalability** (Priority: HIGH)
- **Hard-coded Heroku URLs**: `{HEROKU_APP_NAME}.herokuapp.com` embedded in code
- **Single-mode webhook**: Webhook path uses bot token (security concern), no health check endpoints
- **File-based persistence**: `PicklePersistence` to local file prevents horizontal scaling
- **No containerization**: No Docker, making AWS deployment challenging
- **Synchronous blocking calls**: Minecraft server lookups block the bot, affecting responsiveness under load
- **Impact**: Cannot leverage AWS services, no horizontal scaling, vendor lock-in, poor performance

### Additional Technical Debt
- **No logging infrastructure**: Logs written to files locally, not centralized
- **No metrics/monitoring**: No observability into bot health, command usage, or error rates
- **No input validation**: URL validation only checks length (< 35 chars), no regex/format checks
- **No tests**: Zero unit tests, integration tests, or E2E tests
- **No CI/CD**: No automated builds, linting, or deployments
- **No type hints**: Python code lacks type annotations
- **Deprecated API usage**: `pass_args`, `pass_chat_data` are deprecated patterns in newer telegram-bot versions

---

## Proposed AWS-Ready Architecture & Stack

### Target Architecture Pattern: **Modern Microservices with Event-Driven Components**

#### Core Architecture Principles
1. **Containerized Services**: Dockerized applications for consistent deployment across environments
2. **Separation of Concerns**: Clear boundaries between bot interface, business logic, and external integrations
3. **Event-Driven Communication**: Asynchronous processing for long-running operations
4. **Managed Services First**: Leverage AWS managed services to reduce operational overhead
5. **Infrastructure as Code**: All infrastructure defined in code (not implemented in this phase)
6. **Cloud-Native Patterns**: Stateless services, distributed configuration, centralized logging

#### Proposed AWS Services Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│                    Telegram Users/Clients                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS API Gateway (REST/WebSocket)             │
│  - Webhook endpoint for Telegram                                │
│  - Request validation & throttling                              │
│  - SSL/TLS termination                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Application Load Balancer (ALB)                    │
│  - Health checks                                                │
│  - Multiple target groups                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ECS Fargate / EKS                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Bot Handler Service (Container)                  │  │
│  │  - Receives Telegram updates                             │  │
│  │  - Command routing & validation                          │  │
│  │  - Delegates to backend services                         │  │
│  │  - Sends formatted responses                             │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│  ┌──────────────────────▼──────────────────────────────────┐  │
│  │      Minecraft Query Service (Container)                 │  │
│  │  - Minecraft server status/query logic                   │  │
│  │  - Connection pooling & retry logic                      │  │
│  │  - Result caching                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ ElastiCache  │    │  DynamoDB    │    │  SQS Queue   │
│   (Redis)    │    │              │    │              │
│              │    │ - User state │    │ - Async jobs │
│ - MC server  │    │ - Last query │    │ - Retries    │
│   status     │    │   cache      │    │              │
│   cache      │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Observability Layer                          │
│  - CloudWatch Logs (centralized logging)                        │
│  - CloudWatch Metrics (custom metrics)                          │
│  - AWS X-Ray (distributed tracing)                              │
│  - CloudWatch Alarms (alerting)                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Security Layer                              │
│  - AWS Secrets Manager (bot tokens, API keys)                   │
│  - IAM Roles (service permissions)                              │
│  - VPC (network isolation)                                      │
│  - Security Groups (firewall rules)                             │
└─────────────────────────────────────────────────────────────────┘
```

#### Architecture Components Detail

**1. Bot Handler Service (ECS Fargate)**
- **Purpose**: Telegram webhook receiver and command orchestrator
- **Technology**: Python 3.12, FastAPI for webhook handling, python-telegram-bot 20.x
- **Responsibilities**:
  - Receive and validate Telegram webhook events
  - Parse commands and route to appropriate handlers
  - Call Minecraft Query Service via HTTP/gRPC
  - Format and send responses back to Telegram
  - Handle callback queries (inline buttons)
- **Scaling**: Horizontal auto-scaling based on CPU/memory or request count
- **State**: Stateless (stores nothing locally), retrieves state from DynamoDB

**2. Minecraft Query Service (ECS Fargate)**
- **Purpose**: Isolated service for querying Minecraft servers
- **Technology**: Python 3.12, FastAPI/gRPC, mcstatus library, async I/O
- **Responsibilities**:
  - Execute Minecraft server status/query operations
  - Implement connection pooling and timeout management
  - Cache results in Redis (TTL: 30-60 seconds)
  - Handle retries with exponential backoff
  - Provide health check endpoints
- **Scaling**: Horizontal auto-scaling based on queue depth or latency
- **Benefits**: Isolates network I/O from bot handler, prevents bot blocking

**3. Data Storage**

**DynamoDB** (Primary State Store):
- **Table: `user_sessions`**
  - Partition Key: `chat_id` (string)
  - Attributes: `last_url`, `last_query_time`, `server_data`, `ttl`
  - Purpose: Store per-chat session data, last queried server
  - TTL: Auto-expire old sessions after 7 days

**ElastiCache Redis** (Caching Layer):
- **Key Pattern**: `mc:server:{hostname}:status` / `mc:server:{hostname}:players`
- **TTL**: 30-60 seconds per cache entry
- **Purpose**: Reduce redundant Minecraft server queries, improve response time
- **Benefits**: Sub-millisecond latency, reduces external API calls

**4. Event/Message Queue (Optional - Future Enhancement)**

**Amazon SQS**:
- **Purpose**: Decouple long-running operations, handle spikes in traffic
- **Use Cases**: 
  - Queue Minecraft server queries when many users request simultaneously
  - Scheduled status checks for favorite servers
  - Retry failed queries

**5. API Gateway**
- **Purpose**: Front-facing HTTPS endpoint for Telegram webhook
- **Features**:
  - Request throttling (protect from abuse)
  - Request/response transformation
  - API key validation
  - CORS handling (if needed for web dashboard)
- **Alternative**: Application Load Balancer directly to ECS (simpler, cheaper for this use case)

**6. Observability & Monitoring**

**CloudWatch Logs**:
- Centralized log aggregation from all containers
- Structured logging (JSON format)
- Log insights for querying/analysis

**CloudWatch Metrics**:
- Custom metrics: command counts, query success rates, response times
- Container metrics: CPU, memory, network
- Alarms for error rates, latency spikes

**AWS X-Ray**:
- Distributed tracing across services
- Visualize request flow: API Gateway → Bot Handler → MC Query Service → Redis/DynamoDB

### Technology Stack Modernization

#### Language & Runtime
- **Current**: Python 3.6.14
- **Proposed**: **Python 3.12** (latest stable)
- **Justification**: 
  - Active support until 2028
  - 20-30% performance improvements (faster interpreter, optimized memory)
  - Modern features: structural pattern matching, better type hints, async improvements
  - Security patches and bug fixes
  - Required for latest versions of dependencies

#### Core Framework
- **Current**: python-telegram-bot 13.7 (PTB)
- **Proposed**: **python-telegram-bot 20.7+**
- **Justification**:
  - Complete rewrite with async/await (non-blocking I/O)
  - Better type hints and IDE support
  - Improved error handling and context management
  - Removes deprecated patterns (pass_args, pass_chat_data)
  - Active development and community support
  - **Breaking changes**: Requires refactoring all handlers

#### Minecraft Server Client
- **Current**: mcstatus 6.4.0
- **Proposed**: **mcstatus 11.x** (latest)
- **Justification**:
  - Support for latest Minecraft versions and protocols
  - Bug fixes and performance improvements
  - Better async support
  - Improved error handling

#### Web Framework (NEW)
- **Proposed**: **FastAPI 0.109+**
- **Justification**:
  - High-performance async web framework (ASGI)
  - Automatic OpenAPI/Swagger documentation
  - Built-in data validation with Pydantic
  - Perfect for webhook endpoint and potential REST API
  - Easy integration with CloudWatch, X-Ray
  - Better alternative to Flask/Django for microservices

#### Dependency Management
- **Current**: Simple requirements.txt
- **Proposed**: **Poetry** or **PDM**
- **Justification**:
  - Lock file for reproducible builds
  - Dependency resolution and conflict detection
  - Virtual environment management
  - Build system standardization (PEP 621)
  - Better for multi-service projects

#### Data Validation & Serialization
- **Proposed**: **Pydantic 2.x**
- **Justification**:
  - Type-safe data models
  - Automatic validation and serialization
  - JSON schema generation
  - FastAPI integration
  - Replaces manual dict manipulation

#### Async Redis Client
- **Proposed**: **redis-py 5.x with async support**
- **Justification**:
  - Native async/await support
  - Connection pooling
  - Sentinel/cluster support
  - Direct AWS ElastiCache compatibility

#### AWS SDK
- **Proposed**: **boto3** (latest) for DynamoDB, Secrets Manager, CloudWatch
- **Justification**:
  - Official AWS SDK for Python
  - Comprehensive service coverage
  - Well-documented and maintained
  - Easy credential management (IAM roles)

#### Testing Framework
- **Proposed**: **pytest 8.x** with **pytest-asyncio**, **pytest-mock**, **pytest-cov**
- **Justification**:
  - Industry standard for Python testing
  - Excellent async test support
  - Powerful fixtures and parametrization
  - Code coverage reporting
  - CI/CD integration

#### Code Quality Tools
- **Proposed**:
  - **ruff**: Extremely fast linter/formatter (replaces flake8, black, isort)
  - **mypy**: Static type checker
  - **pre-commit**: Git hooks for automated checks
- **Justification**:
  - Enforce code quality before commits
  - Catch bugs early
  - Consistent code style
  - Fast feedback loop

#### Containerization
- **Proposed**: **Docker** with multi-stage builds
- **Justification**:
  - Consistent environment across dev/staging/prod
  - Required for ECS/EKS deployment
  - Efficient image layering
  - Security scanning integration
  - Easy local testing

#### Infrastructure (Not Implemented Yet)
- **Proposed**: **AWS CDK** (Python) or **Terraform**
- **Justification**: Infrastructure as Code for reproducible deployments

### Proposed Directory Structure (Post-Refactor)

```
MCServerStatBot/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint, test, build
│       └── deploy.yml          # Deploy to AWS (future)
├── docs/
│   ├── architecture.md         # Architecture diagrams
│   ├── api.md                  # API documentation
│   └── deployment.md           # Deployment guide
├── services/
│   ├── bot_handler/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── bot_handler/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py         # FastAPI app + webhook
│   │   │   │   ├── bot.py          # Telegram bot setup
│   │   │   │   ├── handlers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── commands.py # /start, /status, /players
│   │   │   │   │   └── callbacks.py # Inline button handlers
│   │   │   │   ├── services/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── session.py  # Session management
│   │   │   │   │   └── mc_client.py # HTTP client to MC service
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── schemas.py  # Pydantic models
│   │   │   │   ├── config.py       # Settings/env vars
│   │   │   │   └── utils/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── logging.py
│   │   │   │       └── formatting.py
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       └── conftest.py
│   └── mc_query_service/
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── src/
│       │   ├── mc_query/
│       │   │   ├── __init__.py
│       │   │   ├── main.py         # FastAPI app
│       │   │   ├── api/
│       │   │   │   ├── __init__.py
│       │   │   │   └── routes.py   # API endpoints
│       │   │   ├── services/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── query.py    # MC query logic
│       │   │   │   └── cache.py    # Redis caching
│       │   │   ├── models/
│       │   │   │   ├── __init__.py
│       │   │   │   └── schemas.py
│       │   │   └── config.py
│       │   └── tests/
│       │       ├── unit/
│       │       └── integration/
├── shared/
│   └── common/
│       ├── __init__.py
│       ├── aws/
│       │   ├── __init__.py
│       │   ├── dynamodb.py     # DynamoDB client
│       │   ├── secrets.py      # Secrets Manager
│       │   └── cloudwatch.py   # Logging/metrics
│       └── models/
│           └── __init__.py
├── infrastructure/              # Future: IaC
│   ├── aws_cdk/                # CDK stacks (not implemented)
│   └── terraform/              # Terraform modules (alternative)
├── scripts/
│   ├── local_dev.sh            # Run locally with Docker Compose
│   └── setup.sh                # Initial setup
├── docker-compose.yml          # Local development environment
├── .dockerignore
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml              # Root project config
├── README.md
└── REFACTORING_PLAN.md         # This document
```

---

## Phased Refactoring Plan

### Milestone 1: Foundation & Dependency Updates
**Complexity**: Medium  
**Estimated Effort**: 1-2 weeks  
**Goal**: Update core dependencies and establish modern development practices

#### Tasks:
1. **Python Version Upgrade**
   - Update `runtime.txt` to Python 3.12
   - Update `pyproject.toml` (replace `requirements.txt`)
   - Test compatibility with all dependencies
   
2. **Dependency Modernization**
   - Upgrade `python-telegram-bot` from 13.7 → 20.7+
   - Upgrade `mcstatus` from 6.4.0 → 11.x
   - Add new dependencies: FastAPI, Pydantic, boto3, redis-py
   - **Breaking Changes**: Refactor all command handlers for PTB 20.x async API
   
3. **Code Quality Infrastructure**
   - Add `ruff` for linting/formatting
   - Add `mypy` for type checking
   - Add `pytest` with coverage
   - Configure `pre-commit` hooks
   - Set up basic CI with GitHub Actions (lint + test)
   
4. **Type Annotations**
   - Add type hints to all existing functions
   - Create Pydantic models for data structures
   - Ensure mypy passes with strict mode

5. **Basic Testing**
   - Write unit tests for `utils.py`
   - Write unit tests for message formatting functions
   - Mock Telegram API for handler tests
   - Achieve >70% code coverage

#### Success Criteria:
- ✅ All tests pass on Python 3.12
- ✅ CI pipeline runs successfully
- ✅ No type errors from mypy
- ✅ Code passes ruff linting
- ✅ Bot still functional in dev mode (polling)

#### Risks:
- PTB 13 → 20 has major breaking changes (async handlers)
- May need significant handler refactoring

---

### Milestone 2: Architectural Separation - Service Layer
**Complexity**: High  
**Estimated Effort**: 2-3 weeks  
**Goal**: Separate business logic from presentation and introduce proper abstractions

#### Tasks:
1. **Extract Business Logic**
   - Create `services/` directory structure
   - Extract Minecraft query logic into `MinecraftQueryService` class
   - Extract session management into `SessionService` class
   - Extract message formatting into `MessageFormatter` class
   
2. **Introduce Dependency Injection**
   - Implement simple DI container or use `dependency-injector` library
   - Remove global state and hard-coded dependencies
   - Make services injectable into handlers
   
3. **Repository Pattern**
   - Create `SessionRepository` abstraction
   - Implement file-based persistence (current behavior)
   - Design interface for future DynamoDB implementation
   
4. **Error Handling Refactor**
   - Replace bare `except:` with specific exceptions
   - Create custom exception hierarchy
   - Implement centralized error handling middleware
   
5. **Async/Await Throughout**
   - Convert all I/O operations to async
   - Use `asyncio` for concurrent Minecraft queries
   - Implement connection pooling

6. **Testing**
   - Unit tests for all services (with mocks)
   - Integration tests with real mcstatus calls
   - Handler tests with service mocks

#### Success Criteria:
- ✅ Business logic completely decoupled from Telegram API
- ✅ All services have unit tests with >80% coverage
- ✅ No bare `except` blocks remain
- ✅ All I/O is non-blocking async
- ✅ Can swap persistence implementation without touching handlers

#### Deliverables:
- `services/minecraft_query.py`
- `services/session_manager.py`
- `services/message_formatter.py`
- `repositories/session_repository.py`
- `exceptions.py`
- Comprehensive test suite

---

### Milestone 3: Containerization & Local Development
**Complexity**: Medium  
**Estimated Effort**: 1-2 weeks  
**Goal**: Containerize application and create local development environment

#### Tasks:
1. **Dockerfile Creation**
   - Multi-stage Docker build for smaller images
   - Separate stages for dependencies, testing, production
   - Use Python 3.12-slim as base image
   - Non-root user for security
   
2. **Docker Compose Setup**
   - Bot service container
   - Redis container (simulates ElastiCache)
   - DynamoDB Local container
   - Environment variable configuration
   - Volume mounts for local development
   
3. **Configuration Management**
   - Create `config.py` using Pydantic Settings
   - Environment-based configuration (dev/staging/prod)
   - Secrets from environment variables (prepare for AWS Secrets Manager)
   
4. **Local Development Scripts**
   - `scripts/local_dev.sh` to start all services
   - Health check endpoints for all services
   - Hot reload for development
   
5. **Documentation**
   - Update README with Docker instructions
   - Document environment variables
   - Add troubleshooting guide

#### Success Criteria:
- ✅ Bot runs in Docker container
- ✅ Local dev environment starts with `docker-compose up`
- ✅ Redis and DynamoDB Local functional
- ✅ Health check endpoints return 200 OK
- ✅ Hot reload works during development

#### Deliverables:
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `scripts/local_dev.sh`
- Updated `README.md`

---

### Milestone 4: AWS-Ready Microservices Split
**Complexity**: High  
**Estimated Effort**: 2-3 weeks  
**Goal**: Split monolith into two services optimized for AWS deployment

#### Tasks:
1. **Service Separation**
   - **Bot Handler Service**: Webhook receiver, command router
   - **MC Query Service**: Minecraft server querying, caching
   - Define HTTP API contract between services (OpenAPI spec)
   
2. **Bot Handler Service**
   - FastAPI app with webhook endpoint
   - Integrate python-telegram-bot with FastAPI
   - HTTP client to call MC Query Service
   - Session state stored in DynamoDB (not implemented yet, use Redis)
   - Health check endpoint
   
3. **MC Query Service**
   - FastAPI app with REST endpoints
   - `/status` endpoint: Get server status
   - `/players` endpoint: Get player list
   - Redis caching layer (TTL: 30-60s)
   - Connection pooling for Minecraft queries
   - Health check endpoint
   
4. **Inter-Service Communication**
   - HTTP client with retry logic
   - Circuit breaker pattern (optional: use tenacity library)
   - Request/response schemas with Pydantic
   
5. **Observability**
   - Structured JSON logging (prepare for CloudWatch)
   - Log correlation IDs across services
   - Custom metrics endpoints (Prometheus format)
   - OpenTelemetry instrumentation (optional)
   
6. **Testing**
   - Unit tests for each service
   - Integration tests with both services running
   - Contract tests for API between services
   - Load testing (locust or k6)

#### Success Criteria:
- ✅ Two independent services run in separate containers
- ✅ Services communicate via HTTP API
- ✅ Redis caching reduces redundant MC queries by >80%
- ✅ Each service has independent health check
- ✅ Logs include correlation IDs for request tracing
- ✅ Services can be deployed independently

#### Deliverables:
- `services/bot_handler/` (complete service)
- `services/mc_query_service/` (complete service)
- `shared/common/` (shared utilities)
- OpenAPI specs for MC Query Service
- Load test scripts
- Architecture documentation

---

### Milestone 5: AWS Integration & Production Readiness
**Complexity**: High  
**Estimated Effort**: 2-3 weeks  
**Goal**: Integrate AWS services and prepare for production deployment

#### Tasks:
1. **AWS SDK Integration**
   - Add boto3 for AWS services
   - Configure IAM role-based authentication (not passwords)
   - Test locally with AWS credentials
   
2. **DynamoDB Integration**
   - Implement `DynamoDBSessionRepository`
   - Create DynamoDB table design
   - Migration script from file-based to DynamoDB
   - Local testing with DynamoDB Local
   
3. **Redis/ElastiCache Integration**
   - Update cache layer for ElastiCache compatibility
   - Connection pooling and failover handling
   - Cache invalidation strategies
   
4. **Secrets Management**
   - Move bot token to AWS Secrets Manager
   - Update config to fetch secrets at startup
   - Rotate secrets without redeploying
   
5. **CloudWatch Integration**
   - Configure CloudWatch Logs handler
   - Custom metrics: command counts, query latency, cache hit rate
   - CloudWatch Alarms for error rates
   - AWS X-Ray tracing integration (optional)
   
6. **Webhook Configuration**
   - Update webhook endpoint to use API Gateway or ALB URL
   - SSL/TLS certificate setup
   - Remove Heroku-specific code
   
7. **Production Configuration**
   - Environment-specific configs (dev/staging/prod)
   - Resource limits and auto-scaling configurations
   - Security hardening (non-root user, read-only filesystem)
   
8. **Deployment Documentation**
   - Step-by-step AWS deployment guide
   - ECS task definitions (JSON)
   - Required IAM policies
   - Rollback procedures
   
9. **Testing**
   - Integration tests against real AWS services (dev account)
   - Chaos engineering: test service failures
   - Performance testing under load

#### Success Criteria:
- ✅ Bot stores state in DynamoDB
- ✅ MC queries cached in Redis/ElastiCache
- ✅ All secrets retrieved from Secrets Manager
- ✅ Logs flow to CloudWatch Logs
- ✅ Custom metrics visible in CloudWatch
- ✅ Services run in ECS Fargate (local simulation)
- ✅ Webhook mode functional with HTTPS
- ✅ Documentation complete for AWS deployment

#### Deliverables:
- `shared/common/aws/` (AWS service clients)
- DynamoDB table schema and migration scripts
- CloudWatch dashboard configurations
- ECS task definitions
- Deployment documentation
- Production-ready Docker images

---

### Post-Refactor Maintenance Plan

#### Continuous Improvement
- **CI/CD Pipeline**: Automated deployments to staging on merge to `main`
- **Monitoring**: CloudWatch dashboards for key metrics
- **Alerting**: PagerDuty/Opsgenie integration for critical alerts
- **Security**: Dependabot for dependency updates, Snyk for vulnerability scanning
- **Performance**: Regular load testing and optimization
- **Documentation**: Keep architecture docs updated with changes

#### Future Enhancements (Beyond Refactor Scope)
1. **Web Dashboard**: React/Vue.js dashboard to manage favorite servers
2. **Scheduled Checks**: CloudWatch Events trigger periodic status checks
3. **Notifications**: Push notifications when servers go offline/online
4. **GraphQL API**: Alternative to REST for flexible queries
5. **Multi-Region**: Deploy to multiple AWS regions for global coverage
6. **Kubernetes**: Migrate from ECS to EKS for more control
7. **gRPC**: Replace HTTP with gRPC between services for better performance
8. **Infrastructure as Code**: Implement full AWS CDK/Terraform for one-click deployments

---

## Summary

This refactoring plan transforms MCServerStatBot from an **outdated, monolithic, Heroku-specific application** into a **modern, cloud-native, AWS-ready microservices architecture**. The phased approach ensures:

1. **Incremental value delivery**: Each milestone produces working software
2. **Risk mitigation**: Test thoroughly before moving to next phase
3. **Rollback capability**: Can stop at any milestone if needed
4. **Team learning**: Gradual introduction of new technologies
5. **AWS readiness**: Final architecture fully optimized for AWS deployment

**Total Estimated Effort**: 8-13 weeks (2-3 months) for complete refactor, not including AWS infrastructure deployment.

**Key Architectural Benefits**:
- ✅ Horizontally scalable (stateless services)
- ✅ Fault-tolerant (service isolation, caching, retries)
- ✅ Observable (centralized logging, metrics, tracing)
- ✅ Testable (dependency injection, mocked services)
- ✅ Maintainable (clear separation of concerns, type safety)
- ✅ Secure (secrets management, IAM roles, VPC isolation)
- ✅ Cost-effective (serverless options, auto-scaling, caching)

This plan provides a clear roadmap from the current state to a production-ready, AWS-hosted solution without implementing the actual deployment infrastructure yet.
