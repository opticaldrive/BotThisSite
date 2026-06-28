from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="templates/")


@router.get("/data")
def get_data(request: Request):
    # the chart fetches /api/graphs/* itself, so this view just serves the shell
    return templates.TemplateResponse(request=request, name="data.html")
