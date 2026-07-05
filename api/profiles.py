from fastapi import APIRouter

from database import SessionDep

router = APIRouter(prefix="/api/users", tags=["stats"])


@router.get("/")
def get_profile(
    session: SessionDep,
):
    """return
    username
    total captchas
    captchas per type
    rates: {"total":{"5min":captchassolvedper5min, 1h, 1day}}

    """
    return None


# @router.get("/")
# def get_counts(
#     session: SessionDep,
# ):
#     """return
#     username
#     total captchas
#     captchas per type
#     rates: {"total":{"5min":captchassolvedper5min, 1h, 1day}}

#     """
#     return None
