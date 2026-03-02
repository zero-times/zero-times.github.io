// Main JavaScript file for the Portuguese Personal Blog

document.addEventListener('DOMContentLoaded', function() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (!href || href === '#' || href === '#!' || href.startsWith('#!') || this.hasAttribute('data-bs-toggle')) {
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
    });
  });

  // Reading progress indicator for post pages
  const progressBar = document.querySelector('.reading-progress__bar');
  const progressRoot = progressBar ? progressBar.closest('.reading-progress') : null;
  if (progressBar) {
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
  if (backToTop) {
    const toggleBackToTop = () => {
      const shouldShow = window.scrollY > 480;
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
    backToTop.addEventListener('click', scrollToTop);
    toggleBackToTop();
    window.addEventListener('scroll', toggleBackToTop, { passive: true });
    window.addEventListener('resize', toggleBackToTop);
  }

  // Enhance form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      // Add basic validation if not already present
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;

      requiredFields.forEach(field => {
        const trimmedValue = field.value.trim();
        const fieldValid = trimmedValue.length > 0 && field.validity.valid;

        if (!fieldValid) {
          field.classList.add('is-invalid');
          field.setAttribute('aria-invalid', 'true');
          isValid = false;
        } else {
          field.classList.remove('is-invalid');
          field.removeAttribute('aria-invalid');
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

    // Real-time validation feedback
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    inputs.forEach(input => {
      const updateValidity = function() {
        const trimmedValue = this.value.trim();
        const fieldValid = trimmedValue.length > 0 && this.validity.valid;

        if (!fieldValid) {
          this.classList.add('is-invalid');
          this.setAttribute('aria-invalid', 'true');
        } else {
          this.classList.remove('is-invalid');
          this.removeAttribute('aria-invalid');
        }
      };
      input.addEventListener('blur', updateValidity);
      input.addEventListener('input', updateValidity);
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

    mobileDrawer.querySelectorAll('a[href]').forEach(link => {
      link.addEventListener('click', () => {
        drawerInstance.hide();
      });
    });

    syncMenuState(false);
  }

  // Ensure security rel attributes for external links that open in new tabs
  const newTabLinks = document.querySelectorAll('a[target="_blank"]');
  newTabLinks.forEach(link => {
    const relValue = link.getAttribute('rel') || '';
    const relTokens = relValue.split(/\s+/).filter(Boolean);
    let changed = false;
    ['noopener', 'noreferrer'].forEach(token => {
      if (!relTokens.includes(token)) {
        relTokens.push(token);
        changed = true;
      }
    });
    if (changed) {
      link.setAttribute('rel', relTokens.join(' '));
    }
  });

  // Add language attribute to html tag if not present
  if (!document.documentElement.getAttribute('lang')) {
    document.documentElement.setAttribute('lang', 'pt-BR');
  }

  // Add image defaults for performance (avoid overriding eager images)
  const images = document.querySelectorAll('img');
  images.forEach(img => {
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

  const iframes = document.querySelectorAll('iframe');
  iframes.forEach(frame => {
    if (!frame.hasAttribute('loading')) {
      frame.setAttribute('loading', 'lazy');
    }
    if (!frame.hasAttribute('title')) {
      const fallbackTitle = frame.getAttribute('data-title') || frame.getAttribute('aria-label') || 'Embedded content';
      frame.setAttribute('title', fallbackTitle);
    }
  });

  const mediaElements = document.querySelectorAll('video, audio');
  mediaElements.forEach(media => {
    if (!media.hasAttribute('preload')) {
      media.setAttribute('preload', 'metadata');
    }
    if (media.tagName.toLowerCase() === 'video' && !media.hasAttribute('playsinline')) {
      media.setAttribute('playsinline', '');
    }
  });

  const lazyImages = document.querySelectorAll('img[data-src]');
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          imageObserver.unobserve(img);
        }
      });
    });

    lazyImages.forEach(img => imageObserver.observe(img));
  }

  const newsInlineThumbs = document.querySelectorAll('img.news-inline-thumb');
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

  // Add focus management for dropdowns
  const dropdowns = document.querySelectorAll('.dropdown-toggle');
  dropdowns.forEach(dropdown => {
    dropdown.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        this.click();
      }
    });
  });

  // Enhance modal dialogs (if any)
  const modals = document.querySelectorAll('.modal');
  modals.forEach(modal => {
    const modalElement = new bootstrap.Modal(modal);
    
    // Trap focus inside modal
    modal.addEventListener('shown.bs.modal', function() {
      const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    });
  });
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
