import asyncio
from datetime import time
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.core.database import AsyncSessionLocal, Base
from app.models.location import Location
from app.models.barber import Barber
from app.models.service import Service
from app.models.schedule import WorkingSchedule

async def seed():
    session = AsyncSessionLocal()
    try:
        # 1. Location
        res = await session.execute(select(Location).limit(1))
        loc = res.scalars().first()
        if not loc:
            loc = Location(name="Tashkent City Shop", address="123 Amir Temur St", city="Tashkent")
            session.add(loc)
            await session.flush()
            print(f"Created location: {loc.name}")
        else:
            print(f"Using existing location: {loc.name}")

        # 2. Barbers
        res1 = await session.execute(select(Barber).where(Barber.telegram_id == 11111))
        b1 = res1.scalars().first()
        if not b1:
            b1 = Barber(
                location_id=loc.id,
                telegram_id=11111,
                full_name="Barber Bir (Dev Barber)",
                phone="+998901111111",
                bio="Professional sochlarni va soqollarni tekshirish ustasi.",
                is_active=True,
            )
            session.add(b1)
            await session.flush()
            print(f"Created Barber Bir: {b1.full_name}")
        else:
            print("Barber Bir already exists")

        res2 = await session.execute(select(Barber).where(Barber.telegram_id == 22222))
        b2 = res2.scalars().first()
        if not b2:
            b2 = Barber(
                location_id=loc.id,
                telegram_id=22222,
                full_name="Barber Ikki (Dev Barber)",
                phone="+998902222222",
                bio="Tajribali stilist.",
                is_active=True,
            )
            session.add(b2)
            await session.flush()
            print(f"Created Barber Ikki: {b2.full_name}")
        else:
            print("Barber Ikki already exists")

        # 3. Schedules
        for b in [b1, b2]:
            for weekday in range(7):
                stmt = (
                    pg_insert(WorkingSchedule)
                    .values(
                        barber_id=b.id,
                        weekday=weekday,
                        is_working=True,
                        start_time=time(9, 0),
                        end_time=time(18, 0),
                    )
                    .on_conflict_do_nothing(index_elements=["barber_id", "weekday"])
                )
                await session.execute(stmt)

        # 4. Services
        for b in [b1, b2]:
            res = await session.execute(select(Service).where(Service.barber_id == b.id))
            svcs = res.scalars().all()
            if not svcs:
                s1 = Service(
                    barber_id=b.id,
                    name="Soch olish",
                    price_uzs=50_000 if b.telegram_id == 11111 else 45_000,
                    duration_minutes=30,
                    is_active=True,
                )
                s2 = Service(
                    barber_id=b.id,
                    name="Soqol olish",
                    price_uzs=30_000,
                    duration_minutes=20,
                    is_active=True,
                )
                session.add_all([s1, s2])
                print(f"Added services for barber: {b.full_name}")

        await session.commit()
        print("Database seeding completed.")
    except Exception as e:
        await session.rollback()
        print(f"Seeding failed: {e}")
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(seed())
