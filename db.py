import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")
pool = None


# ---------- INIT ----------

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles(
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            age TEXT,
            gender TEXT,
            height TEXT,
            bio TEXT,
            photo TEXT,
            username TEXT
        )
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS likes(
            from_id BIGINT,
            to_id BIGINT,
            PRIMARY KEY (from_id, to_id)
        )
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS bans(
            user_id BIGINT PRIMARY KEY,
            reason TEXT
        )
        """)


# ---------- ПРОФІЛІ ----------

async def save_profile(data):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO profiles VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (user_id) DO UPDATE SET
        name=$2, age=$3, gender=$4,
        height=$5, bio=$6, photo=$7, username=$8
        """, *data)


async def get_profile(uid):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM profiles WHERE user_id=$1",
            uid
        )


async def get_all_profiles():
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM profiles ORDER BY user_id"
        )


async def delete_profile(uid):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM profiles WHERE user_id=$1",
            uid
        )

        await conn.execute(
            "DELETE FROM likes WHERE from_id=$1 OR to_id=$1",
            uid
        )

        await conn.execute(
            "DELETE FROM bans WHERE user_id=$1",
            uid
        )


# ---------- ПОСЛІДОВНИЙ ПОШУК ----------

async def get_next_profile(gender, my_id, offset):
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
        SELECT *
        FROM profiles
        WHERE gender=$1
        AND user_id != $2
        AND user_id NOT IN (
            SELECT to_id FROM likes WHERE from_id=$2
        )
        ORDER BY user_id
        OFFSET $3
        LIMIT 1
        """, gender, my_id, offset)


# ---------- ЛАЙКИ ----------

async def add_like(from_id, to_id):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO likes VALUES ($1,$2)
        ON CONFLICT DO NOTHING
        """, from_id, to_id)


async def is_mutual(a, b):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("""
        SELECT 1 FROM likes
        WHERE from_id=$1 AND to_id=$2
        """, b, a)

        return r is not None


# ---------- КІЛЬКІСТЬ МАТЧІВ ----------

async def get_matches_count():
    async with pool.acquire() as conn:
        r = await conn.fetchrow("""
        SELECT COUNT(*) FROM likes l1
        JOIN likes l2
        ON l1.from_id = l2.to_id
        AND l1.to_id = l2.from_id
        WHERE l1.from_id < l1.to_id
        """)
        return r[0] if r else 0


# ---------- БАНИ ----------

async def ban_user(uid, reason):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO bans VALUES ($1,$2)
        ON CONFLICT (user_id)
        DO UPDATE SET reason=$2
        """, uid, reason)


async def is_banned(uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            "SELECT 1 FROM bans WHERE user_id=$1",
            uid
        )
        return r is not None


async def get_ban_reason(uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            "SELECT reason FROM bans WHERE user_id=$1",
            uid
        )
        return r["reason"] if r else None
