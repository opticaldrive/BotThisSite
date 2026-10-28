from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="templates/")


@router.get("/data")
@router.get("/d")
def get_data(request: Request):
    # the chart fetches /api/graphs/* itself, so this view just serves the shell
    return templates.TemplateResponse(request=request, name="data.html")


@router.get("/data/users")
@router.get("/d/u")
def get_user_data(request: Request):
    return templates.TemplateResponse(request=request, name="user_data.html")


@router.get("/data/scores")
@router.get("/d/s")
def get_user_scores(request: Request):
    return templates.TemplateResponse(request=request, name="user_scores.html")
