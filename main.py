from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import DB_handler
import asyncio
from passlib.hash import bcrypt
from contextlib import asynccontextmanager





@asynccontextmanager
async def lifespan(app: FastAPI):
    await DB_handler.init_conn_pool()                       ## postgress module and its helpers init
    asyncio.create_task(DB_handler.session_cleaner())

app = FastAPI()
pages = Jinja2Templates(directory="frontend")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):

    public_endpoint = ["/", "/userlogin", "/adminlogin", "/register", "/invalid"]
    if request.url.path in public_endpoint:
        return await call_next(request)
    
    id = request.cookies.get("session_id")
    if not id:
        return RedirectResponse("/invalid")
    
    status = await DB_handler.validate_session_id(id)

    if status:
        response = await call_next(request)
        return response
    else:
        return RedirectResponse("/invalid")
    




@app.get("/")
async def landing(request: Request):
    return pages.TemplateResponse("landing.html", {"request": request})

@app.get("/userlogin")
async def userlogin_get(request: Request):
    return pages.TemplateResponse("userlogin.html", {"request": request})

@app.get("/adminlogin")
async def adminlogin_get(request: Request):
    return pages.TemplateResponse("adminlogin.html", {"request": request})

@app.get("/register")
async def register_get(request: Request):
    return pages.TemplateResponse("register.html", {"request": request})


@app.get("/invalid")
async def invalid(request: Request):
    return pages.TemplateResponse("invalid.html", {"request": request})


@app.post("/userlogin")                         # request = {"username" : <username>, "password": <password>}
async def userlogin_post(request: Request):
    data = await request.json()

    status, session_id = await DB_handler.get_session_id(data.get("username"), hashpass(data.get("password")))["session_id"]
    if status!=True:
        return RedirectResponse("/invalid")
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    return redirect

@app.post("/adminlogin")                        # request = {"username" : <username>, "password": <password>}
async def adminlogin_post(request: Request):
    data = await request.json()

    status, session_id = await DB_handler.get_session_id(data.get("username"), hashpass(data.get("password")))["session_id"]
    if status!=True:
        return RedirectResponse("/invalid")
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    return redirect

@app.post("/register")                          # request = {"emailid": <email>, "username" : <username>, "password": <password>, "access_level": <access_level>}
async def register_post(request: Request):
    data = request.json()
    
    status, response = await DB_handler.register_user(data.get("emailid"), data.get("username"), hashpass(data.get("password")), data.get("type"))

    return JSONResponse({"message": response})



@app.get("/home")
async def gethome(request: Request):
   
   id = request.cookies.get("session_id")
   status, role = await DB_handler.get_access_level(id)

   if status:
        if role == "admin":
            package = adminhome()
            return package
        elif role == "user":
            package = userhome()
            return package
   else:
       return {"error": role}

async def adminhome(request: Request):
    rows = await DB_handler.get_admin_landing()
    users = [dict(row) for row in rows]         
    return pages.TemplateResponse(
        "adminhome.html",
        {"request": request, "users": users}
    )

def userhome():
    return pages.TemplateResponse(
        "userhome.html"
    )

def hashpass(password):
    hashed = bcrypt.using(rounds=12).hash(password)
    return hashed