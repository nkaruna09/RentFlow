import pytest
import sqlalchemy as sa

from app.api.deps import get_db
from app.db.base import Base
from app.db.session import async_session_factory


@pytest.mark.asyncio
async def test_async_session_factory_can_select_one():
    async with async_session_factory() as session:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar_one() == 1

    session_gen = get_db()
    session = await session_gen.__anext__()
    try:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar_one() == 1
    finally:
        await session_gen.aclose()

    assert Base.metadata is not None
