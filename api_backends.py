import json
from typing import Optional, Tuple

import aiohttp


class DashScopeBackend:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        model: str = "qwen-image-2.0-pro",
        size: str = "1024*1024",
        n: int = 1,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.size = size
        self.n = n
        self.timeout = timeout

    async def generate(self, prompt: str) -> Tuple[bool, Optional[str]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {"size": self.size, "n": self.n},
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return False, f"百炼请求失败 (HTTP {resp.status}): {error_text}"

                    result = await resp.json()
                    return self._parse_response(result)

        except aiohttp.ClientError as e:
            return False, f"百炼网络错误: {str(e)}"
        except Exception as e:
            return False, f"百炼未知错误: {str(e)}"

    def _parse_response(self, result: dict) -> Tuple[bool, Optional[str]]:
        output = result.get("output", {})

        choices = output.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", [])
            for item in content:
                if "image" in item:
                    return True, item["image"]
                if "text" in item:
                    pass

        results = output.get("results", [])
        if results:
            first = results[0]
            if first.get("url"):
                return True, first["url"]
            if first.get("b64_json"):
                return True, f"data:image/png;base64,{first['b64_json']}"

        return False, f"百炼未返回图片: {json.dumps(result, ensure_ascii=False)}"


class SeedreamBackend:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        model: str = "doubao-seedream-4.0",
        size: str = "1024x1024",
        n: int = 1,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.size = size
        self.n = n
        self.timeout = timeout

    async def generate(self, prompt: str) -> Tuple[bool, Optional[str]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": self.size,
            "n": self.n,
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return False, f"Seedream 请求失败 (HTTP {resp.status}): {error_text}"

                    result = await resp.json()
                    data_list = result.get("data", [])
                    if data_list and data_list[0].get("url"):
                        return True, data_list[0]["url"]

                    b64_json = data_list[0].get("b64_json") if data_list else None
                    if b64_json:
                        return True, f"data:image/png;base64,{b64_json}"

                    return False, f"Seedream 未返回图片: {json.dumps(result, ensure_ascii=False)}"

        except aiohttp.ClientError as e:
            return False, f"Seedream 网络错误: {str(e)}"
        except Exception as e:
            return False, f"Seedream 未知错误: {str(e)}"


def create_backend(config: dict):
    provider = config.get("provider", "dashscope")
    if provider == "dashscope":
        return DashScopeBackend(
            api_key=config.get("dashscope_api_key", ""),
            base_url=config.get(
                "dashscope_base_url",
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            ),
            model=config.get("dashscope_model", "qwen-image-2.0-pro"),
            size=config.get("dashscope_size", "1024*1024"),
            n=int(config.get("dashscope_n", 1)),
            timeout=int(config.get("timeout", 120)),
        )
    elif provider == "seedream":
        return SeedreamBackend(
            api_key=config.get("seedream_api_key", ""),
            base_url=config.get(
                "seedream_base_url",
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            ),
            model=config.get("seedream_model", "doubao-seedream-4.0"),
            size=config.get("seedream_size", "1024x1024"),
            n=int(config.get("seedream_n", 1)),
            timeout=int(config.get("timeout", 120)),
        )
    else:
        raise ValueError(f"不支持的文生图接口: {provider}")