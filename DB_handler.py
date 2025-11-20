import asyncpg
import asyncio
import os
from dotenv import load_dotenv


load_dotenv()

conn_pool = None

async def init_conn_pool():
    global conn_pool
    conn_pool = asyncpg.create_pool(
        user=os.getenv("PSQUSER"),
        password=os.getenv("PSQPASS"),
        database="mlscproject1",
        host = "localhost",
        port = 9112
    )

async def get_admin_landing():
    async with conn_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM users;")
        return rows


async def get_session_id(username,password_hash):
    async with conn_pool.acquire() as connection:
        rows = await connection.fetchrow("SELECT id,username,password_hash FROM users WHERE username = $1 AND password_hash = $2;", username, password_hash)
        if rows:
            session_id = await connection.fetchrow("INSERT INTO sessions (user_id, expires_at) VALUES ($1, NOW() + INTERVAL '1 day') RETURNING session_id;",rows['id'] )
            return True,session_id["session_id"]
        else:
            return False,"invalid credentials"


async def validate_session_id(sessionid):
    async with conn_pool.acquire() as connection:
        rows = await connection.fetchrow("SELECT session_id FROM sessions WHERE session_id = $1 AND expires_at > NOW();", sessionid)
    if rows:
        return True
    else:
        return False

async def session_cleaner():
    while True:
        async with conn_pool.acquire() as connection:
            await connection.execute("DELETE FROM sessions WHERE expires_at < NOW();")
        await asyncio.sleep(300)
    

async def register_user(email,username,password_hash,access_level):
    async with conn_pool.acquire() as connection:
        conflict = await connection.fetchrow("SELECT username FROM users WHERE username = $1", username)
        if conflict:
            return False,"Username already in DB, Try logging in"
        else:
            await connection.execute("INSERT INTO users (email,username,password_hash,access) VALUES ($1,$2,$3,$4');", email, username, password_hash, access_level)
            return True, "registered new user"


async def get_access_level(session_id):
    async with conn_pool.acquire() as connection:
        row = await connection.fetchrow("""
    SELECT user.access
    FROM sessions session
    JOIN users user ON session.user_id = user.id
    WHERE session.session_id = $1
""", session_id)
        if row:
            return True, row["access"]
        else:
            return False, "could not get access level"




async def main():
    await init_conn_pool()
    asyncio.create_task(session_cleaner())