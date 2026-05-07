"""
ArkLog - Analytics Service

Computes project statistics and health scores from persisted records.

Health score algorithm (0–100):
  Activity  (40pts) — recent commit frequency vs 30-day baseline
  Coverage  (30pts) — ratio of reports published to ClickUp vs generated
  Recency   (30pts) — days since last commit (lower = better)
"""

from datetime import timedelta
from typing import Optional

import structlog
from sqlalchemy import func, select

from app.models.database import AsyncSessionLocal
from app.models.tables import CommitRecord, ProjectRecord, ReportRecord
from app.schemas.analytics import AnalyticsSummaryResponse, HealthScore, ProjectStats
from app.utils.datetime_utils import naive_utcnow

logger = structlog.get_logger(__name__)


class AnalyticsService:
    async def get_project_stats(self, project_name: str) -> Optional[ProjectStats]:
        async with AsyncSessionLocal() as session:
            proj_result = await session.execute(
                select(ProjectRecord).where(ProjectRecord.name == project_name).limit(1)
            )
            project = proj_result.scalar_one_or_none()
            if not project:
                return None

            pid = project.id
            thirty_ago = naive_utcnow() - timedelta(days=30)

            total_commits = await _scalar(
                session, select(func.count(CommitRecord.id)).where(CommitRecord.project_id == pid)
            )
            total_reports = await _scalar(
                session, select(func.count(ReportRecord.id)).where(ReportRecord.project_id == pid)
            )
            published_reports = await _scalar(
                session,
                select(func.count(ReportRecord.id)).where(
                    ReportRecord.project_id == pid, ReportRecord.status == "published"
                ),
            )
            recent_commits = await _scalar(
                session,
                select(func.count(CommitRecord.id)).where(
                    CommitRecord.project_id == pid, CommitRecord.committed_at >= thirty_ago
                ),
            )
            last_commit_at = await _scalar(
                session,
                select(func.max(CommitRecord.committed_at)).where(CommitRecord.project_id == pid),
            )

            days_ago: Optional[int] = None
            if last_commit_at:
                days_ago = (naive_utcnow() - last_commit_at).days

            return ProjectStats(
                project_name=project_name,
                total_commits=total_commits,
                total_reports=total_reports,
                published_reports=published_reports,
                avg_commits_per_day=round(recent_commits / 30, 2),
                last_activity_days_ago=days_ago,
            )

    async def get_health_score(self, project_name: str) -> Optional[HealthScore]:
        stats = await self.get_project_stats(project_name)
        if not stats:
            return None

        # Activity (40pts)
        cpd = stats.avg_commits_per_day
        if cpd >= 1.0:
            activity = 40
        elif cpd >= 0.5:
            activity = 30
        elif cpd >= 0.1:
            activity = 20
        elif stats.total_commits > 0:
            activity = 10
        else:
            activity = 0

        # Coverage (30pts)
        if stats.total_reports == 0:
            coverage = 15  # neutral when system is fresh
        else:
            coverage = round((stats.published_reports / stats.total_reports) * 30)

        # Recency (30pts)
        d = stats.last_activity_days_ago
        if d is None:
            recency = 0
        elif d == 0:
            recency = 30
        elif d <= 3:
            recency = 25
        elif d <= 7:
            recency = 20
        elif d <= 14:
            recency = 15
        elif d <= 30:
            recency = 10
        else:
            recency = 5

        score = activity + coverage + recency
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"

        return HealthScore(
            project_name=project_name,
            score=score,
            grade=grade,
            factors={"activity": activity, "coverage": coverage, "recency": recency},
        )

    async def get_summary(self) -> AnalyticsSummaryResponse:
        from app.config.projects import projects_config

        all_stats: list[ProjectStats] = []
        for project in projects_config.projects:
            stats = await self.get_project_stats(project.name)
            if stats:
                all_stats.append(stats)

        most_active = max(all_stats, key=lambda s: s.total_commits, default=None)

        return AnalyticsSummaryResponse(
            total_projects=len(all_stats),
            total_commits=sum(s.total_commits for s in all_stats),
            total_reports=sum(s.total_reports for s in all_stats),
            most_active_project=most_active.project_name if most_active else None,
            projects=all_stats,
        )


async def _scalar(session, stmt):
    """Execute a scalar select statement and return the result (or 0 if None)."""
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return value if value is not None else 0
