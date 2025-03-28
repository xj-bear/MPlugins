# MoviePilot 插件

这是一个 MoviePilot 的第三方插件仓库，提供以下插件：

## 插件列表

### Jackett搜索器
- 版本：1.0
- 描述：支持 Jackett API的资源搜索器，用于电影、电视剧资源检索
- 作者：jason
- 用户等级：2（认证用户可见）

## 目录结构

```
├── plugins.v2/          # V2版本插件目录
│   └── jackett/        # Jackett插件
│       ├── __init__.py
│       ├── requirements.txt
│       └── README.md
├── package.v2.json      # V2版本插件配置
└── README.md           # 项目说明
```

## 使用说明

1. 在 MoviePilot 的插件市场中添加此仓库地址: https://github.com/xj-bear/MPlugins
2. 在插件市场中安装所需的插件
3. 根据插件说明进行配置和使用

## Jackett搜索器插件使用说明

### 安装步骤
1. 先安装配置好Jackett服务，确保能正常使用
2. 在Jackett管理页面获取API Key
3. 安装本插件，在配置中填入Jackett地址和API Key
4. 保存配置后，即可在媒体搜索时使用Jackett搜索结果

### 配置说明
- **Jackett地址**：填写可访问的Jackett服务地址，如 `http://127.0.0.1:9117`
- **API Key**：Jackett页面顶部显示的API Key
- **使用索引器**：可指定使用的索引器ID，多个用英文逗号分隔，留空则使用全部
- **请求超时**：设置请求超时时间，默认60秒

## 注意事项

1. 本插件仅适用于MoviePilot V2版本
2. 使用本插件需要先安装配置好Jackett服务
3. 确保MoviePilot能够访问到Jackett服务
4. 如遇问题，请查看MoviePilot日志

## 开发说明

本仓库遵循 MoviePilot 官方的插件开发规范，详情请参考：
- [MoviePilot 插件开发文档](https://github.com/jxxghp/MoviePilot-Plugins)
- [MoviePilot V2 插件开发指南](https://github.com/jxxghp/MoviePilot-Plugins/blob/main/docs/V2_Plugin_Development.md) 