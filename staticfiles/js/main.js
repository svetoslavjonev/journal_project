document.documentElement.classList.add('js-enabled');

/* Confirm dialogs on destructive forms */
document.querySelectorAll('form[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    const message = form.getAttribute('data-confirm');
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
});

/* Auto-resize textareas */
const autosize = (textarea) => {
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight}px`;
};

document.querySelectorAll('textarea').forEach((textarea) => {
  autosize(textarea);
  textarea.addEventListener('input', () => autosize(textarea));
});

/* "/" focuses search */
document.addEventListener('keydown', (event) => {
  if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) {
    return;
  }
  const active = document.activeElement;
  const isTyping = active && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName);
  if (isTyping) return;

  const searchInput = document.querySelector('input[type="search"], input[name="q"]');
  if (searchInput) {
    event.preventDefault();
    searchInput.focus();
  }
});

/* Mobile nav toggle */
const header = document.querySelector('.site-header');
const navToggle = document.querySelector('.nav-toggle');

if (header && navToggle) {
  const setNavOpen = (open) => {
    header.dataset.navOpen = String(open);
    navToggle.setAttribute('aria-expanded', String(open));
  };

  setNavOpen(false);

  navToggle.addEventListener('click', () => {
    const open = header.dataset.navOpen !== 'true';
    setNavOpen(open);
  });

  /* Close nav when a link inside is activated */
  header.querySelectorAll('.site-nav a, .account-nav a').forEach((link) => {
    link.addEventListener('click', () => setNavOpen(false));
  });

  /* Close nav on Escape */
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && header.dataset.navOpen === 'true') {
      setNavOpen(false);
      navToggle.focus();
    }
  });

  /* Reset on resize past breakpoint */
  const mql = window.matchMedia('(min-width: 761px)');
  const onChange = () => {
    if (mql.matches) setNavOpen(false);
  };
  if (mql.addEventListener) mql.addEventListener('change', onChange);
  else mql.addListener(onChange);
}

/* Back-to-top button */
const backToTop = document.querySelector('.back-to-top');
if (backToTop) {
  backToTop.hidden = false;
  const threshold = 480;

  const onScroll = () => {
    if (window.scrollY > threshold) {
      backToTop.classList.add('is-visible');
    } else {
      backToTop.classList.remove('is-visible');
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* Auto-dismiss success/info messages after a delay */
document.querySelectorAll('.message-success, .message-info').forEach((msg) => {
  setTimeout(() => {
    msg.style.transition = 'opacity 400ms ease, transform 400ms ease';
    msg.style.opacity = '0';
    msg.style.transform = 'translateY(-4px)';
    setTimeout(() => msg.remove(), 420);
  }, 5000);
});