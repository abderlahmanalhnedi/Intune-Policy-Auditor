"""API route collection."""

from fastapi import APIRouter

from intune_auditor.api.routes import (
    audits,
    deviations,
    diagnostics,
    health,
    knowledge_packs,
    settings,
    tenant,
    version,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(version.router)
router.include_router(settings.router)
router.include_router(diagnostics.router)
router.include_router(deviations.router)
router.include_router(audits.router)
router.include_router(knowledge_packs.router)
router.include_router(tenant.router)
