# leaderboard view? like the html part
# everything-in-one-file until i fix this mess
from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from sqlmodel import select, desc, func
from models import User
from database import SessionDep

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/leaderboard", tags=["pages"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


@router.get("")
async def get_leaderboard(request: Request, session: SessionDep):
    statement = (
        select(User).order_by(desc(User.cloudflare_turnstiles_solved))
        # .limit(100)  # limit 100 t?
    )
    # users = session.exec(statement).all()
    users = session.exec(statement).all()
    total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
    total_solved = session.exec(total_statement).one()
    # print(users)s
    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={"users": users, "total_solved": total_solved},
    )


# ui views tbd
