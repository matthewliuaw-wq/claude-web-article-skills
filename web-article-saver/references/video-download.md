# 视频下载详解

三类视频来源，方法各不相同。通用前置：ffmpeg 已安装（`brew install ffmpeg` / `apt install ffmpeg`），校验用 `ffprobe`。

## 一、X/Twitter 视频（HLS 分片流）

X 视频以 HLS 分片流加载，无法直接 curl。完整流程（实战验证可靠）：

### 1. 触发懒加载（关键，不可省）

X 视频默认**不会**请求 m3u8，必须让每个 video 进入视口。用 `browser_run_code_unsafe` 滚动到每个视频的 `top` 位置并悬停（`top` 值来自视频检测步骤）：

```javascript
async (page) => {
  const ys = [991, 3821, 8104, 9878, 11102];  // 每个视频的纵向位置
  for (const y of ys) {
    await page.evaluate((yy) => window.scrollTo(0, yy), y);
    await page.waitForTimeout(1500);
  }
  // 悬停触发预加载（有些视频需悬停才加载流）
  const videos = await page.locator('video').all();
  for (const v of videos) {
    try {
      const box = await v.boundingBox();
      if (box) { await page.mouse.move(box.x + box.width/2, box.y + box.height/2); await page.waitForTimeout(800); }
    } catch(e) {}
  }
  return `scrolled ${ys.length} positions, hovered ${videos.length} videos`;
}
```

### 2. 捕获 master m3u8

滚动后用 `browser_network_requests`（`filter=video.twimg.com.*amplify_video.*m3u8`）取每个视频的 **master 播放列表**——形如 `amplify_video/<ID>/pl/<token>.m3u8?tag=XX&variant_version=1`。按 `<ID>`（与视频检测的 videoId 对应）分组，每个视频取一个 master m3u8。

### 3. 一条命令下载

master m3u8 已包含所有分辨率变体，ffmpeg 会自动选最高并合并音视频：

```bash
ffmpeg -y -i "https://video.twimg.com/amplify_video/<ID>/pl/<token>.m3u8?tag=XX&variant_version=1" \
  -c copy -bsf:a aac_adtstoasc "video-01.mp4"
```

### 4. 失败重试（偶发 `End of file`，按顺序）

1. **先重试同一个 master m3u8**——往往第二次就成功
2. **仍失败**，分别下载最高分辨率变体再合并（变体 m3u8 在 network 请求里能看到）：

```bash
ffmpeg -y -i "amplify_video/<ID>/pl/avc1/<最大WxH>/<token>.m3u8" -c copy -bsf:a aac_adtstoasc v-v.mp4
ffmpeg -y -i "amplify_video/<ID>/pl/mp4a/128000/<token>.m3u8" -c copy -bsf:a aac_adtstoasc v-a.mp4
ffmpeg -y -i v-v.mp4 -i v-a.mp4 -c copy "video-01.mp4" && rm v-v.mp4 v-a.mp4
```

### 5. 验证

`ffprobe` 检查时长/分辨率。X 推文视频通常 15 秒左右、分辨率如 `1280x720` 或 `1470x630`。

**注意**：X 视频需要**已登录**的 Playwright 会话才能获取完整 HLS 流（未登录只能看到封面图）；多个视频可串行下载（简单稳妥），并行时偶发瞬时失败需单独重试。

## 二、微信内嵌视频（mpvideo）

微信文章的视频是 `span.video_iframe[data-mpvid]` / `<mpvideo>` 元素，标识 `vid=wxv_...`。**最简单的视频场景**：页面渲染后对应 `<video>` 元素的 `src` **直接是带签名的 MP4 直链**（`mpvideo.qpic.cn/...mp4?dis_k=...&auth_key=...&dis_t=...`），无需 m3u8、无需 ffmpeg。

### 1. 检测（browser_evaluate）

```javascript
// 微信内嵌视频：<video> src 即签名 MP4 直链
const wxvideos = Array.from(document.querySelectorAll('video')).map(v => ({
  src: v.src || v.currentSrc || '',         // 带签名的 mpvideo MP4（时效性，拿到就下）
  poster: v.poster || '',                    // 封面（mmbiz 图）
  top: Math.round(v.getBoundingClientRect().top + window.scrollY),
})).filter(v => v.src.includes('mpvideo') || v.poster);
return wxvideos;
```

若 `src` 为空（懒加载未触发），先滚动到视频位置再读。

### 2. 立刻下载（签名有时效）

```bash
curl -sL -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
     -H "Referer: 文章URL" "<mpvideo mp4 url>" -o video-01.mp4
```

### 3. 验证 + 封面

`ffprobe` 验时长 + 完整解码（`ffmpeg -v error -i video.mp4 -f null -`）。微信内嵌视频多为完整单文件 MP4（非分片）。封面 `<video poster>` 是 `mmbiz` 图，同样带 Referer curl 下载为 `video-cover.jpg`。

**个别 vid 直链 curl 拿不到**（服务端拒绝）：用 `data-cover` 封面图占位 + 文字标注说明有视频未下载。

## 三、普通网页直链视频

页面 `<video src="https://...mp4">` 是直链的：直接 curl 下载，无需 ffmpeg。用 `ffprobe` 验证完整性即可。

## 嵌入 Markdown

下载的视频用锚点法定位到原文位置（同图片），插入：

```html
<video controls width="100%" src="video-01.mp4"></video>
```

前后加空行，可注明视频内容和时长。
