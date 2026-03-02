"""
Email verification package.

Provides stateless email verification tokens and email delivery.

Submodules and tamplates:
    _tokens.py:               JWT-style stateless token creation and validation.
    _mailer.py:               SMTP email delivery.
    _body_template.html:      HTML email body template.
    _body_template.txt:       Plaintext email body template (fallback if html is not supported).

Exceptions:
    TokenError                Base class for all token errors.
      TokenTypeError          Token has an unexpected type/kind.
      TokenEmailError         Email address in token is invalid or mismatched.
      TokenExpiredError       Token has passed its expiry time.
      TokenSubjectError       Token subject does not match expected value.
      TokenVersionError       Token was created with an unsupported version.
      TokenSignatureError     Token signature is invalid or tampered.

    MailerError               Base class for all mailer errors.
      SMTPSendError           Failure while sending the message.
      SMTPConnectionError     Could not connect to the SMTP server.
      SMTPAuthenticationError SMTP credentials were rejected.
      InvalidAddressError     Recipient address is malformed or rejected.
"""

from ._tokens import (
    create_token,
    validate_token,
    TokenError,
    TokenTypeError,
    TokenExpiredError,
    TokenSubjectError,
    TokenVersionError,
    TokenSignatureError,
    VerificationResult,
)

from ._mailer import (
    send_email,
    MailerError,
    SMTPSendError,
    SMTPConnectionError,
    SMTPAuthenticationError,
    InvalidAddressError,
)

__all__ = [
    # Token functions and errors
    "create_token",
    "validate_token",
    "TokenError",
    "TokenTypeError",
    "TokenExpiredError",
    "TokenSubjectError",
    "TokenVersionError",
    "TokenSignatureError",
    "VerificationResult",
    # Mailer functions and errors
    "send_email",
    "MailerError",
    "SMTPSendError",
    "SMTPConnectionError",
    "SMTPAuthenticationError",
    "InvalidAddressError",
]
