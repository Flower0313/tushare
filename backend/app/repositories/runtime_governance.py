"""Compatibility exports for repositories split by runtime-governance bounded context.

Existing imports remain valid. New code should import the focused repository module.
"""

from app.domain.date_ranges import missing_ranges
from app.repositories.circuit_state import CircuitStateRepository
from app.repositories.legacy_staging import ReplaceDatasetRepository, StagingResourceRepository
from app.repositories.service_heartbeat import ServiceHeartbeatRepository
from app.repositories.trade_calendar_coverage import TradeCalendarCoverageRepository
from app.repositories.upstream_health import UpstreamRequestEventRepository

__all__ = [
    "CircuitStateRepository",
    "ReplaceDatasetRepository",
    "ServiceHeartbeatRepository",
    "StagingResourceRepository",
    "TradeCalendarCoverageRepository",
    "UpstreamRequestEventRepository",
    "missing_ranges",
]
