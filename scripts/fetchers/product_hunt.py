from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from .base import BaseFetcher, Signal


class ProductHuntFetcher(BaseFetcher):
    source_name = "product_hunt"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        token = os.getenv("PRODUCT_HUNT_TOKEN")
        if not token:
            print("[product_hunt] skipped: PRODUCT_HUNT_TOKEN not set")
            return []

        query = """
        query TodayPosts {
          posts(order: VOTES, first: 20) {
            edges {
              node {
                name
                tagline
                votesCount
                commentsCount
                website
                url
                topics(first: 3) { edges { node { name } } }
              }
            }
          }
        }
        """
        resp = await client.post(
            "https://api.producthunt.com/v2/api/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        signals: list[Signal] = []
        for edge in data.get("data", {}).get("posts", {}).get("edges", []):
            node = edge["node"]
            votes = node.get("votesCount", 0)
            tags = [
                t["node"]["name"]
                for t in node.get("topics", {}).get("edges", [])
            ]
            signals.append(
                Signal(
                    source="Product Hunt",
                    title=node["name"],
                    url=node.get("website") or node.get("url", ""),
                    raw_score=votes,
                    score=min(votes / 500.0, 1.0),
                    comments=node.get("commentsCount", 0),
                    summary=node.get("tagline", ""),
                    tags=tags,
                )
            )
        return signals
