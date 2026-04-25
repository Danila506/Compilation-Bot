from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_cursor: Mapped[str | None] = mapped_column(String(255))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    raw_documents: Mapped[list[DocumentRaw]] = relationship(back_populates="source")


class DocumentRaw(Base):
    __tablename__ = "documents_raw"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)

    source: Mapped[Source] = relationship(back_populates="raw_documents")
    normalized: Mapped[DocumentNormalized | None] = relationship(back_populates="raw_document")


class DocumentNormalized(Base):
    __tablename__ = "documents_normalized"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("documents_raw.id"), unique=True, nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), index=True, nullable=False)
    title_clean: Mapped[str] = mapped_column(String(1024), nullable=False)
    text_clean: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str] = mapped_column(String(32), default="unknown")
    tokens_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    simhash: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    raw_document: Mapped[DocumentRaw] = relationship(back_populates="normalized")
    mechanics: Mapped[list[DocumentMechanic]] = relationship(back_populates="document")
    scores: Mapped[list[DocumentScore]] = relationship(back_populates="document")


class MechanicsCatalog(Base):
    __tablename__ = "mechanics_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(128), default="general")


class DocumentMechanic(Base):
    __tablename__ = "document_mechanics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents_normalized.id"), nullable=False)
    mechanic_id: Mapped[int] = mapped_column(ForeignKey("mechanics_catalog.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_snippet: Mapped[str] = mapped_column(String(1024), default="")

    document: Mapped[DocumentNormalized] = relationship(back_populates="mechanics")


class GameProfile(Base):
    __tablename__ = "game_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    mechanic_weights_json: Mapped[dict] = mapped_column(JSON, default=dict)
    negative_filters_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DocumentScore(Base):
    __tablename__ = "document_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents_normalized.id"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("game_profile.id"), nullable=False)
    score_total: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    document: Mapped[DocumentNormalized] = relationship(back_populates="scores")


class DedupIndex(Base):
    __tablename__ = "dedup_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents_normalized.id"), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    duplicate_of_document_id: Mapped[int | None] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TelegramSubscription(Base):
    __tablename__ = "telegram_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("game_profile.id"), nullable=False)
    min_score: Mapped[float] = mapped_column(Float, default=1.4)
    digest_mode: Mapped[str] = mapped_column(String(32), default="instant")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SentItem(Base):
    __tablename__ = "sent_items"
    __table_args__ = (UniqueConstraint("chat_id", "document_id", name="uq_sent_chat_doc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents_normalized.id"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    message_id: Mapped[str | None] = mapped_column(String(64))


class DocumentFeedback(Base):
    __tablename__ = "document_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents_normalized.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
