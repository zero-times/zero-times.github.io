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

  // Enhance form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      // Add basic validation if not already present
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;

      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          field.classList.add('is-invalid');
          isValid = false;
        } else {
          field.classList.remove('is-invalid');
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
        announceToScreenReader('Por favor, preencha todos os campos obrigatórios.');
      }
    });

    // Real-time validation feedback
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    inputs.forEach(input => {
      const updateValidity = function() {
        if (!this.value.trim()) {
          this.classList.add('is-invalid');
        } else {
          this.classList.remove('is-invalid');
        }
      };
      input.addEventListener('blur', updateValidity);
      input.addEventListener('input', updateValidity);
    });
  });

  // Update active nav link based on current page
  const navLinks = document.querySelectorAll('.nav-link');
  const currentPage = window.location.pathname;
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    const isBlogSection = href === '/blog/' && currentPage.startsWith('/blog/');
    const isCurrent = href === currentPage || isBlogSection;

    if (isCurrent) {
      link.setAttribute('aria-current', 'page');
      link.classList.add('active');
    } else {
      link.removeAttribute('aria-current');
      link.classList.remove('active');
    }
  });

  // Add language attribute to html tag if not present
  if (!document.documentElement.getAttribute('lang')) {
    document.documentElement.setAttribute('lang', 'pt-BR');
  }

  // Add image defaults for performance (avoid overriding eager images)
  const images = document.querySelectorAll('img');
  images.forEach(img => {
    if (!img.hasAttribute('loading')) {
      img.setAttribute('loading', 'lazy');
    }
    if (!img.hasAttribute('decoding')) {
      img.setAttribute('decoding', 'async');
    }
    if (!img.hasAttribute('alt')) {
      img.setAttribute('alt', '');
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
