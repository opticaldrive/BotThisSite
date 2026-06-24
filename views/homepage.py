from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from database import SessionDep
from services.leaderboard_cache import get_stats
from providers import PROVIDERS

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


@router.get("/")
async def get_homepage(request: Request, session: SessionDep):
    stats = get_stats(session=session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total_solved": stats["total_solved"],
            "providers": list(PROVIDERS.values()),
        },
    )


# ui views tbd
