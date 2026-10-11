from slowapi import Limiter
from slowapi.util import get_remote_address # Returns ip for current address
from .config import LIMITER_URL

# Counts requests per IP in Redis. If Redis is down, falls back to
# counting in memory instead of failing every request
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=LIMITER_URL,
    in_memory_fallback_enabled=True,
)
