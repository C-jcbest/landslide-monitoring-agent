"""Beidou credential binding API routes."""

from typing import Protocol

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from app.api.v1.auth import get_current_user_from_any_token
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.schemas.beidou import (
    BeidouCredentialStatusResponse,
    BeidouCredentialUpsertRequest,
)
from app.services.beidou.client import BeidouRequestError
from app.services.beidou.credentials import create_beidou_credential_service
from app.services.beidou.crypto import BeidouCryptoError

router = APIRouter()


class CredentialService(Protocol):
    """Protocol for route-level Beidou credential services."""

    async def get_status(self, user_id: int) -> BeidouCredentialStatusResponse:
        """Return current credential status."""
        ...

    async def bind_or_update(self, user_id: int, username: str, password: str) -> BeidouCredentialStatusResponse:
        """Bind or update credentials."""
        ...

    async def unbind(self, user_id: int) -> BeidouCredentialStatusResponse:
        """Unbind credentials."""
        ...


credential_service: CredentialService | None = None


def _get_credential_service() -> CredentialService:
    global credential_service
    if credential_service is None:
        credential_service = create_beidou_credential_service()
    return credential_service


@router.get("/credentials/status", response_model=BeidouCredentialStatusResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["beidou_credentials"][0])
async def get_beidou_credential_status(
    request: Request,
    user: User = Depends(get_current_user_from_any_token),
) -> BeidouCredentialStatusResponse:
    """Return current user's Beidou credential binding status."""
    try:
        return await _get_credential_service().get_status(user.id)
    except Exception as e:
        logger.exception("beidou_credential_operation_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail="北斗凭据状态查询失败。")


@router.put("/credentials", response_model=BeidouCredentialStatusResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["beidou_credentials"][0])
async def bind_beidou_credentials(
    request: Request,
    payload: BeidouCredentialUpsertRequest,
    user: User = Depends(get_current_user_from_any_token),
) -> BeidouCredentialStatusResponse:
    """Bind or update current user's Beidou credentials."""
    try:
        return await _get_credential_service().bind_or_update(
            user.id,
            payload.username,
            payload.password.get_secret_value(),
        )
    except BeidouRequestError as e:
        raise HTTPException(status_code=_status_for_beidou_error(e), detail=e.message)
    except BeidouCryptoError as e:
        logger.exception("beidou_credential_operation_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail="北斗凭据加密配置错误。")
    except Exception as e:
        logger.exception("beidou_credential_operation_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail="北斗凭据保存失败。")


@router.delete("/credentials", response_model=BeidouCredentialStatusResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["beidou_credentials"][0])
async def unbind_beidou_credentials(
    request: Request,
    user: User = Depends(get_current_user_from_any_token),
) -> BeidouCredentialStatusResponse:
    """Unbind current user's Beidou credentials."""
    try:
        return await _get_credential_service().unbind(user.id)
    except Exception as e:
        logger.exception("beidou_credential_operation_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail="北斗凭据解绑失败。")


def _status_for_beidou_error(error: BeidouRequestError) -> int:
    if error.error_code in {"beidou_invalid_credentials"}:
        return 401
    if error.error_code in {
        "beidou_permission_denied",
        "beidou_invalid_account_format",
        "beidou_password_expired",
        "beidou_account_disabled",
        "beidou_invalid_password_format",
        "beidou_auth_failed",
        "beidou_request_rejected",
    }:
        return 400
    if error.error_code in {"beidou_timeout", "beidou_unavailable"}:
        return 503
    if error.error_code == "beidou_bad_response":
        return 502
    return 500
