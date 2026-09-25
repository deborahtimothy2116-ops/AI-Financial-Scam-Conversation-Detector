"""Analysis repository for persistence and historical analytics."""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload
from app.models.analysis import Analysis
from app.models.indicator import Indicator
from app.models.recommendation import Recommendation
from app.repositories.base_repository import BaseRepository
from app.schemas.analysis import IndicatorResponse, StructuredRecommendation


class AnalysisRepository(BaseRepository[Analysis]):
    def __init__(self, db: Session):
        super().__init__(Analysis, db)

    def get_analysis_with_relations(self, analysis_id: str) -> Optional[Analysis]:
        """Fetch analysis record including eagerly loaded indicators and feedback."""
        return (
            self.db.query(Analysis)
            .options(
                joinedload(Analysis.indicators),
                joinedload(Analysis.recommendation_records),
                joinedload(Analysis.feedback),
            )
            .filter(Analysis.id == analysis_id)
            .first()
        )

    def get_user_analysis_by_id(self, user_id: str, analysis_id: str) -> Optional[Analysis]:
        """Fetch an analysis record only if it belongs to the given user."""
        return (
            self.db.query(Analysis)
            .options(
                joinedload(Analysis.indicators),
                joinedload(Analysis.recommendation_records),
                joinedload(Analysis.feedback),
            )
            .filter(Analysis.id == analysis_id, Analysis.user_id == user_id)
            .first()
        )

    def create_analysis_record(
        self,
        raw_text: str,
        cleaned_text: str,
        input_source: str,
        detected_language: str,
        language_confidence: float,
        scam_category: str,
        risk_score: float,
        risk_level: str,
        is_scam: bool,
        explanation: str,
        recommendations: Union[List[str], List[StructuredRecommendation]],
        extracted_entities: Dict[str, Any],
        indicators_data: List[IndicatorResponse],
        llm_provider_used: str,
        processing_time_ms: float,
        user_id: Optional[str] = None,
        ai_score: Optional[float] = None,
        rule_score: Optional[float] = None,
        analysis_mode: Optional[str] = None,
    ) -> Analysis:
        """Create analysis record along with associated red-flag indicators and recommendations."""
        # Normalize recommendations to list of strings and list of structured items
        rec_strings: List[str] = []
        structured_recs: List[Tuple[str, str]] = []

        for item in recommendations:
            if isinstance(item, str):
                rec_strings.append(item)
                structured_recs.append(("high", item))
            elif isinstance(item, StructuredRecommendation):
                rec_strings.append(item.text)
                structured_recs.append((item.priority, item.text))
            elif isinstance(item, dict):
                p = item.get("priority", "high")
                t = item.get("text", "")
                rec_strings.append(t)
                structured_recs.append((p, t))

        mode = analysis_mode or ("fallback_rules" if "rule" in str(llm_provider_used) else "ai_plus_rules")
        ai_sc = ai_score if ai_score is not None else risk_score
        rule_sc = rule_score if rule_score is not None else risk_score

        analysis = Analysis(
            user_id=user_id,
            input_source=input_source,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            detected_language=detected_language,
            language_confidence=language_confidence,
            scam_category=scam_category,
            risk_score=risk_score,
            risk_level=risk_level,
            is_scam=is_scam,
            explanation=explanation,
            recommendations_json=json.dumps(rec_strings),
            extracted_entities_json=json.dumps(extracted_entities),
            llm_provider_used=llm_provider_used,
            processing_time_ms=processing_time_ms,
            ai_score=ai_sc,
            rule_score=rule_sc,
            analysis_mode=mode,
        )
        self.db.add(analysis)
        self.db.flush()  # Generate analysis.id

        # Insert indicators
        for ind in indicators_data:
            indicator_model = Indicator(
                analysis_id=analysis.id,
                title=ind.title,
                description=ind.description or ind.title,
                severity=ind.severity.value if hasattr(ind.severity, "value") else str(ind.severity),
                confidence=ind.confidence,
                snippet=ind.snippet or ind.evidence or ind.description,
                rule_id=ind.rule_id,
            )
            self.db.add(indicator_model)

        # Insert recommendation records
        for prio, text in structured_recs:
            if text:
                rec_model = Recommendation(
                    analysis_id=analysis.id,
                    priority=prio,
                    text=text,
                )
                self.db.add(rec_model)

        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_user_history_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        scam_category: Optional[str] = None,
        risk_level: Optional[str] = None,
        is_scam: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[Analysis], int]:
        """Fetch filtered and paginated history for an authenticated user."""
        query = self.db.query(Analysis).filter(Analysis.user_id == user_id)

        if scam_category:
            query = query.filter(Analysis.scam_category.ilike(f"%{scam_category}%"))
        if risk_level and risk_level.upper() != "ALL":
            query = query.filter(Analysis.risk_level.ilike(f"%{risk_level}%"))
        if is_scam is not None:
            query = query.filter(Analysis.is_scam == is_scam)
        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(
                (Analysis.cleaned_text.ilike(term)) | (Analysis.explanation.ilike(term))
            )

        total = query.count()
        items = (
            query.order_by(desc(Analysis.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Compute aggregated statistics for an authenticated user's scan history."""
        user_analyses = self.db.query(Analysis).filter(Analysis.user_id == user_id)
        total_scans = user_analyses.count()

        if total_scans == 0:
            return {
                "total_scans": 0,
                "total_scams_flagged": 0,
                "high_critical_count": 0,
                "safe_conversations_count": 0,
                "scam_prevention_rate_percent": 0.0,
                "scams_by_category": {},
                "scams_by_risk_level": {},
                "recent_activity_count_last_7_days": 0,
            }

        total_scams_flagged = user_analyses.filter(Analysis.is_scam == True).count()
        high_critical_count = user_analyses.filter(
            Analysis.risk_level.in_(["HIGH", "CRITICAL"])
        ).count()
        safe_count = user_analyses.filter(Analysis.risk_level.in_(["SAFE", "LOW"])).count()

        # Group by category
        cat_counts = (
            self.db.query(Analysis.scam_category, func.count(Analysis.id))
            .filter(Analysis.user_id == user_id)
            .group_by(Analysis.scam_category)
            .all()
        )
        scams_by_category = {cat: count for cat, count in cat_counts}

        # Group by risk level
        level_counts = (
            self.db.query(Analysis.risk_level, func.count(Analysis.id))
            .filter(Analysis.user_id == user_id)
            .group_by(Analysis.risk_level)
            .all()
        )
        scams_by_risk_level = {lvl: count for lvl, count in level_counts}

        # 7-day activity
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_count = user_analyses.filter(Analysis.created_at >= seven_days_ago).count()

        prevention_rate = round((total_scams_flagged / total_scans) * 100, 1)

        return {
            "total_scans": total_scans,
            "total_scams_flagged": total_scams_flagged,
            "high_critical_count": high_critical_count,
            "safe_conversations_count": safe_count,
            "scam_prevention_rate_percent": prevention_rate,
            "scams_by_category": scams_by_category,
            "scams_by_risk_level": scams_by_risk_level,
            "recent_activity_count_last_7_days": recent_count,
        }

    def delete_user_analysis(self, user_id: str, analysis_id: str) -> bool:
        """Delete an analysis record belonging to a specific user."""
        analysis = (
            self.db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == user_id)
            .first()
        )
        if analysis:
            self.db.delete(analysis)
            self.db.commit()
            return True
        return False

    def clear_user_history(self, user_id: str) -> int:
        """Delete all analysis records belonging to a user and return deleted count."""
        records = self.db.query(Analysis).filter(Analysis.user_id == user_id).all()
        count = len(records)
        for record in records:
            self.db.delete(record)
        self.db.commit()
        return count
