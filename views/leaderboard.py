from fastapi import Request, APIRouter, HTTPException
from fastapi.templating import Jinja2Templates
from providers import listed_providers
from sqlmodel import select, desc, func
from models import User
from database import SessionDep
from services.leaderboard_cache import get_stats, captcha_columns

router = APIRouter(prefix="", tags=["pages"])

templates = Jinja2Templates(directory="templates/")


@router.get("/leaderboard")
@router.get("/l")
def get_leaderboard(
    request: Request,
    session: SessionDep,
    captcha: str | None = None,
    all: bool | None = False,
):
    stats = get_stats(session=session)

    providers = listed_providers()  # iclllllllllll this
    if captcha is not None and captcha not in {p.slug for p in providers}:
        raise HTTPException(404, "nu uh we don't have that captcha")

    users = list(stats["data"])
    # aaaaa help
    # providers_slugs = {p.slug: p for p in providers}
    # selected_slug = providers_slugs.get(captcha)

    if captcha is not None:
        users.sort(
            key=lambda user: user["by_type"].get(captcha, 0),
            reverse=True,
        )

    if not all:
        users = users[:100]

    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={
            "users": users,
            "providers": captcha_columns(),
            "selected_captcha": captcha,
            "total_solved": stats["total_solved"],
            "cache_age": stats["cache_age"],
        },
    )
