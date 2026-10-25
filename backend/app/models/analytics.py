from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalyticsDataset(Base):
    __tablename__ = "analytics_dataset"
    __table_args__ = {"schema": "platform"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    api_name: Mapped[str] = mapped_column(
        ForeignKey("platform.api_metadata.api_name", ondelete="RESTRICT"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(10), nullable=False, default="TABLE")
    sql_text: Mapped[str | None] = mapped_column(Text)
    sql_hash: Mapped[str | None] = mapped_column(String(64))
    parameters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="VALID")
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AnalyticsDashboard(Base):
    __tablename__ = "analytics_dashboard"
    __table_args__ = {"schema": "platform"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    global_filters: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    query_controls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AnalyticsChart(Base):
    __tablename__ = "analytics_chart"
    __table_args__ = {"schema": "platform"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("platform.analytics_dashboard.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("platform.analytics_dataset.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    chart_type: Mapped[str] = mapped_column(String(20), nullable=False)
    dimension: Mapped[str | None] = mapped_column(String(100))
    metric: Mapped[str | None] = mapped_column(String(100))
    aggregation: Mapped[str] = mapped_column(String(10), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grid_span: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    height_px: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=320)
    filters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    sort_by: Mapped[str] = mapped_column(String(20), nullable=False, default="metric")
    sort_desc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    date_granularity: Mapped[str | None] = mapped_column(String(10))
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def definition(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "dashboard_id": self.dashboard_id,
            "dataset_id": self.dataset_id,
            "title": self.title,
            "chart_type": self.chart_type,
            "dimension": self.dimension,
            "metric": self.metric,
            "aggregation": self.aggregation,
            "position": self.position,
            "grid_span": self.grid_span,
            "height_px": self.height_px,
            "filters": self.filters,
            "sort_by": self.sort_by,
            "sort_desc": self.sort_desc,
            "top_n": self.top_n,
            "date_granularity": self.date_granularity,
            "config_version": self.config_version,
            "config": self.config if self.config_version == 2 else None,
        }


class AnalyticsDashboardPublication(Base):
    __tablename__ = "analytics_dashboard_publication"
    __table_args__ = {"schema": "platform"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    dashboard_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform.analytics_dashboard.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    public_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnalyticsDashboardRevision(Base):
    __tablename__ = "analytics_dashboard_revision"
    __table_args__ = {"schema": "platform"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("platform.analytics_dashboard_publication.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
