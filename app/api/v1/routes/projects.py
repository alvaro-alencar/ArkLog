"""Legacy project APIs backed only by the current user's GitHub connection."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_identity
from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    IntegrationConnectionRecord,
    ProjectRecord,
    ReportUsageRecord,
)
from app.schemas.project import InstantReportRequest, ProjectCreate, ProjectListResponse, ProjectResponse
from app.security.access import fail_usage, reserve_report
from app.security.ark_auth import ArkIdentity
from app.security.credentials import decrypt_credentials
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _require_approved(identity: ArkIdentity) -> None:
    if identity.access.status not in {"TRIAL", "ACTIVE"}:
        detail = (
            "Acesso ao ArkLog ainda não foi liberado."
            if identity.access.status == "PENDING"
            else "Acesso ao ArkLog bloqueado."
        )
        raise HTTPException(status_code=403, detail=detail)


async def _github_token(identity: ArkIdentity) -> str | None:
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        connection = await session.scalar(
            select(IntegrationConnectionRecord)
            .where(
                IntegrationConnectionRecord.user_id == identity.user.id,
                IntegrationConnectionRecord.organization_id == organization_id,
                IntegrationConnectionRecord.provider == "github",
                IntegrationConnectionRecord.status == "ACTIVE",
            )
            .order_by(IntegrationConnectionRecord.updated_at.desc())
        )
    if connection is None:
        return None
    return str(decrypt_credentials(connection.encrypted_credentials).get("access_token") or "") or None


@router.get("", response_model=ProjectListResponse)
async def list_user_projects(identity: ArkIdentity = Depends(get_identity)) -> ProjectListResponse:
    _require_approved(identity)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.user_id == identity.user.id)
        )
        projects = result.scalars().all()
    from app.schemas.project import ProjectSummary

    summaries = [
        ProjectSummary(
            id=project.id,
            name=project.name,
            repo_full_name=project.repo_full_name,
            description=project.description,
            created_at=project.created_at,
        )
        for project in projects
    ]
    return ProjectListResponse(count=len(summaries), projects=summaries)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    identity: ArkIdentity = Depends(get_identity),
) -> Any:
    _require_approved(identity)
    repo_full_name = data.repo_full_name.strip()
    if not _REPO_PATTERN.fullmatch(repo_full_name):
        raise HTTPException(
            status_code=400,
            detail="Informe o repositório no formato proprietário/projeto.",
        )
    if data.reports:
        raise HTTPException(
            status_code=410,
            detail="Destinos legados foram desativados. Crie um fluxo com uma conexão de destino.",
        )
    if identity.access.status == "TRIAL":
        async with AsyncSessionLocal() as session:
            count = await session.scalar(
                select(func.count(ProjectRecord.id)).where(
                    ProjectRecord.user_id == identity.user.id
                )
            )
        if int(count or 0) >= settings.arklog_trial_max_projects:
            raise HTTPException(status_code=403, detail="O teste gratuito permite apenas um projeto.")

    from app.integrations.github.api_client import fetch_repository_metadata

    owner, repo = repo_full_name.split("/", 1)
    token = await _github_token(identity)
    try:
        metadata = await fetch_repository_metadata(
            owner,
            repo,
            token=token,
            use_global_token=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Conecte o GitHub ou use um repositório público válido.",
        ) from exc
    if metadata.get("private") and not token:
        raise HTTPException(status_code=403, detail="Conecte o GitHub para usar repositórios privados.")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            collision = await session.scalar(
                select(ProjectRecord).where(
                    ProjectRecord.name == data.name,
                    ProjectRecord.user_id == identity.user.id,
                )
            )
            if collision:
                raise HTTPException(status_code=400, detail="Já existe um projeto com este nome.")
            project = ProjectRecord(
                name=data.name.strip(),
                repo_full_name=repo_full_name,
                description=data.description,
                report_style=data.report_style,
                tech_stack=data.tech_stack,
                business_context=data.business_context,
                user_id=identity.user.id,
            )
            session.add(project)
            await session.flush()
            project_id = project.id
        project = await session.scalar(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id)
            .options(selectinload(ProjectRecord.destinations))
        )
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, identity: ArkIdentity = Depends(get_identity)) -> Any:
    _require_approved(identity)
    async with AsyncSessionLocal() as session:
        project = await session.scalar(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id, ProjectRecord.user_id == identity.user.id)
            .options(selectinload(ProjectRecord.destinations))
        )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, identity: ArkIdentity = Depends(get_identity)) -> None:
    _require_approved(identity)
    async with AsyncSessionLocal() as session, session.begin():
        project = await session.scalar(
            select(ProjectRecord).where(
                ProjectRecord.id == project_id,
                ProjectRecord.user_id == identity.user.id,
            )
        )
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado.")
        await session.delete(project)


@router.post("/{project_id}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def backfill_commits(project_id: int, identity: ArkIdentity = Depends(get_identity)) -> dict:
    if identity.access.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Backfill exige acesso completo ao ArkLog.")

    from app.integrations.github.api_client import fetch_all_commits
    from app.repositories.commit_repository import CommitRepository

    async with AsyncSessionLocal() as session:
        project = await session.scalar(
            select(ProjectRecord).where(
                ProjectRecord.id == project_id,
                ProjectRecord.user_id == identity.user.id,
            )
        )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    token = await _github_token(identity)
    owner, repo = project.repo_full_name.split("/", 1)
    commits = await fetch_all_commits(owner, repo, token=token, use_global_token=False)
    saved = 0
    async with AsyncSessionLocal() as session, session.begin():
        commit_repo = CommitRepository(session)
        for commit in commits:
            if not await commit_repo.exists_for_project(commit.sha, project_id):
                await commit_repo.save_commit(commit, project_id)
                saved += 1
    return {"status": "ok", "saved": saved, "total": len(commits)}


@router.post("/{project_id}/instant-report")
async def trigger_instant_report(
    project_id: int,
    data: InstantReportRequest,
    identity: ArkIdentity = Depends(get_identity),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_approved(identity)
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key é obrigatório.")
    async with AsyncSessionLocal() as session:
        project = await session.scalar(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id, ProjectRecord.user_id == identity.user.id)
            .options(selectinload(ProjectRecord.destinations))
        )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    window_hours = data.window_hours
    if identity.access.status == "TRIAL" and (
        window_hours <= 0 or window_hours > settings.arklog_trial_max_window_hours
    ):
        raise HTTPException(status_code=400, detail="O teste gratuito cobre no máximo sete dias.")

    usage, is_new = await reserve_report(
        identity,
        idempotency_key,
        trigger="instant",
        project_id=project_id,
    )
    if not is_new:
        return {
            "status": usage.status.lower(),
            "usage_id": usage.id,
            "report_id": usage.report_id,
            "idempotent_replay": True,
        }

    since = naive_utcnow() - timedelta(hours=window_hours) if window_hours > 0 else None
    token = await _github_token(identity)
    owner, repo = project.repo_full_name.split("/", 1)
    try:
        from app.integrations.github.api_client import fetch_github_activity

        activity = await fetch_github_activity(
            owner,
            repo,
            since=since,
            token=token,
            use_global_token=False,
            trial_limits=identity.access.status == "TRIAL",
        )
        from app.core.events import event_bus

        await event_bus.publish(
            "commit.batch_ready",
            {
                "project_name": project.name,
                "project_id": project.id,
                "user_id": identity.user.id,
                "usage_id": usage.id,
                "access_status": identity.access.status,
                "description": project.description,
                "tech_stack": project.tech_stack,
                "business_context": project.business_context,
                "report_style": project.report_style,
                "clickup_task_id": "",
                "trigger": "instant",
                **activity,
                "commit_count": len(activity["commits"]),
            },
        )
    except Exception as exc:
        await fail_usage(usage.id, str(exc))
        raise HTTPException(status_code=502, detail="Não foi possível gerar o relatório.") from exc

    async with AsyncSessionLocal() as session:
        final_usage = await session.scalar(
            select(ReportUsageRecord).where(ReportUsageRecord.id == usage.id)
        )
    total_activity = sum(len(values) for values in activity.values())
    return {
        "status": final_usage.status.lower() if final_usage else "completed",
        "usage_id": usage.id,
        "report_id": final_usage.report_id if final_usage else None,
        "commit_count": len(activity["commits"]),
        "total_activity": total_activity,
        "idempotent_replay": False,
    }
