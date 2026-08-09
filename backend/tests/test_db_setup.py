import sqlalchemy as sa
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.base import Base


@pytest.mark.asyncio
async def test_async_session_factory_can_select_one(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr("app.db.session.engine", engine)
    monkeypatch.setattr("app.db.session.async_session_factory", factory)

    async with factory() as session:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar_one() == 1

    assert callable(get_db)
    assert Base.metadata is not None
