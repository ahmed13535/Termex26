import asyncio
import aiosqlite
from config import DB_PATH, PROVINCES

async def fill_cities():
    async with aiosqlite.connect(DB_PATH) as db:
        # التأكد من وجود جدول cities
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_name TEXT,
                country TEXT,
                px INTEGER,
                py INTEGER,
                owner_id INTEGER DEFAULT 0,
                original_country TEXT,
                is_occupied INTEGER DEFAULT 0,
                occupation_progress REAL DEFAULT 0.0,
                occupied_by_id INTEGER DEFAULT 0,
                occupied_since INTEGER DEFAULT 0,
                merged INTEGER DEFAULT 0,
                resources TEXT,
                color_r INTEGER DEFAULT 180,
                color_g INTEGER DEFAULT 180,
                color_b INTEGER DEFAULT 180,
                UNIQUE(city_name, country)
            )
        """)
        # إضافة أعمدة الألوان إذا لم تكن موجودة
        for col in ["color_r", "color_g", "color_b"]:
            try:
                await db.execute(f"ALTER TABLE cities ADD COLUMN {col} INTEGER DEFAULT 180")
            except:
                pass
        # إدخال المدن من PROVINCES
        for country, cities in PROVINCES.items():
            for city, coords in cities.items():
                if coords["px"] == 0 and coords["py"] == 0:
                    continue
                await db.execute("""
                    INSERT OR IGNORE INTO cities (city_name, country, px, py, original_country, resources)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (city, country, coords["px"], coords["py"], country, '{"food":100,"gold":50000}'))
        await db.commit()
        print("✅ تم تعبئة المدن بنجاح!")

asyncio.run(fill_cities())
