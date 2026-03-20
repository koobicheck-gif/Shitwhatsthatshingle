'use strict';

/**
 * Store — localStorage history manager.
 * Persists the last MAX_ENTRIES analysis results across sessions.
 */
const Store = (() => {
  const KEY = 'shingleid_history';
  const MAX_ENTRIES = 100;

  /** Return all entries (newest first). */
  function getAll() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || '[]');
    } catch {
      return [];
    }
  }

  /**
   * Save a new analysis result.
   * @param {Object} result  The API response from /api/identify
   */
  function add(result) {
    const entries = getAll();
    entries.unshift({
      id: Date.now(),
      ts: Date.now(),
      color_name:          result.color_name          || null,
      manufacturer:        result.manufacturer        || null,
      product_line:        result.product_line        || null,
      hex_preview:         result.hex_preview         || null,
      condition:           result.condition           || 'unknown',
      final_confidence:    result.final_confidence    || 0,
      color_reasoning:     result.color_reasoning     || null,
      condition_reasoning: result.condition_reasoning || null,
      requires_manual_review: !!result.requires_manual_review,
      alternatives:        result.alternatives        || [],
    });
    if (entries.length > MAX_ENTRIES) entries.length = MAX_ENTRIES;
    try {
      localStorage.setItem(KEY, JSON.stringify(entries));
    } catch {
      // Storage quota exceeded — trim older entries and retry once
      entries.length = Math.floor(MAX_ENTRIES / 2);
      try { localStorage.setItem(KEY, JSON.stringify(entries)); } catch { /* give up */ }
    }
  }

  /** Wipe all history. */
  function clear() {
    localStorage.removeItem(KEY);
  }

  return { getAll, add, clear };
})();
