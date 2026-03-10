# DeepLearning.AI Transcript Crawler

一个用于爬取 DeepLearning.AI 平台课程视频字幕的 Python 爬虫工具。

## 功能特点

- 🎥 自动爬取课程所有课时的视频字幕
- 🔐 支持手动登录，确保可以访问付费课程内容
- 📝 将字幕导出为 Markdown 格式，便于阅读和学习
- 🔄 智能处理 "Show more" 按钮，获取完整字幕
- 🛡️ 多重选择器策略，适应不同页面结构

## 支持的课程

目前主要针对以下课程进行了优化：

- **Agent Skills with Anthropic** - DeepLearning.AI 与 Anthropic 联合出品

## 安装要求

- Python 3.8+
- Playwright

## 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/deeplearning-ai-transcript-crawler.git
cd deeplearning-ai-transcript-crawler
```

2. 安装依赖

```bash
pip install playwright
python -m playwright install chromium
```

## 使用方法

### 方式一：带登录功能的爬虫（推荐）

适用于需要登录才能访问的课程内容：

```bash
python crawler_with_login.py
```

运行后会自动打开浏览器，你需要：

1. 在浏览器中登录你的 DeepLearning.AI 账号
2. 导航到目标课程页面
3. 在终端按 Enter 键继续
4. 等待爬虫自动爬取所有字幕

### 方式二：基础爬虫

适用于公开访问的课程：

```bash
python crawler.py
```

## 输出文件

爬取完成后会生成以下文件：

- **transcripts.md** - 所有课时的字幕 Markdown 文件
- **progress.json** - 爬取进度和原始数据

## 文件说明

| 文件 | 说明 |
|------|------|
| `crawler.py` | 基础爬虫脚本，无需登录 |
| `crawler_with_login.py` | 带登录功能的爬虫脚本 |
| `transcripts.md` | 生成的字幕文件（示例） |
| `requirements.txt` | Python 依赖列表 |

## 注意事项

1. **登录要求**：部分课程需要登录 DeepLearning.AI 账号才能访问
2. **网络稳定**：确保网络连接稳定，避免爬取中断
3. **尊重版权**：本工具仅供个人学习使用，请勿用于商业用途或公开传播付费课程内容
4. **使用频率**：请合理控制爬取频率，避免对网站造成负担

## 技术栈

- **Python 3.8+** - 主要编程语言
- **Playwright** - 浏览器自动化工具
- **asyncio** - 异步编程

## 项目结构

```
.
├── crawler.py              # 基础爬虫
├── crawler_with_login.py   # 带登录功能的爬虫
├── requirements.txt        # 依赖文件
├── transcripts.md          # 字幕输出文件（示例）
├── README.md              # 项目说明
├── LICENSE                # 开源协议
└── .gitignore            # Git 忽略文件
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

## 免责声明

本工具仅供学习和研究使用。使用本工具爬取的内容版权归原课程平台所有，请遵守相关平台的使用条款和版权规定。

## 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [Issue](../../issues)
- 发送邮件至 [694335238@qq.com]

---

⭐ 如果这个项目对你有帮助，欢迎 Star 支持！

