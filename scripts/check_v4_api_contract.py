"""Exercise the V4 FastAPI handlers against the local database."""
import asyncio
import json

from frontend.app import decision_data, decisions


def payload(response):
    return json.loads(response.body.decode("utf-8"))


async def main() -> None:
    listing = payload(await decisions(limit=20))
    assert listing["count"] == 6
    detail = payload(await decision_data("2024-fwcfb-458"))
    assert detail["citation"] == "[2024] FWCFB 458"
    assert any(edge["relation_type"] == "cites" for edge in detail["refs"])
    assert any(edge["relation_type"] == "interprets" for edge in payload(await decision_data("2025-fwcfb-3500"))["refs"])
    print(f"V4 API contract passed: list={listing['count']} decision_refs={len(detail['refs'])}")


if __name__ == "__main__":
    asyncio.run(main())
