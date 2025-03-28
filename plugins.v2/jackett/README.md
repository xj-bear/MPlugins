# Jackett 搜索器插件

本插件用于连接 Jackett 搜索器，可以通过 Jackett API 搜索各种资源站点的影视资源。
作者：jason
仓库地址：https://github.com/xj-bear/MPlugins

## 功能特性

- 支持 Jackett API 搜索
- 支持指定索引器筛选
- 支持按影视类型搜索
- 支持 IMDB ID 精确匹配
- 自动解析种子信息，包括大小、做种数等

## 使用说明

### 安装 Jackett

首先需要安装 Jackett，请参考官方文档：https://github.com/Jackett/Jackett

### 配置插件

1. 在 Jackett 管理页面（一般为 http://your-ip:9117）获取 API Key
2. 在 MoviePilot 插件配置页面填写以下信息：
   - Jackett 地址：Jackett 的访问地址，例如 `http://127.0.0.1:9117`
   - API Key：从 Jackett 页面获取的 API Key
   - 使用索引器：可选，指定要使用的索引器ID，多个用英文逗号分隔，留空则使用全部
   - 请求超时（秒）：API 请求超时时间，默认 60 秒

## 注意事项

1. 需确保 MoviePilot 能够访问到 Jackett 服务
2. 搜索结果质量取决于 Jackett 中配置的站点
3. 如使用 Docker 部署，注意容器间的网络连通性

## 更新历史

### v1.0
- 初始版本
- 支持基本的 Jackett API 搜索功能 