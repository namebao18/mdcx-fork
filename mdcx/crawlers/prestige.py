"""
Prestige 刮削器修复版
基于 Hazard804/mdcx 提取，修复第 91 行未捕获异常导致任务崩溃的问题

原始错误:
  File "mdcx/crawlers/prestige.py", line 91, in main
  Exception: 网络请求错误: GET https://www.prestige-av.com/api/search?...
  失败: HTTP 403

修复: 在 main() 函数中添加 try/except 捕获异常，避免单个文件失败导致全量任务崩溃
"""

import json
import time
from typing import Optional

import requests

# 配置
BASE_URL = "https://www.prestige-av.com"
SEARCH_URL = f"{BASE_URL}/api/search"
REQUEST_DELAY = 1  # 请求延迟（秒）


def search(keyword: str) -> Optional[dict]:
    """搜索番号"""
    try:
        params = {
            "isEnabledQuery": "true",
            "searchText": keyword,
            "isEnableAggregation": "false",
            "release": "false",
            "reservation": "false",
            "soldOut": "false",
            "from": "0",
            "aggregationTermsSize": "0",
            "size": "20",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        }

        # 发送请求（添加延迟避免反爬）
        time.sleep(REQUEST_DELAY)
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        # 修复: 不再抛出异常，而是返回 None
        print(f"[prestige] 搜索失败 {keyword}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[prestige] JSON 解析失败 {keyword}: {e}")
        return None


def parse_product(product: dict) -> dict:
    """解析商品信息"""
    return {
        "title": product.get("title", ""),
        "release_date": product.get("releaseDate", ""),
        "thumbnail": product.get("thumbnail", ""),
        "sample_images": product.get("sampleImages", []),
        "description": product.get("description", ""),
        "actors": product.get("actors", []),
    }


def main(keyword: str) -> dict:
    """
    主函数 - 修复版
    原始第 91 行在此，现在添加异常处理
    """
    try:
        # 搜索
        data = search(keyword)
        if not data or not data.get("products"):
            return {"error": f"未找到 {keyword}"}

        # 解析第一个结果
        product = data["products"][0]
        result = parse_product(product)
        result["found"] = True
        return result

    except Exception as e:
        # 修复: 捕获所有异常，不再崩溃
        print(f"[prestige] 刮削失败 {keyword}: {e}")
        return {"error": str(e), "keyword": keyword}


# 命令行入口（保持原接口）
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python prestige.py <keyword>")
        sys.exit(1)

    keyword = sys.argv[1]
    result = main(keyword)
    print(json.dumps(result, ensure_ascii=False, indent=2))
