import datetime as dt

def utc_now_iso() -> str:
    """UTC time in ISO 8601."""
    return dt.datetime.now(dt.timezone.utc).isoformat()
