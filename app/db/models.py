import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id         : Mapped[str]      = mapped_column(String, primary_key=True, default=gen_uuid)
    email      : Mapped[str]      = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_pw  : Mapped[str]      = mapped_column(String, nullable=False)
    is_admin   : Mapped[bool]     = mapped_column(Boolean, default=False)
    created_at : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    documents  : Mapped[list["Document"]] = relationship(back_populates="user")
    traces     : Mapped[list["LLMTrace"]] = relationship(back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id         : Mapped[str]      = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id    : Mapped[str]      = mapped_column(ForeignKey("users.id"), nullable=False)
    filename   : Mapped[str]      = mapped_column(String, nullable=False)
    s3_key     : Mapped[str]      = mapped_column(String, nullable=False)
    status     : Mapped[str]      = mapped_column(String, default="pending")
    created_at : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user       : Mapped["User"]   = relationship(back_populates="documents")


class LLMTrace(Base):
    __tablename__ = "llm_traces"

    id                : Mapped[str]      = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id           : Mapped[str]      = mapped_column(ForeignKey("users.id"), nullable=False)
    question          : Mapped[str]      = mapped_column(String)
    model_name        : Mapped[str]      = mapped_column(String, default="")
    prompt_tokens     : Mapped[int]      = mapped_column(Integer, default=0)
    completion_tokens : Mapped[int]      = mapped_column(Integer, default=0)
    total_tokens      : Mapped[int]      = mapped_column(Integer, default=0)
    total_cost_usd    : Mapped[float]    = mapped_column(Float,   default=0.0)
    embed_ms          : Mapped[int]      = mapped_column(Integer, default=0)
    retrieve_ms       : Mapped[int]      = mapped_column(Integer, default=0)
    llm_ms            : Mapped[int]      = mapped_column(Integer, default=0)
    total_ms          : Mapped[int]      = mapped_column(Integer, default=0)
    created_at        : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user              : Mapped["User"]   = relationship(back_populates="traces")