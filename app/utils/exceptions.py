class GuberaException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, code: str = "BAD_REQUEST"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class TenantNotFoundError(GuberaException):
    def __init__(self, message: str = "Tenant not found"):
        super().__init__(message, code="TENANT_NOT_FOUND")

class UserNotFoundError(GuberaException):
    def __init__(self, message: str = "User not found"):
        super().__init__(message, code="USER_NOT_FOUND")

class InvalidCredentialsError(GuberaException):
    def __init__(self, message: str = "Invalid email/phone or password"):
        super().__init__(message, code="INVALID_CREDENTIALS")

class InvalidOTPError(GuberaException):
    def __init__(self, message: str = "Invalid OTP verification code"):
        super().__init__(message, code="INVALID_OTP")

class ExpiredOTPError(GuberaException):
    def __init__(self, message: str = "OTP verification code has expired"):
        super().__init__(message, code="EXPIRED_OTP")

class OTPThrottleError(GuberaException):
    def __init__(self, message: str = "Please wait before requesting a new OTP"):
        super().__init__(message, code="OTP_THROTTLE")

class UnauthorizedError(GuberaException):
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(message, code="UNAUTHORIZED")

class ValidationError(GuberaException):
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")
