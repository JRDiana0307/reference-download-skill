# Publisher-Specific PDF Download Strategies

## 通用流程

所有出版商共用以下核心流程：

1. 通过 Edge CDP 打开文章页面
2. 等待页面加载（默认 12 秒）
3. 验证页面标题是否与预期标题匹配（词重叠相似度 > 0.35）
4. 根据出版商类型找到 PDF URL
5. 下载 PDF 二进制数据并保存

## ScienceDirect / Elsevier

**识别特征**: URL 包含 `sciencedirect.com`

**PDF URL 提取**: 从页面 HTML 解析 `pdfDownload` JSON metadata：
```javascript
// HTML 中的 JSON 格式
"pdfDownload":{"isPdfFullText":true,"urlMetadata":{"queryParams":{"md5":"...","pid":"..."},"pii":"...","pdfExtension":"pdf","path":"science/article/pii/..."}}
```

**下载流程**:
1. 从 metadata 构造 pdfft URL: `https://www.sciencedirect.com/{path}/{pii}pdf?md5={md5}&pid={pid}`
2. 在新标签页打开 pdfft URL
3. 等待重定向到 `pdf.sciencedirectassets.com/.../main.pdf?...`
4. 从重定向后的页面 `fetch(window.location.href)` 获取 PDF bytes
5. Base64 解码后保存

**注意事项**:
- 老旧论文（2005 年以前）的 pdfft 可能返回 403，需机构订阅
- 有时需要重试——pdfft URL 中的 token 可能过期
- `crasolve=1` 参数表示需要 challenge-response 验证

## Springer

**识别特征**: URL 包含 `link.springer.com`

**PDF URL 提取**: `<meta name="citation_pdf_url" content="...">`

**下载流程**: 从文章页 `fetch(pdf_url)` —— 文章页和 PDF 同域(`link.springer.com`)，无 CORS 问题

**示例 PDF URL**: `https://link.springer.com/content/pdf/10.1007/s11630-015-0781-3.pdf`

## IOP (IOPscience)

**识别特征**: URL 包含 `iopscience.iop.org`

**PDF URL 提取**: `<meta name="citation_pdf_url" content="...">`

**下载流程**: 从文章页 `fetch(pdf_url)` —— 同源

**示例 PDF URL**: `https://iopscience.iop.org/article/10.1088/1757-899X/209/1/012060/pdf`

## Emerald

**识别特征**: URL 包含 `emerald.com`

**PDF URL 提取**: `<meta name="citation_pdf_url" content="...">`

**下载流程**: 从文章页 `fetch(pdf_url)`

**示例 PDF URL**: `https://www.emerald.com/hff/article-pdf/31/7/2373/1348409/hff-07-2020-0456.pdf`

## ASME

**识别特征**: URL 包含 `asmedigitalcollection.asme.org`

**PDF URL 提取**: `<meta name="citation_pdf_url" content="...">`

**下载流程**: 从文章页 `fetch(pdf_url)`

**注意事项**: ASME 可能要求机构订阅。未登录用户访问 PDF URL 会被重定向到摘要页面（`redirectedFrom=PDF`）

## AIAA (ARC)

**识别特征**: URL 包含 `arc.aiaa.org`

**PDF URL 提取**: 查找 `<a>` 标签中 `href` 包含 `/doi/pdf/` 的链接

**下载流程**: 从文章页 `fetch(pdf_url)`

**示例 PDF URL**: `https://arc.aiaa.org/doi/pdf/10.2514/2.1964`

## Taylor & Francis

**识别特征**: URL 包含 `tandfonline.com`

**PDF URL 提取**: 查找 `<a>` 标签中 `href` 包含 `/doi/pdf/` 的链接

**下载流程**: 从文章页 `fetch(pdf_url)`

**示例 PDF URL**: `https://www.tandfonline.com/doi/pdf/10.1080/01457630304040`

## MDPI

**识别特征**: URL 包含 `mdpi.com`

**PDF URL 提取**: `<meta name="citation_pdf_url" content="...">`

**下载流程**: MDPI 阻止 `fetch()` 和 `XHR` 请求（CSP 策略），必须使用浏览器下载机制：
1. 在空白页设置 `Browser.setDownloadBehavior({behavior: "allow", downloadPath: "..."})`
2. 使用 `Page.navigate({url: pdf_url})` 导航到 PDF URL
3. 浏览器自动下载 PDF 到指定目录
4. 等待 15 秒后检查下载目录

**示例 PDF URL**: `https://www.mdpi.com/1996-1073/17/4/818/pdf?version=1707386675`

## CNKI / 知网

**识别特征**: URL 包含 `cnki.net` 或 `jasp.com.cn`（航空动力学报等中文期刊）

**PDF URL 提取**: 无标准 meta 标签或链接。PDF 下载通过 JavaScript 触发。

**下载流程**:
1. 打开文章页面
2. 设置 `Browser.setDownloadBehavior({behavior: "allow", downloadPath: "..."})`
3. 通过 `Runtime.evaluate` 注入 JS 点击页面上的"PDF下载"按钮
4. 浏览器下载 PDF 到指定目录
5. 等待 10 秒后检查下载目录，重命名文件

**注意事项**:
- 知网的 PDF 文件名可能是乱码——需手动重命名
- 需要机构订阅或已登录知网账号
- 部分知网页面需要多次等待才能完全加载

## 通用 PDF URL 查找策略（优先级从高到低）

1. `<meta name="citation_pdf_url">` — 覆盖大多数出版商
2. `<a href>` 中包含 `/pdf/` 或以 `.pdf` 结尾 — AIAA, T&F
3. ScienceDirect `pdfDownload` JSON metadata — Elsevier 专用
4. 对于 MDPI 和 CNKI：不适用 fetch，改用浏览器下载行为

## fetch() 通用代码

```javascript
new Promise((resolve) => {
    fetch(pdfUrl, {credentials: 'include'})
        .then(r => {
            if (!r.ok) return resolve('HTTP_ERR:' + r.status);
            return r.arrayBuffer();
        })
        .then(buf => {
            if (typeof buf === 'string') return resolve(buf);
            const chunk = 0x8000;
            let binary = '';
            const bytes = new Uint8Array(buf);
            for (let i = 0; i < bytes.length; i += chunk) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
            }
            resolve(btoa(binary));
        })
        .catch(err => resolve('ERR:' + err.message));
})
```

此 JS 代码通过 CDP `Runtime.evaluate` 的 `awaitPromise: true` 模式执行，结果通过 WebSocket 返回给 Python。
