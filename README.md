# JmTool — AstrBot JM 漫画插件

基于 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) 的 AstrBot 漫画下载 / 长图合并转发插件。

> 内置 jmcomic 核心库，开箱即用，无需额外下载 JMComic-Crawler。

## 功能

| 命令 | 说明 |
|------|------|
| `.jm` | 显示使用教程 |
| `.jmtest` | 一键自检所有依赖 |
| `.jm<ID>` | 下载本子，拼接长图，合并转发 |
| `.jms <关键词>` | 搜索本子，返回前 5 条 |
| `.jms +全彩 +人妻` | 同时包含「全彩」和「人妻」 |
| `.jms 全彩 -人妻` | 包含「全彩」排除「人妻」 |

## 安装

### 1. 下载

```bash
git clone https://github.com/Rirs123/JmTool.git
```

将 `JmTool` 文件夹放入 AstrBot 的 `data/plugins/` 目录。

### 2. 安装依赖

**Windows**: 双击 `setup.bat`，自动安装 + 自检。

**Linux / macOS**:
```bash
cd JmTool
pip install -r requirements.txt
```

### 3. 验证

重启 AstrBot，在群里发送 `.jmtest`，看到全部通过即可使用。

## 目录结构

```
JmTool/
├── main.py            # 插件主程序（~800 行）
├── metadata.yaml      # 插件元信息
├── requirements.txt   # Python 依赖
├── setup.bat          # Windows 一键环境配置
├── README.md          # 说明文档
└── jmcomic/           # 内置 JMComic 爬虫核心
    ├── api.py         # 下载 & 搜索 API
    ├── jm_downloader.py
    ├── jm_plugin.py   # 插件系统（img2pdf, zip, long_img）
    └── ...
```

## 依赖

| 包 | 用途 |
|----|------|
| commonx | JM 爬虫基础工具库 |
| curl_cffi | 模拟浏览器指纹 |
| Pillow | 图片处理 & 长图拼接 |
| pycryptodome | 解密禁漫混淆图片 |
| PyYAML | 配置解析 |

## 工作流程

```
用户: .jm123456
  → 查询本子信息（标题、作者、标签、章节数）
  → 下载所有图片到临时目录
  → 每 5 张拼接为一张长图
  → 分批合并转发到群聊
  → 自动清理临时文件
```

## 故障排查

发送 `.jmtest` 会逐项检查所有依赖。

| 报错 | 解决 |
|------|------|
| `commonx 未安装` | `pip install commonx` |
| `curl_cffi 未安装` | `pip install curl_cffi` |
| `下载完成但未找到图片` | 检查服务器能否访问禁漫 |
| `长图生成失败` | `pip install Pillow` |

## 配置

可在 `main.py` 顶部的 `build_long_images` 函数中修改：
- `group_size`: 每张长图包含的图片数（默认 5）
- `quality`: 长图 JPEG 质量（默认 70）

## License

MIT

## 作者

**Rirs** — [GitHub](https://github.com/Rirs123)

欢迎提 Issue 和 PR！
