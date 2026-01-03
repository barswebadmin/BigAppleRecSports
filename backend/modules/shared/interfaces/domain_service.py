"""
Base protocol for all domain services.

Domain services must be pure business logic with zero external dependencies.
They communicate with integration layers via DTOs.
"""

from typing import Protocol, Any, TypeVar, Generic

# Type variable for request/response
TRequest = TypeVar('TRequest')
TResponse = TypeVar('TResponse')


class DomainService(Protocol, Generic[TRequest, TResponse]):
    """
    Base protocol for all domain services.
    
    Domain services must:
    1. Accept requests as domain objects or DTOs
    2. Return results as domain objects or DTOs
    3. Have zero knowledge of external systems (Slack, Shopify, AWS)
    4. Be 100% unit testable without mocks
    5. Be pure functions (no side effects except via injected dependencies)
    
    Example:
        class RefundEligibilityService(DomainService[RefundRequest, EligibilityResult]):
            def process(self, request: RefundRequest) -> EligibilityResult:
                # Pure business logic here
                return EligibilityResult(eligible=True, reason="Within window")
    """
    
    def process(self, request: TRequest) -> TResponse:
        """
        Process a domain request and return a domain result.
        
        Args:
            request: Domain request object or DTO
            
        Returns:
            Domain result object or DTO
            
        Raises:
            ValueError: If request is invalid (business rule violation)
            NotImplementedError: If subclass doesn't implement
        """
        ...


class AsyncDomainService(Protocol, Generic[TRequest, TResponse]):
    """
    Async version of DomainService for services requiring async operations.
    
    Use when domain logic requires I/O (rare - prefer sync when possible).
    """
    
    async def process(self, request: TRequest) -> TResponse:
        """
        Async process a domain request and return a domain result.
        
        Args:
            request: Domain request object or DTO
            
        Returns:
            Domain result object or DTO
            
        Raises:
            ValueError: If request is invalid (business rule violation)
            NotImplementedError: If subclass doesn't implement
        """
        ...

