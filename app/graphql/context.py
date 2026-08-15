import uuid
import asyncio
from typing import Optional, Any
import jwt
from fastapi import Request, Depends
from strawberry.fastapi import BaseContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres import get_db_session
from app.users.models import User
from app.auth.services import auth_service
from app.users.services import user_service
from app.tenants.services import tenant_domain_service
from app.utils.exceptions import UnauthorizedError

class SafeAsyncSession:
    """Thread-safe wrapper for AsyncSession to prevent concurrent operations in Strawberry GraphQL."""
    def __init__(self, session: AsyncSession):
        self._session = session
        self._lock = asyncio.Lock()

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await self._session.execute(*args, **kwargs)

    async def scalar(self, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await self._session.scalar(*args, **kwargs)

    async def scalars(self, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await self._session.scalars(*args, **kwargs)

    async def commit(self) -> Any:
        async with self._lock:
            return await self._session.commit()

    async def rollback(self) -> Any:
        async with self._lock:
            return await self._session.rollback()

    async def refresh(self, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await self._session.refresh(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

class GraphQLContext(BaseContext):
    """Custom GraphQL context containing database sessions, authenticated user info, and dataloaders."""
    def __init__(self, db: SafeAsyncSession, tenant_id: Optional[uuid.UUID], user: Optional[User], dataloaders=None):
        super().__init__()
        self.db = db
        self.tenant_id = tenant_id
        self.user = user
        self.dataloaders = dataloaders


async def get_graphql_context(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> GraphQLContext:
    """FastAPI dependency that constructs the GraphQL context for each request."""
    tenant_id: Optional[uuid.UUID] = None
    user: Optional[User] = None
    safe_db = SafeAsyncSession(db)

    # 1. Parse Tenant ID from HTTP Headers
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id_header:
        try:
            tenant_id = uuid.UUID(tenant_id_header)
        except ValueError:
            pass

    # 2. Parse User Authentication from JWT Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = auth_service.decode_token(token)
            if payload.get("type") == "access":
                user_id_str = payload.get("sub")
                tenant_id_str = payload.get("tenant_id")
                
                # Fallback: get tenant ID from JWT if it wasn't specified in the X-Tenant-ID header
                if not tenant_id and tenant_id_str:
                    tenant_id = uuid.UUID(tenant_id_str)

                # Fetch user details scoped to the resolved tenant
                if user_id_str and tenant_id:
                    user_id = uuid.UUID(user_id_str)
                    user = await user_service.get_user_by_id(safe_db, user_id, tenant_id)
        except jwt.ExpiredSignatureError:
            # Do not raise an error here to allow public queries to proceed as a guest.
            pass
        except jwt.InvalidTokenError:
            # Ignore invalid tokens to allow public queries to proceed.
            pass
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            pass

    # 3. Fallback: Parse Tenant ID based on domain host lookup
    if not tenant_id:
        hostname = request.url.hostname or (request.headers.get("host", "").split(":")[0] if request.headers.get("host") else None)
        if hostname:
            tenant_id = await tenant_domain_service.get_tenant_id_by_domain(safe_db, hostname)

    dataloaders = None
    if tenant_id:
        from app.graphql.dataloaders import DataLoaders
        dataloaders = DataLoaders(db=safe_db, tenant_id=tenant_id)

    return GraphQLContext(db=safe_db, tenant_id=tenant_id, user=user, dataloaders=dataloaders)
