import sys
import time
from contextlib import contextmanager

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.config import settings

provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("sachcart")

def setup_telemetry(app):
    FastAPIInstrumentor.instrument_app(app)

@contextmanager
def record_span(span_name: str, audit_id: str):
    start = time.perf_counter()
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("audit_id", str(audit_id))
        status = "ok"
        try:
            yield span
        except Exception as e:
            status = "error"
            span.record_exception(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            span.set_attribute("status", status)
            span.set_attribute("duration_ms", round(duration_ms, 2))
