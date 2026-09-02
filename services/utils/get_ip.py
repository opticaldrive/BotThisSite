from fastapi import Request


def get_ip(request: Request):
    """
    get_ip(request: Request) -> ip: str
    put in fastapi req get ip
    """
    xff = request.headers.get("X-Forwarded-For")  # caddy revprox does this
    # last element, not first: caddy appends the real peer to whatever the
    # client sent, so everything left of it is attacker-controlled text.
    ip = xff.split(",")[-1].strip() if xff else request.client.host
    return ip
