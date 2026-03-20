'use strict';

const App = (() => {
  let activeView = 'analyze';

  // ─── Init ─────────────────────────────────────────────────────────────────
  function init() {
    Upload.init();
    bindAnalyzeButtons();
    bindNavigation();
    bindMobileSidebar();
    bindClearHistory();
  }

  // ─── Navigation ───────────────────────────────────────────────────────────
  function bindNavigation() {
    document.querySelectorAll('.nav-item[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.dataset.view;
        switchView(view);
        // Close sidebar on mobile after nav click
        closeMobileSidebar();
      });
    });
  }

  function switchView(view) {
    if (view === activeView) return;
    activeView = view;

    // Update nav active state
    document.querySelectorAll('.nav-item[data-view]').forEach(btn => {
      btn.classList.toggle('nav-item--active', btn.dataset.view === view);
    });

    // Show / hide views
    document.querySelectorAll('.view').forEach(el => {
      el.classList.add('hidden');
    });
    const target = document.getElementById(viewId(view));
    if (target) {
      target.classList.remove('hidden');
      // Trigger re-animation
      target.style.animation = 'none';
      void target.offsetWidth; // reflow
      target.style.animation = '';
    }

    // Render dashboard when switching to it
    if (view === 'dashboard') {
      Dashboard.render();
    }
  }

  function viewId(view) {
    return { analyze: 'viewAnalyze', dashboard: 'viewDashboard' }[view] || 'viewAnalyze';
  }

  // ─── Mobile sidebar ───────────────────────────────────────────────────────
  function bindMobileSidebar() {
    const toggle  = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (toggle) toggle.addEventListener('click', () => {
      const open = sidebar.classList.contains('sidebar--open');
      open ? closeMobileSidebar() : openMobileSidebar();
    });

    if (overlay) overlay.addEventListener('click', closeMobileSidebar);
  }

  function openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.add('sidebar--open');
    overlay.classList.remove('hidden');
  }

  function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.remove('sidebar--open');
    overlay.classList.add('hidden');
  }

  // ─── Analysis buttons ─────────────────────────────────────────────────────
  function bindAnalyzeButtons() {
    document.getElementById('analyzeBtn').addEventListener('click', runAnalysis);
    document.getElementById('tryAnotherBtn').addEventListener('click', resetToUpload);
    document.getElementById('retryBtn').addEventListener('click', resetToUpload);
  }

  async function runAnalysis() {
    const blob = Upload.getBlob();
    if (!blob) {
      showError('No Photo', 'Please select a photo before analyzing.');
      return;
    }

    showLoading();

    try {
      const result = await API.identifyShingle(blob, true);
      Store.add(result); // persist to history
      showResults(result);
    } catch (err) {
      let title = 'Analysis Failed';
      let msg = err.message || 'An unexpected error occurred. Please try again.';

      if (err.code === 'API_KEY_NOT_CONFIGURED') {
        title = 'API Key Required';
        msg = 'Copy .env.example to .env and add your Anthropic API key, then restart the server.';
      } else if (err.status === 503) {
        title = 'Service Unavailable';
        msg = 'The vision service is temporarily unavailable. Please try again in a moment.';
      } else if (err.status === 400) {
        title = 'Invalid Photo';
      }

      showError(title, msg);
    }
  }

  // ─── Clear history ────────────────────────────────────────────────────────
  function bindClearHistory() {
    const btn = document.getElementById('clearHistoryBtn');
    if (btn) btn.addEventListener('click', () => {
      if (!window.confirm('Clear all analysis history? This cannot be undone.')) return;
      Store.clear();
      Dashboard.render();
    });
  }

  // ─── State transitions ────────────────────────────────────────────────────
  function showLoading() {
    hide('resultsPlaceholder');
    hide('resultsCard');
    hide('errorState');
    show('loadingState');
  }

  function showResults(data) {
    hide('loadingState');
    hide('resultsPlaceholder');
    hide('errorState');
    Results.render(data);
    show('resultsCard');
  }

  function showError(title, msg) {
    hide('loadingState');
    hide('resultsCard');
    hide('resultsPlaceholder');
    document.getElementById('errorTitle').textContent = title || 'Error';
    document.getElementById('errorMsg').textContent   = msg   || 'Please try again.';
    show('errorState');
  }

  function resetToUpload() {
    Upload.reset();
    hide('resultsCard');
    hide('loadingState');
    hide('errorState');
    show('resultsPlaceholder');
  }

  // ─── Utilities ────────────────────────────────────────────────────────────
  function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
  function hide(id) { document.getElementById(id)?.classList.add('hidden'); }

  // Expose for upload.js error delegation
  window.App = { showError };

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
