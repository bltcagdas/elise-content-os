import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

FIXED_LOCAL_DATE = __import__("datetime").date(2026, 5, 11)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def stable_dubai_day(monkeypatch):
    monkeypatch.setattr("app.services.planner.local_today", lambda: FIXED_LOCAL_DATE)
    monkeypatch.setattr("app.services.planner.is_sunday", lambda day=None: False)
    monkeypatch.setattr("app.services.memory.local_today", lambda: FIXED_LOCAL_DATE)
