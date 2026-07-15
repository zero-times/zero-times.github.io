// Build Ledger interactions: theme, navigation, progress and accessible feedback.

(function () {
  'use strict';

  const onReady = (callback) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
      return;
    }
    callback();
  };

  onReady(() => {
    const root = document.documentElement;
    const body = document.body;
    const lang = (body.dataset.pageLang || root.lang || 'zh').toLowerCase();
    const isEnglish = lang.startsWith('en');
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const prefersReducedMotion = reducedMotionQuery.matches;
    const prefersReducedData = Boolean(connection && connection.saveData) ||
      window.matchMedia('(prefers-reduced-data: reduce)').matches;
    const liveRegion = document.getElementById('aria-live-region');

    const messages = isEnglish ? {
      required: 'Complete the required fields before sending.',
      invalidEmail: 'Enter a valid email address.',
      menuLoading: 'Loading menu',
      embedded: 'Embedded content',
      themeDark: 'Dark theme enabled.',
      themeLight: 'Light theme enabled.'
    } : {
      required: '请先填写必填内容再发送。',
      invalidEmail: '请输入有效的邮箱地址。',
      menuLoading: '正在加载菜单',
      embedded: '嵌入内容',
      themeDark: '已切换到深色主题。',
      themeLight: '已切换到浅色主题。'
    };

    const announce = (message) => {
      if (!liveRegion || !message) return;
      liveRegion.textContent = '';
      window.requestAnimationFrame(() => {
        window.setTimeout(() => {
          liveRegion.textContent = message;
        }, 40);
      });
    };

    const scheduleIdle = (task, timeout = 1200) => {
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(task, { timeout });
      } else {
        window.setTimeout(task, Math.min(timeout, 600));
      }
    };

    // Theme control ---------------------------------------------------------
    const themeButtons = document.querySelectorAll('[data-theme-toggle]');
    const getEffectiveTheme = () => {
      const explicitTheme = root.getAttribute('data-theme');
      if (explicitTheme === 'light' || explicitTheme === 'dark') return explicitTheme;
      return darkModeQuery.matches ? 'dark' : 'light';
    };

    const updateThemeColor = () => {
      const themeColorMeta = document.querySelector('meta[name="theme-color"]:not([media])');
      if (!themeColorMeta) return;
      const background = getComputedStyle(root).getPropertyValue('--ledger-bg').trim();
      if (background) themeColorMeta.setAttribute('content', background);
    };

    const syncThemeButtons = () => {
      const isDark = getEffectiveTheme() === 'dark';
      themeButtons.forEach((button) => {
        button.setAttribute('aria-pressed', String(isDark));
        button.setAttribute('aria-label', isDark ? button.dataset.labelLight : button.dataset.labelDark);
        const icon = button.querySelector('[data-theme-icon]');
        if (icon) icon.textContent = isDark ? '☼' : '◐';
      });
      updateThemeColor();
    };

    const applyTheme = (theme, persist) => {
      root.setAttribute('data-theme', theme);
      root.style.colorScheme = theme;
      if (persist) {
        try {
          window.localStorage.setItem('hoa-site-theme', theme);
        } catch (error) {
          // A blocked storage API should not prevent theme switching.
        }
      }
      syncThemeButtons();
    };

    themeButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const nextTheme = getEffectiveTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme, true);
        announce(nextTheme === 'dark' ? messages.themeDark : messages.themeLight);
      });
    });

    darkModeQuery.addEventListener('change', () => {
      if (!root.hasAttribute('data-theme')) syncThemeButtons();
    });
    syncThemeButtons();

    // Scroll progress and back-to-top --------------------------------------
    const progressBar = document.querySelector('[data-scroll-progress]');
    const backToTop = document.querySelector('.back-to-top');
    let scrollFramePending = false;

    const updateScrollUI = () => {
      const scrollRange = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
      const progress = Math.min(1, Math.max(0, window.scrollY / scrollRange));
      if (progressBar) progressBar.style.transform = `scaleX(${progress.toFixed(4)})`;
      if (backToTop) {
        const shouldShow = window.scrollY > 520;
        backToTop.hidden = !shouldShow;
        backToTop.classList.toggle('is-visible', shouldShow);
      }
      scrollFramePending = false;
    };

    const requestScrollUpdate = () => {
      if (scrollFramePending) return;
      scrollFramePending = true;
      window.requestAnimationFrame(updateScrollUI);
    };

    updateScrollUI();
    window.addEventListener('scroll', requestScrollUpdate, { passive: true });
    window.addEventListener('resize', requestScrollUpdate, { passive: true });

    if (backToTop) {
      backToTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
      });
    }

    // Reveal meaningful content once, without hiding anything when JS fails.
    const revealItems = Array.from(document.querySelectorAll(
      '[data-reveal], .portfolio-hero, .portfolio-section, .portfolio-archive-banner, .project-detail__section'
    ));
    if (revealItems.length && !prefersReducedMotion && !prefersReducedData && 'IntersectionObserver' in window) {
      root.classList.add('reveal-ready');
      const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

      revealItems.forEach((item) => revealObserver.observe(item));
    } else {
      revealItems.forEach((item) => item.classList.add('is-revealed'));
    }

    // Accessible in-page navigation ---------------------------------------
    document.addEventListener('click', (event) => {
      const anchor = event.target.closest('a[href^="#"]');
      if (!anchor || anchor.getAttribute('href') === '#' || anchor.hasAttribute('data-bs-toggle')) return;
      let target;
      try {
        target = document.querySelector(anchor.getAttribute('href'));
      } catch (error) {
        return;
      }
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
      const id = target.id;
      if (id) history.pushState(null, '', `#${encodeURIComponent(id)}`);
    });

    // Navigation state -----------------------------------------------------
    const normalizePath = (path) => {
      const normalized = (path || '/').replace(/\/+$/, '');
      return normalized || '/';
    };
    const currentPath = normalizePath(window.location.pathname);

    document.querySelectorAll('[data-site-nav]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href) return;
      let url;
      try {
        url = new URL(href, window.location.origin);
      } catch (error) {
        return;
      }
      if (url.origin !== window.location.origin) return;
      const linkPath = normalizePath(url.pathname);
      const isCurrent = linkPath === currentPath || (linkPath.endsWith('/blog') && currentPath.includes('/blog'));
      link.classList.toggle('is-active', isCurrent);
      if (isCurrent) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });

    // Lazy-load Bootstrap only for the mobile drawer.
    const drawer = document.getElementById('siteMobileDrawer');
    const menuButton = document.getElementById('mobileMenuButton');
    const menuButtonLabel = document.getElementById('mobileMenuButtonLabel');
    const bootstrapSrc = body.dataset.bootstrapSrc;
    let bootstrapPromise;

    const loadBootstrap = () => {
      if (window.bootstrap && window.bootstrap.Offcanvas) return Promise.resolve(window.bootstrap);
      if (bootstrapPromise) return bootstrapPromise;
      bootstrapPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = bootstrapSrc;
        script.async = true;
        script.fetchPriority = 'low';
        script.onload = () => window.bootstrap && window.bootstrap.Offcanvas ? resolve(window.bootstrap) : reject(new Error('Offcanvas unavailable'));
        script.onerror = () => reject(new Error('Bootstrap failed to load'));
        document.body.appendChild(script);
      }).catch((error) => {
        bootstrapPromise = null;
        throw error;
      });
      return bootstrapPromise;
    };

    const getDrawerInstance = () => {
      if (!drawer || !window.bootstrap || !window.bootstrap.Offcanvas) return null;
      const Offcanvas = window.bootstrap.Offcanvas;
      if (typeof Offcanvas.getOrCreateInstance === 'function') {
        return Offcanvas.getOrCreateInstance(drawer);
      }
      return Offcanvas.getInstance(drawer) || new Offcanvas(drawer);
    };

    const enhanceDrawer = () => {
      if (!drawer || !menuButton || !window.bootstrap || drawer.dataset.enhanced === 'true') return;
      const instance = getDrawerInstance();
      if (!instance) return;
      const closeButton = drawer.querySelector('.site-mobile-drawer__close');
      const openLabel = menuButton.getAttribute('aria-label');
      const closeLabel = closeButton ? closeButton.getAttribute('aria-label') : openLabel;
      const defaultButtonText = menuButtonLabel ? menuButtonLabel.textContent : '';
      const isolationTargets = [document.getElementById('main-content'), document.querySelector('.site-footer-v2')].filter(Boolean);

      const setIsolation = (isOpen) => {
        isolationTargets.forEach((target) => {
          if (isOpen) {
            target.setAttribute('inert', '');
            target.setAttribute('aria-hidden', 'true');
          } else {
            target.removeAttribute('inert');
            target.removeAttribute('aria-hidden');
          }
        });
      };

      drawer.addEventListener('show.bs.offcanvas', () => setIsolation(true));
      drawer.addEventListener('shown.bs.offcanvas', () => {
        menuButton.setAttribute('aria-expanded', 'true');
        menuButton.setAttribute('aria-label', closeLabel);
      });
      drawer.addEventListener('hidden.bs.offcanvas', () => {
        setIsolation(false);
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.setAttribute('aria-label', openLabel);
        if (menuButtonLabel) menuButtonLabel.textContent = defaultButtonText;
        menuButton.focus({ preventScroll: true });
      });
      drawer.addEventListener('click', (event) => {
        const link = event.target.closest('a[href]');
        if (link) instance.hide();
      });
      if (closeButton) {
        closeButton.addEventListener('click', (event) => {
          event.preventDefault();
          instance.hide();
        });
      }
      drawer.dataset.enhanced = 'true';
    };

    if (drawer && menuButton && bootstrapSrc) {
      const warmDrawer = () => loadBootstrap().then(enhanceDrawer).catch(() => {});
      menuButton.addEventListener('pointerenter', warmDrawer, { once: true, passive: true });
      menuButton.addEventListener('focus', warmDrawer, { once: true, passive: true });
      menuButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (window.bootstrap && window.bootstrap.Offcanvas) {
          enhanceDrawer();
          const instance = getDrawerInstance();
          if (instance) instance.show();
          return;
        }
        menuButton.setAttribute('aria-busy', 'true');
        if (menuButtonLabel) menuButtonLabel.textContent = messages.menuLoading;
        loadBootstrap().then(() => {
          enhanceDrawer();
          const instance = getDrawerInstance();
          if (instance) instance.show();
        }).finally(() => {
          menuButton.removeAttribute('aria-busy');
        });
      }, { capture: true });
      if (!prefersReducedData) scheduleIdle(warmDrawer, 2200);
    }

    // Form validation and Formspree warm-up -------------------------------
    document.querySelectorAll('form').forEach((form) => {
      const requiredFields = Array.from(form.querySelectorAll('[required]'));
      if (!requiredFields.length) return;

      const validate = (field) => {
        const valid = field.validity.valid && String(field.value || '').trim().length > 0;
        field.classList.toggle('is-invalid', !valid);
        if (valid) field.removeAttribute('aria-invalid');
        else field.setAttribute('aria-invalid', 'true');
        return valid;
      };

      requiredFields.forEach((field) => {
        field.addEventListener('blur', () => validate(field));
        field.addEventListener('input', () => {
          if (field.classList.contains('is-invalid') && field.validity.valid) validate(field);
        });
      });

      form.addEventListener('submit', (event) => {
        const firstInvalid = requiredFields.find((field) => !validate(field));
        if (!firstInvalid) return;
        event.preventDefault();
        firstInvalid.focus({ preventScroll: true });
        firstInvalid.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' });
        announce(firstInvalid.type === 'email' && firstInvalid.value ? messages.invalidEmail : messages.required);
      });
    });

    const formspreeForms = document.querySelectorAll('form[action*="formspree.io"]');
    if (formspreeForms.length) {
      let warmed = false;
      const warmFormspree = () => {
        if (warmed) return;
        warmed = true;
        const preconnect = document.createElement('link');
        preconnect.rel = 'preconnect';
        preconnect.href = 'https://formspree.io';
        preconnect.crossOrigin = 'anonymous';
        document.head.appendChild(preconnect);
      };
      formspreeForms.forEach((form) => {
        form.addEventListener('focusin', warmFormspree, { once: true, passive: true });
        form.addEventListener('pointerdown', warmFormspree, { once: true, passive: true });
      });
    }

    // Content safety and media defaults -----------------------------------
    const contentRoot = document.querySelector('.post-content, .article-post, .share-article');
    if (contentRoot) {
      scheduleIdle(() => {
        contentRoot.querySelectorAll('img').forEach((image) => {
          if (!image.hasAttribute('alt')) image.setAttribute('alt', '');
          if (!image.hasAttribute('decoding')) image.setAttribute('decoding', 'async');
          if (!image.hasAttribute('loading') && !image.classList.contains('featured-image')) image.setAttribute('loading', 'lazy');
        });

        contentRoot.querySelectorAll('iframe').forEach((frame) => {
          if (!frame.hasAttribute('loading')) frame.setAttribute('loading', 'lazy');
          if (!frame.hasAttribute('title')) frame.setAttribute('title', messages.embedded);
          if (!frame.hasAttribute('referrerpolicy')) frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
        });

        contentRoot.querySelectorAll('a[href]').forEach((link) => {
          let url;
          try {
            url = new URL(link.href, window.location.href);
          } catch (error) {
            return;
          }
          if (!/^https?:$/.test(url.protocol) || url.origin === window.location.origin) return;
          link.target = '_blank';
          const rel = new Set((link.rel || '').split(/\s+/).filter(Boolean));
          ['noopener', 'noreferrer', 'nofollow', 'external'].forEach((token) => rel.add(token));
          link.rel = Array.from(rel).join(' ');
          link.classList.add('is-external-link');
        });
      }, 1000);
    }
  });
})();
