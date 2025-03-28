# MoviePilot Jackett搜索插件

这是一个为MoviePilot开发的Jackett资源搜索插件，可以通过Jackett API扩展资源搜索能力。

## 功能特点

- 支持通过Jackett API搜索多个资源站点
- 支持自定义Jackett服务器地址和API密钥
- 支持搜索结果过滤和排序
- 支持资源详情查看
- 兼容MoviePilot V2版本

## 目录结构

```
plugins.v2/
  ├── jackett/
  │   ├── __init__.py      # 插件主程序
  │   ├── service.py       # 服务类封装
  │   └── config.py        # 配置定义
package.v2.json            # V2版本插件配置
```

## 配置说明

插件配置项包括：

- `host`: Jackett服务器地址，例如：http://localhost:9117
- `api_key`: Jackett API密钥
- `indexers`: 搜索源列表，可选，默认搜索全部
- `proxy`: 代理服务器地址，可选

## 版本历史

### v1.0
- 初始版本
- 基本的Jackett搜索功能
- 支持配置Jackett服务器和API密钥

## 使用方法

1. 在MoviePilot插件市场中安装本插件
2. 配置Jackett服务器地址和API密钥
3. 重启MoviePilot服务使配置生效
4. 在资源搜索时将自动调用Jackett进行搜索

## 开发者

- 作者：jason
- 联系方式：请通过GitHub Issues反馈问题

## 许可证

MIT License

Jackett 插件
这是一个用于 MoviePilot 的 Jackett 搜索插件，支持通过 Jackett 搜索资源。

功能特性
支持配置 Jackett 服务器地址和 API Key
支持选择性启用特定的索引器
支持资源搜索并返回结果

配置说明
启用插件：开启或关闭插件功能
Jackett地址：填写 Jackett 服务器的访问地址，例如：http://localhost:9117 
API Key：填写 Jackett 的 API Key（在Jackett管理界面右上角可以找到）
管理密码：如果Jackett设置了管理密码，需要填写
索引器：选择要启用的索引器（可多选，留空则使用全部索引器）
使用方法
确保 Jackett 服务正常运行且可以访问
在 Jackett 中添加并测试索引器，确保索引器可用
在插件配置页面填写相关配置信息
启用插件并保存配置
使用"重新加载索引器到搜索系统"按钮刷新索引器列表
故障排除
无法连接到 Jackett：

检查 Jackett 服务是否正常运行
确认服务器地址是否正确
检查网络连接是否正常
API Key 无效：

确认是否正确复制了完整的 API Key
在 Jackett 管理界面重新生成 API Key
索引器列表为空：

确认 Jackett 中是否已添加索引器
检查索引器是否可以正常工作
查看日志中的详细错误信息
注意事项
请确保 Jackett 服务器可以正常访问
API Key 请妥善保管，不要泄露
建议选择合适的索引器以提高搜索效率


API 接口
获取索引器列表
接口地址：/api/v1/jackett/indexers
请求方式：GET
返回格式：
{
  "code": 0,
  "data": [
    {
      "id": "索引器ID",
      "name": "索引器名称",
      ...
    }
  ]
}

注意事项
请确保 Jackett 服务器可以正常访问
API Key 请妥善保管，不要泄露
建议选择合适的索引器以提高搜索效率