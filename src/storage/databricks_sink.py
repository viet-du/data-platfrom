"""
Databricks Volume sink (optional backend).

Disabled by default; enable only when DATABRICKS_HOST + DATABRICKS_TOKEN +
DATABRICKS_VOLUME_PATH are set. Implement here when you want raw JSON
to land in Databricks instead of Drive (useful if you have a Databricks
SQL Warehouse doing the silver/gold transform).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .cloud_sink import CloudSink

logger = logging.getLogger(__name__)


class DatabricksVolumeSink(CloudSink):
    """Write JSON batches into a Databricks Unity Catalog Volume.

    Requires:
        DATABRICKS_HOST       e.g. https://dbc-xxx.cloud.databricks.com
        DATABRICKS_TOKEN      personal access token
        DATABRICKS_VOLUME_PATH e.g. /Volumes/main/default/news-raw
    """

    name = "databricks_volume"

    def __init__(
        self,
        host: str,
        token: str,
        volume_path: str,
    ):
        self.host = host.rstrip("/")
        self.token = token
        self.volume_path = volume_path.rstrip("/")

    def write_batch(self, source: str, articles: List[Dict[str, Any]]) -> Optional[str]:
        if not articles:
            return None

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rel_path = f"{self.volume_path}/{source}/{source}_{ts}.json"
        body = json.dumps(
            {
                "source": source,
                "crawled_at": datetime.utcnow().isoformat(),
                "article_count": len(articles),
                "articles": articles,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return self._put(rel_path, body)

    def write_payload(self, source: str, payload: Dict[str, Any], filename: str) -> Optional[str]:
        if payload is None:
            return None
        rel_path = f"{self.volume_path}/{source}/{filename}"
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return self._put(rel_path, body)

    def _put(self, rel_path: str, body: bytes) -> Optional[str]:
        import requests

        url = f"{self.host}/api/2.0/fs/files{rel_path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/octet-stream",
        }
        try:
            resp = requests.put(url, headers=headers, data=body, timeout=60)
            if not resp.ok:
                logger.error(
                    "Databricks PUT %s failed: HTTP %s — %s",
                    rel_path,
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            logger.info("Databricks upload OK: %s", rel_path)
            return rel_path
        except requests.RequestException as e:
            logger.error("Databricks PUT error: %s", e)
            return None

    def health_check(self) -> bool:
        try:
            import requests

            url = f"{self.host}/api/2.0/fs/directories{self.volume_path}"
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            )
            return resp.ok
        except requests.RequestException as e:
            logger.warning("Databricks health check failed: %s", e)
            return False


def try_build_databricks_sink() -> Optional[DatabricksVolumeSink]:
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    volume = os.environ.get("DATABRICKS_VOLUME_PATH")
    if not (host and token and volume):
        return None
    return DatabricksVolumeSink(host=host, token=token, volume_path=volume)