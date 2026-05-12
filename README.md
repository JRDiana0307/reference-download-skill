# Reference Download Skill

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

A **Claude Code skill** for batch downloading academic paper PDFs from multiple publishers through a live, already-authorized Microsoft Edge browser session. Uses the Chrome DevTools Protocol (CDP) to extract and download PDFs without triggering bot detection or paywall blocks.

### Supported Publishers

| Publisher | Strategy |
|-----------|----------|
| **ScienceDirect / Elsevier** | Extract `pdfDownload` JSON metadata → pdfft redirect → `fetch()` |
| **Springer** | `<meta name="citation_pdf_url">` → `fetch()` from article page |
| **AIAA** (arc.aiaa.org) | `<a href="/doi/pdf/">` link → `fetch()` from article page |
| **Taylor & Francis** | `<a href="/doi/pdf/">` link → `fetch()` from article page |
| **IOP** (iopscience) | `<meta name="citation_pdf_url">` → `fetch()` from article page |
| **MDPI** | `<meta name="citation_pdf_url">` → `Browser.setDownloadBehavior` + `Page.navigate` |
| **Emerald** | `<meta name="citation_pdf_url">` → `fetch()` from article page |
| **ASME** | `<meta name="citation_pdf_url">` → `fetch()` from article page |
| **CNKI / 知网** | Click PDF download button → `Browser.setDownloadBehavior` |

### Features

- **Multi-publisher support**: 9 platforms covered, including Chinese academic databases
- **Title verification**: Validates paper title against expected title before downloading (catches wrong DOIs)
- **Anti-detection**: Operates through a real browser session with manual authentication — indistinguishable from normal browsing
- **Respectful pacing**: Configurable delays between downloads to avoid rate limiting
- **Detailed reporting**: Outputs `results.csv` and `missing.csv` for audit trails
- **Proper naming**: PDFs named as `[Number]Author et al. - Year - Title.pdf`

### Prerequisites

- Windows 10/11
- Microsoft Edge
- Python 3.10+
- `websocket-client` package

```bash
pip install websocket-client
```

### Installation

```bash
# Via npx skills (recommended)
npx skills add JRDiana0307/reference-download-skill

# Or manual install
git clone https://github.com/JRDiana0307/reference-download-skill.git ~/.claude/skills/reference-download-skill/
```

### Quick Start

#### 1. Launch Edge with remote debugging

```powershell
powershell -ExecutionPolicy Bypass -File ~/.claude/skills/reference-download-skill/scripts/launch_edge.ps1
```

#### 2. Authenticate manually in the Edge window

- Sign in to publisher websites (institutional or personal account)
- Pass any CAPTCHA / bot verification
- Open any article and click "View PDF" to confirm access
- **Keep the Edge window open**

#### 3. Prepare an input CSV

```csv
number,doi,title,year,journal,first_author,note,formatted
1,10.1007/s11630-015-0781-3,Experimental study on...,2015,Journal of Thermal Science,Zhang,,10.1007/s11630-015-0781-3
2,10.1016/j.paerosci.2003.08.001,Fifty years of hypersonics...,2003,Progress in Aerospace Sciences,Bertin,,10.1016/j.paerosci.2003.08.001
```

CSV columns: `number` (required), `doi` (required), `title` (required), `year`, `journal`, `first_author` (required), `note` (optional URL override), `formatted`

#### 4. Run the download

```bash
python ~/.claude/skills/reference-download-skill/scripts/devtools_universal_fetch.py \
  --input-csv input.csv \
  --out-dir ./output \
  --debug-port 9222 \
  --page-wait-seconds 12 \
  --inter-item-sleep-seconds 10
```

### How It Works

