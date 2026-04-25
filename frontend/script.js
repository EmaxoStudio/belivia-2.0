document.addEventListener('DOMContentLoaded', function () {
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealDelayStep = 36;
  var revealDelayMax = 144;

  var revealGroups = [
    'main section:not(.hero)',
    'main > .cta-band',
    'main > .cta-band-soft',
    'main > .einsatz-strip'
  ];

  var cardGroups = [
    '.services-grid > *',
    '.check-cards > *',
    '.contact-cards > *',
    '.related-services-grid > *',
    '.trust-grid > *',
    '.funnel-check-grid > *'
  ];

  function markRevealTargets(selectorList, staggered) {
    document.querySelectorAll(selectorList.join(', ')).forEach(function (element, index) {
      if (element.classList.contains('hero')) {
        return;
      }

      element.classList.add('reveal');

      if (staggered) {
        var delay = Math.min((index % 6) * revealDelayStep, revealDelayMax);
        element.style.setProperty('--reveal-delay', delay + 'ms');
      }
    });
  }

  markRevealTargets(revealGroups, false);
  markRevealTargets(cardGroups, true);

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    document.querySelectorAll('.reveal').forEach(function (element) {
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

  document.querySelectorAll('.reveal').forEach(function (element) {
    observer.observe(element);
  });
});
