import aiosqlite
import random

DB = "dating.db"

# ---------- INIT ----------

async def init_db():
    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS profiles(
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age TEXT,
            gender TEXT,
            height TEXT,
            bio TEXT,
            photo TEXT,
            username TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS likes(
            from_id INTEGER,
            to_id INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bans(
            user_id INTEGER PRIMARY KEY,
            reason TEXT
        )
        """)

        await db.commit()


# ---------- ПРОФІЛІ ----------

async def save_profile(data):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "REPLACE INTO profiles VALUES (?,?,?,?,?,?,?,?)",
            data
        )
        await db.commit()


async def get_profile(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT * FROM profiles WHERE user_id=?",
            (uid,)
        )
        return await cur.fetchone()


async def get_all_profiles():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT * FROM profiles")
        return await cur.fetchall()


async def delete_profile(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "DELETE FROM profiles WHERE user_id=?",
            (uid,)
        )

        await db.execute(
            "DELETE FROM likes WHERE from_id=? OR to_id=?",
            (uid, uid)
        )

        await db.execute(
            "DELETE FROM bans WHERE user_id=?",
            (uid,)
        )

        await db.commit()


# ---------- ПОШУК ----------

async def random_profile(gender, my_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT * FROM profiles
        WHERE gender=? AND user_id!=?
        """, (gender, my_id))

        rows = await cur.fetchall()
        return random.choice(rows) if rows else None


# ---------- ЛАЙКИ ----------

async def add_like(from_id, to_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO likes VALUES (?,?)",
            (from_id, to_id)
        )
        await db.commit()


async def is_mutual(a, b):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT 1 FROM likes
        WHERE from_id=? AND to_id=?
        """, (b, a))

        return await cur.fetchone() is not None


# ---------- КІЛЬКІСТЬ МАТЧІВ ----------

async def get_matches_count():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT COUNT(*) FROM likes l1
        JOIN likes l2
        ON l1.from_id = l2.to_id
        AND l1.to_id = l2.from_id
        WHERE l1.from_id < l1.to_id
        """)
        r = await cur.fetchone()
        return r[0] if r else 0


# ---------- БАНИ ----------

async def ban_user(uid, reason):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bans VALUES (?,?)",
            (uid, reason)
        )
        await db.commit()


async def is_banned(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT 1 FROM bans WHERE user_id=?",
            (uid,)
        )
        return await cur.fetchone() is not None


async def get_ban_reason(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT reason FROM bans WHERE user_id=?",
            (uid,)
        )
        r = await cur.fetchone()
        return r[0] if r else None
