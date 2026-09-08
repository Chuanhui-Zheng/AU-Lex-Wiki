"""Exercise the V5 agreement API handlers against the local database."""
import asyncio
import json

from frontend.app import agreement_data, agreements


def payload(response):
    return json.loads(response.body.decode("utf-8"))


async def main() -> None:
    listing = payload(await agreements(limit=20))
    assert listing["count"] == 6
    detail = payload(await agreement_data("AE521821"))
    assert detail["industry"] == "Retail"
    assert any(edge["relation_type"] == "compares_to" for edge in detail["refs"])
    assert any(edge["relation_type"] == "approved_by" for edge in detail["refs"])
    print(f"V5 API contract passed: list={listing['count']} agreement_refs={len(detail['refs'])}")


if __name__ == "__main__":
    asyncio.run(main())
