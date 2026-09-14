# -*- coding: utf-8 -*-
"""
mdcx JavDB 移动 API crawler（javdb_mobile）
================================================================
基于现成模板 mdcx/crawlers/javdbapi.py 改写，走 JavDB 官方 App 的 JSON API：
  - https://jdforrepam.com/api/v2/search?q=<番号>&type=movie   （搜索，拿 movie id + 官方中文标题）
  - https://jdforrepam.com/api/v2/movies/<id>                    （详情，37 字段）

优点（已实测 2026-09-14，真实库样本命中率 24/25）：
  - 免登录（匿名可用）
  - 不挑 IP（日本/美国/直连全通），无 Cloudflare、无版权限制、无封 IP
  - 字段全：番号/标题/演员+头像/片商/导演/系列/标签/评分/想看/发行/时长/封面/剧照/预告
  - 搜索结果 title 是 JavDB 官方中文译名 → 作 title，mdcx 只需繁转简（省 LLM 翻译）
  - 缺点：无「简介」→ 由 mdcx 其它源（airav_cc/jav321）自动补，无需处理

番号标准化（吸取 mdcx 官方设计）：
  mdcx 内部番号是「带数字前缀」形态（如 259LUXU-1862），由 number.py 的
  get_file_number() 用 ManualConfig.SUREN_DIC 补全而来；而 JavDB 存「不带数字前缀」
  （如 LUXU-1862）。因此本 crawler 反向用 SUREN_DIC 去前缀后搜索。含 S-Cute 特例
  （229SCUTE-953 → SCUTE-953）。普通番号（SSIS-465）原样即可，零误伤。

部署步骤（改 mdcx-fork 仓库，走 CI 重建镜像）：
  1. 本文件放到 mdcx/crawlers/javdb_mobile.py
  2. mdcx/config/enums.py 的 Website 枚举加：JAVDB_MOBILE = "javdb_mobile"
  3. mdcx/crawlers/__init__.py 加：register_crawler(javdb_mobile.JavdbMobileCrawler)
  4. mdcx/config/models.py：DEFAULT_FIELD_SITE_PRIORITY + website_youma/suren 加 JAVDB_MOBILE
  5. 运行配置 config.v2.json 同步加 javdb_mobile（见方案文档）
  6. push → GitHub Actions 重建镜像 → NAS docker compose pull && up -d
"""
import hashlib
import re
import time
from typing import override
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict

from mdcx.config.models import Website
from mdcx.manual import ManualConfig
from mdcx.models.types import CrawlerResult

from .base import CralwerException, CrawlerData
from .dmm_new import DMMContext, DmmCrawler

# JavDB 移动端签名（客户端公开契约，硬编码；若上游轮换需同步更新）
_JAVDB_MOBILE_BASE = "https://jdforrepam.com"
_JAVDB_SIG_PREFIX = "lpw6vgqzsp"
_JAVDB_SIG_SECRET = (
    "71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa"
)

# 无码关键词（判断 mosaic 用；"破解"是有码破解，需排除）
_UNCENSORED_KEYWORDS = ("無碼", "無修正", "无码", "无修正", "無修", "Uncensored")


class JavdbMobileMovie(BaseModel):
    """移动 API /api/v2/movies/{id} 的 movie 对象（只取需要的字段）"""
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    number: str | None = None
    title: str | None = None
    cover_url: str | None = None
    thumb_url: str | None = None
    duration: int | str | None = None
    score: float | str | None = None
    want_watch_count: int | None = None
    release_date: str | None = None
    maker_name: str | None = None
    publisher_name: str | None = None
    series_name: str | None = None
    director_name: str | None = None
    tags: list[dict] | None = None
    actors: list[dict] | None = None
    preview_images: list[dict] | None = None
    preview_video_url: str | None = None


