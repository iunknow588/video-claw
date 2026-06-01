from __future__ import annotations

from dataclasses import dataclass

from departments.CEO.core.config import settings


@dataclass(slots=True)
class RedisRuntime:
    host: str
    port: int
    db: int
    password: str | None
    decode_responses: bool

    def build_url(self) -> str:
        password_part = f":{self.password}@" if self.password else ""
        return f"redis://{password_part}{self.host}:{self.port}/{self.db}"


def get_redis_runtime() -> RedisRuntime:
    redis = settings.redis
    return RedisRuntime(
        host=str(redis.host),
        port=int(redis.port),
        db=int(redis.db),
        password=redis.password,
        decode_responses=bool(redis.decode_responses),
    )
