"""
Coleta posts do Instagram usando a API do Apify.
Actor usado: apify~instagram-scraper
"""

import os
import time
import logging
import requests
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "apify~instagram-scraper"


class InstagramCollector:
    def __init__(self):
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN não definido nas variáveis de ambiente.")

    async def collect(self, profiles: list[str], max_posts: int = 20) -> dict[str, list[dict]]:
        """
        Coleta os posts mais recentes de cada perfil.
        Retorna um dict: { username: [post, ...] }
        """
        results = {}

        for username in profiles:
            logger.info(f"Coletando posts de @{username}...")
            try:
                posts = self._fetch_profile(username, max_posts)
                results[username] = posts
                logger.info(f"  → {len(posts)} posts coletados de @{username}")
            except Exception as e:
                logger.error(f"  → Erro ao coletar @{username}: {e}")
                results[username] = []

        return results

    def _fetch_profile(self, username: str, max_posts: int) -> list[dict]:
        """Executa o actor do Apify via HTTP e retorna os posts normalizados."""
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": max_posts,
            "addParentData": False,
        }

        # Inicia o run
        resp = requests.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
            params={"token": self.api_token},
            json=run_input,
            timeout=30,
        )
        resp.raise_for_status()
        run_data = resp.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]

        # Aguarda o run terminar (polling)
        logger.info(f"  → Run iniciado ({run_id}), aguardando conclusão...")
        for _ in range(60):  # timeout de ~5 min
            time.sleep(5)
            status_resp = requests.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": self.api_token},
                timeout=15,
            )
            status = status_resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Run do Apify falhou com status: {status}")

        # Busca os itens do dataset
        items_resp = requests.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": self.api_token, "limit": max_posts},
            timeout=30,
        )
        items_resp.raise_for_status()
        raw_items = items_resp.json()

        return [self._normalize_post(item, username) for item in raw_items]

    def _normalize_post(self, raw: dict, username: str) -> dict:
        """Normaliza um post bruto do Apify para o formato interno."""
        timestamp_str = raw.get("timestamp", "")
        published_at = None
        if timestamp_str:
            try:
                published_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Tipo do post
        product_type = raw.get("productType", "")
        media_type = raw.get("type", "")
        if product_type == "clips" or media_type == "video":
            post_type = "reel"
        elif raw.get("images") and len(raw.get("images", [])) > 1:
            post_type = "carrossel"
        elif media_type == "sidecar":
            post_type = "carrossel"
        else:
            post_type = "imagem"

        caption = raw.get("caption", "") or ""
        short_caption = caption[:300] + "..." if len(caption) > 300 else caption

        return {
            "username": username,
            "post_id": raw.get("id", ""),
            "url": raw.get("url", f"https://www.instagram.com/p/{raw.get('shortCode', '')}/"),
            "type": post_type,
            "published_at": published_at,
            "caption": short_caption,
            "likes": raw.get("likesCount", 0) or 0,
            "comments": raw.get("commentsCount", 0) or 0,
            "views": raw.get("videoViewCount", None),
            "engagement": (raw.get("likesCount", 0) or 0) + (raw.get("commentsCount", 0) or 0),
        }

    def filter_by_date(self, posts: list[dict], target_date: datetime.date) -> list[dict]:
        """Filtra posts publicados em uma data específica."""
        filtered = []
        for post in posts:
            pub = post.get("published_at")
            if pub and pub.date() == target_date:
                filtered.append(post)
        return filtered