from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.analytics import AnalyticsDashboardPublication
from app.schemas.analytics import PublicationSettings, PublishedChart
from app.services.analytics_publication import _hash_password, publication_status, verify_password


def publication(settings: PublicationSettings) -> AnalyticsDashboardPublication:
    return AnalyticsDashboardPublication(
        dashboard_id=1,
        public_key="test",
        version=1,
        status="PUBLISHED",
        settings=settings.model_dump(mode="json"),
        published_at=datetime.now(UTC),
    )


def test_expired_publication_is_not_active():
    item = publication(
        PublicationSettings(
            name="测试",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    assert publication_status(item) == "EXPIRED"


def test_naive_expiry_is_normalized_to_utc():
    settings = PublicationSettings(name="测试", expires_at=datetime(2026, 10, 25))
    assert settings.expires_at.tzinfo == UTC


def test_access_password_is_salted_and_never_stored_as_plaintext():
    first, second = _hash_password("secret-password"), _hash_password("secret-password")
    assert first != second
    assert "secret-password" not in first
    assert verify_password("secret-password", first)
    assert not verify_password("wrong", first)


def test_password_change_flags_are_not_persisted_or_combined():
    settings = PublicationSettings(name="测试", remove_password=True)
    assert "remove_password" not in settings.model_dump(mode="json")
    assert "password" not in settings.model_dump(mode="json")
    with pytest.raises(ValidationError):
        PublicationSettings(name="测试", password="new-secret", remove_password=True)


def test_old_published_chart_without_layout_uses_compatible_defaults():
    chart = PublishedChart.model_validate(
        {
            "id": 1,
            "public_id": "legacy-chart",
            "dataset_id": 1,
            "title": "旧图表",
            "chart_type": "line",
        }
    )
    assert chart.grid_span == 1
    assert chart.height_px == 320
