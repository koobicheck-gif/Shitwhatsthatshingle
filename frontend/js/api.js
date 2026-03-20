'use strict';

const API = (() => {
  const BASE_URL = (typeof CONFIG !== 'undefined' ? CONFIG.API_BASE_URL : '/api');

  async function identifyShingle(imageBlob, includeAlternatives = true) {
    const form = new FormData();
    form.append('image', imageBlob, 'shingle.jpg');
    form.append('include_alternatives', includeAlternatives ? 'true' : 'false');

    const response = await fetch(`${BASE_URL}/identify`, {
      method: 'POST',
      body: form,
    });

    const data = await response.json();

    if (!response.ok) {
      const message = data?.detail?.error || data?.detail || 'An unexpected error occurred.';
      const code = data?.detail?.code || 'UNKNOWN_ERROR';
      const err = new Error(message);
      err.code = code;
      err.status = response.status;
      throw err;
    }

    return data;
  }

  async function getHealth() {
    const response = await fetch(`${BASE_URL}/health`);
    return response.json();
  }

  return { identifyShingle, getHealth };
})();
