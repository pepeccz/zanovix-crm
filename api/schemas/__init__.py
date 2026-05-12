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
from api.schemas.diagnostic import DiagnosticDimensions, DiagnosticPlanItem, DiagnosticRead
from api.schemas.lead import (
    LeadAssign,
    LeadCreate,
    LeadFilters,
    LeadListResponse,
    LeadRead,
    LeadStatusUpdate,
)
from api.schemas.message import MessageCreate, MessageListResponse, MessageOut
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
from api.schemas.ticket import TicketCreate, TicketListResponse, TicketOut, TicketPatch

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
    # Diagnostic
    "DiagnosticDimensions",
    "DiagnosticPlanItem",
    "DiagnosticRead",
    # Lead (existing)
    "LeadCreate",
    "LeadStatusUpdate",
    "LeadAssign",
    "LeadFilters",
    "LeadRead",
    "LeadListResponse",
    # Message
    "MessageCreate",
    "MessageOut",
    "MessageListResponse",
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
    # Ticket
    "TicketCreate",
    "TicketPatch",
    "TicketOut",
    "TicketListResponse",
]
