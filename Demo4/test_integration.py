import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Alert
from priority_score import calculate_priority_score


@pytest.fixture
def test_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    original_overrides = app.dependency_overrides.copy()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        engine.dispose()


def test_alert_priority_matches_calculated_score(test_context):
    client, session_factory = test_context
    with session_factory() as session:
        alert = Alert(severity="critical", metric_value=15, threshold=10)
        session.add(alert)
        session.commit()
        session.refresh(alert)

        expected = {
            "alert_id": alert.id,
            "priority_score": calculate_priority_score(
                alert.severity,
                alert.metric_value,
                alert.threshold,
            ),
        }

    response = client.get(f"/alerts/{expected['alert_id']}/priority")

    assert response.status_code == 200
    assert response.json() == expected


def test_nonexistent_alert_returns_404(test_context):
    client, _ = test_context

    response = client.get("/alerts/999999/priority")

    assert response.status_code == 404


# --- Edge case added manually ---
def test_zero_threshold_alert_returns_422(test_context):
    client, session_factory = test_context
    with session_factory() as db:
        alert = Alert(severity="warning", metric_value=50, threshold=0)
        db.add(alert)
        db.commit()
        alert_id = alert.id
    response = client.get(f"/alerts/{alert_id}/priority")
    assert response.status_code == 422
    assert "threshold must not be zero" in response.json()["detail"]