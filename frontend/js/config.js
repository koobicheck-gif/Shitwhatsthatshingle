'use strict';

/**
 * ShingleID frontend configuration.
 *
 * When running locally via `uvicorn backend.main:app`, the API is served
 * from the same origin so API_BASE_URL defaults to '/api'.
 *
 * When deployed to GitHub Pages (no backend), set this to the URL of your
 * deployed backend, e.g.:
 *   window.SHINGLEID_API_URL = 'https://your-backend.fly.dev';
 *
 * You can also set it via a <script> tag before this file loads:
 *   <script>window.SHINGLEID_API_URL = 'https://...';</script>
 */
const CONFIG = {
  API_BASE_URL: (window.SHINGLEID_API_URL || '').replace(/\/$/, '') + '/api',
};
