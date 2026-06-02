from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from sqlmodel import select, desc, func
from models import User
from database import SessionDep

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


@router.get("/")
async def get_homepage(request: Request, session: SessionDep):
    total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
    total_solved = session.exec(total_statement).one()
    # print(users)s
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"total_solved": total_solved},
    )


# ui views tbd
