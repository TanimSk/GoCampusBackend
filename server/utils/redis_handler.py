# utils/redis_handler.py
from django.conf import settings
import redis
import json
import redis.asyncio as aioredis

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
