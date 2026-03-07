// Main JavaScript file for the Portuguese Personal Blog

document.addEventListener('DOMContentLoaded', function() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const prefersReducedDataMedia = window.matchMedia('(prefers-reduced-data: reduce)').matches;
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const prefersReducedData = prefersReducedDataMedia || !!(
    connection && (connection.saveData || connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g' || connection.effectiveType === '3g')
  );

  // Use delegated smooth scrolling to avoid binding listeners to every anchor node.
  document.addEventListener('click', function(e) {
    const anchor = e.target.closest('a[href^="#"]');
    if (!anchor) {
      return;
    }
    const href = anchor.getAttribute('href');
    if (!href || href === '#' || href === '#!' || href.startsWith('#!') || anchor.hasAttribute('data-bs-toggle')) {
      return;
    }
    let target = null;
    try {
      target = document.querySelector(href);
    } catch (err) {
      return;
    }
    if (!target) {
      return;
    }
    e.preventDefault();
    target.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'start'
    });

    const targetId = target.getAttribute('id');
    if (targetId) {
      const encodedHash = `#${encodeURIComponent(targetId)}`;
      if (window.location.hash !== encodedHash) {
        history.pushState(null, '', encodedHash);
      }
    }

    if (!target.hasAttribute('tabindex')) {
      target.setAttribute('tabindex', '-1');
      target.setAttribute('data-anchor-focus-temp', 'true');
    }

    const focusDelay = prefersReducedMotion ? 0 : 220;
    window.setTimeout(() => {
      target.focus({ preventScroll: true });
      if (target.getAttribute('data-anchor-focus-temp') === 'true') {
        target.removeAttribute('tabindex');
        target.removeAttribute('data-anchor-focus-temp');
      }
    }, focusDelay);
  });

  // Reading progress indicator for post pages
  const progressBar = document.querySelector('.reading-progress__bar');
  const progressRoot = progressBar ? progressBar.closest('.reading-progress') : null;
  if (progressBar && !prefersReducedData) {
    let ticking = false;
    const updateProgress = () => {
      const docHeight = document.documentElement.scrollHeight;
      const winHeight = window.innerHeight;
      const maxScroll = Math.max(docHeight - winHeight, 1);
      const progress = Math.min(100, Math.max(0, (window.scrollY / maxScroll) * 100));
      progressBar.style.width = `${progress.toFixed(2)}%`;
      if (progressRoot) {
        const roundedProgress = Math.round(progress);
        progressRoot.setAttribute('aria-valuenow', `${roundedProgress}`);
        progressRoot.setAttribute('aria-valuetext', `Progresso de leitura: ${roundedProgress}%`);
      }
      ticking = false;
    };
    const requestTick = () => {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(updateProgress);
      }
    };
    updateProgress();
    window.addEventListener('scroll', requestTick, { passive: true });
    window.addEventListener('resize', requestTick);
  }

  // Back-to-top button for long pages
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop && !prefersReducedData) {
    const backToTopThreshold = 480;
    let backToTopTicking = false;
    const setBackToTopVisibility = (shouldShow) => {
      if (shouldShow) {
        backToTop.hidden = false;
        backToTop.classList.add('is-visible');
      } else {
        backToTop.classList.remove('is-visible');
        backToTop.hidden = true;
      }
    };
    const scrollToTop = () => {
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion ? 'auto' : 'smooth'
      });
    };
    const requestBackToTopTick = () => {
      if (backToTopTicking) {
        return;
      }
      backToTopTicking = true;
      window.requestAnimationFrame(() => {
        setBackToTopVisibility(window.scrollY > backToTopThreshold);
        backToTopTicking = false;
      });
    };
    backToTop.addEventListener('click', scrollToTop);
    if ('IntersectionObserver' in window) {
      const sentinel = document.createElement('span');
      sentinel.setAttribute('aria-hidden', 'true');
      sentinel.style.cssText = `position:absolute;top:${backToTopThreshold}px;left:0;width:1px;height:1px;pointer-events:none;opacity:0;`;
      document.body.prepend(sentinel);

      const observer = new IntersectionObserver((entries) => {
        const entry = entries[0];
        setBackToTopVisibility(!entry.isIntersecting);
      });
      observer.observe(sentinel);

      window.addEventListener('pagehide', () => {
        observer.disconnect();
        sentinel.remove();
      }, { once: true });
    } else {
      setBackToTopVisibility(window.scrollY > backToTopThreshold);
      window.addEventListener('scroll', requestBackToTopTick, { passive: true });
      window.addEventListener('resize', requestBackToTopTick);
    }
  }

  // Enhance form validation
  const forms = document.querySelectorAll('form');
  const requiredInputSelector = 'input[required], textarea[required], select[required]';
  const validateRequiredField = (field) => {
    if (!field || !field.matches(requiredInputSelector)) {
      return true;
    }

    const trimmedValue = typeof field.value === 'string' ? field.value.trim() : field.value;
    const fieldValid = trimmedValue.length > 0 && field.validity.valid;

    if (!fieldValid) {
      field.classList.add('is-invalid');
      field.setAttribute('aria-invalid', 'true');
      return false;
    }

    field.classList.remove('is-invalid');
    field.removeAttribute('aria-invalid');
    return true;
  };

  forms.forEach(form => {
    const requiredFields = form.querySelectorAll('[required]');
    if (!requiredFields.length) {
      return;
    }

    form.addEventListener('submit', function(e) {
      let isValid = true;

      requiredFields.forEach(field => {
        if (!validateRequiredField(field)) {
          isValid = false;
        }
      });

      if (!isValid) {
        e.preventDefault();
        form.classList.add('was-validated');
        const firstInvalid = form.querySelector('.is-invalid, [required]:invalid');
        if (firstInvalid) {
          firstInvalid.focus({ preventScroll: true });
          firstInvalid.scrollIntoView({
            behavior: prefersReducedMotion ? 'auto' : 'smooth',
            block: 'center'
          });
        }
        let announceMessage = 'Por favor, preencha todos os campos obrigatórios.';
        if (firstInvalid) {
          const trimmedValue = firstInvalid.value.trim();
          if (firstInvalid.type === 'email' && trimmedValue && !firstInvalid.validity.valid) {
            announceMessage = 'Por favor, insira um email válido.';
          } else if (firstInvalid.type === 'url' && trimmedValue && !firstInvalid.validity.valid) {
            announceMessage = 'Por favor, insira um link válido.';
          }
        }
        announceToScreenReader(announceMessage);
      }
    });

    // Real-time validation feedback with event delegation to reduce listeners on mobile forms.
    form.addEventListener('input', function(e) {
      validateRequiredField(e.target);
    });

    form.addEventListener('focusout', function(e) {
      validateRequiredField(e.target);
    });
  });

  // Update active nav state for desktop nav and mobile drawer nav.
  const normalizePath = (path) => {
    if (!path) return '/';
    const trimmed = path.replace(/\/+$/, '');
    return trimmed || '/';
  };

  const currentPath = normalizePath(window.location.pathname);
  const navLinks = document.querySelectorAll('[data-site-nav]');
  navLinks.forEach(link => {
    if (link.getAttribute('aria-disabled') === 'true') {
      return;
    }

    const href = link.getAttribute('href');
    if (!href) {
      return;
    }

    let resolved;
    try {
      resolved = new URL(href, window.location.origin);
    } catch (err) {
      return;
    }

    if (resolved.origin !== window.location.origin) {
      return;
    }

    const linkPath = normalizePath(resolved.pathname);
    const isBlogSection = linkPath === '/blog' && currentPath.startsWith('/blog');
    const isCurrent = currentPath === linkPath || isBlogSection;

    link.classList.toggle('is-active', isCurrent);
    if (isCurrent) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  });

  // Mobile drawer state sync: Menu <-> Fechar and aria-expanded.
  const mobileDrawer = document.getElementById('siteMobileDrawer');
  const mobileMenuButton = document.getElementById('mobileMenuButton');
  const mobileMenuButtonLabel = document.getElementById('mobileMenuButtonLabel');
  if (mobileDrawer && mobileMenuButton && window.bootstrap && bootstrap.Offcanvas) {
    const drawerInstance = bootstrap.Offcanvas.getOrCreateInstance(mobileDrawer);
    const syncMenuState = (isExpanded) => {
      mobileMenuButton.setAttribute('aria-expanded', String(isExpanded));
      mobileMenuButton.setAttribute('aria-label', isExpanded ? 'Fechar menu principal' : 'Abrir menu principal');
      if (mobileMenuButtonLabel) {
        mobileMenuButtonLabel.textContent = isExpanded ? 'Fechar' : 'Menu';
      }
    };

    mobileDrawer.addEventListener('shown.bs.offcanvas', () => syncMenuState(true));
    mobileDrawer.addEventListener('hidden.bs.offcanvas', () => syncMenuState(false));

    mobileDrawer.addEventListener('click', (event) => {
      const link = event.target.closest('a[href]');
      if (!link || !mobileDrawer.contains(link) || link.hasAttribute('data-bs-toggle')) {
        return;
      }
      drawerInstance.hide();
    });

    syncMenuState(false);
  }

  // Ensure security rel attributes for external links that open in new tabs
  const ensureSecureRel = (link) => {
    if (!link || link.getAttribute('target') !== '_blank') {
      return;
    }
    const href = link.getAttribute('href') || '';
    let isExternalHttp = false;
    try {
      const resolvedUrl = new URL(href, window.location.origin);
      isExternalHttp = /^https?:$/i.test(resolvedUrl.protocol) && resolvedUrl.origin !== window.location.origin;
    } catch (err) {
      isExternalHttp = false;
    }

    const relValue = link.getAttribute('rel') || '';
    const relTokens = relValue.split(/\s+/).filter(Boolean);
    let changed = false;
    ['noopener', 'noreferrer'].forEach(token => {
      if (!relTokens.includes(token)) {
        relTokens.push(token);
        changed = true;
      }
    });
    if (isExternalHttp) {
      ['nofollow', 'external'].forEach(token => {
        if (!relTokens.includes(token)) {
          relTokens.push(token);
          changed = true;
        }
      });
    }
    if (changed) {
      link.setAttribute('rel', relTokens.join(' '));
    }
  };

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[target="_blank"]');
    if (!link) {
      return;
    }
    ensureSecureRel(link);
  }, { capture: true });

  // Add language attribute to html tag if not present
  if (!document.documentElement.getAttribute('lang')) {
    document.documentElement.setAttribute('lang', 'pt-BR');
  }

  const enhanceMediaDefaults = () => {
    // Add media defaults on content area only to reduce unnecessary DOM work.
    const mediaScope = document.querySelector('main') || document.body;
    const imagesMissingDefaults = mediaScope.querySelectorAll(
      'img:not([src^="data:"]):not([loading]), ' +
      'img:not([src^="data:"]):not([decoding]), ' +
      'img:not([src^="data:"]):not([alt]), ' +
      'img:not([src^="data:"])[loading="lazy"]:not([fetchpriority])'
    );
    imagesMissingDefaults.forEach(img => {
      const fetchPriority = img.getAttribute('fetchpriority');
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', fetchPriority === 'high' ? 'eager' : 'lazy');
      }
      if (!img.hasAttribute('decoding')) {
        img.setAttribute('decoding', 'async');
      }
      if (!img.hasAttribute('alt')) {
        img.setAttribute('alt', '');
      }
      if (!img.hasAttribute('fetchpriority') && img.getAttribute('loading') === 'lazy') {
        img.setAttribute('fetchpriority', 'low');
      }
    });

    const iframesMissingDefaults = mediaScope.querySelectorAll(
      'iframe:not([loading]), iframe:not([fetchpriority]), iframe:not([title]), iframe:not([referrerpolicy])'
    );
    iframesMissingDefaults.forEach(frame => {
      if (!frame.hasAttribute('loading')) {
        frame.setAttribute('loading', 'lazy');
      }
      if (!frame.hasAttribute('fetchpriority')) {
        frame.setAttribute('fetchpriority', 'low');
      }
      if (!frame.hasAttribute('title')) {
        const fallbackTitle = frame.getAttribute('data-title') || frame.getAttribute('aria-label') || 'Embedded content';
        frame.setAttribute('title', fallbackTitle);
      }
      if (!frame.hasAttribute('referrerpolicy')) {
        frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
      }
    });

    const mediaElementsMissingDefaults = mediaScope.querySelectorAll(
      'video:not([preload]), video:not([playsinline]), audio:not([preload])'
    );
    mediaElementsMissingDefaults.forEach(media => {
      if (!media.hasAttribute('preload')) {
        media.setAttribute('preload', 'metadata');
      }
      if (media.tagName.toLowerCase() === 'video' && !media.hasAttribute('playsinline')) {
        media.setAttribute('playsinline', '');
      }
    });

    const lazyImages = mediaScope.querySelectorAll('img[data-src]');
    if (lazyImages.length > 0) {
      if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              const img = entry.target;
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
              observer.unobserve(img);
            }
          });
        });

        lazyImages.forEach(img => imageObserver.observe(img));
      } else {
        lazyImages.forEach(img => {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
        });
      }
    }

    const newsInlineThumbs = mediaScope.querySelectorAll('img.news-inline-thumb');
    newsInlineThumbs.forEach(img => {
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
      if (!img.hasAttribute('decoding')) {
        img.setAttribute('decoding', 'async');
      }
      if (!img.hasAttribute('fetchpriority')) {
        img.setAttribute('fetchpriority', 'low');
      }
      if (!img.hasAttribute('alt')) {
        img.setAttribute('alt', 'Imagem relacionada à notícia');
      }
      img.classList.add('news-inline-thumb--lazy');
    });
  };

  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(enhanceMediaDefaults, { timeout: prefersReducedData ? 2200 : 1200 });
  } else {
    window.setTimeout(enhanceMediaDefaults, prefersReducedData ? 700 : 300);
  }

  // Add focus management for dropdowns with delegated listener to reduce bindings
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter' && e.key !== ' ') {
      return;
    }
    const dropdown = e.target.closest('.dropdown-toggle');
    if (!dropdown) {
      return;
    }
    e.preventDefault();
    dropdown.click();
  });

  // Enhance modal dialogs (if any) without forcing eager Bootstrap instances.
  if (window.bootstrap && window.bootstrap.Modal) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
      modal.addEventListener('shown.bs.modal', function() {
        const focusableElements = modal.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        }
      });
    });
  }
});

// Utility function for dynamic content updates
function updateLanguage(lang) {
  // Update language in URL or perform other language switching logic
  console.log(`Switching to language: ${lang}`);
  // Additional logic would go here
}

// Utility function for announcement of dynamic content changes
function announceToScreenReader(message) {
  const element = document.getElementById('aria-live-region');
  if (!element) {
    return;
  }
  element.textContent = '';
  window.requestAnimationFrame(() => {
    window.setTimeout(() => {
      element.textContent = message;
    }, 50);
  });
}
