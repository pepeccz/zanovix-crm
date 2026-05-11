"""
Pydantic schema re-exports.

Import from here to avoid deep sub-module imports across the codebase.
"""

from api.schemas.activity_log import ActivityLogListResponse, ActivityLogRead
from api.schemas.client import (
    ClientCreate,
    ClientDetailResponse,
    ClientFilters,
    ClientListResponse,
    ClientRead,
    ClientStageChange,
    ClientUpdate,
)
from api.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from api.schemas.convert_lead import ConvertLeadBody
from api.schemas.lead import (
    LeadAssign,
    LeadCreate,
    LeadFilters,
    LeadListResponse,
    LeadRead,
    LeadStatusUpdate,
)
from api.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from api.schemas.service import (
    ServiceCreate,
    ServiceFilters,
    ServiceListResponse,
    ServiceRead,
    ServiceStateChange,
    ServiceStub,
    ServiceUpdate,
)

__all__ = [
    # Activity log
    "ActivityLogRead",
    "ActivityLogListResponse",
    # Client
    "ClientCreate",
    "ClientUpdate",
    "ClientRead",
    "ClientDetailResponse",
    "ClientListResponse",
    "ClientFilters",
    "ClientStageChange",
    # Contact
    "ContactCreate",
    "ContactUpdate",
    "ContactRead",
    # Convert lead
    "ConvertLeadBody",
    # Lead (existing)
    "LeadCreate",
    "LeadStatusUpdate",
    "LeadAssign",
    "LeadFilters",
    "LeadRead",
    "LeadListResponse",
    # Milestone
    "MilestoneCreate",
    "MilestoneUpdate",
    "MilestoneRead",
    # Service
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceRead",
    "ServiceStub",
    "ServiceListResponse",
    "ServiceFilters",
    "ServiceStateChange",
]
