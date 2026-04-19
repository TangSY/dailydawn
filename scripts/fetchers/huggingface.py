from __future__ import annotations

import httpx

from .base import BaseFetcher, Signal


class HuggingFaceFetcher(BaseFetcher):
    source_name = "huggingface"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        signals: list[Signal] = []
        # 模型
        try:
            resp = await client.get(
                "https://huggingface.co/api/models",
                params={"sort": "likes7d", "direction": -1, "limit": 20},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            for m in resp.json():
                likes = m.get("likes", 0)
                signals.append(
                    Signal(
                        source="HuggingFace Models",
                        title=m.get("modelId") or m.get("id", ""),
                        url=f"https://huggingface.co/{m.get('modelId') or m.get('id','')}",
                        raw_score=likes,
                        score=min(likes / 500.0, 1.0),
                        tags=m.get("tags", [])[:5],
                        # lastModified 是 HF 模型卡最后更新时间（ISO 8601），
                        # 新发布的模型首次 push 即 last-modified，语义等同"发布时间"
                        published_at=m.get("lastModified") or m.get("createdAt"),
                    )
                )
        except Exception as e:
            print(f"[huggingface models] {e}")

        # 数据集
        try:
            resp = await client.get(
                "https://huggingface.co/api/datasets",
                params={"sort": "likes7d", "direction": -1, "limit": 10},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            for d in resp.json():
                likes = d.get("likes", 0)
                signals.append(
                    Signal(
                        source="HuggingFace Datasets",
                        title=d.get("id", ""),
                        url=f"https://huggingface.co/datasets/{d.get('id','')}",
                        raw_score=likes,
                        score=min(likes / 200.0, 1.0),
                        tags=d.get("tags", [])[:3],
                        published_at=d.get("lastModified") or d.get("createdAt"),
                    )
                )
        except Exception as e:
            print(f"[huggingface datasets] {e}")

        return signals
