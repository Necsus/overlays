from typing import cast

from fastapi import HTTPException, Request, status

from app.application.session import (
    SESSION_COOKIE_NAME,
    SessionIdentity,
    SessionSigner,
)
from app.application.streamer_access import StreamerAccessGuard
from app.infrastructure.database import DatabaseError


async def require_session_identity(request: Request) -> SessionIdentity:
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session_signer = cast(
        SessionSigner,
        request.app.state.session_signer,
    )
    identity = session_signer.verify(cookie_value)

    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    access_guard = cast(StreamerAccessGuard, request.app.state.streamer_access)
    try:
        streamer = await access_guard.load_streamer(identity.twitch_user_id)
    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify streamer access",
        ) from None
    if streamer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Streamer access is disabled",
        )
    # Logout or expiry may have happened while the database check was awaiting I/O.
    if session_signer.verify(cookie_value) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    request.state.streamer = streamer
    return identity
