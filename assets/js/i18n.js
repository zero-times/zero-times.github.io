// 多语言内容切换功能
// 用于 zero-times.github.io 博客的国际化支持

// 从URL参数、本地存储或浏览器语言获取首选语言
function getPreferredLanguage() {
  // 检查URL参数
  const urlParams = new URLSearchParams(window.location.search);
  const langFromUrl = urlParams.get('lang');
  if (langFromUrl) {
    return normalizeLanguageCode(langFromUrl);
  }
  
  // 检查本地存储
  const storedLang = localStorage.getItem('preferred-language');
  if (storedLang) {
    return normalizeLanguageCode(storedLang);
  }
  
  // 检测浏览器语言
  const browserLang = navigator.language || navigator.userLanguage;
  return normalizeLanguageCode(browserLang);
}

// 规范化语言代码
function normalizeLanguageCode(lang) {
  if (!lang) return 'pt-br';
  
  const normalized = lang.toLowerCase();
  
  if (normalized.startsWith('pt') || normalized.includes('br')) {
    return 'pt-br';
  } else if (normalized.startsWith('en')) {
    return 'en';
  } else if (normalized.startsWith('zh') || normalized.startsWith('cn')) {
    return 'zh';
  }
  
  // 默认返回葡萄牙语（面向巴西用户）
  return 'pt-br';
}

// 设置HTML的lang属性
function setHtmlLanguage() {
  const currentLang = getPreferredLanguage();
  document.documentElement.lang = currentLang.replace('-', '_');
  
  // 更新语言选择器
  const langSelector = document.getElementById('language-switcher-select');
  if (langSelector) {
    langSelector.value = currentLang;
  }
  
  // 应用语言特定的样式
  applyLanguageSpecificStyles(currentLang);
}

// 应用语言特定的样式
function applyLanguageSpecificStyles(lang) {
  // 移除之前可能添加的语言类
  document.body.classList.remove('lang-pt-br', 'lang-en', 'lang-zh');
  
  // 添加当前语言类
  document.body.classList.add(`lang-${lang.replace('-', '_')}`);
  
  // 特定于中文的样式调整
  if (lang === 'zh') {
    // 中文排版优化
    document.body.style.fontFeatureSettings = '"liga", "clig", "calt", "hanj"';
  } else {
    document.body.style.fontFeatureSettings = 'normal';
  }
}

// 切换语言
function changeLanguage(lang) {
  // 规范化语言代码
  const normalizedLang = normalizeLanguageCode(lang);
  
  // 存储用户选择
  localStorage.setItem('preferred-language', normalizedLang);
  
  // 重新加载页面以应用新的语言设置
  location.search = `lang=${normalizedLang}`;
}

// 等待DOM加载完成后设置语言
document.addEventListener('DOMContentLoaded', function() {
  setHtmlLanguage();
  
  // 监听语言切换器的变化
  const langSelector = document.getElementById('language-switcher-select');
  if (langSelector) {
    langSelector.addEventListener('change', function() {
      changeLanguage(this.value);
    });
  }
});

// 导出函数以便在其他地方使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getPreferredLanguage,
    normalizeLanguageCode,
    changeLanguage
  };
}