class JavdbMobileCrawler(DmmCrawler):
    @classmethod
    @override
    def site(cls) -> Website:
        return Website.JAVDB_MOBILE

    @classmethod
    @override
    def base_url_(cls) -> str:
        return _JAVDB_MOBILE_BASE

    # ---------------- 工具 ----------------
    @staticmethod
    def _headers() -> dict[str, str]:
        """构造移动端签名请求头（免登录）"""
        ts = int(time.time())
        digest = hashlib.md5(f"{ts}{_JAVDB_SIG_SECRET}".encode("utf-8")).hexdigest()
        return {
            "User-Agent": "Dart/3.5 (dart:io)",
            "Accept-Language": "zh-TW",
            "jdSignature": f"{ts}.{_JAVDB_SIG_PREFIX}.{digest}",
            "Accept": "application/json",
        }

    @staticmethod
    def _norm_number(value: str) -> str:
        """番号标准化（比较用）：去分隔符 + 大写"""
        return re.sub(r"[-_.\s]", "", str(value or "")).upper()

    @classmethod
    def _search_variants(cls, number: str) -> list[str]:
        """
        生成搜索变体：原样 + 去数字前缀。
        吸取 mdcx number.py 的 SUREN_DIC 设计（mdcx 内部带前缀，JavDB 不带）。
        """
        variants = [number]
        upper = number.upper()
        for key, value in ManualConfig.SUREN_DIC.items():
            tag = key.rstrip("-").upper()          # "LUXU" / "SHN" / "CUTE"
            # 常规素人：{value}{tag}，如 259LUXU / 200GANA / 116SHN
            if upper.startswith(f"{value}{tag}"):
                variants.append(number[len(str(value)):])
                break
            # S-Cute 特例：229SCUTE-953（key="CUTE-" 但实际番号是 "SCUTE-"）
            if tag == "CUTE" and upper.startswith(f"{value}SCUTE"):
                variants.append(number[len(str(value)):])
                break
        else:
            # SUREN_DIC 未覆盖时通用兜底：3位数字 + 字母 + 破折号 + 数字（如 123ABC-456）
            if m := re.match(r"^(\d{3})([A-Za-z]+-\d+)$", number):
                variants.append(m.group(2))
        return list(dict.fromkeys(variants))

    @classmethod
    def _judge_mosaic(cls, title: str, tags: list[str]) -> str:
        """判断有码/无码（模仿 mdcx 现有源；'破解'属有码破解，排除）"""
        text = f"{title} {' '.join(tags)}"
        if "破解" in text:
            return "有码"
        return "无码" if any(kw in text for kw in _UNCENSORED_KEYWORDS) else "有码"

    # ---------------- 搜索 ----------------
    async def _find_movie(self, ctx: DMMContext, number: str) -> dict | None:
        """按番号（含变体）搜索，返回精确匹配的 movie 搜索结果项（含 id + 官方标题）"""
        target = self._norm_number(number)
        for query in self._search_variants(number):
            url = f"{self.base_url}/api/v2/search?{urlencode({'q': query, 'type': 'movie', 'limit': 10})}"
            ctx.debug(f"移动API搜索: {url}")
            resp, error = await self.async_client.get_json(url, headers=self._headers())
            if resp is None:
                ctx.debug(f"搜索失败({query}): {error}")
                continue
            movies = (resp.get("data") or {}).get("movies") or []
            q_norm = self._norm_number(query)
            for m in movies:
                m_norm = self._norm_number(m.get("number"))
                # 精确匹配：与输入番号相等，或与当前查询变体相等
                if m_norm == target or m_norm == q_norm:
                    return m
        return None

    # ---------------- 主流程 ----------------
    @override
    async def _run(self, ctx: DMMContext) -> CrawlerResult:
        number = ctx.input.number.strip()
        if not number:
            raise CralwerException("番号为空")

        hit = await self._find_movie(ctx, number)
        if not hit or not hit.get("id"):
            raise CralwerException("移动API未找到该番号")

        movie_id = hit["id"]
        detail_url = f"{self.base_url}/api/v2/movies/{movie_id}"
        ctx.debug(f"移动API详情: {detail_url}")
        resp, error = await self.async_client.get_json(detail_url, headers=self._headers())
        if resp is None:
            raise CralwerException(f"详情请求失败: {error}")
        movie_raw = (resp.get("data") or {}).get("movie") or {}
        if not movie_raw:
            raise CralwerException("详情返回空")

        movie = JavdbMobileMovie.model_validate(movie_raw)
        data = self._to_crawler_data(
            movie,
            fallback_number=number,
            search_title=str(hit.get("title") or ""),  # 搜索结果的官方中文标题
        )
        data.source = self.site().value
        result = data.to_result()
        return await self.post_process(ctx, result)

    def _to_crawler_data(
        self,
        m: JavdbMobileMovie,
        *,
        fallback_number: str,
        search_title: str = "",
    ) -> CrawlerData:
        """移动 API movie -> CrawlerData（mdcx 统一结构）"""
        actors = [a.get("name", "") for a in (m.actors or []) if a.get("name")]
        tags = [t.get("name", "") for t in (m.tags or []) if t.get("name")]
        previews = [(p.get("large_url") or p.get("thumb_url")) for p in (m.preview_images or [])]

        cn_title = search_title.strip()          # JavDB 官方中文译名（繁中，mdcx 自动转简）
        jp_title = (m.title or "").strip()       # 详情日文原名
        # title 优先中文（省一次 LLM 翻译），originaltitle 用日文原名
        title = cn_title or jp_title
        originaltitle = jp_title or cn_title

        return CrawlerData(
            # 番号保持 mdcx 输入形态（带前缀），不用 JavDB 的（不带前缀），
            # 避免同一影片因不同源番号写法不同而分到不同目录
            number=fallback_number,
            title=title,
            originaltitle=originaltitle,
            outline="",                          # 移动API无简介 → 留空由其它源补
            originalplot="",
            thumb=(m.thumb_url or "").strip(),
            poster=(m.cover_url or "").strip(),
            trailer=(m.preview_video_url or "").strip(),
            release=(m.release_date or "").strip(),
            runtime=str(m.duration) if m.duration else "",
            studio=(m.maker_name or "").strip(),
            publisher=(m.publisher_name or "").strip(),   # post_process 用 studio 兜底
            series=(m.series_name or "").strip(),
            actors=actors,
            all_actors=actors,
            directors=[m.director_name] if m.director_name else [],
            tags=tags,
            extrafanart=[u for u in previews if u],
            score=str(m.score) if m.score is not None else "",
            wanted=str(m.want_watch_count) if m.want_watch_count is not None else "",
            external_id=m.id or "",
            mosaic=self._judge_mosaic(title, tags),
        )

    @override
    async def post_process(self, ctx: DMMContext, res: CrawlerResult) -> CrawlerResult:
        if not res.publisher:
            res.publisher = res.studio
        if not res.originaltitle:
            res.originaltitle = res.title
        return await super().post_process(ctx, res)
