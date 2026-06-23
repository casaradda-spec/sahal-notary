(function () {
  var STORAGE_KEY = 'sahal_sidebar_collapsed';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var sidebar = document.getElementById('app-sidebar');
    var hamburger = document.getElementById('sidebar-toggle');
    var overlay = document.getElementById('sidebar-overlay');
    var collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (!sidebar) return;

    function openMobile() {
      sidebar.classList.add('mobile-open');
      if (overlay) overlay.classList.add('active');
      if (hamburger) {
        hamburger.classList.add('open');
        hamburger.setAttribute('aria-expanded', 'true');
      }
      document.body.classList.add('sidebar-no-scroll');
    }

    function closeMobile() {
      sidebar.classList.remove('mobile-open');
      if (overlay) overlay.classList.remove('active');
      if (hamburger) {
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      }
      document.body.classList.remove('sidebar-no-scroll');
    }

    if (hamburger) {
      hamburger.addEventListener('click', function () {
        if (sidebar.classList.contains('mobile-open')) closeMobile();
        else openMobile();
      });
    }
    if (overlay) overlay.addEventListener('click', closeMobile);
    sidebar.querySelectorAll('.sidebar-nav a').forEach(function (link) {
      link.addEventListener('click', closeMobile);
    });

    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        var collapsed = sidebar.classList.toggle('collapsed');
        try { localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0'); } catch (e) {}
      });
    }
  });
})();
