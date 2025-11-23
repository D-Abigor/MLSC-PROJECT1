from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import DB_handler
from contextlib import asynccontextmanager

verbose = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    await DB_handler.init_conn_pool_and_cleaner()                       ## postgress module and its helpers init
    yield

app = FastAPI(lifespan=lifespan)
pages = Jinja2Templates(directory="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_endpoint = ["/", "/userlogin", "/adminlogin", "/register", "/invalid", "/docs", "/redoc", "/docs/oauth2-redirect", "/openapi.json", "/checkavailability"]

    if request.url.path in public_endpoint:
        return await call_next(request)
    
    id = request.cookies.get("session_id")
    if not id:
        return pages.TemplateResponse("invalid.html", {"request": request, "error":"invalid credentials"})
    
    status = await DB_handler.validate_session_id(id)

    if status:
        response = await call_next(request)
        return response
    else:
        return pages.TemplateResponse("invalid.html", {"request": request, "error":"invalid session id"})
    


#---------------------------------------GET ENDPOINTS-------------------------------#

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

@app.get("/checkavailability")
async def check_availability(username: str):
    print("checking availability")
    response = await DB_handler.check_username_availability(username)
    return response


@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    await DB_handler.delete_session_id(session_id)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session_id")
    return response

@app.get("/home")
async def gethome(request: Request):            
   id = request.cookies.get("session_id")
   status, role = await DB_handler.get_access_level(id)

   if status:
        if role == "admin" and request.cookies.get("origin") == "adminlogin":                       # to be moved ito /adminlogin endpoints and validated for proper access level for the given login endpoint before proceeding to /home
            package = await adminhome(request)
        elif role == "user" and request.cookies.get("origin") == "userlogin":
            package = await userhome(request)
        else:
            return pages.TemplateResponse("invalid.html", {"request": request, "error":"Unknown role"})
        return package
   else:
       return pages.TemplateResponse("invalid.html", {"request": request, "error":role})


#---------------------------------------POST ENDPOINTS-------------------------------#

@app.post("/userlogin")                         
async def userlogin_post(request: Request):
    data = await request.json()
    status, session_id = await DB_handler.get_session_id(data.get("username"), data.get("password"))
    if status!=True:
        return pages.TemplateResponse("invalid.html", {"request": request, "error":"could not get session ID"})
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    redirect.set_cookie(key="origin", value="userlogin")
    return redirect

@app.post("/adminlogin")
async def adminlogin_post(request: Request):
    data = await request.json()

    status, session_id = await DB_handler.get_session_id(data.get("username"), data.get("password"))
    if status!=True:
        return pages.TemplateResponse("invalid.html", {"request": request, "error":"could not get session ID"})
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    redirect.set_cookie(key="origin", value="adminlogin")
    return redirect

@app.post("/register")                   
async def register_post(request: Request):
    data = await request.json()
    status, response = await DB_handler.register_user(data.get("emailid"), data.get("username"), data.get("password"), data.get("type"))

    return pages.TemplateResponse("invalid.html", {"request": request, "error":response})




#---------------FUNCTIONS TO SEPERATE /HOME ENDPOINT ACCORDING TO ACCESS LEVEL------------------#

async def adminhome(request: Request):
    rows = await DB_handler.get_admin_landing()
    users = [dict(row) for row in rows]      
    return pages.TemplateResponse(
        "adminhome.html",
        {"request": request, "users": users}
    )

async def userhome(request):
    return pages.TemplateResponse(
        "userhome.html",
        {"request": request}
    )