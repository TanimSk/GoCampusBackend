# utils/redis_handler.py
from django.conf import settings
import redis
import json
import redis.asyncio as aioredis
from trainee.models import Session

# Sync Redis (for Django views, signals, admin, celery, etc.)
sync_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)

# Async Redis (for Channels / WebSockets)
async_redis_client = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)

def get_sync_redis():
    return sync_redis_client

def get_async_redis():
    return async_redis_client


def create_redis_session(session_id, trainee_id):
    session_key = f"session:{session_id}"
    json_data = {
        "status": Session.objects.get(id=session_id).status,
        "session_id": str(session_id),
        "trainee_id": str(trainee_id),
        "trainee_latitude": None,
        "trainee_longitude": None,
        "interested_trainers": {
            # "trainer_id": {"trainer_latitude": 12.34, "trainer_longitude": 56.78}
        },
    }

    # Store the session data in Redis with a TTL of 1 hour (3600 seconds)
    get_sync_redis().setex(session_key, 3600, json.dumps(json_data))
