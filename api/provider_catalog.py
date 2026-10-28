from fastapi import APIRouter
from providers import PROVIDERS, CaptchaProvider

router = APIRouter(prefix="/api", tags=["providers"])


def public_provider(provider: CaptchaProvider) -> dict:
    standard = provider.solve_mode == "standard"
    return {
        "slug": provider.slug,
        "name": provider.name,
        "solve_mode": provider.solve_mode,
        "challenge_url": provider.challenge_url,
        "submit_url": provider.submit_url,
        "script_url": provider.script_url,
        "widget_class": provider.widget_class,
        "site_key": provider.site_key if standard else None,
        # "api_endpoint": provider.api_endpoint if standard else None,
    }


@router.get("/providers")
async def get_providers():
    return [public_provider(p) for p in PROVIDERS.values()]
