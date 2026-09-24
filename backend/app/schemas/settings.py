from pydantic import BaseModel


class SettingsItem(BaseModel):
    key: str
    label: str
    type: str
    sensitive: bool
    requires_restart: bool
    description: str
    value: str
    is_set: bool


class SettingsGroup(BaseModel):
    name: str
    items: list[SettingsItem]


class SettingsListResponse(BaseModel):
    groups: list[SettingsGroup]
    env_file: str
    masked_sentinel: str


class SettingsUpdateRequest(BaseModel):
    updates: dict[str, str]


class SettingsUpdateResponse(BaseModel):
    updated: list[str]
    rejected: list[dict]
    requires_restart: list[str]
    restart_required: bool
    audit_id: str | None = None


class RestartResponse(BaseModel):
    restarted: bool
    mode: str
    message: str