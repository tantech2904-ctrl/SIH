from pydantic import BaseModel


class AuditVerifyResponse(BaseModel):
    valid: bool
    checked: int
    chain_length: int
    first_broken_at: str | None = None
    broken_audit_id: str | None = None
    reason: str | None = None
    subreason: str | None = None
    detail: str | None = None
    verified_at: str