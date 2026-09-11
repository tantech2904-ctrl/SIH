from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Use in-memory storage by default for local development. The app can still
# run without Redis, and rate limits remain functional for a single-process
# local instance.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)