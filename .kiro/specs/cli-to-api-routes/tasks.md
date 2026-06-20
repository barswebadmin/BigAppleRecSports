# Implementation Plan: CLI to API Routes

## Overview

This implementation plan converts the existing CLI commands architecture into RESTful API routes, creating a three-tier system with API routers, controllers, and backend services. The implementation follows a staged approach: first creating the route infrastructure, then implementing controllers, and finally integrating with backend services.

**CRITICAL PRINCIPLE: DO NOT REWRITE EXISTING LOGIC**
- All controllers MUST delegate to existing backend services and modules
- NO business logic should be duplicated or rewritten in controllers
- Controllers should ONLY handle HTTP request/response conversion and validation
- Reuse existing service methods, parsers, formatters, and validation logic
- Maintain DRY (Don't Repeat Yourself) principles throughout

## Tasks

- [x] 1. Set up API infrastructure and base components
  - Create directory structure for API routers and controllers
  - Set up base controller class with common functionality
  - Create response formatter utilities and error handling
  - Set up Pydantic models for request/response validation
  - _Requirements: 1.1, 6.3, 8.2_

- [ ] 2. Implement Shopify API routes and controller
  - [x] 2.1 Create Shopify API router with order endpoints
    - Implement GET /api/v1/shopify/orders (list orders)
    - Implement GET /api/v1/shopify/orders/{identifier} (get order)
    - Implement POST /api/v1/shopify/orders/{id}/cancel (cancel order)
    - Implement POST /api/v1/shopify/orders/{id}/refund (refund order)
    - Implement POST /api/v1/shopify/orders/{id}/discount (apply discount)
    - _Requirements: 3.1, 3.4_

  - [ ]* 2.2 Write property test for Shopify identifier parsing
    - **Property 7: Identifier parsing consistency**
    - **Validates: Requirements 3.4**

  - [x] 2.3 Create Shopify API controller
    - Implement ShopifyAPIController class following webhook controller pattern
    - REUSE existing Shopify service methods - DO NOT rewrite business logic
    - REUSE existing identifier parsing from CLI commands - DO NOT duplicate
    - REUSE existing error handling patterns from backend modules
    - Add ONLY HTTP-specific error mapping and response formatting
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.4 Write property test for controller delegation
    - **Property 4: Controller delegation consistency**
    - **Validates: Requirements 2.3**

  - [x] 2.5 Add Shopify product and customer endpoints
    - Implement product endpoints (GET list, GET by ID, PUT update)
    - Implement customer endpoints (GET list, GET by ID, PUT update)
    - REUSE existing service methods from backend/modules/integrations/shopify
    - Add ONLY HTTP routing and response formatting - NO business logic
    - _Requirements: 3.2, 3.3_

  - [ ]* 2.6 Write unit tests for Shopify endpoints
    - Test endpoint availability and response formats
    - Test error handling scenarios
    - Test authentication and validation
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 3. Implement Slack API routes and controller
  - [ ] 3.1 Create Slack API router with user endpoints
    - Implement GET /api/v1/slack/users (list users)
    - Implement GET /api/v1/slack/users/{identifier} (get user)
    - Implement PUT /api/v1/slack/users/{id} (update user)
    - _Requirements: 4.1, 4.4_

  - [ ] 3.2 Create Slack API controller
    - Implement SlackAPIController class following webhook controller pattern
    - REUSE existing Slack service methods - DO NOT rewrite business logic
    - REUSE existing identifier parsing from CLI commands (email/user ID logic)
    - REUSE existing bot configuration and authentication from backend modules
    - Add ONLY HTTP-specific response formatting and error handling
    - _Requirements: 2.1, 2.2, 2.3, 4.5_

  - [ ]* 3.3 Write property test for Slack authentication consistency
    - **Property 9: Authentication consistency**
    - **Validates: Requirements 4.5**

  - [ ] 3.4 Add Slack group and channel endpoints
    - Implement group endpoints (GET list, GET by ID, POST add-member, DELETE remove-member)
    - Implement channel endpoints (GET list, GET by ID)
    - REUSE existing service methods from backend/modules/integrations/slack
    - Add ONLY HTTP routing and response formatting - NO business logic
    - _Requirements: 4.2, 4.3_

  - [ ]* 3.5 Write unit tests for Slack endpoints
    - Test endpoint availability and response formats
    - Test user identifier parsing (emails vs user IDs)
    - Test bot authentication and permissions
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 4. Implement Google API routes and controller
  - [ ] 4.1 Create Google API router with user endpoints
    - Implement GET /api/v1/google/users (list users)
    - Implement GET /api/v1/google/users/{identifier} (get user)
    - Implement POST /api/v1/google/users (create user)
    - Implement PUT /api/v1/google/users/{id} (update user)
    - _Requirements: 5.1, 5.4_

  - [ ] 4.2 Create Google API controller
    - Implement GoogleAPIController class following webhook controller pattern
    - REUSE existing Google service methods - DO NOT rewrite business logic
    - REUSE existing Google authentication and API client from backend modules
    - REUSE existing data format validation from CLI commands
    - Add ONLY HTTP-specific response formatting and error handling
    - _Requirements: 2.1, 2.2, 2.3, 5.4, 5.5_

  - [ ]* 4.3 Write property test for Google data format consistency
    - **Property 8: Response format consistency**
    - **Validates: Requirements 5.5**

  - [ ] 4.4 Add Google group and sheets endpoints
    - Implement group endpoints (GET list, GET by ID, POST add-member, DELETE remove-member)
    - Implement sheets endpoints (GET read, PUT update, POST write)
    - REUSE existing service methods from backend/modules/integrations/google
    - Add ONLY HTTP routing and response formatting - NO business logic
    - _Requirements: 5.2, 5.3_

  - [ ]* 4.5 Write unit tests for Google endpoints
    - Test endpoint availability and response formats
    - Test Google authentication and API client usage
    - Test data format validation and conversion
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 5. Checkpoint - Ensure all basic endpoints are working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement request/response handling and validation
  - [ ] 6.1 Create comprehensive request validation
    - REUSE existing parameter validation from CLI commands - DO NOT duplicate
    - REUSE existing Pydantic models from backend modules where available
    - Add ONLY HTTP-specific request body validation
    - Implement consistent error responses using existing error patterns
    - _Requirements: 6.1, 6.2, 8.3_

  - [ ]* 6.2 Write property test for parameter validation
    - **Property 5: Parameter validation consistency**
    - **Validates: Requirements 6.2**

  - [ ] 6.3 Implement response formatting and consistency
    - REUSE existing response formatters from CLI commands where possible
    - REUSE existing pagination logic from backend modules
    - Add ONLY HTTP-specific JSON response formatting
    - Maintain same data structure as CLI JSON output
    - _Requirements: 6.3, 6.5, 9.5_

  - [ ]* 6.4 Write property test for response format consistency
    - **Property 8: Response format consistency**
    - **Validates: Requirements 6.3**

  - [ ] 6.5 Add comprehensive error handling
    - REUSE existing exception handling patterns from backend modules
    - REUSE existing logging configuration and patterns
    - Add ONLY HTTP status code mapping for existing exceptions
    - Maintain same error message formats as CLI commands
    - _Requirements: 6.4, 8.1, 8.2, 8.4_

  - [ ]* 6.6 Write property test for error handling consistency
    - **Property 6: Error handling consistency**
    - **Validates: Requirements 6.4, 8.2**

- [ ] 7. Implement authentication and authorization
  - [ ] 7.1 Add authentication middleware and validation
    - REUSE existing authentication mechanisms from CLI commands
    - REUSE existing permission validation logic from backend modules
    - Add ONLY HTTP middleware wrapper for existing auth logic
    - Maintain same authentication flow as CLI commands
    - _Requirements: 7.1, 7.3, 7.4_

  - [ ]* 7.2 Write property test for authentication error handling
    - **Property 10: Authentication error handling**
    - **Validates: Requirements 7.4**

  - [ ] 7.3 Integrate with existing service authentication
    - REUSE existing API keys and tokens from backend configuration
    - REUSE existing security boundaries and validation logic
    - Add ONLY HTTP-specific credential handling
    - Maintain same security patterns as existing implementations
    - _Requirements: 7.2, 7.5_

  - [ ]* 7.4 Write unit tests for authentication and authorization
    - Test authentication middleware functionality
    - Test permission validation logic
    - Test credential handling and security boundaries
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 8. Add API documentation and discoverability
  - [ ] 8.1 Generate comprehensive OpenAPI documentation
    - Configure FastAPI to generate complete OpenAPI specs
    - Add detailed descriptions for all endpoints and parameters
    - Include request/response schemas and examples
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ]* 8.2 Write property test for documentation completeness
    - **Property 15: Documentation completeness**
    - **Validates: Requirements 10.1, 10.2**

  - [ ] 8.3 Add error response documentation
    - Document all possible error responses with status codes
    - Include error response schemas and examples
    - Ensure documentation reflects CLI command functionality
    - _Requirements: 10.4, 10.5_

  - [ ]* 8.4 Write unit tests for API documentation
    - Test OpenAPI spec generation and completeness
    - Test documentation accuracy and consistency
    - Test error response documentation
    - _Requirements: 10.1, 10.4, 10.5_

