"""Enumerations for the browser acquisition domain."""

from enum import Enum


class BrowserState(str, Enum):
    """Tracks the lifecycle state of a managed browser instance."""
    IDLE = "IDLE"
    LAUNCHING = "LAUNCHING"
    READY = "READY"
    NAVIGATING = "NAVIGATING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


class SessionState(str, Enum):
    """Persistent session authentication state."""
    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"


class CaptchaType(str, Enum):
    """Types of CAPTCHA / human-verification challenges encountered."""
    RECAPTCHA_V2 = "RECAPTCHA_V2"
    RECAPTCHA_V3 = "RECAPTCHA_V3"
    HCAPTCHA = "HCAPTCHA"
    IMAGE_CHALLENGE = "IMAGE_CHALLENGE"
    SMS_OTP = "SMS_OTP"
    SLIDER = "SLIDER"
    UNKNOWN = "UNKNOWN"


class PlatformName(str, Enum):
    """Supported job platform identifiers."""
    NAUKRI = "naukri"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    UNSTOP = "unstop"
    INTERNSHALA = "internshala"
