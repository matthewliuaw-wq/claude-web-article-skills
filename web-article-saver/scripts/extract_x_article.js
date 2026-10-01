// web-article-saver/scripts/extract_x_article.js
//
// 用途：抓取 X 长文章（x.com/<user>/status/<id> 或 x.com/i/article/<id>）的结构化正文。
// 用法：先 browser_navigate(url) 打开文章（登录墙会短暂闪过，稍等正文自动渲染），
//       然后把【本文件整体内容】作为 Playwright MCP `browser_evaluate` 工具的 `function`
//       参数传入（本文件本身就是一个 `() => {...}` 箭头函数，在页面上下文执行）。
//
// 返回 { text, imgs, coverCandidates }：
//   - text            正文；图片位置已用 [[IMG1]]..[[IMGn]] 内联占位（与 imgs 下标对应），
//                     <pre>/<code> 已包成 ``` 代码围栏。直接把 [[IMGn]] 替换成 ![](images/img-0N.ext) 即可。
//   - imgs            [{i, src, w, h}] 正文内嵌图直链（已去头像 / emoji / 小图标）。
//   - coverCandidates [{src, w, h}]   封面候选 = article 级别、在正文容器【之外】的大图（≥400px）。
//                     X 长文章封面常在 header，walker 正文里抓不到，这里兜底；取第一个当封面。
//
// 为什么不用 browser_snapshot：长文章 snapshot 是 59KB+ 的 yaml 无障碍树，爆 context 且
// 代码块 / 图位难精确还原；本 walker 一次出「正文 + 图位 + 代码围栏」，紧凑十倍、图文天然对齐。
// 长文章一律走本 walker；只有短推文（几句正文、无代码块）才退回 browser_snapshot 兜底。
() => {
  const body = document.querySelector('[data-testid="longformRichTextComponent"]');
  const article = document.querySelector('article');
  if (!body) return {
    error: 'longformRichTextComponent 未找到：可能不是长文章（短推文请改用 browser_snapshot），或正文还没渲染（稍等几秒重跑）'
  };

  const out = [];
  const imgs = [];
  let imgIdx = 0;

  // 形参用 el 而非 img,避免与调用方 / 页面作用域的 img 变量遮蔽(曾致 ReferenceError: img is not defined)
  const isContentImg = (el) => {
    const src = el.src || el.currentSrc || '';
    return src && /twimg|media|pbs/.test(src)
      && !/emoji|avatar|profile/i.test(src)
      && Math.max(el.naturalWidth || 0, el.naturalHeight || 0) >= 120;
  };

  const walk = (node) => {
    if (node.nodeType === 3) { const t = node.textContent; if (t.trim()) out.push(t); return; }
    if (node.nodeType !== 1) return;
    const tag = node.tagName.toLowerCase();
    if (tag === 'img') {
      if (isContentImg(node)) {
        imgIdx++;
        imgs.push({ i: imgIdx, src: node.src || node.currentSrc, w: node.naturalWidth, h: node.naturalHeight });
        out.push(`\n\n[[IMG${imgIdx}]]\n\n`);
      }
      return;
    }
    if (tag === 'br') { out.push('\n'); return; }
    if (tag === 'pre' || tag === 'code') {
      const code = (node.innerText || '').replace(/\n{3,}/g, '\n\n').trim();
      if (code) out.push(`\n\n\`\`\`\n${code}\n\`\`\`\n\n`);
      return;
    }
    // 表格支持：遇到 <table> 直接转 markdown 表格（首行作表头，生成对齐行）
    if (tag === 'table') {
      const rows = Array.from(node.querySelectorAll('tr'));
      if (rows.length) {
        const cells = rows.map(tr => Array.from(tr.querySelectorAll('th,td'))
          .map(c => (c.innerText || '').trim().replace(/\|/g, '\\|').replace(/\n/g, ' ')));
        const header = cells[0];
        const bodyRows = cells.slice(1);
        let md = '\n\n| ' + header.join(' | ') + ' |\n|' + header.map(() => ':---').join('|') + '|\n';
        bodyRows.forEach(r => { md += '| ' + r.join(' | ') + ' |\n'; });
        out.push(`\n${md}\n`);
      }
      return;
    }
    const isHeading = /^h[1-4]$/.test(tag);
    const isBlock = ['p','div','li','h1','h2','h3','h4','blockquote','figure','section','ul','ol'].includes(tag);
    for (const c of node.childNodes) walk(c);
    if (isHeading) out.push('\n\n');
    else if (isBlock) out.push('\n');
  };
  walk(body);

  // 封面兜底：article 内、但在 longform 正文容器【之外】的大图（X 长文章封面常在 header）
  const bodyImgSet = new Set(body.querySelectorAll('img'));
  let coverCandidates = [];
  if (article) {
    coverCandidates = Array.from(article.querySelectorAll('img'))
      .filter(i => !bodyImgSet.has(i) && isContentImg(i) && (i.naturalWidth || 0) >= 400)
      .map(i => ({ src: i.src || i.currentSrc, w: i.naturalWidth, h: i.naturalHeight }));
  }

  return {
    text: out.join('').replace(/\n{3,}/g, '\n\n').trim(),
    imgs,
    coverCandidates
  };
}
