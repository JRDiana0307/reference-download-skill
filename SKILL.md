---
name: reference-download-skill
description: Download academic paper PDFs from ScienceDirect, Springer, AIAA, Taylor & Francis, IOP, MDPI, Emerald, ASME, CNKI using Edge browser DevTools Protocol. Use when the user needs to batch download references, verify paper content, or collect PDFs from multiple publishers. Supports both English and Chinese (知网) academic databases. Requires Windows + Microsoft Edge.
---

# Reference Download Skill

通过 Microsoft Edge 浏览器的 Chrome DevTools Protocol (CDP) 批量下载学术论文 PDF，支持中英文主流出版商。

## 适用场景

- 批量下载论文参考文献的 PDF 全文
- 验证论文中引用的参考文献内容是否真实存在
- 从多个出版商平台（包括知网）收集论文

## 前置条件

- Windows 操作系统
- Microsoft Edge 浏览器
- Python 3.10+
- `websocket-client` Python 包

## 工作流程

### 1. 启动专用 Edge 会话

运行 [scripts/launch_edge.ps1](scripts/launch_edge.ps1) 启动带远程调试端口的 Edge：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Diana\.claude\skills\reference-download-skill\scripts\launch_edge.ps1
```

这会打开一个独立的 Edge 窗口，启用 DevTools 端口 9222。

### 2. 手动完成登录认证

在刚打开的 Edge 窗口中：
- 登录 ScienceDirect / Springer / AIAA / 知网等（个人或机构账号）
- 通过人机验证页面（如 CAPTCHA）
- 随机打开一篇文章，点击"View PDF"确认能正常查看
- **保持 Edge 窗口不关闭**

### 3. 准备输入 CSV

创建 UTF-8 编码的 CSV 文件，包含以下列：

```csv
number,doi,title,year,journal,first_author,note,formatted
1,10.1007/s11630-015-0781-3,Experimental study on measurement and calculation...,2015,Journal of Thermal Science,Zhang,https://doi.org/10.1007/s11630-015-0781-3,10.1007/s11630-015-0781-3
```

| 列 | 必填 | 说明 |
|----|------|------|
| number | ✓ | 引用编号 |
| doi | ✓ | DOI（无 DOI 时可用中文期刊的 CNKI DOI） |
| title | ✓ | 论文标题（用于验证下载内容是否正确） |
| year | ✓ | 发表年份 |
| journal | - | 期刊名（仅用于报告） |
| first_author | ✓ | 第一作者姓氏（用于文件命名） |
| note | - | 可放入直接的文章 URL。脚本优先使用此 URL 而非 DOI |
| formatted | - | 纯 DOI 字符串（仅用于报告） |

如果 `note` 列包含 `doi.org` 或 `sciencedirect.com` 的 URL，脚本会优先使用。

### 4. 运行下载脚本

```powershell
python C:\Users\Diana\.claude\skills\reference-download-skill\scripts\devtools_universal_fetch.py \
  --input-csv <输入CSV路径> \
  --out-dir <输出目录> \
  --debug-port 9222 \
  --page-wait-seconds 12 \
  --inter-item-sleep-seconds 10
```

参数说明：
- `--page-wait-seconds`：打开页面后等待加载的秒数（默认 12，网络慢时增加到 15-20）
- `--inter-item-sleep-seconds`：两篇论文之间的等待秒数（默认 10，建议 10 以避免 IP 被封）
- `--limit N`：仅处理前 N 行（用于测试）

### 5. 查看结果

输出目录中会生成：
- `pdfs/` — 成功下载的 PDF 文件
- `results.csv` — 完整结果（包含下载状态和来源 URL）
- `missing.csv` — 失败的条目

PDF 命名格式：`[编号]第一作者等 - 年份 - 标题.pdf`

## 出版商下载策略

详细的各平台 PDF URL 提取方法见 [references/publishers.md](references/publishers.md)。

简表：

| 出版商 | PDF URL 获取方式 | 下载方式 |
|--------|-----------------|---------|
| **ScienceDirect** (Elsevier) | 从 HTML 解析 `pdfDownload` JSON metadata | pdfft URL → 等重定向到 pdf.sciencedirectassets.com → `fetch()` |
| **Springer** | `<meta name="citation_pdf_url">` | 从文章页 `fetch(pdf_url)` |
| **AIAA** (arc.aiaa.org) | `<a href="/doi/pdf/...">` 链接 | 从文章页 `fetch(pdf_url)` |
| **Taylor & Francis** | `<a href="/doi/pdf/...">` 链接 | 从文章页 `fetch(pdf_url)` |
| **IOP** (iopscience) | `<meta name="citation_pdf_url">` | 从文章页 `fetch(pdf_url)` |
| **MDPI** | `<meta name="citation_pdf_url">` | `Browser.setDownloadBehavior` + `Page.navigate` (MDPI 阻止 fetch/XHR) |
| **Emerald** | `<meta name="citation_pdf_url">` | 从文章页 `fetch(pdf_url)` |
| **ASME** | `<meta name="citation_pdf_url">` | 从文章页 `fetch(pdf_url)` |
| **CNKI / 知网** | 点击页面上的"PDF下载"按钮 | `Browser.setDownloadBehavior` + 点击下载按钮 |

## 标题验证

下载前自动验证文章页面标题是否与 CSV 中的预期标题匹配。使用词重叠相似度（阈值 0.35），低于阈值则跳过该条目并标记为 `title_mismatch`。自动清理出版商特定后缀（如" - ScienceDirect"、" | SpringerLink"）。

## 故障排查

见 [references/troubleshooting.md](references/troubleshooting.md)。

## DOI 验证建议

CrossRef API 返回的 DOI 可能有误（尤其是中文论文或老旧论文）。建议：
1. 先用 WebSearch 逐条核验 DOI 是否正确
2. 对无法确认的条目，手动检查论文是否存在
3. AI 生成的引用可能包含"幻影引用"——真实作者 + 真实期刊 + 真实年份，但论文不存在。需特别警惕

## 安全边界

- 仅在已有合法访问权限（个人订阅或机构授权）的情况下使用
- 不绕过付费墙或创建未授权的访问
- 控制下载间隔（≥10 秒），避免触发反爬机制
- Edge 窗口的实时会话必须保持打开
