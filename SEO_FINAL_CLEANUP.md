# SEO 收尾记录

更新时间：2026-03-18

## 已完成的代码侧收尾

- 首页、项目、关于、联系、隐私、条款及英文基础页的 `title` / `description` 已更新为当前个人作品站定位。
- 中英文对应页已基于 `alternate_url` 输出互相指向的 `hreflang`，并补 `x-default`。
- `/blog/` 与 `_posts`、`_blogs` 继续统一 `noindex,follow`，且排除 sitemap。
- 旧分享页、分类页、标签页继续使用重定向页策略，并显式 `noindex`。
- 旧产品入口 `/gmscore/`、`/web_scoreboard/`、`/TaskEase/`、`/YiYanRiCheng/` 已统一为历史入口。
- 旧 app 隐私页 `/gmscore/privacypolicy/` 已补到当前站点，重定向到 [`/privacy-policy/`](/Users/mac/Documents/GitHub/blog/pages/privacy-policy.md)，并显式 `noindex`。
- `assets/js/theme.js` 与 `assets/js/i18n.js` 中残留的 `pt-BR` 默认语言已改为 `zh-CN`，避免前台继续写出旧语言信号。

## 当前旧页面处理规则

### Redirect + noindex

- `/share/`
- `/categories/`
- `/tags/`
- `/gmscore/`
- `/gmscore/privacypolicy/`
- `/web_scoreboard/`
- `/TaskEase/`
- `/YiYanRiCheng/`

说明：在 GitHub Pages 当前托管方式下，这些路径使用“重定向页 + canonical 指向目标页 + noindex”的现实方案。它们不是严格的 HTTP 301。

### Archive + noindex

- `/blog/`
- `_posts` 下全部历史文章
- `_blogs` 下全部历史文章
- 葡语历史内容
- 巴西新闻历史内容

### Core indexable pages

- `/`
- `/projects/`
- `/about/`
- `/contact/`
- `/privacy-policy/`
- `/terms/`
- `/en/`
- `/en/projects/`
- `/en/about/`
- `/en/contact/`
- 3 个项目详情页及其英文对应页

## 仍需手工完成

- 在 Search Console 提交最新 sitemap。
- 在 Search Console 检查 Coverage / Pages。
- 提交旧 URL 移除请求，优先处理旧 app 路径和旧归档路径。
- 对首页、`/projects/`、`/about/`、`/contact/`、`/privacy-policy/`、`/en/` 请求重新抓取。
- 等 Ruby / Bundler 环境修复后，再做一次本地构建，抽查最终输出的 canonical、hreflang 和 sitemap。

## 限制说明

- GitHub Pages 当前不适合直接做真正的 `410 Gone`。如果未来必须精确返回 410，需要接入 CDN、反向代理或其它边缘层。
- 当前站点代码侧已尽量把旧内容降到“可访问但不参与 SEO”的状态，最后的去索引速度仍取决于 Search Console 提交和搜索引擎刷新周期。
