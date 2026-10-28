from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from database import SessionDep
from services.leaderboard_cache import get_stats
from providers import solvable_providers

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo - remove everything from templates


@router.get("/")
def get_homepage(request: Request, session: SessionDep):
    stats = get_stats(session=session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total_solved": stats["total_solved"],
            "providers": solvable_providers(),
        },
    )


# @router.get("/credits")
# def get_credits(request: Request):
#     return templates.TemplateResponse(
#         request=request,
#         name="credits.html",
#         context={},
#     )
