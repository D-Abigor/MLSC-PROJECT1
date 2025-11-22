from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
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
    if verbose:
        print("executing middleware") 
    public_endpoint = ["/", "/userlogin", "/adminlogin", "/register", "/invalid"]

    if request.url.path in public_endpoint:
        return await call_next(request)
    
    id = request.cookies.get("session_id")
    if verbose:
        print("cookie detected by middleware:", id)
    if not id:
        return RedirectResponse("/invalid")
    
    status = await DB_handler.validate_session_id(id)

    if status:
        if verbose:
            print("middleware cookie validation pass!")
        response = await call_next(request)
        if verbose:
            print(response)
        return response
    else:
        if verbose:
            print("middleware cookie validation fail")
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

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    DB_handler.delete_session_id(session_id)

    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("session_id")
    return response


@app.post("/userlogin")                         
async def userlogin_post(request: Request):
    data = await request.json()
    status, session_id = await DB_handler.get_session_id(data.get("username"), data.get("password"))
    if status!=True:
        return RedirectResponse("/invalid")
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    redirect.set_cookie(key="origin", value="userlogin")
    return redirect

@app.post("/adminlogin")
async def adminlogin_post(request: Request):
    data = await request.json()

    status, session_id = await DB_handler.get_session_id(data.get("username"), data.get("password"))
    if verbose:
        print(status, session_id)
    if status!=True:
        return RedirectResponse("/invalid")
    
    redirect = RedirectResponse(url="/home", status_code=303)
    redirect.set_cookie(key="session_id", value=str(session_id), httponly=True)
    redirect.set_cookie(key="origin", value="adminlogin")
    return redirect

@app.post("/register")                   
async def register_post(request: Request):
    data = await request.json()
    status, response = await DB_handler.register_user(data.get("emailid"), data.get("username"), data.get("password"), data.get("type"))

    return JSONResponse({"message": response})



@app.get("/home")
async def gethome(request: Request):
   if verbose:
       print("at home")                         #####################################

   id = request.cookies.get("session_id")
   if verbose:
       print("cookie detected inside home", id)
   status, role = await DB_handler.get_access_level(id)
   if verbose:
       print("status and role:",status,role)

   if status:
        if verbose:
            print("positive status")
        if role == "admin" and request.cookies.get("origin") == "adminlogin":
            if verbose:
                print("detected login as admin")
            package = await adminhome(request)
            if verbose:
                print("package", package)
            return package
        elif role == "user" and request.cookies.get("origin") == "userlogin":
            package = await userhome(request)
            return package
   else:
       return {"error": role}

async def adminhome(request: Request):
    rows = await DB_handler.get_admin_landing()
    users = [dict(row) for row in rows] 
    if verbose:
        print("users", users)        
    return pages.TemplateResponse(
        "adminhome.html",
        {"request": request, "users": users}
    )

async def userhome(request):
    return pages.TemplateResponse(
        "userhome.html",
        {"request": request}
    )