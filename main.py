from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import requests
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates


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
    id = request.cookies.get("session_id")
    status = checkSessionValidity(id)
    public_endpoint = ["/", "/userlogin", "/adminlogin", "/register", "/invalid"]
    if request.url.path.startswith(tuple(public_endpoint)):
        return await call_next(request)
    
    if not status:
        return RedirectResponse("/invalid")
    
    response = await call_next(request)
    return response




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
    pass

@app.post("/adminlogin")                        # request = {"username" : <username>, "password": <password>}
async def adminlogin_post(request: Request):
    pass

@app.post("/register")                          # request = {"emailid": <email>, "username" : <username>, "password": <password>}
async def register_post(request: Request):
    pass




@app.get("/home")
async def gethome(request: Request):
   id = request.cookies.get("session_id")
   role = getrole(id)
   if role == "admin":
       package = adminhome()
       return package
   elif role == "user":
       package = userhome()
       return package
    


def checkSessionValidity(id):
    pass

def adminhome():
    pass

def userhome():
    pass

def getrole():
    pass