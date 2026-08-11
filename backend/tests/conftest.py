from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core import database
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, Base
from app.main import app
from app.models.barber import Barber
from app.models.location import Location
from sqlalchemy.pool import NullPool

settings = get_settings()
test_database_url = settings.TEST_DATABASE_URL
test_database_name = make_url(test_database_url).database

if (
    test_database_name != settings.TEST_POSTGRES_DB
    or test_database_name == settings.POSTGRES_DB
    or not test_database_name.endswith(("_test", "_test_db"))
):
    raise RuntimeError(
        "Tests require a dedicated database whose name ends in '_test' or "
        "'_test_db' and is different from POSTGRES_DB."
    )

# Re-create the engine for the dedicated test database. NullPool prevents
# connections from crossing pytest event-loop boundaries.
test_engine = create_async_engine(
    test_database_url,
    echo=settings.DEBUG,
    poolclass=NullPool,
)
database.engine = test_engine
AsyncSessionLocal.configure(bind=test_engine)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables in the test database at session startup."""
    # Ensure a clean state by dropping and recreating all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session and roll back any changes made during the test."""
    from app.core.database import get_db  # noqa: PLC0415
    async with AsyncSessionLocal() as session:
        # Override FastAPI dependency
        async def _get_db() -> AsyncGenerator[AsyncSession, None]:
            yield session

        app.dependency_overrides[get_db] = _get_db
        try:
            yield session
        finally:
            await session.rollback()
            app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def test_location(db_session: AsyncSession) -> Location:
    """Create a test location in the database."""
    loc = Location(name="Test City Shop", address="123 Tashkent St", city="Tashkent")
    db_session.add(loc)
    await db_session.flush()
    return loc


@pytest_asyncio.fixture
async def barber1(db_session: AsyncSession, test_location: Location) -> Barber:
    """Create first test barber."""
    b = Barber(
        location_id=test_location.id,
        telegram_id=11111,
        full_name="Barber Bir",
        phone="+998901111111",
        bio="Senior stylist 1",
        is_active=True,
    )
    db_session.add(b)
    await db_session.flush()
    return b


@pytest_asyncio.fixture
async def barber2(db_session: AsyncSession, test_location: Location) -> Barber:
    """Create second test barber."""
    b = Barber(
        location_id=test_location.id,
        telegram_id=22222,
        full_name="Barber Ikki",
        phone="+998902222222",
        bio="Senior stylist 2",
        is_active=True,
    )
    db_session.add(b)
    await db_session.flush()
    return b


@pytest_asyncio.fixture
async def client_anon() -> AsyncGenerator[AsyncClient, None]:
    """Client with no authentication headers."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_b1(barber1: Barber) -> AsyncGenerator[AsyncClient, None]:
    """Client authenticated as Barber 1 (telegram_id 11111)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 11111"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_b2(barber2: Barber) -> AsyncGenerator[AsyncClient, None]:
    """Client authenticated as Barber 2 (telegram_id 22222)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 22222"},
    ) as client:
        yield client
