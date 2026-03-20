'use strict';

const App = (() => {
  function init() {
    Upload.init();
    bindButtons();
  }

  function bindButtons() {
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
    document.getElementById('errorMsg').textContent = msg || 'Please try again.';
    show('errorState');
  }

  function resetToUpload() {
    Upload.reset();
    hide('resultsCard');
    hide('loadingState');
    hide('errorState');
    show('resultsPlaceholder');
  }

  function show(id) { document.getElementById(id).classList.remove('hidden'); }
  function hide(id) { document.getElementById(id).classList.add('hidden'); }

  // Expose showError for upload module
  window.App = { showError };

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
