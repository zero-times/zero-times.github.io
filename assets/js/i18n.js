// Simple language switching for zero-times.github.io
// Simplified version without complex internationalization

(function () {
  const DEFAULT_LANG = 'pt-BR';
  
  function updateBodyClasses(lang, dir) {
    if (!document.body) return;
    const classes = document.body.className
      .split(' ')
      .filter((cls) =>
        cls &&
        !cls.startsWith('locale-') &&
        !cls.startsWith('lang-') &&
        !cls.startsWith('dir-')
      );

    classes.push(`locale-${lang}`);
    classes.push(`dir-${dir}`);
    document.body.className = classes.join(' ');
  }

  function updateLanguage(lang) {
    const normalizedLang = lang || DEFAULT_LANG;
    const dir = 'ltr'; // Default to left-to-right

    document.documentElement.lang = normalizedLang;
    document.documentElement.dir = dir;

    const metaLang = document.querySelector('meta[name="language"]');
    if (metaLang) {
      metaLang.setAttribute('content', normalizedLang);
    }

    updateBodyClasses(normalizedLang, dir);

    const langSelector = document.getElementById('language-switcher-select');
    if (langSelector) {
      langSelector.value = normalizedLang;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    updateLanguage(DEFAULT_LANG);

    const langSelector = document.getElementById('language-switcher-select');
    if (langSelector) {
      langSelector.addEventListener('change', function () {
        // For now, just update the language without complex translation
        updateLanguage(this.value);
      });
    }
  });
})();