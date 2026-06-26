from fastapi import APIRouter, Depends, Header, Response, status

from ..schemas.admin import LoginRequest, LoginResponse
from ..security.admin_auth import login, logout, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=LoginResponse)
def admin_login(body: LoginRequest) -> LoginResponse:
    return LoginResponse(token=login(body.password))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def admin_logout(authorization: str | None = Header(default=None)) -> Response:
    logout(authorization[len("Bearer ") :].strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
