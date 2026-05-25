import aiosqlite
import json
import time
from config import DB_PATH, COUNTRIES, PROVINCES

# ======================== تهيئة قاعدة البيانات ========================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            country TEXT UNIQUE,
            capital TEXT,
            flag TEXT,
            gold REAL DEFAULT 50000000,
            food INTEGER DEFAULT 10000,
            energy INTEGER DEFAULT 5000,
            soldiers INTEGER DEFAULT 10000,
            tanks INTEGER DEFAULT 0,
            artillery INTEGER DEFAULT 0,
            aircraft INTEGER DEFAULT 0,
            missiles INTEGER DEFAULT 0,
            air_defense INTEGER DEFAULT 0,
            carriers INTEGER DEFAULT 0,
            submarines INTEGER DEFAULT 0,
            bio_weapons INTEGER DEFAULT 0,
            nukes INTEGER DEFAULT 0,
            damage_bonus REAL DEFAULT 1.0,
            defense_bonus REAL DEFAULT 1.0,
            morale INTEGER DEFAULT 100,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            prestige INTEGER DEFAULT 0,
            is_frozen INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0,
            last_active INTEGER DEFAULT 0,
            color_r INTEGER DEFAULT 180,
            color_g INTEGER DEFAULT 180,
            color_b INTEGER DEFAULT 180
        );
        CREATE TABLE IF NOT EXISTS map_cells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT,
            owner TEXT,
            original_owner TEXT,
            is_occupied INTEGER DEFAULT 0,
            color_r INTEGER DEFAULT 180,
            color_g INTEGER DEFAULT 180,
            color_b INTEGER DEFAULT 180
        );
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            building_type TEXT,
            level INTEGER DEFAULT 1,
            built_at INTEGER DEFAULT 0,
            UNIQUE(user_id, building_type)
        );
        CREATE TABLE IF NOT EXISTS wars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            attacker_country TEXT,
            defender_country TEXT,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            winner_id INTEGER DEFAULT 0,
            occupation_progress REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS cooldowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            expires_at INTEGER,
            UNIQUE(user_id, action)
        );
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_id INTEGER,
            details TEXT,
            timestamp INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS straits (
            name TEXT PRIMARY KEY,
            controller_id INTEGER DEFAULT 0,
            blocked INTEGER DEFAULT 0,
            blocked_until INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS alliances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            leader_id INTEGER,
            members TEXT DEFAULT '[]',
            flag_file_id TEXT,
            created_at INTEGER DEFAULT 0,
            treaty TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS intel_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER,
            target_id INTEGER,
            operation_type TEXT,
            success INTEGER DEFAULT 0,
            detected INTEGER DEFAULT 0,
            executed_at INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS nuclear_projects (
            user_id INTEGER PRIMARY KEY,
            atomic_cycles INTEGER DEFAULT 0,
            hydrogen_cycles INTEGER DEFAULT 0,
            atomic_completed INTEGER DEFAULT 0,
            hydrogen_completed INTEGER DEFAULT 0,
            last_update INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS bio_projects (
            user_id INTEGER PRIMARY KEY,
            bio_cycles INTEGER DEFAULT 0,
            toxin_cycles INTEGER DEFAULT 0,
            bio_completed INTEGER DEFAULT 0,
            toxin_completed INTEGER DEFAULT 0,
            last_update INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT UNIQUE,
            current_price REAL DEFAULT 100.0,
            last_update INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS user_stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            resource_name TEXT,
            quantity INTEGER DEFAULT 0,
            UNIQUE(user_id, resource_name)
        );
        CREATE TABLE IF NOT EXISTS disaster_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT,
            affected_country TEXT,
            effect TEXT,
            timestamp INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS crops (
            crop_name TEXT PRIMARY KEY,
            base_price REAL,
            growth_hours INTEGER,
            emoji TEXT
        );
        CREATE TABLE IF NOT EXISTS user_crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            crop_name TEXT,
            quantity INTEGER DEFAULT 0,
            last_harvest INTEGER DEFAULT 0,
            UNIQUE(user_id, crop_name)
        );
        CREATE TABLE IF NOT EXISTS infrastructure (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            food_capacity INTEGER DEFAULT 10000,
            energy_capacity INTEGER DEFAULT 5000,
            army_capacity INTEGER DEFAULT 20000,
            upgrade_cost REAL DEFAULT 1000000
        );
        CREATE TABLE IF NOT EXISTS occupied_territories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            territory_name TEXT,
            occupied_by INTEGER,
            original_owner TEXT,
            occupied_at INTEGER,
            merge_ready_at INTEGER,
            is_merged INTEGER DEFAULT 0,
            resources TEXT,
            UNIQUE(territory_name)
        );
        CREATE TABLE IF NOT EXISTS colonies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colony_name TEXT,
            colonizer_id INTEGER,
            original_owner_id INTEGER,
            colonized_at INTEGER,
            last_harvest_at INTEGER,
            daily_income REAL DEFAULT 0,
            UNIQUE(colony_name)
        );
        CREATE TABLE IF NOT EXISTS harvest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            harvested_at INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS active_groups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            activated_at INTEGER DEFAULT 0,
            announcements_topic_id INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS punishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            reason TEXT,
            expires_at INTEGER,
            issued_by INTEGER,
            issued_at INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS game_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
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
        );
        """)
        await db.commit()
        await init_cities()
        await init_stocks()
        await init_crops()
        await migrate_db()

async def init_cities():
    """إدخال جميع المدن من PROVINCES إلى قاعدة البيانات"""
    async with aiosqlite.connect(DB_PATH) as db:
        for country, cities in PROVINCES.items():
            for city_name, coords in cities.items():
                if coords["px"] == 0 and coords["py"] == 0:
                    continue
                await db.execute("""
                    INSERT OR IGNORE INTO cities (city_name, country, px, py, original_country, resources)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (city_name, country, coords["px"], coords["py"], country, json.dumps({"food":100, "gold":50000})))
        await db.commit()

