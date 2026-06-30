# notproud of this vibecoded antiabuse that isn't needed
# DO NOT PUSH TO PROD THIS DOES NOT WORK IDC
# disable ratelimits by uh
import time

from fastapi import HTTPException

FAIL_WINDOW_SECONDS = 300  # 5 minutes rolling window for failure grouping
FAIL_THRESHOLD = 20  # failures before temporary block
BLOCK_BASE_SECONDS = 120  # starting block duration after threshold
MAX_BACKOFF_SECONDS =  60 * 60 # 1 hr,  # 10 * 365 * 24 * 60 * 60  # ~10 years, cap for exponential backoff
# 
_failures: dict[str, dict] = {}


def _now() -> int:
    return int(time.time())


def _cleanup(ip: str) -> None:
    state = _failures.get(ip)
    if not state:
        return

    now = _now()
    if state["blocked_until"] and state["blocked_until"] <= now:
        # keep the state until the window expires, so repeated failures grow the ban
        state["blocked_until"] = 0

    if now - state["last_failure_at"] > FAIL_WINDOW_SECONDS and not state["blocked_until"]:
        _failures.pop(ip, None)


def check_failed_verify_allowed(ip: str) -> None:
    """Raise 429 if this IP is currently blocked from failed captcha verification."""
    _cleanup(ip)
    state = _failures.get(ip)
    if not state:
        return

    now = _now()
    blocked_until = state.get("blocked_until", 0)
    if blocked_until and blocked_until > now:
        raise HTTPException(
            429,
            f"nu uh: 1. make your bot better, 2. stop spammy 3:  blocked for {blocked_until - now} seconds.",
        )


def record_failed_verify(ip: str) -> None:
    """Record a failed captcha verification and apply exponential backoff when thresholds are reached."""
    now = _now()
    state = _failures.get(ip)

    if not state or now - state["last_failure_at"] > FAIL_WINDOW_SECONDS:
        state = {
            "failure_count": 1,
            "first_failure_at": now,
            "last_failure_at": now,
            "blocked_until": 0,
        }
    else:
        state["failure_count"] += 1
        state["last_failure_at"] = now

    if state["failure_count"] >= FAIL_THRESHOLD:
        block_stage = (state["failure_count"] - FAIL_THRESHOLD) // FAIL_THRESHOLD
        block_seconds = min(BLOCK_BASE_SECONDS * (2 ** block_stage), MAX_BACKOFF_SECONDS)
        state["blocked_until"] = now + block_seconds
    else:
        state["blocked_until"] = 0

    _failures[ip] = state


def record_successful_verify(ip: str) -> None:
    """Keep failure state until it naturally expires after a successful verify."""
    _cleanup(ip)
