
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_analyst
from app.core.rate_limit import limiter
from app.core.config import settings
from app.db.session import get_db
from app.enrichment.orchestrator import _default_providers
from app.enrichment.cache import get_cached
from app.models.enrichment import EnrichmentResult
from app.models.user import User

router = APIRouter()


def _classify(indicator: str) -> str:
    import ipaddress
    try:
        ipaddress.ip_address(indicator)
        return "ip"
    except ValueError:
        pass
    if "." in indicator and " " not in indicator and "/" not in indicator:
        return "domain"
    if len(indicator) in (32, 40, 64) and all(c in "0123456789abcdefABCDEF" for c in indicator):
        return "hash"
    if indicator.startswith("http://") or indicator.startswith("https://"):
        return "url"
    return "other"


@router.get("/{indicator}")
@limiter.limit(settings.RATE_LIMIT_ENRICH)
def lookup(
    request: Request,
    indicator: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    type_hint: str | None = Query(None, alias="type"),
):
    itype = type_hint or _classify(indicator)
    if itype == "other":
        raise HTTPException(status_code=400, detail="Could not determine indicator type")
    results = []
    for p in _default_providers():
        if itype not in p.indicator_types:
            continue
        cached = get_cached(db, provider=p.name, indicator=indicator, indicator_type=itype)
        if cached:
            results.append({**cached.to_dict(), "cached": True})
            continue
        res = p.safe_lookup(indicator, itype)
        results.append(res.to_dict())
    return {"indicator": indicator, "type": itype, "results": results}


@router.get("/history/{indicator}")
def history(indicator: str, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    rows = db.query(EnrichmentResult).filter(EnrichmentResult.indicator == indicator) \
        .order_by(desc(EnrichmentResult.created_at)).limit(50).all()
    return {"items": [{
        "provider": r.provider, "status": r.status, "result": r.result,
        "created_at": r.created_at.isoformat(), "latency_ms": r.latency_ms,
    } for r in rows]}