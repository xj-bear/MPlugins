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
    plugin_icon = "https://raw.githubusercontent.com/Jackett/Jackett/master/src/Jackett.Common/Content/favicon.ico"
    # 插件版本
    plugin_version = "1.08"
    # 插件作者
    plugin_author = "jason"
    # 作者主页
    author_url = "https://github.com/xj-bear"
    # 插件配置项ID前缀
    plugin_config_prefix = "jackett_"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _host = None
    _api_key = None
    _indexers = []
    _proxy = None
    _verify_ssl = False
    _timeout = 30
    _session = None
    _enabled = False
    _initialized = False

    async def init_plugin(self, config: Dict[str, Any] = None) -> None:
        """
        插件初始化
        """
        if self._initialized:
            return
        
        try:
            if not config:
                logger.error("Jackett插件初始化失败：配置为空")
                return

            self._host = config.get("host", "").rstrip('/')
            self._api_key = config.get('api_key')
            self._indexers = config.get('indexers', [])
            self._proxy = config.get('proxy')
            self._verify_ssl = config.get('verify_ssl', False)
            self._timeout = config.get('timeout', 30)

            if not self._host or not self._api_key:
                logger.error("Jackett插件初始化失败：服务器地址或API密钥未配置")
                return

            # 创建新的会话
            if not self._session:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                self._session = aiohttp.ClientSession(timeout=timeout)
                logger.info("Jackett创建新的HTTP会话")

            # 测试连接
            success, message = await self.test_connection()
            if not success:
                logger.error(f"Jackett连接测试失败：{message}")
                return

            # 注册事件
            eventmanager.register_event(eventmanager.EventType.SearchTorrent, self.search)
            
            self._enabled = True
            self._initialized = True
            logger.info(f"Jackett插件初始化完成：host={self._host}, indexers={self._indexers}")

        except Exception as e:
            logger.error(f"Jackett插件初始化出错：{str(e)}")
            self._enabled = False
            self._initialized = False

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
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Jackett创建新的HTTP会话")

        try:
            # 构建请求参数
            if not params:
                params = {}
            params["apikey"] = self._api_key

            # 发送请求
            async with self._session.get(
                url,
                params=params,
                proxy=self._proxy,
                ssl=self._verify_ssl,
                timeout=self._timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Jackett请求失败: HTTP {response.status} - {error_text}")
                    return {}

        except aiohttp.ClientTimeout:
            logger.error(f"Jackett请求超时: {url}")
            return {}
        except aiohttp.ClientError as e:
            logger.error(f"Jackett网络错误: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Jackett请求异常: {str(e)}")
            return {}

    async def get_indexers(self) -> List[Dict]:
        """
        获取所有搜索源
        """
        if not self._enabled:
            return []
            
        url = urljoin(self._host, "/api/v2.0/indexers")
        result = await self._request(url)
        if isinstance(result, list):
            return result
        return []

    async def search(self, keyword: str, mtype: MediaType = None) -> List[Dict]:
        """
        搜索资源
        """
        if not self._enabled:
            return []

        if not keyword:
            logger.warning("搜索关键词为空")
            return []

        try:
            # 根据媒体类型设置搜索分类
            category = None
            if mtype == MediaType.Movie:
                category = "2000"  # 电影
            elif mtype == MediaType.TV:
                category = "5000"  # 剧集
            else:
                category = "2000,5000"  # 电影和剧集

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
                    peers = int(item.get("Peers", 0))
                    seeders = int(item.get("Seeders", 0))
                    leechers = peers - seeders if peers > seeders else 0

                    # 转换大小为字节
                    size = int(item.get("Size", 0))

                    # 添加结果
                    search_results.append({
                        "title": item.get("Title", ""),
                        "description": item.get("Description", ""),
                        "enclosure": item.get("Link", ""),
                        "size": size,
                        "seeders": seeders,
                        "peers": peers,
                        "leechers": leechers,
                        "downloadvolumefactor": float(item.get("DownloadVolumeFactor", 1)),
                        "uploadvolumefactor": float(item.get("UploadVolumeFactor", 1)),
                        "page_url": item.get("Guid", ""),
                        "indexer": item.get("Tracker", ""),
                        "date": item.get("PublishDate", ""),
                        "category": item.get("CategoryDesc", "")
                    })
                except Exception as e:
                    logger.error(f"处理搜索结果异常: {str(e)}")
                    continue

            logger.info(f"Jackett搜索完成，返回 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"Jackett搜索异常: {str(e)}")
            return []

    async def test_connection(self) -> Tuple[bool, str]:
        """
        测试连接
        """
        if not self._host or not self._api_key:
            return False, "服务器地址或API密钥未配置"

        try:
            url = urljoin(self._host, "/api/v2.0/indexers")
            result = await self._request(url)
            if isinstance(result, list):
                return True, "连接成功"
            return False, "未获取到搜索源"
        except Exception as e:
            return False, f"连接失败：{str(e)}"

    def get_form(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        获取配置表单
        """
        return {
            "schema": [
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
                        'placeholder': '在Jackett管理页面获取'
                    }
                },
                {
                    'component': 'VTextField',
                    'props': {
                        'model': 'proxy',
                        'label': '代理服务器',
                        'placeholder': '可选，示例：http://localhost:7890'
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
                    'component': 'VSlider',
                    'props': {
                        'model': 'timeout',
                        'label': '超时时间(秒)',
                        'min': 10,
                        'max': 60,
                        'step': 5
                    }
                }
            ]
        }, {
            'host': 'http://localhost:9117',
            'api_key': '',
            'indexers': [],
            'proxy': '',
            'verify_ssl': False,
            'timeout': 30
        }

    async def stop_service(self):
        """
        停止插件服务
        """
        try:
            if self._session:
                await self._session.close()
                self._session = None
                logger.info("Jackett关闭HTTP会话")
        except Exception as e:
            logger.error(f"关闭Jackett会话异常：{str(e)}")
        finally:
            self._enabled = False
            self._initialized = False

    @staticmethod
    def get_command() -> List[Dict]:
        """
        获取命令
        """
        return []

    def get_api(self) -> List[Dict]:
        """
        获取API
        """
        return [
            {
                "path": "/jackett/test",
                "endpoint": self.test_connection,
                "methods": ["GET"],
                "summary": "测试Jackett连接",
                "description": "测试Jackett服务器连接是否正常"
            }
        ] 