'use strict';

/**
 * Dashboard — renders stats, history list, trend chart, and breakdowns.
 * Reads from Store. Called by App whenever the dashboard view becomes active
 * or a new result is saved.
 */
const Dashboard = (() => {

  // ─── Condition display config ─────────────────────────────────────────────
  const COND_LABELS = {
    new: 'New', good: 'Good', worn: 'Worn',
    faded: 'Faded', damaged: 'Damaged', unknown: 'Unknown',
  };

  // Accent colour per condition (for breakdown bars)
  const COND_COLORS = {
    new: '#22c55e', good: '#3d8ef0', worn: '#f59e0b',
    faded: '#d4900a', damaged: '#ef4444', unknown: '#4a6785',
  };

  // Confidence → colour
  function confColor(v) {
    if (v >= 0.8) return '#22c55e';
    if (v >= 0.6) return '#f59e0b';
    return '#ef4444';
  }

  // ─── Render entry-point ───────────────────────────────────────────────────
  function render() {
    const entries = Store.getAll();
    renderStats(entries);
    renderHistoryList(entries);
    renderTrendChart(entries);
    renderConditionBreakdown(entries);
    renderColorBreakdown(entries);
  }

  // ─── Stats cards ──────────────────────────────────────────────────────────
  function renderStats(entries) {
    // Total
    setText('statTotal', entries.length);

    // Average confidence
    if (entries.length > 0) {
      const avg = entries.reduce((s, e) => s + (e.final_confidence || 0), 0) / entries.length;
      setText('statAvgConf', Math.round(avg * 100) + '%');
    } else {
      setText('statAvgConf', '—');
    }

    // Today
    const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
    const todayCount = entries.filter(e => e.ts >= todayStart.getTime()).length;
    setText('statToday', todayCount);

    // Top manufacturer
    const mfrCounts = {};
    entries.forEach(e => {
      const m = e.manufacturer;
      if (m) mfrCounts[m] = (mfrCounts[m] || 0) + 1;
    });
    const topMfr = Object.keys(mfrCounts).sort((a, b) => mfrCounts[b] - mfrCounts[a])[0];
    setText('statTopMfr', topMfr || '—');

    // History count badge
    setText('historyCount', entries.length);
  }

  // ─── History list ─────────────────────────────────────────────────────────
  function renderHistoryList(entries) {
    const list = document.getElementById('historyList');
    if (!list) return;

    if (entries.length === 0) {
      list.innerHTML = `
        <div class="history-empty">
          <svg width="38" height="38" viewBox="0 0 38 38" fill="none" aria-hidden="true">
            <circle cx="19" cy="19" r="16" stroke="var(--border)" stroke-width="1.5"/>
            <path d="M11 27L19 12L27 27H11Z" stroke="var(--border)" stroke-width="1.5" stroke-linejoin="round"/>
          </svg>
          <p>No analyses yet</p>
          <span>Upload a photo to get started</span>
        </div>`;
      return;
    }

    const frag = document.createDocumentFragment();
    entries.slice(0, 50).forEach((entry, i) => {
      const item = buildHistoryItem(entry, i);
      frag.appendChild(item);
    });

    list.innerHTML = '';
    list.appendChild(frag);
  }

  function buildHistoryItem(entry, index) {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.style.animationDelay = `${Math.min(index * 28, 250)}ms`;

    const pct = Math.round((entry.final_confidence || 0) * 100);
    const color = confColor(entry.final_confidence || 0);
    const swatchBg = entry.hex_preview || 'linear-gradient(135deg,#555,#333)';
    const cond = (entry.condition || 'unknown').toLowerCase();
    const condLabel = COND_LABELS[cond] || cond;

    const meta = [entry.manufacturer, entry.product_line].filter(Boolean).join(' · ');

    el.innerHTML = `
      <div class="history-item__swatch" style="background:${escHtml(swatchBg)}"></div>
      <div class="history-item__info">
        <div class="history-item__name">${escHtml(entry.color_name || 'Unknown Color')}</div>
        <div class="history-item__meta">${escHtml(meta || 'Unknown manufacturer')}</div>
      </div>
      <span class="condition-badge condition-badge--${cond}" style="align-self:center">${escHtml(condLabel)}</span>
      <div class="history-item__right">
        <div class="history-item__bar">
          <div class="history-item__bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="history-item__conf" style="color:${color}">${pct}%</span>
        <span class="history-item__time">${timeAgo(entry.ts)}</span>
      </div>`;

    return el;
  }

  // ─── Confidence trend chart (canvas) ─────────────────────────────────────
  function renderTrendChart(entries) {
    const canvas = document.getElementById('confidenceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    // Size canvas to its CSS display width
    const displayW = canvas.clientWidth || 300;
    const displayH = parseInt(canvas.getAttribute('height')) || 72;

    canvas.width  = displayW * dpr;
    canvas.height = displayH * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, displayW, displayH);

    const data = entries.slice(0, 20).reverse(); // oldest → newest

    if (data.length < 2) {
      drawChartEmpty(ctx, displayW, displayH, data.length === 1 ? 'Only 1 scan — need 2+ for a trend' : 'No data yet');
      return;
    }

    const pts = data.map((e, i) => ({
      x: (i / (data.length - 1)) * displayW,
      y: displayH - (e.final_confidence || 0) * (displayH - 14) - 4,
    }));

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, displayH);
    grad.addColorStop(0, 'rgba(61,142,240,0.22)');
    grad.addColorStop(1, 'rgba(61,142,240,0)');

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      const cp1x = (pts[i - 1].x + pts[i].x) / 2;
      ctx.bezierCurveTo(cp1x, pts[i - 1].y, cp1x, pts[i].y, pts[i].x, pts[i].y);
    }
    ctx.lineTo(displayW, displayH);
    ctx.lineTo(0, displayH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Stroke line
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      const cp1x = (pts[i - 1].x + pts[i].x) / 2;
      ctx.bezierCurveTo(cp1x, pts[i - 1].y, cp1x, pts[i].y, pts[i].x, pts[i].y);
    }
    ctx.strokeStyle = '#3d8ef0';
    ctx.lineWidth = 1.8;
    ctx.stroke();

    // Dots
    pts.forEach((pt, i) => {
      const v = data[i].final_confidence || 0;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 2.8, 0, Math.PI * 2);
      ctx.fillStyle = confColor(v);
      ctx.fill();
    });

    // Update label
    const lbl = document.getElementById('trendLabel');
    if (lbl) lbl.textContent = `last ${data.length} scan${data.length !== 1 ? 's' : ''}`;
  }

  function drawChartEmpty(ctx, w, h, msg) {
    ctx.font = `12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`;
    ctx.fillStyle = 'rgba(60,95,128,0.8)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(msg, w / 2, h / 2);
  }

  // ─── Condition breakdown ───────────────────────────────────────────────────
  function renderConditionBreakdown(entries) {
    const el = document.getElementById('conditionBreakdown');
    if (!el) return;
    if (entries.length === 0) {
      el.innerHTML = '<div class="breakdown-empty">No data yet</div>';
      return;
    }

    const counts = {};
    entries.forEach(e => {
      const c = (e.condition || 'unknown').toLowerCase();
      counts[c] = (counts[c] || 0) + 1;
    });

    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const max = sorted[0][1];

    el.innerHTML = sorted.map(([cond, count]) => `
      <div class="breakdown-row">
        <span class="breakdown-label">${escHtml(COND_LABELS[cond] || cond)}</span>
        <div class="breakdown-track">
          <div class="breakdown-fill" style="width:${(count / max * 100).toFixed(1)}%;background:${COND_COLORS[cond] || '#4a6785'}"></div>
        </div>
        <span class="breakdown-count">${count}</span>
      </div>`).join('');
  }

  // ─── Color breakdown (top 6) ───────────────────────────────────────────────
  function renderColorBreakdown(entries) {
    const el = document.getElementById('colorBreakdown');
    if (!el) return;
    if (entries.length === 0) {
      el.innerHTML = '<div class="breakdown-empty">No data yet</div>';
      return;
    }

    const counts = {};
    entries.forEach(e => {
      const name = e.color_name;
      if (name) counts[name] = (counts[name] || 0) + 1;
    });

    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (sorted.length === 0) {
      el.innerHTML = '<div class="breakdown-empty">No color data</div>';
      return;
    }

    const max = sorted[0][1];

    el.innerHTML = sorted.map(([name, count]) => `
      <div class="breakdown-row">
        <span class="breakdown-label">${escHtml(name)}</span>
        <div class="breakdown-track">
          <div class="breakdown-fill" style="width:${(count / max * 100).toFixed(1)}%;background:var(--accent)"></div>
        </div>
        <span class="breakdown-count">${count}</span>
      </div>`).join('');
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────
  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function timeAgo(ts) {
    const diff = Date.now() - ts;
    const s = Math.floor(diff / 1000);
    if (s < 60)  return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60)  return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24)  return `${h}h ago`;
    const d = Math.floor(h / 24);
    return `${d}d ago`;
  }

  function escHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(String(str)));
    return d.innerHTML;
  }

  // Re-render chart on resize (debounced)
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const entries = Store.getAll();
      renderTrendChart(entries);
    }, 120);
  });

  return { render };
})();
