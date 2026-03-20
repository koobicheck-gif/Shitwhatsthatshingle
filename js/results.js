'use strict';

const Results = (() => {
  const CONDITION_LABELS = {
    new: 'New',
    good: 'Good',
    worn: 'Worn',
    faded: 'Faded',
    damaged: 'Damaged',
    unknown: 'Unknown',
  };

  function render(data) {
    // Color name and metadata
    document.getElementById('colorName').textContent = data.color_name || '—';

    const meta = [data.manufacturer, data.product_line].filter(Boolean).join(' · ');
    document.getElementById('colorMeta').textContent = meta || 'Manufacturer unknown';

    // Color swatch
    const swatch = document.getElementById('colorSwatchLarge');
    if (data.hex_preview) {
      swatch.style.background = data.hex_preview;
    } else {
      swatch.style.background = 'linear-gradient(135deg, #555, #333)';
    }

    // Condition badge
    const badge = document.getElementById('conditionBadge');
    const cond = (data.condition || 'unknown').toLowerCase();
    badge.textContent = CONDITION_LABELS[cond] || cond;
    badge.className = `condition-badge condition-badge--${cond}`;

    // Confidence bar
    const pct = Math.round((data.final_confidence || 0) * 100);
    const fill = document.getElementById('confidenceBarFill');
    fill.style.width = `${pct}%`;
    fill.style.background = confidenceColor(data.final_confidence || 0);
    document.getElementById('confidencePct').textContent = `${pct}%`;

    // Reasoning
    document.getElementById('colorReasoning').textContent =
      data.color_reasoning || 'No reasoning provided.';
    document.getElementById('conditionReasoning').textContent =
      data.condition_reasoning || 'No reasoning provided.';

    // Alternatives
    const altSection = document.getElementById('alternativesSection');
    const altList = document.getElementById('alternativesList');
    altList.innerHTML = '';

    if (data.alternatives && data.alternatives.length > 0) {
      altSection.classList.remove('hidden');
      data.alternatives.forEach((alt) => {
        const chip = document.createElement('div');
        chip.className = 'alt-chip';
        const namePct = Math.round((alt.confidence || 0) * 100);
        const altMeta = [alt.manufacturer, alt.product_line].filter(Boolean).join(' · ');
        chip.innerHTML = `
          <span class="alt-chip__name">${escHtml(alt.color_name)} <small style="color:var(--text-muted)">(${namePct}%)</small></span>
          ${altMeta ? `<span class="alt-chip__meta">${escHtml(altMeta)}</span>` : ''}
        `;
        altList.appendChild(chip);
      });
    } else {
      altSection.classList.add('hidden');
    }

    // Review warning
    const warn = document.getElementById('reviewWarning');
    if (data.requires_manual_review) {
      warn.classList.remove('hidden');
    } else {
      warn.classList.add('hidden');
    }
  }

  function confidenceColor(conf) {
    if (conf >= 0.8) return '#2ecc71';
    if (conf >= 0.6) return '#f0a500';
    return '#d94f4f';
  }

  function escHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  return { render };
})();
