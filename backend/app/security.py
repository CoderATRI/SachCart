import socket
import ipaddress
import hashlib
import hmac
from urllib.parse import urlparse
from fastapi import Request, HTTPException
import redis
from app.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def validate_target_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url or len(url) > 2048:
        raise HTTPException(status_code=422, detail="Invalid URL: exceeds 2048 characters or is empty")
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid URL format")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="URL scheme must be http or https")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="URL missing hostname")
    if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
        raise HTTPException(status_code=422, detail="Localhost target is rejected")
    try:
        ip = ipaddress.ip_address(hostname)
        raise HTTPException(status_code=422, detail="IP literals are rejected")
    except ValueError:
        pass
    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_loopback
                or ip_obj.is_private
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
                or ip_obj.is_unspecified
            ):
                raise HTTPException(status_code=422, detail="Target resolves to private or restricted network")
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="Unable to resolve hostname")
    return url

def get_client_ip(request: Request) -> str:
    if request.client and request.client.host == "127.0.0.1":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def is_valid_api_key(header_key: str | None) -> bool:
    if not header_key or not settings.SACHCART_API_KEYS.strip():
        return False
    header_hash = hashlib.sha256(header_key.strip().encode("utf-8")).digest()
    for valid_key in settings.SACHCART_API_KEYS.split(","):
        k = valid_key.strip()
        if not k:
            continue
        valid_hash = hashlib.sha256(k.encode("utf-8")).digest()
        if hmac.compare_digest(header_hash, valid_hash):
            return True
    return False

def check_rate_limits(request: Request) -> str:
    client_ip = get_client_ip(request)
    header_key = request.headers.get("x-api-key")
    has_valid_key = is_valid_api_key(header_key)
    is_local = client_ip in ("127.0.0.1", "::1", "localhost")
    limit = 100 if (has_valid_key or is_local) else 5
    rate_key = f"rate:hour:{client_ip}"
    current = redis_client.incr(rate_key)
    if current == 1:
        redis_client.expire(rate_key, 3600)
    if current > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    running_count = int(redis_client.get(f"running:{client_ip}") or 0)
    if running_count >= 2:
        raise HTTPException(status_code=429, detail="Maximum concurrent audits reached")
    return client_ip

def increment_running(client_ip: str):
    redis_client.incr(f"running:{client_ip}")
    redis_client.expire(f"running:{client_ip}", 600)

def decrement_running(client_ip: str):
    count = redis_client.decr(f"running:{client_ip}")
    if count <= 0:
        redis_client.delete(f"running:{client_ip}")
