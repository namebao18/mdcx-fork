#!/usr/bin/env python3
import re
from typing import override

from ..config.models import Website
from .base import BaseCrawler, Context, CralwerException, CrawlerData

SITE = "https://www.prestige-av.com"


def get_actor(page_data):
    """获取演员列表（容错：字段缺失时返回空列表）"""
    actor_new_list = []
    try:
        for each in page_data.get("actress") or []:
            name = (each or {}).get("name")
            if name:
                actor_new_list.append(name.replace(" ", ""))
    except Exception:
        pass
    return actor_new_list


def get_extrafanart(page_data):
    """获取剧照列表（容错：字段缺失时返回空列表）"""
    result = []
    try:
        for each in page_data.get("media") or []:
            path = (each or {}).get("path")
            if path:
                result.append(f"{SITE}/api/media/" + path)
    except Exception:
        pass
    return result


def get_year(release):
    try:
        result = str(re.search(r"\d{4}", release).group())
        return result
    except Exception:
        return release


def get_tag(page_data):
    """获取标签（容错：字段缺失时返回空列表）"""
    new_list = []
    try:
        for each in page_data.get("genre") or []:
            name = (each or {}).get("name")
            if name:
                new_list.append(name)
    except Exception:
        pass
    return new_list


def get_real_url(html_search, number):
    """从搜索结果中匹配番号对应的详情地址（容错：结构异常时返回空串）"""
    try:
        result = html_search["hits"]["hits"]
    except Exception:
        return ""
    for each in result or []:
        try:
            source = each["_source"]
            productUuid = source["productUuid"]
            deliveryItemId = source["deliveryItemId"]
        except Exception:
            continue
        if deliveryItemId.endswith(number.upper()):
            return f"{SITE}/api/product/" + productUuid
    return ""


def get_media_path(page_data, key):
    try:
        path = page_data[key]["path"]
        if path:
            media_url = f"{SITE}/api/media/" + path
            return "" if "noimage" in media_url else media_url
    except Exception:
        return ""
    return ""


class PrestigeCrawler(BaseCrawler):
    @classmethod
    @override
    def site(cls) -> Website:
        return Website.PRESTIGE

    @classmethod
    @override
    def base_url_(cls) -> str:
        return SITE

    @override
    async def _run(self, ctx: Context):
        # ===== 魔改：整个流程包一层异常兜底 =====
        # 原版在字段缺失 / 网络异常时会抛出未捕获异常，导致该站点的刮削直接中断。
        # 这里统一转换为 CralwerException，交给上层按「单个网站失败」处理，
        # 不会影响其它数据源与整个刮削任务。
        try:
            return await self._run_inner(ctx)
        except CralwerException:
            raise
        except Exception as e:
            raise CralwerException(f"prestige 解析异常: {type(e).__name__}: {e}") from e

    async def _run_inner(self, ctx: Context):
        real_url = ""
        if ctx.input.appoint_url:
            real_url = ctx.input.appoint_url.replace("goods", "api/product")

        if not real_url:
            search_url = (
                f"{self.base_url}/api/search?isEnabledQuery=true&searchText={ctx.input.number}"
                "&isEnableAggregation=false&release=false&reservation=false&soldOut=false"
                "&from=0&aggregationTermsSize=0&size=20"
            )
            ctx.debug(f"搜索地址: {search_url}")
            ctx.debug_info.search_urls = [search_url]
            html_search, error = await self.async_client.get_json(search_url)
            if html_search is None:
                raise CralwerException(f"网络请求错误: {error}")
            real_url = get_real_url(html_search, ctx.input.number)
            if not real_url:
                raise CralwerException("搜索结果: 未匹配到番号！")

        detail_url = real_url.replace("api/product", "goods")
        ctx.debug(f"番号地址: {detail_url}")
        ctx.debug_info.detail_urls = [detail_url]

        page_data, error = await self.async_client.get_json(real_url)
        if page_data is None:
            raise CralwerException(f"网络请求错误: {error}")
        if not isinstance(page_data, dict):
            raise CralwerException(f"数据格式异常: 期望 dict，实际 {type(page_data).__name__}")

        title = str(page_data.get("title") or "").replace("【配信専用】", "").strip()
        if not title:
            raise CralwerException("数据获取失败: 未获取到 title！")

        release = ""
        try:
            release = page_data["sku"][0]["salesStartAt"][:10]
        except Exception:
            pass
        try:
            director = page_data["directors"][0]["name"]
        except Exception:
            director = ""
        try:
            series = page_data["series"]["name"]
        except Exception:
            series = ""
        try:
            studio = page_data["maker"]["name"]
        except Exception:
            studio = ""
        try:
            publisher = page_data["label"]["name"]
        except Exception:
            publisher = ""
        try:
            trailer = f"{SITE}/api/media/" + page_data["movie"]["path"]
        except Exception:
            trailer = ""

        body = str(page_data.get("body") or "")

        data = CrawlerData(
            number=ctx.input.number,
            title=title,
            originaltitle=title,
            actors=get_actor(page_data),
            outline=body,
            originalplot=body,
            tags=get_tag(page_data),
            release=release,
            year=get_year(release),
            runtime=str(page_data.get("playTime") or ""),
            score="",
            series=series,
            directors=[director] if director else [],
            studio=studio,
            publisher=publisher,
            thumb=get_media_path(page_data, "packageImage"),
            poster=get_media_path(page_data, "thumbnail"),
            extrafanart=get_extrafanart(page_data),
            trailer=trailer,
            image_download=True,
            mosaic="有码",
            external_id=detail_url,
            wanted="",
        )
        result = data.to_result()
        result.source = self.site().value
        ctx.debug("数据获取成功！")
        return result

    @override
    async def _generate_search_url(self, ctx: Context) -> list[str] | str | None:
        return None

    @override
    async def _parse_search_page(self, ctx: Context, html, search_url: str) -> list[str] | str | None:
        return None

    @override
    async def _parse_detail_page(self, ctx: Context, html, detail_url: str) -> CrawlerData | None:
        return None
