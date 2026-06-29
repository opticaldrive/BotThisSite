from fastapi import Request


def get_ip(request: Request):
    """
    get_ip(request: Request) -> ip: str
    put in fastapi req get ip
    """
    xff = request.headers.get("X-Forwarded-For")  # caddy revprox does this
    ip = xff.split(",")[0].strip() if xff else request.client.host
    return ip