async def init_stocks():
    async with aiosqlite.connect(DB_PATH) as db:
        resources = ["قمح", "ذهب", "نفط", "حديد", "خشب", "قهوة", "شاي"]
        for res in resources:
            await db.execute("INSERT OR IGNORE INTO stocks (resource_name, current_price, last_update) VALUES (?, 100.0, ?)", (res, int(time.time())))
        await db.commit()

async def init_crops():
    async with aiosqlite.connect(DB_PATH) as db:
        crops = [
            ("قمح", 500, 2, "🌾"), ("أرز", 600, 3, "🍚"), ("بطاطا", 400, 2, "🥔"),
            ("قهوة", 1200, 6, "☕"), ("شاي", 800, 4, "🍃"), ("طماطم", 300, 1, "🍅"),
            ("ذرة", 450, 2, "🌽"), ("زيتون", 700, 5, "🫒")
        ]
        for crop in crops:
            await db.execute("INSERT OR IGNORE INTO crops (crop_name, base_price, growth_hours, emoji) VALUES (?, ?, ?, ?)", crop)
        await db.commit()

async def migrate_db():
    """ترحيل قاعدة البيانات: إضافة الأعمدة المفقودة"""
    async with aiosqlite.connect(DB_PATH) as db:
        # إضافة أعمدة الألوان إلى users إن لم تكن موجودة
        for col in ["color_r", "color_g", "color_b"]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 180")
            except:
                pass
        # إضافة أعمدة الألوان إلى cities إن لم تكن موجودة
        for col in ["color_r", "color_g", "color_b"]:
            try:
                await db.execute(f"ALTER TABLE cities ADD COLUMN {col} INTEGER DEFAULT 180")
            except:
                pass
        # إضافة أعمدة أخرى قد تكون مفقودة
        try:
            await db.execute("ALTER TABLE users ADD COLUMN gov_system TEXT DEFAULT 'جمهورية'")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN religion TEXT DEFAULT 'إسلام'")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN intel_level INTEGER DEFAULT 0")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN intel_exp INTEGER DEFAULT 0")
        except: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN fortify_level INTEGER DEFAULT 0")
        except: pass
        await db.commit()

