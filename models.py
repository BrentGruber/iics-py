"""Pydantic models for the IICS REST API"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# -- Authentication ------------------------------------


class SessionInfo(BaseModel):
    """Holds active session detailsf or reuse across requests"""

    user_id: str = Field(..., alias="id")
    name: str = Field(..., alias="name")
    org_id: str = Field(..., alias="orgId")
    org_name: str | None = Field(None, alias="orgName")
    server_url: str = Field(..., alias="serverUrl")
    session_id: str = Field(..., alias="icSessionId")
    # The serverUrl becomes the base URL for all subsequent API calls

    model_config = {"populate_by_name": True}


# -- Connections ---------------------------------------


class Connection(BaseModel):
    """Represents a connection in IICS"""

    id: str
    org_id: str = Field(..., alias="orgId")
    name: str = Field(..., alias="name")
    description: str | None = None
    create_time: datetime | None = Field(None, alias="createTime")
    update_time: datetime | None = Field(None, alias="updateTime")
    created_by: str | None = Field(None, alias="createdBy")
    updated_by: str | None = Field(None, alias="updatedBy")

    model_config = {"populate_by_name": True}
