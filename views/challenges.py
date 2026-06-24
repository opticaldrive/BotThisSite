from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from services.utils.cleandata import clean_data
from providers import get_provider

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["pages", "challenges"])

templates = Jinja2Templates(directory="templates/")


@router.get("/{slug}")
async def serve_challenge(slug: str, name: str, request: Request):
    provider = get_provider(slug)
    name = clean_data(name)
    return templates.TemplateResponse(
        request=request,
        name=provider.template,
        context={
            "name": name,
            "sitekey": provider.site_key,
            "provider": provider,
        },
    )
