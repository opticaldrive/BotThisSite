from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from services.utils.cleandata import clean_data
from config import CF_SITE_KEY

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["pages", "challenges"])

templates = Jinja2Templates(directory="templates/")


@router.get("/cf-turnstile")
async def serve_cf_turnstile(name: str, request: Request):
    print(name)
    name = clean_data(name)
    return templates.TemplateResponse(
        request=request,
        name="challenges/cf-turnstile.html",
        context={"name": name, "sitekey": CF_SITE_KEY},
    )
