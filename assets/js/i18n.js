// Multi-language content switching
// For zero-times.github.io internationalization support

(function () {
  const DATA = window.I18N_DATA || {};
  const DEFAULT_LANG = normalizeLanguageCode(DATA.defaultLang || 'pt-br');
  const SUPPORTED_LANGS = (DATA.supportedLangs || ['pt-br', 'en', 'zh'])
    .map((lang) => normalizeLanguageCode(lang))
    .filter((lang, index, arr) => arr.indexOf(lang) === index);
  const SITE_TITLE = DATA.siteTitle || '';
  const SITE_EMAIL = DATA.siteEmail || '';

  function normalizeLanguageCode(lang) {
    if (!lang) return 'pt-br';
    const normalized = String(lang).trim().toLowerCase().replace('_', '-');

    if (normalized.startsWith('pt')) return 'pt-br';
    if (normalized.startsWith('en')) return 'en';
    if (normalized.startsWith('zh') || normalized.startsWith('cn')) return 'zh';

    return normalized;
  }

  function ensureSupported(lang) {
    const normalized = normalizeLanguageCode(lang);
    if (SUPPORTED_LANGS.includes(normalized)) {
      return normalized;
    }
    return DEFAULT_LANG;
  }

  function isRtlLanguage(lang) {
    return ['ar', 'he', 'fa', 'ur'].some((prefix) => lang.startsWith(prefix));
  }

  function getPreferredLanguage() {
    const urlParams = new URLSearchParams(window.location.search);
    const langFromUrl = urlParams.get('lang');
    if (langFromUrl) {
      return ensureSupported(langFromUrl);
    }

    const storedLang = localStorage.getItem('preferred-language');
    if (storedLang) {
      return ensureSupported(storedLang);
    }

    const browserLang = navigator.language || navigator.userLanguage;
    return ensureSupported(browserLang || DEFAULT_LANG);
  }

  function updateUrlLanguage(lang) {
    const url = new URL(window.location.href);
    url.searchParams.set('lang', lang);
    window.history.replaceState({}, '', url.toString());
  }

  function resolvePath(root, path) {
    if (!root || !path) return undefined;
    const parts = path.split('.');
    let value = root;

    for (const part of parts) {
      if (Array.isArray(value)) {
        const index = Number(part);
        value = Number.isInteger(index) ? value[index] : undefined;
      } else if (value && typeof value === 'object') {
        value = value[part];
      } else {
        value = undefined;
      }

      if (value === undefined || value === null) break;
    }

    return value;
  }

  function interpolate(value) {
    if (typeof value !== 'string') return value;
    return value
      .replace(/\{\{\s*site\.title\s*\}\}/g, SITE_TITLE)
      .replace(/\{\{\s*site\.email\s*\}\}/g, SITE_EMAIL)
      .replace(/\{\{\s*title\s*\}\}/g, SITE_TITLE)
      .replace(/\{\{\s*email\s*\}\}/g, SITE_EMAIL);
  }

  function getTranslation(key, lang) {
    const root = { ...(DATA.translations || {}) };
    if (DATA.menus) {
      root.menus = DATA.menus;
    }

    let value = resolvePath(root, key);

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      value =
        value[lang] ||
        value[DEFAULT_LANG] ||
        value.en ||
        value['pt-br'] ||
        value.zh ||
        Object.values(value)[0];
    }

    if (typeof value === 'string') {
      return interpolate(value);
    }

    return value;
  }

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

  function applyTranslations(lang) {
    const normalizedLang = ensureSupported(lang);

    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.textContent = value;
      }
    });

    document.querySelectorAll('[data-i18n-html]').forEach((el) => {
      const key = el.getAttribute('data-i18n-html');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.innerHTML = value;
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.setAttribute('placeholder', value);
      }
    });

    document.querySelectorAll('[data-i18n-value]').forEach((el) => {
      const key = el.getAttribute('data-i18n-value');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.setAttribute('value', value);
      }
    });

    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const key = el.getAttribute('data-i18n-title');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.setAttribute('title', value);
      }
    });

    document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
      const key = el.getAttribute('data-i18n-aria');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.setAttribute('aria-label', value);
      }
    });

    document.querySelectorAll('[data-i18n-alt]').forEach((el) => {
      const key = el.getAttribute('data-i18n-alt');
      const value = getTranslation(key, normalizedLang);
      if (typeof value === 'string') {
        el.setAttribute('alt', value);
      }
    });
  }

  function updateLanguage(lang) {
    const normalizedLang = ensureSupported(lang);
    const dir = isRtlLanguage(normalizedLang) ? 'rtl' : 'ltr';

    document.documentElement.lang = normalizedLang;
    document.documentElement.dir = dir;

    const metaLang = document.querySelector('meta[name="language"]');
    if (metaLang) {
      metaLang.setAttribute('content', normalizedLang);
    }

    updateBodyClasses(normalizedLang, dir);

    if (document.body) {
      if (normalizedLang === 'zh') {
        document.body.style.fontFeatureSettings = '"liga", "clig", "calt", "hanj"';
      } else {
        document.body.style.fontFeatureSettings = 'normal';
      }
    }

    const langSelector = document.getElementById('language-switcher-select');
    if (langSelector) {
      langSelector.value = normalizedLang;
    }

    applyTranslations(normalizedLang);
  }

  function changeLanguage(lang) {
    const normalizedLang = ensureSupported(lang);
    localStorage.setItem('preferred-language', normalizedLang);
    updateUrlLanguage(normalizedLang);
    updateLanguage(normalizedLang);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const initialLang = getPreferredLanguage();
    updateLanguage(initialLang);

    const langSelector = document.getElementById('language-switcher-select');
    if (langSelector) {
      langSelector.addEventListener('change', function () {
        changeLanguage(this.value);
      });
    }
  });

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      getPreferredLanguage,
      normalizeLanguageCode,
      changeLanguage,
      applyTranslations,
    };
  }
})();
