'use strict';

/**
 * ShingleID frontend configuration.
 *
 * ANTHROPIC_API_KEY: Set at runtime from localStorage (user is prompted on first visit).
 * COLORS_BASE_URL: Base URL for fetching data/colors.json.
 */
const CONFIG = {
  get ANTHROPIC_API_KEY() {
    return localStorage.getItem('shingleid_api_key') || '';
  },
  set ANTHROPIC_API_KEY(key) {
    if (key) localStorage.setItem('shingleid_api_key', key);
    else localStorage.removeItem('shingleid_api_key');
  },
  COLORS_BASE_URL: '',
};