- [ ] 9. Integration and wiring
  - [ ] 9.1 Integrate API routers with main FastAPI application
    - Add all API routers to main.py with proper prefixes
    - Configure CORS and middleware for API endpoints
    - Set up proper error handling and logging middleware
    - _Requirements: 1.1, 1.5_

  - [ ]* 9.2 Write property test for URL pattern consistency
    - **Property 3: URL pattern consistency**
    - **Validates: Requirements 1.5**

  - [ ] 9.3 Add frontend integration support
    - REUSE existing request building patterns from CLI commands
    - REUSE existing response formatting logic where applicable
    - Add ONLY HTTP-specific utilities for frontend consumption
    - Maintain same data structures and formats as CLI output
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 9.4 Write integration tests for complete API flows
    - Test end-to-end API workflows
    - Test frontend integration scenarios
    - Test cross-service consistency
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 10. Final checkpoint - Ensure all tests pass and API is fully functional
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Implementation follows existing patterns from webhook controllers
- All API endpoints maintain consistency with CLI command functionality

**CRITICAL IMPLEMENTATION RULES:**
- NEVER rewrite existing business logic from backend/* modules
- ALWAYS reuse existing service methods, parsers, formatters, and validators
- Controllers should ONLY handle HTTP request/response conversion
- Maintain DRY principles - if logic exists in backend, reuse it
- Follow existing patterns from webhook controllers for consistency