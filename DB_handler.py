import asyncpg
import asyncio
import os
from dotenv import load_dotenv
from passlib.hash import bcrypt

verbose = True
load_dotenv()

conn_pool = None
tokenCleanFrequency = 180                           # variable controlling frequency of expired session token cleaner
bcryptCost = 12                                     # bcrypt hashing compute cost


async def init_conn_pool_and_cleaner():
    global conn_pool
    conn_pool = await asyncpg.create_pool(
        user=os.getenv("PSQUSER"),                      
        password=os.getenv("PSQPASS"),
        database=os.getenv("DBNAME"),
        host = "localhost",
        port = 9112
    )
    asyncio.create_task(session_cleaner())              # expired token cleaning function run asynchronously

async def get_admin_landing():                          # function to get data to be displayed in the /home page of admin user from psql
    async with conn_pool.acquire() as connection:
        rows = await connection.fetch("SELECT * FROM users;")
        return rows


async def get_session_id(username,password):            # function that gets new/active session token from psql
    async with conn_pool.acquire() as connection:
        passhash = await connection.fetchrow("SELECT id,username,password_hash FROM users WHERE username = $1;", username)

        if passhash:
            if bcrypt.verify(password, passhash["password_hash"]):
                existing_token = await connection.fetchrow("SELECT session_id FROM sessions WHERE user_id = $1;", passhash["id"])
                if existing_token:
                    return True,existing_token["session_id"]
                session_id = await connection.fetchrow("INSERT INTO sessions (user_id, expires_at) VALUES ($1, NOW() + INTERVAL '1 day') RETURNING session_id;",passhash['id'] )
                return True,session_id["session_id"]
        else:
            return False,"invalid credentials"

async def validate_session_id(sessionid):               # validating a submitted session_id to check for expiry and existence
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
        await asyncio.sleep(tokenCleanFrequency)
    

async def register_user(email,username,password,access_level):
    async with conn_pool.acquire() as connection:
        conflict = await connection.fetchrow("SELECT username FROM users WHERE username = $1", username)
        password_hashed = await hashpass(password)
        if conflict:
            return False,"Username already in DB, Try logging in"
        else:
            await connection.execute("INSERT INTO users (email,username,password_hash,access) VALUES ($1,$2,$3,$4);", email, username, password_hashed, access_level)
            return True, "registered new user"


async def get_access_level(session_id):
    if verbose:
        print("getting access level for/home endpoint")
    async with conn_pool.acquire() as connection:
        row = await connection.fetchrow("SELECT u.access FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.session_id = $1;", session_id)
        if row:
            return True, row["access"]
        else:
            return False, "could not get access level"
        

async def delete_session_id(session_id):
    async with conn_pool.acquire() as connection:
        await connection.execute("DELETE FROM sessions WHERE session_id = $1", session_id)


async def check_username_availability(username):
    async with conn_pool.acquire() as connection:
        print("db_handler is checking availability for", username)
        rows = await connection.fetchrow("SELECT username from users WHERE username = $1;", username)
        return {"available": not rows} 



# hashing password with bcrypt to store passwords securely on the DB

async def hashpass(password):                                                                           
    hashed = await asyncio.to_thread(bcrypt.using(rounds=bcryptCost).hash, str(password))
    return hashed


