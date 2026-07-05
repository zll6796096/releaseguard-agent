import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Demo Store")

# Setup directories relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class CheckoutRequest(BaseModel):
    name: str
    email: str
    card: str

@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Landing page endpoint."""
    return templates.TemplateResponse(request, "index.html")

@app.get("/checkout", response_class=HTMLResponse)
def checkout(request: Request, bug: bool = False):
    """Checkout page endpoint. Hides checkout button if env var or query parameter is set."""
    env_bug = os.environ.get("BUG_HIDE_CHECKOUT_BUTTON", "").lower() in ("true", "1", "yes")
    hide_button = bug or env_bug
    return templates.TemplateResponse(
        request,
        "checkout.html", 
        {"hide_button": hide_button}
    )

@app.post("/checkout")
async def process_checkout(request: Request):
    """Processes checkout POST request (both form data and JSON body)."""
    # Accept form data if browser post, or JSON if programmatic probe
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
            name = data.get("name", "")
            email = data.get("email", "")
        except Exception:
            name, email = "", ""
    else:
        form_data = await request.form()
        name = form_data.get("name", "")
        email = form_data.get("email", "")

    return JSONResponse(content={
        "status": "success",
        "message": f"Order processed successfully for {name or 'customer'}.",
        "email": email
    })