1. **Edge CDP Connection** — Launches a dedicated Edge instance with `--remote-debugging-port=9222` and `--remote-allow-origins=*`
2. **Session Reuse** — You manually authenticate once; the script reuses your logged-in browser session
3. **Page Automation** — Opens DOI/article URLs, waits for page load, extracts PDF metadata
4. **Publisher Detection** — Automatically identifies the publisher platform and applies the correct extraction strategy
5. **PDF Download** — Uses same-origin `fetch()` or `Browser.setDownloadBehavior` + navigation depending on the publisher
6. **Title Verification** — Compares page title with expected title (word overlap > 0.35) to catch DOI errors
7. **Save & Report** — Saves PDF with standardized naming, generates success/failure reports

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--debug-port` | 9222 | Edge remote debugging port |
| `--page-wait-seconds` | 12 | Seconds to wait after opening each page |
| `--inter-item-sleep-seconds` | 10 | Seconds between downloads (anti-rate-limiting) |
| `--limit N` | 0 (all) | Only process the first N rows |

### Output Structure

```
output/
├── pdfs/                      # Downloaded PDFs
│   ├── [1]Zhang等 - 2015 - Experimental study....pdf
│   └── [2]Bertin等 - 2003 - Fifty years of hypersonics....pdf
├── results.csv                # Full results with status and source URLs
├── missing.csv                # Failed entries only
├── downloaded_doi.txt         # DOIs of successfully downloaded papers
└── summary.txt                # Download statistics
```

### Common Issues

| Status | Meaning | Action |
|--------|---------|--------|
| `title_mismatch` | DOI points to wrong paper | Verify DOI via CrossRef/WebSearch, update CSV |
| `no_pdf_metadata` | Not on this publisher platform | Paper may be on a different publisher |
| `fetch_failed` | Publisher blocks programmatic fetch | For MDPI, use the download-behavior fallback |
| `no_url` | Missing DOI and note in CSV | Add DOI or direct URL |

### Disclaimer

This tool is designed for legitimate academic use. It does **not**:

- Bypass paywalls or create access where none exists
- Circumvent DRM or copyright protections
- Enable unauthorized bulk downloading

Use only with content you have lawful access to through personal or institutional subscription. Respect publisher terms of service and rate limits.

### License

MIT License. See [LICENSE](LICENSE) file for details.

---

<a name="中文"></a>
## 中文

一个**Claude Code 技能**，通过已登录的 Microsoft Edge 浏览器会话批量下载学术论文 PDF。使用 Chrome DevTools Protocol (CDP) 从多个出版商平台提取和下载 PDF，无需担心机器人检测或付费墙拦截。

### 支持的出版商平台

| 出版商 | 提取策略 |
|--------|----------|
| **ScienceDirect / Elsevier** | 提取 `pdfDownload` JSON 元数据 → pdfft 重定向 → `fetch()` |
| **Springer** | `<meta name="citation_pdf_url">` → 从文章页 `fetch()` |
| **AIAA** (arc.aiaa.org) | `<a href="/doi/pdf/">` 链接 → 从文章页 `fetch()` |
| **Taylor & Francis** | `<a href="/doi/pdf/">` 链接 → 从文章页 `fetch()` |
| **IOP** (iopscience) | `<meta name="citation_pdf_url">` → 从文章页 `fetch()` |
| **MDPI** | `<meta name="citation_pdf_url">` → `Browser.setDownloadBehavior` + `Page.navigate` |
| **Emerald** | `<meta name="citation_pdf_url">` → 从文章页 `fetch()` |
| **ASME** | `<meta name="citation_pdf_url">` → 从文章页 `fetch()` |
| **CNKI / 知网** | 点击"PDF下载"按钮 → `Browser.setDownloadBehavior` |

### 功能特点

- **多平台支持**：覆盖 9 个出版商，包括中文学术数据库
- **标题验证**：下载前核验文章标题，自动识别错误的 DOI
- **反检测**：通过真实浏览器会话操作，手动登录认证，与正常浏览无异
- **合理间隔**：可配置下载间隔，避免触发反爬机制
- **详细报告**：输出 `results.csv` 和 `missing.csv`，完整的审计追踪
- **规范命名**：PDF 文件命名为 `[编号]作者等 - 年份 - 标题.pdf`

### 前置条件

- Windows 10/11
- Microsoft Edge 浏览器
- Python 3.10+
- `websocket-client` 包

```bash
pip install websocket-client
```

### 安装

```bash
# 推荐：通过 npx skills 安装
npx skills add JRDiana0307/reference-download-skill

