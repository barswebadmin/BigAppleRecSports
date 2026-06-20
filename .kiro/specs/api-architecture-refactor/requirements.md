# API Architecture Refactor - Requirements

## Overview
Refactor the backend API architecture to follow industry-standard MVC/Controller-Service patterns with clear separation of concerns, moving validation from routers to controllers, and establishing consistent response formatting patterns.

## Problem Statement
Currently, the API backend has:
- Validation logic split between routers and controllers
- Response formatting happening in multiple layers
- Inconsistent patterns across different endpoints
- Controllers doing some data transformation that should be in services
- Unclear boundaries between router, controller, and service responsibilities

## Goals
1. Establish clear separation of concerns following industry best practices
2. Move all request validation from routers to controllers
3. Standardize response formatting across all endpoints
4. Create reusable patterns for future API development
5. Improve testability and maintainability

## User Stories

### US-1: As a backend developer, I want clear architectural boundaries
**Acceptance Criteria:**
- 1.1: Routers only handle routing and basic parameter extraction
- 1.2: Controllers handle all request validation and response formatting
- 1.3: Services contain only business logic and return DTOs
- 1.4: Each layer has a single, well-defined responsibility

### US-2: As a backend developer, I want consistent validation patterns
**Acceptance Criteria:**
- 2.1: All request validation happens in controllers using Pydantic models
- 2.2: Validation errors return consistent 400 responses
- 2.3: No validation logic exists in routers
- 2.4: Validation is easily testable in isolation

### US-3: As a backend developer, I want standardized response formatting
**Acceptance Criteria:**
- 3.1: All successful responses follow a consistent structure
- 3.2: All error responses follow a consistent structure
- 3.3: Response formatting happens only in controllers
- 3.4: Services return domain objects/DTOs, not HTTP responses

### US-4: As a backend developer, I want the orders API to follow the new pattern
**Acceptance Criteria:**
- 4.1: Orders router delegates all validation to controller
- 4.2: Orders controller validates all inputs before calling service
- 4.3: Orders service returns structured DTOs
- 4.4: Response formatting is consistent across all order endpoints

### US-5: As a backend developer, I want clear documentation of the architecture
**Acceptance Criteria:**
- 5.1: Architecture diagram shows layer responsibilities
- 5.2: Code examples demonstrate the pattern
- 5.3: Migration guide for updating other endpoints
- 5.4: Testing patterns documented for each layer

## Current State Analysis

### Router Layer (`backend/routers/orders.py`)
**Current Responsibilities:**
- Route definition and HTTP method mapping
- Query parameter extraction and basic validation (min_length, max_length)
- Pydantic model validation
- Routing logic based on `reason` parameter
- Exception handling and HTTP error mapping

**Issues:**
- Too much validation logic (should be in controller)
- Business logic for routing based on reason (should be in controller)
- Direct exception handling (should delegate to controller)

### Controller Layer (`backend/modules/integrations/shopify/controllers/api_controller.py`)
**Current Responsibilities:**
- Logging API requests
- Parsing identifiers (business logic)
- Building query parameters for service
- Calling service methods
- Converting service responses to HTTP responses
- Exception mapping to HTTP errors
- Response formatting

**Issues:**
- Some validation still in router
- Data transformation (order object to dict) should be in service
- Response formatting is verbose and repetitive

### Service Layer (`backend/modules/integrations/shopify/services/shopify_service.py`)
**Current Responsibilities:**
- Business logic for order operations
- Shopify API interactions
- Data enrichment (cancellation status, refund calculations)
- Payment summary calculations
- Returns raw Shopify objects or dicts

**Issues:**
- Returns mixed types (sometimes objects, sometimes dicts)
- Should return consistent DTOs
- Some response structure building (status_code, success, message) should be in controller

### Models Layer (`backend/modules/integrations/shopify/models/`)
**Current State:**
- `requests.py`: Pydantic models for request validation
- `api_models.py`: Response models
- Mixed usage patterns

## Target Architecture

### Layer Responsibilities

#### Router Layer
**ONLY:**
- Define routes and HTTP methods
- Extract raw parameters from request
- Call controller methods
- Return controller responses

**NEVER:**
- Validate business rules
- Transform data
- Call services directly
- Handle business exceptions

#### Controller Layer
**ONLY:**
- Validate all request inputs using Pydantic models
- Call appropriate service methods
- Format service responses into HTTP responses
- Map service exceptions to HTTP status codes
- Log requests/responses

**NEVER:**
- Contain business logic
- Access databases directly
- Call external APIs directly
- Transform domain data (services return DTOs)

#### Service Layer
**ONLY:**
- Implement business logic
- Interact with external APIs (Shopify)
- Perform calculations and data enrichment
- Return DTOs (Data Transfer Objects)
- Raise domain exceptions

**NEVER:**
- Know about HTTP (status codes, headers, etc.)
- Format responses for HTTP
- Validate HTTP request format

## Non-Functional Requirements

### NFR-1: Performance
- Refactoring should not degrade performance
- Validation should be efficient
- Response formatting should be minimal overhead

### NFR-2: Backward Compatibility
- Existing API contracts must remain unchanged
- Response formats must stay consistent
- HTTP status codes must remain the same

### NFR-3: Testability
- Each layer should be independently testable
- Controllers should be testable without routers
- Services should be testable without controllers
- Validation should be testable in isolation

### NFR-4: Maintainability
- Clear patterns that are easy to follow
- Minimal code duplication
- Self-documenting code structure
- Easy to add new endpoints

## Out of Scope
- Changing API contracts or response formats
- Refactoring non-orders endpoints (future work)
- Database layer changes
- Authentication/authorization changes
- Performance optimization beyond maintaining current levels

## Success Metrics
1. All validation moved from routers to controllers
2. Zero business logic in routers
3. Consistent response formatting across all endpoints
4. All tests passing with improved coverage
5. Clear documentation of patterns for future development

## Dependencies
- Pydantic for validation models
- FastAPI for routing
- Existing service layer implementations

## Risks and Mitigations

### Risk 1: Breaking existing functionality
**Mitigation:** Comprehensive test coverage before and after refactoring

### Risk 2: Inconsistent patterns during migration
**Mitigation:** Complete one endpoint fully before moving to others

### Risk 3: Performance degradation
**Mitigation:** Benchmark before and after, optimize if needed

### Risk 4: Team confusion during transition
**Mitigation:** Clear documentation and examples, pair programming sessions
