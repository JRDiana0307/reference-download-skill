# 故障排查 / Troubleshooting

## Edge DevTools 连接问题

### WebSocket 403 Forbidden

**症状**: `WebSocketBadStatusException: Handshake status 403 Forbidden`

**原因**: Edge 启动时缺少 `--remote-allow-origins=*` 参数

**解决**: 重新启动 Edge，确保 launch_edge.ps1 中包含此参数。已在当前版本中修复。

### Edge 窗口关闭

**症状**: `ConnectionRefusedError` 或 `ConnectionAbortedError`

**解决**: 重新运行 `launch_edge.ps1`，重新登录各平台。

## 下载状态说明

| 状态 | 含义 | 处理方式 |
|------|------|---------|
| `downloaded` | 下载成功 | 无需处理 |
| `existing_file` | 文件已存在（跳过） | 如需重新下载，先删除旧文件 |
| `no_pdf_metadata` | 文章页未找到 PDF 链接 | 非该出版商平台（如用 ScienceDirect 方法下载 Springer 论文），或需机构订阅 |
| `no_pdf_url` | 页面加载成功但无 PDF 链接 | 出版商不支持，或需要手动交互 |
| `title_mismatch` | DOI 指向的论文与预期不符 | **DOI 不正确**，需重新验证 DOI |
| `fetch_failed` | `fetch()` 请求失败 | MDPI CSP 拦截（改用 download behavior），或需登录 |
| `no_url` | CSV 中无 DOI 且 note 列为空 | 补充 DOI 或 URL |
| `no_candidate_urls` | 无法从 CSV 构建 URL | 同上 |

## 标题验证失败 (title_mismatch)

这是最重要的错误——**说明 DOI 指向了错误的论文**。

**常见原因**:
1. CrossRef 返回的 DOI 有误（尤其是中文论文和 2005 年前的论文）
2. AI 生成的引用（幻影引用）
3. 论文引用本身有误（期刊名/卷号/页码错误）

**处理步骤**:
1. 用 WebSearch 搜索论文标题 + 第一作者
2. 找到正确的 DOI
3. 更新 CSV 中的 DOI
4. 删除错误的 PDF 文件后重新下载

## 科学上网 / 开放获取

### MDPI 论文下载失败

MDPI 是开放获取出版商，但会阻止 `fetch()` 和 `XMLHttpRequest` 请求 PDF。已使用 `Browser.setDownloadBehavior` + `Page.navigate` 方式绕过。

### SSRN 预印本

SSRN 在中国大陆可能被墙。可通过浏览器会话下载。如果直接 `urllib` 请求超时，使用 Edge CDP 方式。

### 知网 (CNKI) 下载

知网 PDF 下载通过 JavaScript 触发，无直接 PDF URL。处理方式：
1. 设置 `Browser.setDownloadBehavior`
2. 点击"PDF下载"链接
3. 下载到指定目录后重命名（知网的文件名可能是乱码或编号）

## 性能优化

### 下载速度

36 篇论文大约需要 15-20 分钟（每篇 ~30 秒）。主要时间分布：
- 页面加载等待：12-15 秒/篇
- PDF fetch：5-10 秒/篇
- 间隔睡眠：10 秒/篇（避免触发反爬）

### 减少间隔时间

如果网络状况良好且不会触发反爬机制，可将 `--inter-item-sleep-seconds` 减小到 5。

### 并行下载（不推荐）

不建议并行下载——Edg DevTools 的 WebSocket 连接不适合高并发，且可能触发出版商的反爬机制导致 IP 被封。

## 常见出版商特有问题

### ScienceDirect 返回 403

- 老旧论文（2005 年前）的 pdfft 链接可能需要额外认证
- 可尝试通过 `Browser.setDownloadBehavior` + 直接导航到 pdfft URL
- 或从 Cal Poly / arXiv / 作者主页获取免费后印本

### Springer / AIAA 需要订阅

- 确认已登录机构账号
- 部分论文即使登录也无法下载（需单独购买）

### ASME 重定向到摘要页

- ASME PDF URL 在未登录状态下会重定向到摘要页
- 从文章页 `fetch(pdf_url)` 可以绕过此限制