# 或手动安装
git clone https://github.com/JRDiana0307/reference-download-skill.git ~/.claude/skills/reference-download-skill/
```

### 快速开始

#### 1. 启动带远程调试的 Edge

```powershell
powershell -ExecutionPolicy Bypass -File ~/.claude/skills/reference-download-skill/scripts/launch_edge.ps1
```

#### 2. 在 Edge 窗口中手动完成认证

- 登录各出版商网站（机构账号或个人账号）
- 通过人机验证（CAPTCHA）
- 打开任意一篇文章，点击"View PDF"确认能正常访问
- **保持 Edge 窗口不关闭**

#### 3. 准备输入 CSV 文件

```csv
number,doi,title,year,journal,first_author,note,formatted
1,10.1007/s11630-015-0781-3,Experimental study on...,2015,Journal of Thermal Science,Zhang,,10.1007/s11630-015-0781-3
2,10.1016/j.paerosci.2003.08.001,Fifty years of hypersonics...,2003,Progress in Aerospace Sciences,Bertin,,10.1016/j.paerosci.2003.08.001
```

CSV 列说明：`number`（必填）、`doi`（必填）、`title`（必填）、`year`（年份）、`journal`（期刊名）、`first_author`（第一作者，必填）、`note`（可选的 URL 覆盖地址）、`formatted`（纯 DOI 字符串）

#### 4. 运行下载

```bash
python ~/.claude/skills/reference-download-skill/scripts/devtools_universal_fetch.py \
  --input-csv input.csv \
  --out-dir ./output \
  --debug-port 9222 \
  --page-wait-seconds 12 \
  --inter-item-sleep-seconds 10
```

### 工作原理

1. **Edge CDP 连接** — 启动独立 Edge 实例，开启 `--remote-debugging-port=9222` 和 `--remote-allow-origins=*`
2. **会话复用** — 用户手动认证一次，脚本复用已登录的浏览器会话
3. **页面自动化** — 打开 DOI/文章 URL，等待页面加载，提取 PDF 元数据
4. **平台识别** — 自动识别出版商平台，应用正确的提取策略
5. **PDF 下载** — 根据出版商类型，使用同源 `fetch()` 或 `Browser.setDownloadBehavior` + 导航方式下载
6. **标题验证** — 将页面标题与预期标题比对（词重叠度 > 0.35），识别 DOI 错误
7. **保存与报告** — 按规范命名保存 PDF，生成成功/失败报告

### 参数配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--debug-port` | 9222 | Edge 远程调试端口 |
| `--page-wait-seconds` | 12 | 打开页面后的等待秒数 |
| `--inter-item-sleep-seconds` | 10 | 两篇论文之间的间隔秒数（防反爬） |
| `--limit N` | 0（全部） | 仅处理前 N 行 |

### 输出结构

```
output/
├── pdfs/                      # 已下载的 PDF
│   ├── [1]Zhang等 - 2015 - Experimental study....pdf
│   └── [2]Bertin等 - 2003 - Fifty years of hypersonics....pdf
├── results.csv                # 完整结果（含状态和来源 URL）
├── missing.csv                # 仅失败条目
├── downloaded_doi.txt         # 成功下载的 DOI 列表
└── summary.txt                # 下载统计
```

### 常见问题

| 状态 | 含义 | 处理方式 |
|------|------|----------|
| `title_mismatch` | DOI 指向了错误的论文 | 通过 CrossRef/WebSearch 验证 DOI，更新 CSV |
| `no_pdf_metadata` | 不在该出版商平台 | 论文可能在另一个出版商平台 |
| `fetch_failed` | 出版商阻止了程序化请求 | MDPI 使用 download-behavior 替代方案 |
| `no_url` | CSV 缺少 DOI 和 note | 补充 DOI 或直接 URL |

### DOI 验证建议

CrossRef API 返回的 DOI 可能有误（尤其是中文论文和 2005 年以前的老论文）。建议下载前：

1. 用 WebSearch 逐条验证 DOI
2. 警惕 AI 生成的"幻影引用"——真实作者 + 真实期刊 + 真实年份，但论文本身不存在
3. 对无法确认的条目，手动检查论文是否存在

### 免责声明

本工具仅供合法学术用途。它**不会**：

- 绕过付费墙或创建未授权的访问
- 规避 DRM 或版权保护
- 支持未经授权的批量下载

请仅在您通过个人或机构订阅拥有合法访问权限的情况下使用。遵守出版商的服务条款和速率限制。

### 许可证

MIT License。详见 [LICENSE](LICENSE) 文件。
