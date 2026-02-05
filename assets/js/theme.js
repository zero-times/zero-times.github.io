// Main JavaScript file for the Portuguese Personal Blog

document.addEventListener('DOMContentLoaded', function() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
          block: 'start'
        });
      }
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
        alert('Por favor, preencha todos os campos obrigatórios.');
      }
    });

    // Real-time validation feedback
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    inputs.forEach(input => {
      input.addEventListener('blur', function() {
        if (!this.value.trim()) {
          this.classList.add('is-invalid');
        } else {
          this.classList.remove('is-invalid');
        }
      });
    });
  });

  // Add ARIA attributes for better accessibility
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    if (!link.getAttribute('aria-current')) {
      link.setAttribute('aria-current', 'false');
    }
  });

  // Update active nav link based on current page
  const currentPage = window.location.pathname;
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPage || 
        (currentPage.includes('/blog/') && link.getAttribute('href') === '/blog/')) {
      link.setAttribute('aria-current', 'true');
      link.classList.add('active');
    }
  });

  // Add language attribute to html tag if not present
  if (!document.documentElement.getAttribute('lang')) {
    document.documentElement.setAttribute('lang', 'pt-BR');
  }

  // Add image lazy loading for performance
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
  let element = document.getElementById('aria-live-region');
  if (!element) {
    element = document.createElement('div');
    element.id = 'aria-live-region';
    element.setAttribute('aria-live', 'polite');
    element.setAttribute('aria-atomic', 'true');
    element.style.position = 'absolute';
    element.style.left = '-9999px';
    document.body.appendChild(element);
  }
  element.textContent = message;
}
