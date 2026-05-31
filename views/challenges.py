from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["pages", "challenges"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


@router.get("/cf-turnstile")
async def serve_cf_turnstile(name: str, request: Request):
    # a
    # todo: serve htmls
    # return True
    print(name)
    return templates.TemplateResponse(
        request=request, name="challenges/cf-turnstile.html", context={"name": name}
    )
