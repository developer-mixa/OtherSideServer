"""Domain-specific exceptions."""

from uuid import UUID


class DomainError(Exception):
    """Base domain exception.

    ``code`` is a stable, machine-readable identifier the presentation layer sends
    to clients so they can render a localized message instead of ``message``,
    which stays English and is only a developer/fallback hint.
    """

    default_code = "domain_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or self.default_code
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""

    default_code = "not_found"

    def __init__(self, entity_name: str, entity_id: UUID | str, code: str | None = None) -> None:
        super().__init__(f"{entity_name} with id={entity_id} not found", code)
        self.entity_name = entity_name
        self.entity_id = entity_id


class DuplicateEntityError(DomainError):
    """Raised when a unique constraint would be violated."""

    default_code = "duplicate"

    def __init__(self, entity_name: str, field: str, value: str, code: str | None = None) -> None:
        super().__init__(f"{entity_name} with {field}={value!r} already exists", code)
        self.entity_name = entity_name
        self.field = field
        self.value = value


class AuthenticationError(DomainError):
    """Raised on invalid credentials."""

    default_code = "authentication_error"

    def __init__(self, message: str = "Invalid credentials", code: str | None = None) -> None:
        super().__init__(message, code)


class AuthorizationError(DomainError):
    """Raised when user lacks required permissions."""

    default_code = "authorization_error"

    def __init__(self, message: str = "Insufficient permissions", code: str | None = None) -> None:
        super().__init__(message, code)


class ValidationError(DomainError):
    """Raised on domain validation failure."""

    default_code = "validation_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code)


class PaymentVerificationError(DomainError):
    """Raised when Robokassa signature or payment data is invalid."""

    default_code = "payment_verification_error"

    def __init__(
        self, message: str = "Payment verification failed", code: str | None = None
    ) -> None:
        super().__init__(message, code)


class EmailNotVerifiedError(DomainError):
    """Raised when login is attempted before email verification is complete."""

    default_code = "email_not_verified"

    def __init__(self, message: str = "Email not verified", code: str | None = None) -> None:
        super().__init__(message, code)
