import json
import os
import xml.etree.ElementTree
import requests
from urllib.parse import urlencode, unquote
from typing import Dict, List, Any, Optional, Tuple

from app.core.config import settings
from app.core.event import eventmanager
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType, MediaType


class Jackett(_PluginBase):
    # 插件名称
    plugin_name = "Jackett搜索器"
    # 插件描述
    plugin_desc = "支持Jackett API的资源搜索器，用于电影、电视剧资源检索。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/Jackett/Jackett/master/.github/jackett-logo.svg"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "jason"
    # 作者主页
    author_url = "https://github.com/xj-bear"
    # 插件配置项ID前缀
    plugin_config_prefix = "jackett_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _api_key = None
    _url = None
    _timeout = None
    _indexers = None

    # 配置属性
    _enabled = False
    _api_url = "http://127.0.0.1:9117"
    _api_key_value = ""
    _indexers_filter = ""  # 使用的索引器，为空使用全部
    _req_timeout = 60

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            self._api_url = config.get("api_url", "http://127.0.0.1:9117").rstrip('/')
            self._api_key_value = config.get("api_key", "")
            self._indexers_filter = config.get("indexers", "")
            self._req_timeout = int(config.get("timeout", 60))

        self._api_key = self._api_key_value
        self._url = self._api_url
        self._timeout = self._req_timeout
        
        # 获取全部索引器
        if self._enabled and self._api_key and self._url:
            try:
                self._indexers = self._get_indexers()
                logger.info(f"Jackett插件初始化完成，共加载索引器：{len(self._indexers)} 个")
            except Exception as e:
                logger.error(f"Jackett插件初始化失败：{str(e)}")
                self._indexers = []

    def get_state(self) -> bool:
        return self._enabled and self._api_key and self._url

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        :return: 注册成功的服务列表
        """
        return [{
            "id": "Jackett",
            "name": "Jackett搜索器",
            "trigger": [
                "search_medias"  # 通过添加这个能力，使得jackett也能被调用作为搜索器
            ],
            "schema": [{
                "name": "search_medias",
                "description": "搜索媒体资源",
                "doc": "搜索媒体资源",
                "parameters": {
                    "type": "object",
                    "required": ["key_word"],
                    "properties": {
                        "key_word": {
                            "type": "string",
                            "description": "搜索关键词",
                        },
                        "media_type": {
                            "type": "string",
                            "description": "媒体类型，movie/tv，为空则全部"
                        },
                        "imdb_id": {
                            "type": "string",
                            "description": "IMDB ID，为空则全部"
                        }
                    }
                }
            }]
        }]

    @eventmanager.register(EventType.SearchMedias)
    def search_medias(self, event):
        """
        搜索资源并返回结果
        """
        if not self.get_state():
            return

        # 查询参数
        key_word = event.event_data.get("key_word")
        media_type = event.event_data.get("media_type")
        imdb_id = event.event_data.get("imdb_id")

        if not key_word:
            return None

        logger.info(f"Jackett开始搜索：{key_word}，类型：{media_type}，IMDB ID：{imdb_id}")

        results = []
        try:
            indexers = []
            # 过滤索引器
            if self._indexers_filter:
                filter_indexers = self._indexers_filter.split(',')
                for indexer in self._indexers:
                    if indexer.get("id") in filter_indexers:
                        indexers.append(indexer)
            else:
                indexers = self._indexers

            # 分别使用每个索引器搜索
            for indexer in indexers:
                indexer_id = indexer.get("id")
                try:
                    search_results = self._search_indexer(indexer_id, key_word, media_type, imdb_id)
                    if search_results:
                        for item in search_results:
                            item["site"] = indexer.get("name") or indexer_id
                            results.append(item)
                except Exception as e:
                    logger.error(f"Jackett搜索索引器 {indexer_id} 失败：{str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Jackett搜索失败：{str(e)}")

        # 返回结果
        if results:
            event.event_data["results"] = results
            return results

        return None

    def _get_indexers(self) -> List[Dict]:
        """
        获取所有可用的索引器
        """
        try:
            api_url = f"{self._url}/api/v2.0/indexers?apikey={self._api_key}"
            response = requests.get(api_url, timeout=self._timeout)
            if response.status_code != 200:
                logger.error(f"获取Jackett索引器失败：{response.status_code} - {response.text}")
                return []
            
            return response.json()
        except Exception as e:
            logger.error(f"获取Jackett索引器出错：{str(e)}")
            return []

    def _search_indexer(self, indexer_id: str, key_word: str, media_type: str = None, imdb_id: str = None) -> List[Dict]:
        """
        使用指定索引器搜索资源
        """
        # 构建查询参数
        params = {
            "apikey": self._api_key,
            "t": "search",
            "q": key_word
        }

        # 添加IMDB ID过滤
        if imdb_id:
            params["imdbid"] = imdb_id.replace("tt", "")

        # 添加类型过滤
        if media_type:
            if media_type == MediaType.MOVIE:
                params["cat"] = "2000,2010,2020,2030,2040,2045,2050,2060"
            elif media_type == MediaType.TV:
                params["cat"] = "5000,5010,5020,5030,5040,5045,5050,5060,5070,5080"

        # 构建API URL
        api_url = f"{self._url}/api/v2.0/indexers/{indexer_id}/results/torznab/api?{urlencode(params)}"

        try:
            response = requests.get(api_url, timeout=self._timeout)
            if response.status_code != 200:
                logger.error(f"搜索Jackett索引器 {indexer_id} 失败：{response.status_code} - {response.text}")
                return []

            # 解析XML结果
            try:
                return self._parse_torznab_xml(response.text)
            except Exception as e:
                logger.error(f"解析Jackett响应失败：{str(e)}")
                return []
        except Exception as e:
            logger.error(f"调用Jackett API失败：{str(e)}")
            return []

    def _parse_torznab_xml(self, xml_content: str) -> List[Dict]:
        """
        解析Torznab XML响应为资源列表
        """
        results = []
        try:
            root = xml.etree.ElementTree.fromstring(xml_content)
            items = root.findall(".//item")
            
            for item in items:
                # 基本信息
                title = item.find("title")
                title = title.text if title is not None else ""
                
                # 链接信息（磁力链接优先）
                link = None
                for enclosure in item.findall("enclosure"):
                    if enclosure.get("type") == "application/x-bittorrent":
                        link = enclosure.get("url")
                        break
                
                if not link:
                    # 查找是否有磁力链接
                    magnet = item.find(".//torznab:attr[@name='magneturl']", {"torznab": "http://torznab.com/schemas/2015/feed"})
                    if magnet is not None:
                        link = magnet.get("value")
                    else:
                        link_elem = item.find("link")
                        link = link_elem.text if link_elem is not None else None
                
                if not link:
                    continue
                
                # 大小
                size_elem = item.find("size")
                size = int(size_elem.text) if size_elem is not None else 0
                
                # 发布时间
                pubdate_elem = item.find("pubDate")
                pubdate = pubdate_elem.text if pubdate_elem is not None else ""
                
                # 种子信息
                seeders = 0
                peers = 0
                leechers = 0
                
                for attr in item.findall(".//{http://torznab.com/schemas/2015/feed}attr"):
                    name = attr.get("name")
                    value = attr.get("value")
                    if name == "seeders" and value:
                        seeders = int(value)
                    elif name == "peers" and value:
                        peers = int(value)
                
                # 计算leechers
                if peers > 0 and seeders > 0:
                    leechers = peers - seeders
                
                # 资源详情页
                desc_link = ""
                comments = item.find("comments")
                if comments is not None:
                    desc_link = comments.text
                else:
                    guid = item.find("guid")
                    if guid is not None:
                        desc_link = guid.text
                
                # 构建结果
                result = {
                    "title": title,
                    "magnet_link": link,
                    "enclosure": link,
                    "description": "",
                    "type": "torrent",
                    "size": size,
                    "pubdate": pubdate,
                    "seeders": seeders,
                    "peers": peers,
                    "leechers": leechers,
                    "page_url": desc_link
                }
                
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"解析Torznab XML出错：{str(e)}")
            return []

    def get_form(self) -> List[Dict[str, Any]]:
        """
        拼装插件配置页面表单
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 8
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_url',
                                            'label': 'Jackett地址',
                                            'placeholder': 'http://127.0.0.1:9117'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_key',
                                            'label': 'API Key',
                                            'placeholder': 'Jackett API Key'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'indexers',
                                            'label': '使用索引器',
                                            'placeholder': '留空使用全部，多个用英文逗号分隔'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'timeout',
                                            'label': '请求超时（秒）',
                                            'placeholder': '60'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '本插件用于连接Jackett搜索器，可以通过Jackett API搜索各种资源站点。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

    def get_page(self) -> List[Dict[str, Any]]:
        """
        插件详情页面
        """
        return [
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {
                            'cols': 12
                        },
                        'content': [
                            {
                                'component': 'VAlert',
                                'props': {
                                    'type': 'info',
                                    'variant': 'tonal',
                                    'text': 'Jackett是一个聚合众多BT资源站点的工具，可通过其API统一搜索这些站点的资源。'
                                }
                            }
                        ]
                    }
                ]
            },
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {
                            'cols': 12
                        },
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {
                                    'variant': 'tonal'
                                },
                                'content': [
                                    {
                                        'component': 'VCardText',
                                        'props': {
                                            'class': 'text-center'
                                        },
                                        'content': [
                                            {
                                                'component': 'VBtn',
                                                'props': {
                                                    'color': 'primary',
                                                    'href': 'https://github.com/Jackett/Jackett',
                                                    'target': '_blank',
                                                    'text': 'Jackett 项目主页'
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ] 