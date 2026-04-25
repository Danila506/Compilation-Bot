from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from urllib.parse import quote_plus, urlparse

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.analyzer.mechanic_labels import mechanic_label_ru
from app.analyzer.rule_analyzer import RuleAnalyzer
from app.db.models import (
    DedupIndex,
    DocumentFeedback,
    DocumentNormalized,
    DocumentRaw,
    DocumentScore,
    GameProfile,
    SentItem,
    Source,
)


class SourceRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, source_type: str, source_name: str) -> Source:
        source = self.session.execute(
            select(Source).where(Source.type == source_type, Source.name == source_name)
        ).scalar_one_or_none()
        if source:
            return source
        source = Source(type=source_type, name=source_name)
        self.session.add(source)
        self.session.flush()
        return source


class DocumentRepo:
    def __init__(self, session: Session):
        self.session = session

    def raw_exists(self, source_id: int, external_id: str) -> bool:
        row = self.session.execute(
            select(DocumentRaw.id).where(
                DocumentRaw.source_id == source_id,
                DocumentRaw.external_id == external_id,
            )
        ).first()
        return row is not None

    def insert_raw(self, source_id: int, payload) -> DocumentRaw:
        row = DocumentRaw(
            source_id=source_id,
            external_id=payload.external_id,
            url=payload.url,
            title=payload.title,
            content=payload.content,
            author=payload.author,
            published_at=payload.published_at,
            meta_json=payload.meta,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def insert_normalized(
        self,
        raw_id: int,
        canonical_url: str,
        title_clean: str,
        text_clean: str,
        lang: str,
        tokens_count: int,
        content_hash: str,
        simhash: int,
    ) -> DocumentNormalized:
        row = DocumentNormalized(
            raw_id=raw_id,
            canonical_url=canonical_url,
            title_clean=title_clean,
            text_clean=text_clean,
            lang=lang,
            tokens_count=tokens_count,
            content_hash=content_hash,
            simhash=simhash,
        )
        self.session.add(row)
        self.session.flush()
        return row


class ProfileRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_default_profile(
        self,
        name: str = "2D top-down survival",
        description: str = "Default profile for survival mechanics discovery.",
        tags: list[str] | None = None,
        mechanic_weights: dict | None = None,
        negative_keywords: list[str] | None = None,
    ) -> GameProfile:
        profile = self.session.execute(select(GameProfile).limit(1)).scalar_one_or_none()
        if profile:
            profile.name = name
            profile.description = description
            profile.tags_json = tags or []
            profile.mechanic_weights_json = mechanic_weights or {}
            profile.negative_filters_json = {"keywords": negative_keywords or []}
            self.session.flush()
            return profile
        profile = GameProfile(
            name=name,
            description=description,
            tags_json=tags or [],
            mechanic_weights_json=mechanic_weights or {},
            negative_filters_json={"keywords": negative_keywords or []},
        )
        self.session.add(profile)
        self.session.flush()
        return profile


class DedupRepo:
    def __init__(self, session: Session):
        self.session = session

    def find_by_key(self, dedup_key: str) -> DedupIndex | None:
        return self.session.execute(
            select(DedupIndex).where(DedupIndex.dedup_key == dedup_key)
        ).scalar_one_or_none()

    def find_by_canonical_url(self, canonical_url: str, current_document_id: int) -> DocumentNormalized | None:
        return self.session.execute(
            select(DocumentNormalized)
            .where(DocumentNormalized.canonical_url == canonical_url)
            .where(DocumentNormalized.id != current_document_id)
            .limit(1)
        ).scalar_one_or_none()

    def find_near_simhash(
        self,
        simhash: int,
        current_document_id: int,
        max_distance: int = 3,
    ) -> DocumentNormalized | None:
        rows = self.session.execute(
            select(DocumentNormalized)
            .where(DocumentNormalized.id != current_document_id)
            .limit(500)
        ).scalars()
        for row in rows:
            if (int(row.simhash) ^ int(simhash)).bit_count() <= max_distance:
                return row
        return None

    def add(self, document_id: int, dedup_key: str, duplicate_of_document_id: int | None, method: str):
        row = DedupIndex(
            document_id=document_id,
            dedup_key=dedup_key,
            duplicate_of_document_id=duplicate_of_document_id,
            method=method,
        )
        self.session.add(row)
        self.session.flush()


class ScoreRepo:
    def __init__(self, session: Session):
        self.session = session

    def insert(self, document_id: int, profile_id: int, total: float, breakdown: dict, is_relevant: bool):
        row = DocumentScore(
            document_id=document_id,
            profile_id=profile_id,
            score_total=total,
            score_breakdown_json=breakdown,
            is_relevant=is_relevant,
        )
        self.session.add(row)
        self.session.flush()
        return row


class SentRepo:
    def __init__(self, session: Session):
        self.session = session

    def was_sent(self, chat_id: str, document_id: int) -> bool:
        row = self.session.execute(
            select(SentItem.id).where(SentItem.chat_id == chat_id, SentItem.document_id == document_id)
        ).first()
        return row is not None

    def was_url_sent(self, chat_id: str, canonical_url: str) -> bool:
        row = self.session.execute(
            select(SentItem.id)
            .join(DocumentNormalized, DocumentNormalized.id == SentItem.document_id)
            .where(SentItem.chat_id == chat_id)
            .where(DocumentNormalized.canonical_url == canonical_url)
        ).first()
        return row is not None

    def mark_sent(self, chat_id: str, document_id: int, message_id: str | None):
        row = SentItem(chat_id=chat_id, document_id=document_id, message_id=message_id)
        self.session.add(row)
        self.session.flush()


class FeedbackRepo:
    def __init__(self, session: Session):
        self.session = session

    def add(self, chat_id: str, document_id: int, value: str, note: str = "") -> DocumentFeedback:
        row = DocumentFeedback(chat_id=chat_id, document_id=document_id, value=value, note=note)
        self.session.add(row)
        self.session.flush()
        return row


class ReadRepo:
    def __init__(self, session: Session):
        self.session = session

    def list_sources_overview(self) -> list[dict]:
        rows = self.session.execute(
            select(
                Source.name,
                Source.type,
                func.count(DocumentRaw.id).label("items"),
            )
            .select_from(Source)
            .join(DocumentRaw, DocumentRaw.source_id == Source.id, isouter=True)
            .group_by(Source.id)
            .order_by(Source.name.asc())
        ).all()
        return [
            {"name": row.name, "type": row.type, "items": int(row.items or 0)}
            for row in rows
        ]

    def top_findings_last_hours(self, hours: int = 24, limit: int = 10) -> list[dict]:
        since = datetime.now(timezone.utc).replace(tzinfo=None)
        since = since - timedelta(hours=hours)
        rows = self.session.execute(
            select(
                DocumentNormalized.id.label("doc_id"),
                DocumentNormalized.title_clean,
                DocumentNormalized.canonical_url,
                DocumentScore.score_total,
                DocumentScore.scored_at,
                Source.name.label("source_name"),
            )
            .join(DocumentScore, DocumentScore.document_id == DocumentNormalized.id)
            .join(DocumentRaw, DocumentRaw.id == DocumentNormalized.raw_id)
            .join(Source, Source.id == DocumentRaw.source_id)
            .where(DocumentScore.is_relevant.is_(True))
            .where(Source.type != "steam_search")
            .where(DocumentScore.scored_at >= since)
            .order_by(desc(DocumentScore.score_total), desc(DocumentScore.scored_at))
            .limit(limit)
        ).all()
        return [
            {
                "doc_id": row.doc_id,
                "title": row.title_clean,
                "url": row.canonical_url,
                "score": float(row.score_total),
                "source": row.source_name,
                "scored_at": str(row.scored_at),
            }
            for row in rows
        ]

    def findings_today(self, limit: int = 20) -> list[dict]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self.session.execute(
            select(
                DocumentNormalized.id.label("doc_id"),
                DocumentNormalized.title_clean,
                DocumentNormalized.canonical_url,
                DocumentScore.score_total,
                DocumentScore.scored_at,
                Source.name.label("source_name"),
            )
            .join(DocumentScore, DocumentScore.document_id == DocumentNormalized.id)
            .join(DocumentRaw, DocumentRaw.id == DocumentNormalized.raw_id)
            .join(Source, Source.id == DocumentRaw.source_id)
            .where(DocumentScore.is_relevant.is_(True))
            .where(Source.type != "steam_search")
            .where(DocumentScore.scored_at >= start_of_day)
            .order_by(desc(DocumentScore.scored_at))
            .limit(limit)
        ).all()
        return [
            {
                "doc_id": row.doc_id,
                "title": row.title_clean,
                "url": row.canonical_url,
                "score": float(row.score_total),
                "source": row.source_name,
                "scored_at": str(row.scored_at),
            }
            for row in rows
        ]

    def dashboard_summary(self) -> dict:
        documents = self.session.execute(select(func.count(DocumentNormalized.id))).scalar_one()
        relevant = self.session.execute(
            select(func.count(DocumentScore.id)).where(DocumentScore.is_relevant.is_(True))
        ).scalar_one()
        sent = self.session.execute(select(func.count(SentItem.id))).scalar_one()
        feedback = self.session.execute(select(func.count(DocumentFeedback.id))).scalar_one()
        sources = self.session.execute(select(func.count(Source.id))).scalar_one()
        return {
            "documents": int(documents or 0),
            "relevant": int(relevant or 0),
            "sent": int(sent or 0),
            "feedback": int(feedback or 0),
            "sources": int(sources or 0),
        }

    def dashboard_findings(self, limit: int = 150) -> list[dict]:
        rows = self.session.execute(
            select(
                DocumentNormalized.id.label("doc_id"),
                DocumentNormalized.title_clean,
                DocumentNormalized.canonical_url,
                DocumentNormalized.text_clean,
                DocumentScore.score_total,
                DocumentScore.score_breakdown_json,
                DocumentScore.is_relevant,
                DocumentScore.scored_at,
                Source.name.label("source_name"),
                DocumentRaw.content,
                DocumentRaw.meta_json,
            )
            .join(DocumentScore, DocumentScore.document_id == DocumentNormalized.id)
            .join(DocumentRaw, DocumentRaw.id == DocumentNormalized.raw_id)
            .join(Source, Source.id == DocumentRaw.source_id)
            .where(Source.type != "steam_search")
            .order_by(desc(DocumentScore.scored_at), desc(DocumentScore.score_total))
            .limit(limit)
        ).all()
        doc_ids = [int(row.doc_id) for row in rows]
        feedback_by_doc: dict[int, DocumentFeedback] = {}
        if doc_ids:
            feedback_rows = self.session.execute(
                select(DocumentFeedback)
                .where(DocumentFeedback.document_id.in_(doc_ids))
                .order_by(desc(DocumentFeedback.created_at))
            ).scalars()
            for feedback in feedback_rows:
                feedback_by_doc.setdefault(int(feedback.document_id), feedback)

        findings = []
        analyzer = RuleAnalyzer()
        for row in rows:
            doc_id = int(row.doc_id)
            feedback = feedback_by_doc.get(doc_id)
            content = row.content or row.text_clean or ""
            breakdown = row.score_breakdown_json or {}
            mechanics = breakdown.get("mechanics") or []
            if not mechanics:
                features = analyzer.analyze(row.title_clean or "", content)
                mechanics = [
                    {
                        "key": match.key,
                        "evidence": match.evidence,
                        "introduced": match.introduced,
                        "confidence": match.confidence,
                    }
                    for match in features.mechanics
                ]

            mechanics_ru = [
                {
                    "key": item.get("key", ""),
                    "title": mechanic_label_ru(str(item.get("key", ""))),
                    "evidence": item.get("evidence", ""),
                    "introduced": bool(item.get("introduced", False)),
                    "confidence": float(item.get("confidence", 0.0) or 0.0),
                }
                for item in mechanics
                if item.get("key")
            ]
            introduced_ru = [item["title"] for item in mechanics_ru if item["introduced"]]
            if introduced_ru:
                summary = "Похоже, в материале добавили или переработали: " + ", ".join(introduced_ru) + "."
            elif mechanics_ru:
                summary = "Материал совпал с профилем по механикам: " + ", ".join(
                    item["title"] for item in mechanics_ru
                ) + "."
            else:
                summary = "Явных механик в тексте не найдено; запись стоит проверить вручную."

            image_url = ""
            meta = row.meta_json or {}
            if isinstance(meta, dict):
                image_url = str(meta.get("image_url") or "")
            steam_match = re.search(r"store\.steampowered\.com/app/(\d+)", row.canonical_url or "")
            steam_news_match = re.search(r"store\.steampowered\.com/news/app/(\d+)", row.canonical_url or "")
            youtube_match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]+)", row.canonical_url or "")
            html_image_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
            if not image_url and steam_match:
                image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{steam_match.group(1)}/header.jpg"
            if not image_url and steam_news_match:
                image_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{steam_news_match.group(1)}/header.jpg"
            if not image_url and youtube_match:
                image_url = f"https://img.youtube.com/vi/{youtube_match.group(1)}/hqdefault.jpg"
            if not image_url and html_image_match:
                image_url = html_image_match.group(1)
            if not image_url:
                host = urlparse(row.canonical_url or "").hostname or ""
                if host:
                    image_url = f"https://www.google.com/s2/favicons?domain={quote_plus(host)}&sz=128"
            findings.append(
                {
                    "doc_id": doc_id,
                    "title": row.title_clean,
                    "url": row.canonical_url,
                    "content": content[:3000],
                    "score": float(row.score_total),
                    "breakdown": breakdown,
                    "mechanics_ru": mechanics_ru,
                    "analysis_summary": summary,
                    "is_relevant": bool(row.is_relevant),
                    "source": row.source_name,
                    "image_url": image_url,
                    "scored_at": str(row.scored_at),
                    "feedback_value": feedback.value if feedback else "",
                    "feedback_note": feedback.note if feedback else "",
                    "feedback_created_at": str(feedback.created_at) if feedback else "",
                }
            )
        return findings
