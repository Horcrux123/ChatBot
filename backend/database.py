import base64
import hashlib
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Dict, Any, Optional

from cryptography.fernet import Fernet
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.config import settings

# --- Encryption Utilities ---

def get_fernet_key() -> bytes:
    # Generate a deterministic base64 32-byte key from settings.SECRET_KEY
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)

def encrypt_token(token: str) -> str:
    if not token:
        return ""
    f = Fernet(get_fernet_key())
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    f = Fernet(get_fernet_key())
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


# --- SQLAlchemy Setup ---

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    zoho_user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    memory: Mapped[Optional["UserMemory"]] = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")

    def get_decrypted_access_token(self) -> str:
        return decrypt_token(self.access_token)

    def get_decrypted_refresh_token(self) -> str:
        return decrypt_token(self.refresh_token)

    def set_encrypted_access_token(self, token: str) -> None:
        self.access_token = encrypt_token(token)

    def set_encrypted_refresh_token(self, token: str) -> None:
        self.refresh_token = encrypt_token(token)


class UserMemory(Base):
    __tablename__ = "user_memory"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    last_project_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_project_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Store lists and dicts inside JSON columns
    frequently_used_projects: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    past_queries: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memory")


# --- Database Connection Initialization ---

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
