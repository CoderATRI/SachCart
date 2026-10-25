import sys
import os
import socket
import subprocess
from pathlib import Path
import httpx
import redis
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text
import anthropic
from app.config import settings

def check_python() -> tuple[bool, str]:
    if sys.version_info >= (3, 12):
        return True, f"Python {sys.version.split()[0]}"
    return False, "Python 3.12 or newer is required. Install Python 3.12 or 3.14."

def check_node_npm() -> tuple[bool, str]:
    try:
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        node_res = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        npm_res = subprocess.run([npm_cmd, "--version"], capture_output=True, text=True, check=True)
        version_str = node_res.stdout.strip().lstrip("v")
        major = int(version_str.split(".")[0])
        if major < 20:
            return False, f"Node.js version {node_res.stdout.strip()} is below 20. Update Node.js to v20 or newer."
        return True, f"Node {node_res.stdout.strip()}, npm {npm_res.stdout.strip()}"
    except Exception as e:
        return False, f"Node 20+ and npm must be installed and in PATH ({e}). Install Node.js 20+."

def check_docker() -> tuple[bool, str]:
    try:
        res = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if res.returncode == 0:
            return True, "Docker CLI installed and daemon running"
        return False, "Docker daemon is not running. Please start Docker Desktop."
    except Exception as e:
        return False, f"Docker CLI is not available in PATH ({e}). Please install Docker Desktop."

def check_ports() -> tuple[bool, str]:
    busy = []
    for port in (3000, 8000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                busy.append(port)
    if busy:
        return False, f"Port(s) {', '.join(map(str, busy))} are in use. Stop the processes using them."
    return True, "Ports 3000 and 8000 are free"

def check_services() -> tuple[bool, str]:
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        return False, f"Postgres connection failed ({e}). Run 'docker compose up -d' to start Postgres."
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=3)
        r.ping()
    except Exception as e:
        return False, f"Redis connection failed ({e}). Run 'docker compose up -d' to start Redis."
    try:
        endpoint = settings.MINIO_PUBLIC_URL if settings.MINIO_PUBLIC_URL.startswith("http") else f"http://{settings.MINIO_ENDPOINT}"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        if settings.MINIO_BUCKET not in buckets:
            s3.create_bucket(Bucket=settings.MINIO_BUCKET)
    except Exception as e:
        return False, f"MinIO connection failed ({e}). Run 'docker compose up -d' to start MinIO."
    return True, f"Postgres, Redis, and MinIO reachable (bucket '{settings.MINIO_BUCKET}' ready)"

def check_outside_env_keys() -> tuple[bool, str]:
    outside = []
    for var in ("ANTHROPIC_API_KEY", "TINYFISH_API_KEY"):
        if var in os.environ:
            outside.append(f"{var} in session environment")
    if sys.platform == "win32":
        import winreg
        for subkey, hkey, label in [
            (r"Environment", winreg.HKEY_CURRENT_USER, "Windows User Environment"),
            (r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", winreg.HKEY_LOCAL_MACHINE, "Windows System Environment"),
        ]:
            try:
                with winreg.OpenKey(hkey, subkey) as k:
                    for var in ("ANTHROPIC_API_KEY", "TINYFISH_API_KEY"):
                        try:
                            val, _ = winreg.QueryValueEx(k, var)
                            if val:
                                outside.append(f"{var} in {label}")
                        except FileNotFoundError:
                            pass
            except Exception:
                pass
    if outside:
        return False, f"API key(s) detected outside .env: {', '.join(outside)}. Remove external environment variables so .env is the exclusive source."
    return True, "No API keys set outside .env; .env is the exclusive source"

def check_env_keys() -> tuple[bool, str]:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return False, ".env file is missing in project root. Copy .env.example to .env and configure it."
    if not settings.TINYFISH_API_KEY.strip() or not settings.ANTHROPIC_API_KEY.strip():
        missing = []
        if not settings.TINYFISH_API_KEY.strip():
            missing.append("TINYFISH_API_KEY")
        if not settings.ANTHROPIC_API_KEY.strip():
            missing.append("ANTHROPIC_API_KEY")
        return False, f"Missing required API key(s) in .env: {', '.join(missing)}. Set valid keys in .env."
    return True, ".env exists and required API keys are configured"

def check_tinyfish_key() -> tuple[bool, str]:
    if not settings.TINYFISH_API_KEY.strip():
        return False, "TINYFISH_API_KEY is empty in .env. Obtain a key from https://agent.tinyfish.ai/api-keys."
    try:
        resp = httpx.get(
            "https://api.search.tinyfish.ai?query=test",
            headers={"X-API-Key": settings.TINYFISH_API_KEY.strip()},
            timeout=10.0,
        )
        if resp.status_code == 200:
            return True, "TINYFISH_API_KEY verified via Search API"
        return False, f"TINYFISH_API_KEY verification failed with status {resp.status_code}. Verify your key."
    except Exception as e:
        return False, f"TINYFISH_API_KEY check network error: {e}"

def check_anthropic_key() -> tuple[bool, str]:
    if not settings.ANTHROPIC_API_KEY.strip():
        return False, "ANTHROPIC_API_KEY is empty in .env. Obtain a key from Anthropic console."
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY.strip())
        models_resp = client.models.list()
        model_ids = [m.id for m in models_resp.data]
        if settings.CLAUDE_MODEL not in model_ids:
            return False, f"Configured CLAUDE_MODEL '{settings.CLAUDE_MODEL}' not found for key: {model_ids}."
        return True, f"ANTHROPIC_API_KEY verified and model '{settings.CLAUDE_MODEL}' exists"
    except anthropic.AuthenticationError:
        return False, "Claude API key rejected. Check your Anthropic API key in .env."
    except Exception as e:
        return False, f"ANTHROPIC_API_KEY verification failed ({e}). Check your Anthropic API key."

def main():
    checks = [
        ("Python version", check_python),
        ("Node and npm", check_node_npm),
        ("Docker and daemon", check_docker),
        ("Ports 3000 and 8000", check_ports),
        ("Postgres, Redis, and MinIO", check_services),
        ("Outside environment override", check_outside_env_keys),
        (".env configuration", check_env_keys),
        ("TinyFish API key", check_tinyfish_key),
        ("Anthropic API key and model", check_anthropic_key),
    ]
    failed = False
    for name, check_func in checks:
        passed, msg = check_func()
        if passed:
            print(f"PASS: {name} - {msg}", flush=True)
        else:
            print(f"FAIL: {name} - {msg}", flush=True)
            failed = True
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
