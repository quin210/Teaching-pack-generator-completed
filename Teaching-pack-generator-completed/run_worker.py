import os

from dotenv import load_dotenv
from redis import Redis
from rq import Queue, Worker

load_dotenv()


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    conn = Redis.from_url(redis_url)
    queues = [Queue("teachingpack", connection=conn)]
    worker = Worker(queues, connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
