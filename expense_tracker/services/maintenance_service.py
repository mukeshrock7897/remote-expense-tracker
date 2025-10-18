from ..db import connect_ctx

async def vacuum_analyze() -> dict:
    """Run VACUUM and ANALYZE."""
    async with connect_ctx() as c:
        await c.execute("VACUUM;")
        await c.execute("ANALYZE;")
        await c.commit()
    return {"status": "ok"}
