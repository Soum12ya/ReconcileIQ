import redis, os
from dotenv import load_dotenv

load_dotenv()

print(os.environ["REDIS_URL"])

r = redis.from_url(os.environ["REDIS_URL"])

print("PING:", r.ping())

print("Waiting...")
print(r.blpop("vendor_reply_queue"))