from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import DB_handler
import asyncio
from passlib.hash import bcrypt




asyncio.run(DB_handler.main())     # postgres helper init



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
    data = request.json()
    response = JSONResponse({"message": "Logged in"})
    response.set_cookie(key="session_id", value=createSessionID(data.get("username")), httponly=True)
    return response

@app.post("/adminlogin")                        # request = {"username" : <username>, "password": <password>}
async def adminlogin_post(request: Request):
    data = request.json()
    response = JSONResponse({"message": "Logged in"})
    response.set_cookie(key="session_id", value=createSessionID(data.get("username")), httponly=True)
    return response

@app.post("/register")                          # request = {"emailid": <email>, "username" : <username>, "password": <password>, "access_level": <access_level>}
async def register_post(request: Request):
    data = request.json()
    
    status, response = await DB_handler.register_user(data.get("emailid"), data.get("username"), hashpass(data.get("password")), data.get("type"))

    return JSONResponse({"message": response})





@app.get("/home")
async def gethome(request: Request):
   
   id = request.cookies.get("session_id")
   status, role = getrole(id)

   if status:
        if role == "admin":
            package = adminhome()
            return package
        elif role == "user":
            package = userhome()
            return package
   else:
       print(role)

    
def createSessionID(username):
    pass

def checkSessionValidity(id):
    pass

def adminhome():
    pass

def userhome():
    pass

def getrole():
    pass


def createNewUser():
    pass

def hashpass(password):
    hashed = bcrypt.using(rounds=12).hash(password)
    return hashed