import json
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
import aiohttp
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.event import eventmanager
from app.plugins import _PluginBase
from app.schemas.types import MediaType
from app.utils.http import RequestUtils
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
    # 是否使用SSL验证
    verify_ssl: bool = Field(default=False, description="是否验证SSL证书")
    # 超时时间
    timeout: int = Field(default=30, description="请求超时时间(秒)")

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
    plugin_version = "2.0"
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
    _host: str = None
    _api_key: str = None
    _indexers: List[str] = []
    _proxy: str = None
    _verify_ssl: bool = False
    _timeout: int = 30
    _enabled: bool = False
    _session: Optional[aiohttp.ClientSession] = None

    def init_plugin(self, config: Dict[str, Any] = None) -> None:
        """
        插件初始化
        """
        if config:
            # 初始化配置
            jackett_config = JackettConfig(**config)
            self._host = jackett_config.host.rstrip('/')
            self._api_key = jackett_config.api_key
            self._indexers = jackett_config.indexers
            self._proxy = jackett_config.proxy
            self._verify_ssl = jackett_config.verify_ssl
            self._timeout = jackett_config.timeout
            self._enabled = True
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

    async def _request(self, url: str, params: Dict = None) -> Dict:
        """
        发送请求
        """
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                trust_env=True
            )

        try:
            # 构建请求参数
            if not params:
                params = {}
            params["apikey"] = self._api_key

            # 设置代理
            proxy = self._proxy if self._proxy else None

            # 发送请求
            async with self._session.get(
                url,
                params=params,
                proxy=proxy,
                ssl=self._verify_ssl
            ) as response:
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
        url = urljoin(self._host, "/api/v2.0/indexers")
        result = await self._request(url)
        if isinstance(result, list):
            return result
        return []

    async def search(self, keyword: str, mtype: MediaType = None) -> List[Dict]:
        """
        搜索资源
        :param keyword: 搜索关键词
        :param mtype: 媒体类型
        :return: 搜索结果列表
        """
        if not self._enabled:
            return []

        try:
            # 根据媒体类型设置搜索分类
            category = "5000,5070"  # 默认搜索电影和剧集
            if mtype == MediaType.Movie:
                category = "2000"  # 只搜索电影
            elif mtype == MediaType.TV:
                category = "5000"  # 只搜索剧集

            # 构建搜索参数
            params = {
                "Query": keyword,
                "Category[]": category.split(",")
            }

            # 如果指定了搜索源，则只搜索指定的源
            if self._indexers:
                params["Tracker[]"] = self._indexers

            # 发送搜索请求
            url = urljoin(self._host, "/api/v2.0/indexers/all/results")
            result = await self._request(url, params)

            if not result or "Results" not in result:
                return []

            # 处理搜索结果
            search_results = []
            for item in result.get("Results", []):
                try:
                    # 计算做种和下载人数
                    peers = item.get("Peers", 0)
                    seeders = item.get("Seeders", 0)
                    leechers = peers - seeders if peers > seeders else 0

                    # 转换大小为字节
                    size = item.get("Size", 0)

                    # 添加结果
                    search_results.append({
                        "title": item.get("Title", ""),
                        "description": item.get("Description", ""),
                        "enclosure": item.get("Link", ""),
                        "size": size,
                        "seeders": seeders,
                        "peers": peers,
                        "leechers": leechers,
                        "downloadvolumefactor": item.get("DownloadVolumeFactor", 1),
                        "uploadvolumefactor": item.get("UploadVolumeFactor", 1),
                        "page_url": item.get("Guid", ""),
                        "indexer": item.get("Tracker", ""),
                        "date": item.get("PublishDate", ""),
                        "category": item.get("CategoryDesc", "")
                    })
                except Exception as e:
                    logger.error(f"处理搜索结果异常: {str(e)}")
                    continue

            logger.info(f"Jackett搜索 {keyword} 返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"Jackett搜索异常: {str(e)}")
            return []

    async def test_connection(self) -> Tuple[bool, str]:
        """
        测试连接
        """
        try:
            indexers = await self.get_indexers()
            if indexers:
                return True, "连接成功"
            return False, "未获取到搜索源"
        except Exception as e:
            return False, f"连接失败：{str(e)}"

    def get_form(self) -> List[Dict[str, Any]]:
        """
        获取配置表单
        """
        return [
            {
                'component': 'VTextField',
                'props': {
                    'model': 'host',
                    'label': '服务器地址',
                    'placeholder': 'http://localhost:9117'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'api_key',
                    'label': 'API密钥',
                    'placeholder': '在Jackett管理界面查看'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'indexers',
                    'label': '搜索源',
                    'placeholder': '留空则搜索全部'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'proxy',
                    'label': '代理服务器',
                    'placeholder': 'http://localhost:7890'
                }
            },
            {
                'component': 'VSwitch',
                'props': {
                    'model': 'verify_ssl',
                    'label': '验证SSL证书'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'timeout',
                    'label': '超时时间(秒)',
                    'type': 'number',
                    'placeholder': '30'
                }
            }
        ]

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
        return [
            {
                "path": "/test",
                "endpoint": self.test_connection,
                "methods": ["GET"],
                "summary": "测试连接",
                "description": "测试Jackett服务器连接"
            }
        ] 