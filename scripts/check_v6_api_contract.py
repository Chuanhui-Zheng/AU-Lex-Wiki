"""Exercise the V6 path API against a known official approval edge."""
import asyncio
import json

from frontend.app import graph_path


async def main() -> None:
    response = await graph_path(
        start="agreement:AE521821",
        target="decision:2023-fwcfb-185",
        max_hops=3,
    )
    assert response.status_code == 200
    payload = json.loads(response.body.decode("utf-8"))
    assert len(payload["paths"]) == 1
    path = payload["paths"][0]
    assert path["hops"] == 1
    assert path["edges"][0]["relation_type"] == "approved_by"
    assert path["edges"][0]["source_url"].startswith("https://www.fwc.gov.au/")
    print(f"V6 API contract passed: hops={path['hops']} relation={path['edges'][0]['relation_type']}")


if __name__ == "__main__":
    asyncio.run(main())
