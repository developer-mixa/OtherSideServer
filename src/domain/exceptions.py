"""Domain-specific exceptions."""

from uuid import UUID


class DomainError(Exception):
    """Base domain exception."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""

    def __init__(self, entity_name: str, entity_id: UUID | str) -> None:
        super().__init__(f"{entity_name} with id={entity_id} not found")
        self.entity_name = entity_name
        self.entity_id = entity_id


class DuplicateEntityError(DomainError):
    """Raised when a unique constraint would be violated."""

    def __init__(self, entity_name: str, field: str, value: str) -> None:
        super().__init__(f"{entity_name} with {field}={value!r} already exists")
        self.entity_name = entity_name
        self.field = field
        self.value = value


class AuthenticationError(DomainError):
    """Raised on invalid credentials."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message)


class AuthorizationError(DomainError):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message)


class ValidationError(DomainError):
    """Raised on domain validation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class PaymentVerificationError(DomainError):
    """Raised when Robokassa signature or payment data is invalid."""

    def __init__(self, message: str = "Payment verification failed") -> None:
        super().__init__(message)


class EmailNotVerifiedError(DomainError):
    """Raised when login is attempted before email verification is complete."""

    def __init__(self, message: str = "Email not verified") -> None:
        super().__init__(message)