# ======================== دوال المستخدم الأساسية ========================
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_user_by_country(country: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE country=?", (country,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def create_user(user_id: int, username: str, country: str, capital: str, flag: str):
    info = COUNTRIES.get(country, {})
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, country, capital, flag, created_at, last_active, color_r, color_g, color_b)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, country, capital, flag, int(time.time()), int(time.time()),
              info.get("color", (180,180,180))[0], info.get("color", (180,180,180))[1], info.get("color", (180,180,180))[2]))
        await db.execute("INSERT OR IGNORE INTO infrastructure (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM buildings WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM cooldowns WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM wars WHERE attacker_id=? OR defender_id=?", (user_id, user_id))
        await db.commit()

async def freeze_user(user_id: int, freeze: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_frozen=? WHERE user_id=?", (1 if freeze else 0, user_id))
        await db.commit()

async def update_user(user_id: int, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE user_id=?", vals)
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_banned=0") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_gold(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET gold=gold+? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def deduct_gold(user_id: int, amount: float) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT gold FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row or row[0] < amount: return False
        await db.execute("UPDATE users SET gold=gold-? WHERE user_id=?", (amount, user_id))
        await db.commit()
        return True

async def get_cooldown(user_id: int, action: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT expires_at FROM cooldowns WHERE user_id=? AND action=?", (user_id, action)) as cur:
            row = await cur.fetchone()
            if not row: return 0
            return max(0, row[0] - int(time.time()))

async def set_cooldown(user_id: int, action: str, seconds: int):
    expires = int(time.time()) + seconds
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO cooldowns (user_id, action, expires_at) VALUES (?,?,?)", (user_id, action, expires))
        await db.commit()

async def get_buildings(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM buildings WHERE user_id=?", (user_id,)) as cur:
            rows = await cur.fetchall()
            return {r["building_type"]: dict(r) for r in rows}

async def add_building(user_id: int, building: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT level FROM buildings WHERE user_id=? AND building_type=?", (user_id, building)) as cur:
            row = await cur.fetchone()
        if row:
            await db.execute("UPDATE buildings SET level=level+1 WHERE user_id=? AND building_type=?", (user_id, building))
        else:
            await db.execute("INSERT INTO buildings (user_id, building_type, built_at) VALUES (?,?,?)", (user_id, building, int(time.time())))
        await db.commit()

# ======================== دوال المدن والاحتلال ========================
async def get_city(city_name: str, country: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if country:
            query = "SELECT * FROM cities WHERE city_name=? AND country=?"
            params = (city_name, country)
        else:
            query = "SELECT * FROM cities WHERE city_name=?"
            params = (city_name,)
        async with db.execute(query, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_cities_by_country(country: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM cities WHERE country=?", (country,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def occupy_city(city_name: str, country: str, occupier_id: int, progress: float = 100.0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE cities SET 
                owner_id=?, is_occupied=1, occupation_progress=?, 
                occupied_by_id=?, occupied_since=?, merged=0
            WHERE city_name=? AND country=?
        """, (occupier_id, progress, occupier_id, int(time.time()), city_name, country))
        await db.commit()

async def update_occupation_progress(city_name: str, country: str, progress: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cities SET occupation_progress=?, is_occupied=1 WHERE city_name=? AND country=?", (progress, city_name, country))
        await db.commit()

async def get_all_provinces():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                c.id, c.city_name, c.country, c.px, c.py,
                c.owner_id, c.is_occupied, c.occupation_progress, c.merged,
                c.color_r, c.color_g, c.color_b,
                u.user_id, u.country as owner_country, u.flag as owner_flag
            FROM cities c
            LEFT JOIN users u ON c.owner_id = u.user_id
            ORDER BY c.country, c.city_name
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

# ======================== دوال الحرب والأحلاف ========================
async def get_active_war(attacker_id: int, defender_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM wars WHERE status='active' AND (
                (attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)
            )
        """, (attacker_id, defender_id, defender_id, attacker_id)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def create_war(attacker_id, defender_id, attacker_country, defender_country):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO wars (attacker_id, defender_id, attacker_country, defender_country, started_at) VALUES (?,?,?,?,?)", (attacker_id, defender_id, attacker_country, defender_country, int(time.time())))
        await db.commit()

async def end_war(war_id, winner_id=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE wars SET status='ended', ended_at=?, winner_id=? WHERE id=?", (int(time.time()), winner_id, war_id))
        await db.commit()

async def get_wars_for_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM wars WHERE (attacker_id=? OR defender_id=?) AND status='active'", (user_id, user_id)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

# ======================== دوال الأحلاف ========================
async def create_alliance(name, leader_id, flag_file_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO alliances (name, leader_id, members, flag_file_id, created_at) VALUES (?,?,?,?,?)", (name, leader_id, json.dumps([leader_id]), flag_file_id, int(time.time())))
        await db.commit()

async def get_alliance_by_name(name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM alliances WHERE name=?", (name,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_alliance_by_member(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM alliances") as cur:
            rows = await cur.fetchall()
            for row in rows:
                members = json.loads(row["members"])
                if user_id in members or row["leader_id"] == user_id:
                    return dict(row)
        return None

async def get_alliance(user_id):
    return await get_alliance_by_member(user_id)

async def add_member_to_alliance(alliance_name, user_id):
    alliance = await get_alliance_by_name(alliance_name)
    if not alliance: return False
    members = json.loads(alliance["members"])
    if user_id in members: return False
    members.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE alliances SET members=? WHERE name=?", (json.dumps(members), alliance_name))
        await db.commit()
    return True

async def remove_member_from_alliance(alliance_name, user_id):
    alliance = await get_alliance_by_name(alliance_name)
    if not alliance: return False
    members = json.loads(alliance["members"])
    if user_id not in members: return False
    members.remove(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE alliances SET members=? WHERE name=?", (json.dumps(members), alliance_name))
        await db.commit()
    return True

async def delete_alliance(alliance_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM alliances WHERE name=?", (alliance_name,))
        await db.commit()

async def join_alliance(alliance_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name, members FROM alliances WHERE id=?", (alliance_id,)) as cur:
            row = await cur.fetchone()
            if not row: return False
            name, members_json = row
            members = json.loads(members_json)
            if user_id in members: return False
            members.append(user_id)
            await db.execute("UPDATE alliances SET members=? WHERE id=?", (json.dumps(members), alliance_id))
            await db.commit()
            return True

# ======================== دوال المضائق ========================
async def get_strait(name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM straits WHERE name=?", (name,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def set_strait(name, controller_id, blocked, duration=0):
    blocked_until = int(time.time()) + duration if blocked else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO straits (name, controller_id, blocked, blocked_until) VALUES (?,?,?,?)", (name, controller_id, int(blocked), blocked_until))
        await db.commit()

# ======================== دوال المشروع النووي والبيولوجي ========================
async def get_nuclear_project(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM nuclear_projects WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO nuclear_projects (user_id, last_update) VALUES (?, ?)", (user_id, int(time.time())))
                await db.commit()
                return {"user_id": user_id, "atomic_cycles": 0, "hydrogen_cycles": 0, "atomic_completed": 0, "hydrogen_completed": 0, "last_update": int(time.time())}
            return dict(row)

async def update_nuclear_project(user_id, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE nuclear_projects SET {sets} WHERE user_id=?", vals)
        await db.commit()

async def get_bio_project(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bio_projects WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO bio_projects (user_id, last_update) VALUES (?, ?)", (user_id, int(time.time())))
                await db.commit()
                return {"user_id": user_id, "bio_cycles": 0, "toxin_cycles": 0, "bio_completed": 0, "toxin_completed": 0, "last_update": int(time.time())}
            return dict(row)

async def update_bio_project(user_id, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bio_projects SET {sets} WHERE user_id=?", vals)
        await db.commit()

# ======================== دوال المخابرات ========================
async def log_intel_operation(operator_id, target_id, op_type, success, detected):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO intel_operations (operator_id, target_id, operation_type, success, detected, executed_at)
            VALUES (?,?,?,?,?,?)
        """, (operator_id, target_id, op_type, 1 if success else 0, 1 if detected else 0, int(time.time())))
        await db.commit()

# ======================== دوال البورصة ========================
async def get_all_stocks():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM stocks") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def update_stock_price(resource, new_price):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE stocks SET current_price=?, last_update=? WHERE resource_name=?", (new_price, int(time.time()), resource))
        await db.commit()

async def get_user_stocks(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_stocks WHERE user_id=?", (user_id,)) as cur:
            rows = await cur.fetchall()
            return {r["resource_name"]: dict(r) for r in rows}

async def add_stock(user_id, resource, quantity):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_stocks (user_id, resource_name, quantity)
            VALUES (?, ?, COALESCE((SELECT quantity FROM user_stocks WHERE user_id=? AND resource_name=?), 0) + ?)
        """, (user_id, resource, user_id, resource, quantity))
        await db.commit()

async def remove_stock(user_id, resource, quantity):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantity FROM user_stocks WHERE user_id=? AND resource_name=?", (user_id, resource)) as cur:
            row = await cur.fetchone()
            if not row or row[0] < quantity: return False
        new_qty = row[0] - quantity
        if new_qty == 0:
            await db.execute("DELETE FROM user_stocks WHERE user_id=? AND resource_name=?", (user_id, resource))
        else:
            await db.execute("UPDATE user_stocks SET quantity=? WHERE user_id=? AND resource_name=?", (new_qty, user_id, resource))
        await db.commit()
        return True

# ======================== دوال الكوارث ========================
async def log_disaster(disaster_type, country, effect):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO disaster_log (disaster_type, affected_country, effect, timestamp) VALUES (?,?,?,?)", (disaster_type, country, effect, int(time.time())))
        await db.commit()

# ======================== دوال المتجر المتقدم ========================
async def get_all_crops():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crops") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_user_crops(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_crops WHERE user_id=?", (user_id,)) as cur:
            rows = await cur.fetchall()
            return {r["crop_name"]: dict(r) for r in rows}

async def add_crop_to_user(user_id, crop_name, quantity):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_crops (user_id, crop_name, quantity, last_harvest)
            VALUES (?, ?, COALESCE((SELECT quantity FROM user_crops WHERE user_id=? AND crop_name=?), 0) + ?, ?)
        """, (user_id, crop_name, user_id, crop_name, quantity, int(time.time())))
        await db.commit()

async def update_crop_harvest(user_id, crop_name, new_harvest_time):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_crops SET last_harvest=? WHERE user_id=? AND crop_name=?", (new_harvest_time, user_id, crop_name))
        await db.commit()

# ======================== دوال البنية التحتية ========================
async def get_infrastructure(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM infrastructure WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO infrastructure (user_id) VALUES (?)", (user_id,))
                await db.commit()
                return {"user_id": user_id, "level": 1, "food_capacity": 10000, "energy_capacity": 5000, "army_capacity": 20000, "upgrade_cost": 1000000}
            return dict(row)

async def upgrade_infrastructure(user_id):
    inf = await get_infrastructure(user_id)
    new_level = inf["level"] + 1
    new_food_cap = inf["food_capacity"] + 5000
    new_energy_cap = inf["energy_capacity"] + 2500
    new_army_cap = inf["army_capacity"] + 10000
    new_cost = inf["upgrade_cost"] * 1.5
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE infrastructure SET level=?, food_capacity=?, energy_capacity=?, army_capacity=?, upgrade_cost=?
            WHERE user_id=?
        """, (new_level, new_food_cap, new_energy_cap, new_army_cap, new_cost, user_id))
        await db.commit()
    return new_level

# ======================== دوال الغزو والاستعمار ========================
async def add_occupied_territory(territory, user_id, original_owner, resources, cooldown_seconds=3600):
    merge_ready = int(time.time()) + cooldown_seconds
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO occupied_territories 
            (territory_name, occupied_by, original_owner, occupied_at, merge_ready_at, resources)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (territory, user_id, original_owner, int(time.time()), merge_ready, json.dumps(resources)))
        await db.commit()

async def get_occupied_territory(territory):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM occupied_territories WHERE territory_name=?", (territory,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_user_occupied_territories(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM occupied_territories WHERE occupied_by=? AND is_merged=0", (user_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def merge_territory(territory):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE occupied_territories SET is_merged=1 WHERE territory_name=?", (territory,))
        await db.commit()

async def add_colony(colony_name, colonizer_id, original_owner_id, daily_income):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO colonies (colony_name, colonizer_id, original_owner_id, colonized_at, last_harvest_at, daily_income)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (colony_name, colonizer_id, original_owner_id, int(time.time()), int(time.time()), daily_income))
        await db.commit()

async def get_colonies(colonizer_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM colonies WHERE colonizer_id=?", (colonizer_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_colony_by_name(colony_name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM colonies WHERE colony_name=?", (colony_name,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def delete_colony(colony_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM colonies WHERE colony_name=?", (colony_name,))
        await db.commit()

async def update_colony_harvest(colony_name, new_last_harvest):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE colonies SET last_harvest_at=? WHERE colony_name=?", (new_last_harvest, colony_name))
        await db.commit()

async def record_harvest(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO harvest_log (user_id, amount, harvested_at) VALUES (?, ?, ?)", (user_id, amount, int(time.time())))
        await db.commit()

# ======================== دوال إدارة الجروبات والعقوبات ========================
async def add_active_group(group_id, group_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO active_groups (group_id, group_name, activated_at) VALUES (?, ?, ?)", (group_id, group_name, int(time.time())))
        await db.commit()

async def remove_active_group(group_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_groups WHERE group_id=?", (group_id,))
        await db.commit()

async def get_all_groups():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM active_groups") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def set_announcements_topic(group_id, topic_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE active_groups SET announcements_topic_id=? WHERE group_id=?", (topic_id, group_id))
        await db.commit()

async def add_ban(user_id, duration_hours, admin_id, reason=""):
    expires = int(time.time()) + (duration_hours * 3600) if duration_hours > 0 else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO punishments (user_id, type, reason, expires_at, issued_by, issued_at)
            VALUES (?,?,?,?,?,?)
        """, (user_id, 'ban', reason, expires, admin_id, int(time.time())))
        await db.commit()
        if duration_hours > 0:
            await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        else:
            await db.execute("UPDATE users SET is_banned=1, is_frozen=1 WHERE user_id=?", (user_id,))
        await db.commit()

async def remove_ban(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM punishments WHERE user_id=? AND type='ban'", (user_id,))
        await db.execute("UPDATE users SET is_banned=0, is_frozen=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def add_stigma(user_id, text, admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO punishments (user_id, type, reason, issued_by, issued_at) VALUES (?,?,?,?,?)", (user_id, 'stigma', text, admin_id, int(time.time())))
        await db.commit()

async def remove_stigma(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM punishments WHERE user_id=? AND type='stigma'", (user_id,))
        await db.commit()

async def get_stigma(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT reason FROM punishments WHERE user_id=? AND type='stigma' ORDER BY issued_at DESC LIMIT 1", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# ======================== دوال إعدادات اللعبة ========================
async def set_game_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO game_settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()

async def get_game_setting(key, default="0"):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM game_settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

# ======================== دوال الأدمن والإحصائيات ========================
async def log_admin(admin_id, action, target_id, details):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO admin_logs (admin_id, action, target_id, details, timestamp) VALUES (?,?,?,?,?)", (admin_id, action, target_id, details, int(time.time())))
        await db.commit()

async def get_leaderboard():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT country, flag, gold, soldiers, prestige, xp, level
            FROM users WHERE is_banned=0 ORDER BY prestige DESC, gold DESC LIMIT 15
        """) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def update_occupation(country, owner, progress, color):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE map_cells SET owner=?, is_occupied=1, color_r=?, color_g=?, color_b=?
            WHERE country=?
        """, (owner, color[0], color[1], color[2], country))
        await db.commit()

async def get_map_cells():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM map_cells") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

# ======================== دوال النسخ الاحتياطي ========================
async def backup_game_to_json():
    tables = ["users", "buildings", "wars", "alliances", "map_cells", "straits", "cities", "colonies", "occupied_territories", "stocks", "user_stocks", "crops", "user_crops", "infrastructure", "nuclear_projects", "bio_projects", "intel_operations", "disaster_log", "active_groups", "punishments", "game_settings"]
    backup = {}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for table in tables:
            try:
                async with db.execute(f"SELECT * FROM {table}") as cur:
                    rows = await cur.fetchall()
                    backup[table] = [dict(r) for r in rows]
            except:
                backup[table] = []
    return json.dumps(backup, indent=2, default=str)

async def restore_game_from_json(json_data):
    data = json.loads(json_data)
    async with aiosqlite.connect(DB_PATH) as db:
        for table, rows in data.items():
            if rows:
                try:
                    await db.execute(f"DELETE FROM {table}")
                    for row in rows:
                        columns = ", ".join(row.keys())
                        placeholders = ", ".join(["?"] * len(row))
                        await db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(row.values()))
                except:
                    pass
        await db.commit()
