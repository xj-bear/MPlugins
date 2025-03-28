import json
from typing import Dict, List, Optional, Any
import aiohttp
from pydantic import BaseModel, Field
from app.core.event import eventmanager
from app.plugins import _PluginBase
from app.schemas.types import MediaType
from app.log import logger

class JackettConfig(BaseModel):
    """
    Jackett插件配置
    """
    # Jackett服务器地址
    host: str = Field(default="http://localhost:9117", description="Jackett服务器地址")
    # API密钥
    api_key: str = Field(default="", description="Jackett API密钥")
    # 搜索源列表
    indexers: Optional[List[str]] = Field(default=[], description="指定搜索源列表")
    # 代理服务器
    proxy: Optional[str] = Field(default="", description="代理服务器地址")

class JackettService:
    """
    Jackett服务类
    """
    def __init__(self, host: str, api_key: str, indexers: Optional[List[str]] = None, proxy: Optional[str] = None):
        """
        初始化Jackett服务
        """
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.indexers = indexers or []
        self.proxy = proxy
        # API路径
        self.api_url = f"{self.host}/api/v2.0"
        # 请求头
        self.headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }

    async def _request(self, method: str, url: str, **kwargs) -> Dict:
        """
        发送HTTP请求
        """
        try:
            async with aiohttp.ClientSession() as session:
                # 设置代理
                if self.proxy:
                    kwargs["proxy"] = self.proxy
                async with session.request(method, url, headers=self.headers, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"请求失败: {response.status} - {await response.text()}")
                        return {}
        except Exception as e:
            logger.error(f"请求异常: {str(e)}")
            return {}

    async def get_indexers(self) -> List[Dict]:
        """
        获取所有搜索源
        """
        url = f"{self.api_url}/indexers"
        result = await self._request("GET", url)
        if isinstance(result, list):
            return result
        return []

    async def search(self, keyword: str, category: str = "5000,5070") -> List[Dict]:
        """
        搜索资源
        :param keyword: 搜索关键词
        :param category: 资源类型，默认为Movies和TV
        :return: 搜索结果列表
        """
        # 构建搜索参数
        params = {
            "apikey": self.api_key,
            "Query": keyword,
            "Category[]": category.split(",")
        }
        
        # 如果指定了搜索源，则只搜索指定的源
        if self.indexers:
            params["Tracker[]"] = self.indexers
        
        url = f"{self.api_url}/indexers/all/results"
        result = await self._request("GET", url, params=params)
        
        if not result or "Results" not in result:
            return []
            
        # 处理搜索结果
        search_results = []
        for item in result.get("Results", []):
            try:
                search_results.append({
                    "title": item.get("Title", ""),
                    "description": item.get("Description", ""),
                    "size": item.get("Size", 0),
                    "seeders": item.get("Seeders", 0),
                    "leechers": item.get("Peers", 0) - item.get("Seeders", 0),
                    "downloadvolumefactor": item.get("DownloadVolumeFactor", 1),
                    "uploadvolumefactor": item.get("UploadVolumeFactor", 1),
                    "link": item.get("Link", ""),
                    "guid": item.get("Guid", ""),
                    "pubdate": item.get("PublishDate", ""),
                    "indexer": item.get("Tracker", ""),
                    "category": item.get("CategoryDesc", "")
                })
            except Exception as e:
                logger.error(f"处理搜索结果异常: {str(e)}")
                continue
                
        return search_results

class JackettPlugin(_PluginBase):
    """
    Jackett搜索插件
    """
    # 插件名称
    plugin_name = "Jackett搜索"
    # 插件描述
    plugin_desc = "通过Jackett API扩展资源搜索能力，支持多个资源站点搜索。"
    # 插件图标
    plugin_icon = "search.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "jason"
    # 作者主页
    author_url = "https://github.com/username"
    # 插件配置项ID前缀
    plugin_config_prefix = "jackett_"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _service: Optional[JackettService] = None
    _enabled: bool = False

    def init_plugin(self, config: Dict[str, Any] = None) -> None:
        """
        插件初始化
        """
        self._enabled = True
        if config:
            # 初始化配置
            jackett_config = JackettConfig(**config)
            # 初始化服务
            self._service = JackettService(
                host=jackett_config.host,
                api_key=jackett_config.api_key,
                indexers=jackett_config.indexers,
                proxy=jackett_config.proxy
            )
            # 注册事件
            eventmanager.register_event(eventmanager.EventType.SearchTorrent, self.search)
            logger.info(f"Jackett插件初始化完成")
        else:
            self._enabled = False
            logger.error(f"Jackett插件初始化失败：配置为空")

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return self._enabled

    async def search(self, keyword: str, mtype: MediaType = None) -> List[Dict]:
        """
        搜索资源
        :param keyword: 搜索关键词
        :param mtype: 媒体类型
        :return: 搜索结果列表
        """
        if not self._enabled or not self._service:
            return []

        try:
            # 根据媒体类型设置搜索分类
            category = "5000,5070"  # 默认搜索电影和剧集
            if mtype == MediaType.Movie:
                category = "5000"  # 只搜索电影
            elif mtype == MediaType.TV:
                category = "5070"  # 只搜索剧集

            # 调用Jackett API搜索
            results = await self._service.search(keyword, category)
            logger.info(f"Jackett搜索 {keyword} 返回 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"Jackett搜索异常: {str(e)}")
            return []

    @staticmethod
    def get_command() -> List[Dict]:
        """
        注册命令
        """
        return []

    def get_api(self) -> List[Dict]:
        """
        注册API
        """
        return [] 