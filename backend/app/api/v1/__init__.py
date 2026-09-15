from fastapi import APIRouter

from . import (
    alerts, attck, audit, auth, dashboard, drift, enrichment,
    events, health, incidents, ingest, mappings,
    parsers, quarantine, reports, schema, testlab,
    threat_intel,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(quarantine.router, prefix="/quarantine", tags=["quarantine"])
router.include_router(parsers.router, prefix="/parsers", tags=["parsers"])
router.include_router(enrichment.router, prefix="/enrichment", tags=["enrichment"])
router.include_router(threat_intel.router, prefix="/threat-intel", tags=["threat-intel"])
router.include_router(attck.router, prefix="/attck", tags=["attck"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
router.include_router(schema.router, prefix="/schema", tags=["schema"])
router.include_router(mappings.router, prefix="/mappings", tags=["mappings"])
router.include_router(drift.router, prefix="/drift", tags=["drift"])
router.include_router(testlab.router, prefix="/testlab", tags=["testlab"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(health.router, tags=["health"])