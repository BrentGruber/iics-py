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
    agent_id: str | None = Field(None, alias="agentId")
    runtime_environment_id: str | None = Field(None, alias="runtimeEnvironmentId")
    instance_id: str | None = Field(None, alias="instanceId")
    host: str | None = None
    domain: str | None = None
    database: str | None = None
    client_code: str | None = Field(None, alias="clientCode")
    authentication_type: str | None = Field(None, alias="authenticationType")
    adjusted_jdbc_host_name: str | None = Field(None, alias="adjustedJdbcHostName")
    account_number: str | None = Field(None, alias="accountNumber")
    language_code: str | None = Field(None, alias="languageCode")
    remote_directory: str | None = Field(None, alias="remoteDirectory")
    schema: str | None = None
    service_url: str | None = Field(None, alias="serviceUrl")
    short_description: str | None = Field(None, alias="shortDescription")
    connection_type: str | None = Field(None, alias="type")
    port: int | None = None
    password: str | None = None
    username: str | None = None
    security_token: str | None = Field(None, alias="securityToken")
    sts_url: str | None = Field(None, alias="stsUrl")
    organization_name: str | None = Field(None, alias="organizationName")
    timeout: int | None = None
    trust_certificates_file: str | None = Field(None, alias="trustCertificatesFile")
    certificate_file: str | None = Field(None, alias="certificateFile")
    certificate_file_password: str | None = Field(None, alias="certificateFilePassword")
    certificate_file_type: str | None = Field(None, alias="certificateFileType")
    private_key_file: str | None = Field(None, alias="privateKeyFile")
    private_key_password: str | None = Field(None, alias="privateKeyPassword")
    private_key_file_type: str | None = Field(None, alias="privateKeyFileType")
    conn_params: dict[str, Any] | None = Field(None, alias="connParams")
    federated_id: str | None = Field(None, alias="federatedId")
    internal: bool | None = None
    retry_network_error: bool | None = Field(None, alias="retryNetworkError")
    supports_cci_multi_group: bool | None = Field(None, alias="supportsCCIMultiGroup")

    model_config = {"populate_by_name": True}
