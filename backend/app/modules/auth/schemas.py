from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Company email address.", examples=["alice@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        description="Plaintext password (min 8 characters) — hashed with argon2 before storage.",
        examples=["correct horse battery staple"],
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name shown to other users.",
        examples=["Alice Example"],
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., examples=["correct horse battery staple"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        ..., description="Refresh token issued by /auth/login or a prior /auth/refresh."
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        ..., description="The refresh token whose session should be revoked."
    )


class TokenResponse(BaseModel):
    access_token: str = Field(
        ..., description="Short-lived JWT — send as `Authorization: Bearer <token>`."
    )
    refresh_token: str = Field(
        ..., description="Long-lived token — exchange at /auth/refresh for a new token pair."
    )
    token_type: str = Field(default="bearer", description="Always 'bearer'.")
    expires_in: int = Field(..., description="Access token lifetime in seconds.", examples=[900])
