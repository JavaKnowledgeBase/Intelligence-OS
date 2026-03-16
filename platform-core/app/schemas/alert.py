from pydantic import BaseModel, Field


class AlertPreference(BaseModel):
    """Notification rule returned to the frontend alert center."""

    id: str
    name: str
    channel: str
    trigger: str
    enabled: bool
    scope: str = "tenant"
    severity: str = "medium"


class AlertPreferenceCreate(BaseModel):
    """Payload for creating a new alert rule."""

    name: str = Field(min_length=3)
    channel: str
    trigger: str = Field(min_length=3)
    enabled: bool = True
    scope: str = "tenant"
    severity: str = "medium"
