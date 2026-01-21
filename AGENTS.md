# AGENTS.md

## 项目概述

这是一个基于 Jekyll 构建的个人网站，托管在 GitHub Pages 上。网站展示了个人作品集、博客文章和联系信息。

**网站地址**: https://youllbe.cn
**作者**: 王雄皓 (Hoa)
**邮箱**: x5brain@gmail.com

---

## 技术栈

### 核心框架
- **Jekyll** - 静态网站生成器，GitHub Pages 官方支持
- **Ruby Gems** - Ruby 包管理工具
- **Kramdown** - Markdown 解析器，用于内容渲染

### 前端技术
- **Bootstrap** - 响应式前端框架
- **jQuery** - JavaScript 库
- **SASS/SCSS** - CSS 预处理器
  - 编译模式：压缩 (compressed)
  - SASS 目录：`_sass`

### Jekyll 插件
- `jekyll-paginate` - 文章分页功能 (每页 30 篇)
- `jekyll-sitemap` - 自动生成站点地图
- `jekyll-feed` - RSS 订阅功能
- `jekyll-seo-tag` - SEO 优化标签
- `jekyll-archives` - 文章归档功能

### 第三方服务
- **Disqus** - 评论系统 (youllbe-cn)
- **Google Analytics** - 网站统计分析 (UA-214748269-1)
- **GitHub Pages** - 静态网站托管

---

## 文件目录结构

```
zero-times.github.io/
│
├── _blogs/                          # 博客集合目录
│   └── 2023-06-01-微信小程序改造.md
│
├── _data/                           # 数据文件
│   └── menus.yml                    # 网站菜单配置
│
├── _includes/                       # 可复用的页面组件
│   ├── disqus.html                  # Disqus 评论组件
│   ├── newsletter.html              # 邮件订阅组件
│   ├── pagination.html              # 分页组件
│   ├── postbox.html                 # 文章卡片组件
│   └── sidebar.html                 # 侧边栏组件
│
├── _layouts/                        # 页面布局模板
│   ├── categories.html              # 分类页布局
│   ├── default.html                 # 默认布局
│   ├── page.html                    # 普通页面布局
│   ├── post.html                    # 文章页布局
│   └── share.html                   # 分享页布局
│
├── _posts/                          # 博客文章目录
│   ├── 2024-03-22-待办小帮手.md
│   ├── 2024-04-22-一言日程.md
│   ├── 2025-06-10-广麻记分.md
│   └── 2025-07-15-记分板.md
│
├── _sass/                           # SASS 样式文件
│   └── bootstrap/                   # Bootstrap SASS 源文件
│
├── assets/                          # 静态资源目录
│   ├── css/
│   │   ├── custom.css               # 自定义样式
│   │   └── theme.scss               # 主题样式
│   ├── images/                      # 图片资源
│   │   ├── logo.png                 # 网站 Logo
│   │   ├── favicon.ico              # 网站图标
│   │   └── sal.png                  # 作者头像
│   └── js/                          # JavaScript 文件
│       ├── bootstrap.min.js         # Bootstrap JS
│       ├── jquery.min.js            # jQuery 库
│       └── theme.js                 # 自定义脚本
│
├── pages/                           # 静态页面
│   ├── categories.html              # 分类页
│   ├── contact.html                 # 联系页
│   ├── privacy-policy.md            # 隐私政策
│   └── share.html                   # 分享页
│
├── .gitignore                       # Git 忽略配置
├── 404.html                         # 404 错误页面
├── _config.yml                      # Jekyll 主配置文件
├── CNAME                            # 自定义域名配置
├── Gemfile                          # Ruby 依赖配置
├── index.html                       # 首页
├── LICENSE.txt                      # 许可证文件
└── README.md                        # 项目说明文档
```

---

## 核心配置

### Jekyll 配置 (_config.yml)
- **Permalink 格式**: `/:title/`
- **分页数量**: 30 篇/页
- **时区**: UTC
- **语言**: en_us
- **Markdown 引擎**: kramdown (禁用语法高亮)

### Collections (集合)
- **blogs**: 博客文章集合
  - 输出: 已启用
  - 固定链接: `/blog/:title/`

### 作者信息
- **名称**: Hoa (王雄皓)
- **头像**: assets/images/sal.png
- **网站**: https://youllbe.cn

---

## 本地开发

### 环境要求
- Ruby
- Bundler
- Jekyll

### 启动命令
```bash
bundle install          # 安装依赖
bundle exec jekyll serve # 启动本地服务器
```

本地访问地址：`http://localhost:4000`

---

## 部署

项目通过 GitHub Pages 自动部署，推送到 `master` 分支后会自动构建并发布。

**自定义域名**: 通过 CNAME 文件配置

---

## 最近更新

根据 Git 提交记录：
- **28db616** - feat: 联系页面增强
- **bd372a1** - feat: 隐私更新
- **b92b400** - Update custom.css
- **2c1b3bd** - Update custom.css
- **bbd7935** - Update custom.css

---

## 备注

- 网站采用响应式设计，支持移动端访问
- 使用 Bootstrap 框架确保跨浏览器兼容性
- 集成 SEO 优化插件，便于搜索引擎收录
- 支持 RSS 订阅功能
- 评论系统基于 Disqus 平台
