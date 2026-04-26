document.addEventListener('DOMContentLoaded', function () {
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealDelayStep = 46;
  var revealDelayMax = 230;

  var revealGroups = [
    'main > .cta-band',
    'main > .cta-band-soft',
    'main > .einsatz-strip'
  ];

  var cardGroups = [
    '.service-img-grid > *',
    '.services-grid > *',
    '.steps-grid > *',
    '.check-cards > *',
    '.contact-cards > *',
    '.related-services-grid > *',
    '.trust-grid > *',
    '.funnel-check-grid > *',
    '.faq-list > *'
  ];

  function addReveal(element, revealClass, delay) {
    if (!element || element.classList.contains('hero')) {
      return;
    }

    element.classList.add(revealClass || 'reveal-up');

    if (typeof delay === 'number') {
      element.style.setProperty('--reveal-delay', delay + 'ms');
    }
  }

  function markRevealTargets(selectorList, revealClass, staggered) {
    document.querySelectorAll(selectorList.join(', ')).forEach(function (element, index) {
      addReveal(element, revealClass || 'reveal-up');

      if (staggered) {
        var delay = Math.min((index % 6) * revealDelayStep, revealDelayMax);
        element.style.setProperty('--reveal-delay', delay + 'ms');
      }
    });
  }

  markRevealTargets(revealGroups, 'reveal-soft', false);
  markRevealTargets(cardGroups, 'reveal-up', true);

  document.querySelectorAll('.hero .hero-tag, .hero h1, .hero .benefit-chips, .hero .hero-cta-group, .hero .hero-sub').forEach(function (element, index) {
    addReveal(element, 'reveal-up', Math.min(index * 70, revealDelayMax));
  });
  addReveal(document.querySelector('.hero .hero-img'), 'reveal-right', 160);

  document.querySelectorAll('.image-feature').forEach(function (feature, index) {
    addReveal(feature.querySelector('.image-feature-content'), 'reveal-up', 60);

    var media = feature.querySelector('.image-feature-media');
    if (media && !media.classList.contains('reveal-left') && !media.classList.contains('reveal-right')) {
      addReveal(media, index % 2 === 0 ? 'reveal-right' : 'reveal-left', 120);
    }
  });

  document.querySelectorAll('.two-col, .contact-layout').forEach(function (group) {
    Array.prototype.forEach.call(group.children, function (element, index) {
      addReveal(element, index % 2 === 0 ? 'reveal-up' : 'reveal-right', Math.min(index * 70, revealDelayMax));
    });
  });

  document.querySelectorAll('.trust-strip-item').forEach(function (element, index) {
    addReveal(element, 'reveal-soft', Math.min(index * 45, revealDelayMax));
  });

  document.querySelectorAll('.section-lead, .steps-note, .funnel-check-cta, .info-box, .highlight-box, .next-steps-block, .scope-not-list').forEach(function (element) {
    addReveal(element, 'reveal-up', 80);
  });

  var allRevealSelector = '.reveal, .reveal-left, .reveal-right, .reveal-up, .reveal-soft';

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    document.querySelectorAll(allRevealSelector).forEach(function (element) {
      element.classList.add('visible');
    });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) {
        return;
      }

      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    });
  }, {
    rootMargin: '0px 0px -10% 0px',
    threshold: 0.12
  });

  document.querySelectorAll(allRevealSelector).forEach(function (element) {
    observer.observe(element);
  });
});
