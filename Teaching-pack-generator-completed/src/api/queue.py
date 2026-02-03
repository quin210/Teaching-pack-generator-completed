import os
from redis import Redis
from rq import Queue

def get_redis() -> Redis:
    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return Redis.from_url(url)

def get_queue() -> Queue:
    return Queue("teachingpack", connection=get_redis())
