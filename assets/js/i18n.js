// 多语言内容切换功能
// 用于 zero-times.github.io 博客的国际化支持

// 从本地存储或浏览器语言获取首选语言
function getPreferredLanguage() {
  const storedLang = localStorage.getItem('preferred-language');
  if (storedLang) {
    return storedLang;
  }
  
  // 检测浏览器语言
  const browserLang = navigator.language || navigator.userLanguage;
  if (browserLang.startsWith('pt')) {
    return 'pt-br';
  } else if (browserLang.startsWith('en')) {
    return 'en';
  } else if (browserLang.startsWith('zh')) {
    return 'zh';
  }
  
  // 默认为葡萄牙语（面向巴西用户）
  return 'pt-br';
}

// 根据当前语言设置HTML的lang属性
function setHtmlLanguage() {
  const currentLang = getPreferredLanguage();
  document.documentElement.lang = currentLang;
}

// 初始化语言设置
document.addEventListener('DOMContentLoaded', function() {
  setHtmlLanguage();
});

// 全局语言切换函数（供language-switcher.html使用）
function changeLanguage(lang) {
  localStorage.setItem('preferred-language', lang);
  location.reload();
}