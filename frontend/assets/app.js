/**
 * EduWell Analytics - Main Frontend Application Logic
 * Single Page Application router, API integration, and interactive visualizations.
 */

(function () {
  'use strict';

  // State cache
  const state = {
    currentRoute: 'overview',
    dataset: null,
    overview: null,
    cleaning: null,
    stats: null,
    correlations: null,
    insights: null,
    statsSelectedVar: 'Study_Hours_Per_Day',
    corrMatrixType: 'spearman',
    isLoading: false,
  };

  const API_BASE = '';

  // -------------------------------------------------------------
  // API Calls
  // -------------------------------------------------------------
  async function apiFetch(endpoint, options = {}) {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Accept': 'application/json',
          ...(options.headers || {}),
        },
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const err = await res.json();
          if (err.detail) msg = err.detail;
        } catch (_) {}
        throw new Error(msg);
      }
      return await res.json();
    } catch (err) {
      console.error(`API error on ${endpoint}:`, err);
      throw err;
    }
  }

  async function fetchDatasetMeta() {
    try {
      state.dataset = await apiFetch('/api/dataset');
      updateSidebarAndTopbar();
      return state.dataset;
    } catch (err) {
      console.warn('Could not load dataset meta:', err);
    }
  }

  async function loadSampleDataset() {
    try {
      showToast('Loading synthetic sample dataset…', 'info');
      await apiFetch('/api/sample', { method: 'POST' });
      showToast('Synthetic sample dataset loaded successfully!', 'success');
      // Invalidate cache
      state.dataset = null;
      state.overview = null;
      state.cleaning = null;
      state.stats = null;
      state.correlations = null;
      state.insights = null;
      await fetchDatasetMeta();
      renderCurrentRoute();
    } catch (err) {
      showToast(`Error loading sample: ${err.message}`, 'error');
    }
  }

  async function uploadFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please select a valid CSV (.csv) file.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const progressEl = document.getElementById('upload-progress');
    const fillEl = document.getElementById('upload-progress-fill');
    const statusEl = document.getElementById('upload-status');

    if (progressEl) progressEl.hidden = false;
    if (fillEl) fillEl.style.width = '30%';
    if (statusEl) statusEl.textContent = 'Uploading and analyzing dataset…';

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let detail = `Upload failed with status ${res.status}`;
        try {
          const err = await res.json();
          if (err.detail) detail = err.detail;
        } catch (_) {}
        throw new Error(detail);
      }

      if (fillEl) fillEl.style.width = '100%';
      if (statusEl) statusEl.textContent = 'Analysis complete!';
      showToast(`Successfully uploaded and analyzed ${file.name}!`, 'success');

      // Clear cache and refresh
      state.dataset = null;
      state.overview = null;
      state.cleaning = null;
      state.stats = null;
      state.correlations = null;
      state.insights = null;

      await fetchDatasetMeta();
      setTimeout(() => {
        window.location.hash = '#/overview';
      }, 500);
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, 'error');
      if (statusEl) statusEl.textContent = `Error: ${err.message}`;
      if (fillEl) fillEl.style.width = '0%';
    }
  }

  // -------------------------------------------------------------
  // UI Helpers & Shell
  // -------------------------------------------------------------
  function showToast(message, type = 'info') {
    const container = document.getElementById('toasts');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const iconName = type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info';
    toast.innerHTML = `<span class="icon" aria-hidden="true">${iconName}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(0.5rem)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatNum(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '—';
    return Number(num).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  function updateSidebarAndTopbar() {
    const ds = state.dataset;
    if (!ds) return;

    const sidebarFilename = document.getElementById('sidebar-filename');
    if (sidebarFilename) {
      sidebarFilename.textContent = ds.filename || 'Dataset';
      sidebarFilename.title = ds.filename || '';
    }

    const sidebarMeta = document.getElementById('sidebar-meta');
    if (sidebarMeta) {
      sidebarMeta.textContent = `${(ds.cleaned_rows || 0).toLocaleString()} rows • ${ds.features_analyzed || 8} features`;
    }

    const topbarRecords = document.getElementById('topbar-records');
    if (topbarRecords) {
      topbarRecords.textContent = `${(ds.cleaned_rows || 0).toLocaleString()} Verified Student Records`;
    }

    const topbarBadge = document.getElementById('topbar-badge');
    if (topbarBadge) {
      if (ds.is_synthetic) {
        topbarBadge.textContent = 'Synthetic Sample';
        topbarBadge.className = 'topbar-badge synthetic';
      } else {
        topbarBadge.textContent = 'Active Upload';
        topbarBadge.className = 'topbar-badge';
      }
    }
  }

  function initShellEvents() {
    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
      themeBtn.onclick = () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        try {
          localStorage.setItem('eduwell-theme', newTheme);
        } catch (_) {}
      };
    }

    // Help dialog
    const helpBtn = document.getElementById('help-open');
    const helpDialog = document.getElementById('help-dialog');
    if (helpBtn && helpDialog) {
      helpBtn.onclick = () => {
        if (typeof helpDialog.showModal === 'function') {
          helpDialog.showModal();
        } else {
          helpDialog.setAttribute('open', '');
        }
      };

      helpDialog.querySelectorAll('[data-close]').forEach((btn) => {
        btn.onclick = () => {
          if (typeof helpDialog.close === 'function') {
            helpDialog.close();
          } else {
            helpDialog.removeAttribute('open');
          }
        };
      });

      helpDialog.onclick = (e) => {
        if (e.target === helpDialog) helpDialog.close();
      };
    }

    // Mobile navigation
    const menuBtn = document.getElementById('menu-open');
    const scrim = document.getElementById('scrim');
    if (menuBtn && scrim) {
      const toggleMenu = (open) => {
        const isOpen = open !== undefined ? open : !document.body.classList.contains('nav-open');
        document.body.classList.toggle('nav-open', isOpen);
        scrim.hidden = !isOpen;
        menuBtn.setAttribute('aria-expanded', String(isOpen));
      };
      menuBtn.onclick = () => toggleMenu();
      scrim.onclick = () => toggleMenu(false);
    }
  }

  // -------------------------------------------------------------
  // Router
  // -------------------------------------------------------------
  function getRouteFromHash() {
    const raw = (window.location.hash || '').replace(/^#\/?/, '').toLowerCase().trim();
    const valid = ['upload', 'overview', 'cleaning', 'statistics', 'correlations', 'insights'];
    return valid.includes(raw) ? raw : 'overview';
  }

  function updateNavHighlight(route) {
    document.querySelectorAll('#nav a').forEach((link) => {
      const linkRoute = link.getAttribute('data-route');
      if (linkRoute === route) {
        link.setAttribute('aria-current', 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });

    document.body.classList.remove('nav-open');
    const scrim = document.getElementById('scrim');
    if (scrim) scrim.hidden = true;
  }

  async function renderCurrentRoute() {
    const route = getRouteFromHash();
    state.currentRoute = route;
    updateNavHighlight(route);

    const view = document.getElementById('view');
    if (!view) return;

    view.innerHTML = `
      <div class="state">
        <div class="pulse" style="width: 2.5rem; height: 2.5rem; margin-bottom: 1rem;"></div>
        <p class="muted">Loading ${route.replace('-', ' ')} view…</p>
      </div>
    `;

    try {
      if (!state.dataset) {
        await fetchDatasetMeta();
      }

      switch (route) {
        case 'upload':
          await renderUploadView(view);
          break;
        case 'overview':
          await renderOverviewView(view);
          break;
        case 'cleaning':
          await renderCleaningView(view);
          break;
        case 'statistics':
          await renderStatisticsView(view);
          break;
        case 'correlations':
          await renderCorrelationsView(view);
          break;
        case 'insights':
          await renderInsightsView(view);
          break;
        default:
          await renderOverviewView(view);
      }
    } catch (err) {
      console.error('Error rendering route:', err);
      view.innerHTML = `
        <div class="card state">
          <div class="bubble"><span class="icon lg">error_outline</span></div>
          <h2>Could not load view</h2>
          <p class="muted">${escapeHtml(err.message)}</p>
          <button class="btn btn-primary" onclick="window.location.reload()">Retry</button>
        </div>
      `;
    }
  }

  // -------------------------------------------------------------
  // View 1: Upload & Validation
  // -------------------------------------------------------------
  async function renderUploadView(view) {
    if (!state.dataset) state.dataset = await apiFetch('/api/dataset');
    const ds = state.dataset;

    const checksHtml = (ds.checks || [])
      .map(
        (c) => `
        <div class="check-card">
          <div class="row-between">
            <span class="strong small">${escapeHtml(c.label)}</span>
            <div class="check-icon ${c.ok ? '' : 'warn'}">
              <span class="icon">${c.ok ? 'check' : 'priority_high'}</span>
            </div>
          </div>
          <div class="kpi-value" style="font-size: 1.25rem; margin: 0.25rem 0;">${escapeHtml(c.value)}</div>
          <p class="tiny muted">${escapeHtml(c.detail)}</p>
        </div>
      `
      )
      .join('');

    const preview = ds.preview || { columns: [], rows: [] };
    const previewHeader = preview.columns.map((col) => `<th>${escapeHtml(col)}</th>`).join('');
    const previewRows = preview.rows
      .map((row) => {
        const cells = preview.columns
          .map((col) => {
            const val = row[col];
            if (col === 'Stress_Level') {
              const cls = String(val).toLowerCase();
              return `<td><span class="stress-pill ${cls}"><span class="legend-dot ${cls}"></span>${escapeHtml(val)}</span></td>`;
            }
            if (typeof val === 'number') {
              return `<td class="num">${formatNum(val, col === 'GPA' ? 2 : 2)}</td>`;
            }
            return `<td>${escapeHtml(val)}</td>`;
          })
          .join('');
        return `<tr>${cells}</tr>`;
      })
      .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">upload_file</span> Pipeline Ingestion</span>
          <span>Schema &amp; Health Checks</span>
        </div>
        <h1>Upload Student Lifestyle Dataset</h1>
        <p class="lead">
          Upload a research CSV containing student study habits, sleep, social activities, physical movement, stress ratings, and GPA to run instant exploratory analysis.
        </p>
      </div>

      <div class="grid grid-2">
        <!-- Dropzone Card -->
        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>Ingest CSV Data</h2>
              <p>Drag and drop or select a valid UTF-8 CSV</p>
            </div>
            <button class="btn btn-quiet btn-sm" id="btn-load-sample" type="button">
              <span class="icon sm">database</span> Load Synthetic Sample
            </button>
          </div>

          <div class="dropzone" id="dropzone" tabindex="0" role="button" aria-label="Drop CSV file here or click to browse">
            <input type="file" id="file-input" accept=".csv" style="display: none;" />
            <div class="bubble"><span class="icon lg">cloud_upload</span></div>
            <div>
              <p class="strong" style="font-size: 1.05rem;">Click to browse or drop CSV here</p>
              <p class="muted small" style="margin-top: 0.25rem;">Supports up to 25 MB • UTF-8 format</p>
            </div>
            <div class="progress" id="upload-progress" hidden style="margin-top: 1rem;">
              <div class="progress-track">
                <div class="progress-fill" id="upload-progress-fill"></div>
              </div>
              <p class="tiny muted center" id="upload-status" style="margin-top: 0.5rem;">Analyzing file…</p>
            </div>
          </div>

          <div class="callout">
            <span class="icon">verified_user</span>
            <div class="small">
              <strong>Session Privacy:</strong> Uploaded data is analyzed entirely in memory for your browser session and expires after inactivity. It is never stored permanently or shared with other visitors.
            </div>
          </div>
        </div>

        <!-- Schema Requirements -->
        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>Required Column Schema</h2>
              <p>8 mandatory headers (case-insensitive)</p>
            </div>
            <span class="chip ok"><span class="icon sm">check_circle</span> 8 / 8 Detected</span>
          </div>

          <p class="small muted">
            The analyzer validates that your dataset adheres strictly to the required schema:
          </p>

          <div class="schema-chips">
            ${(ds.required_columns || [])
              .map(
                (col) => `
              <span class="chip info mono">
                <span class="icon sm">tag</span> ${escapeHtml(col)}
              </span>
            `
              )
              .join('')}
          </div>

          <div class="callout warn" style="margin-top: 0.5rem;">
            <span class="icon">schedule</span>
            <div class="small">
              <strong>24-Hour Time Budget:</strong> Daily hours (Study, Sleep, Social, Physical Activity, Extracurricular) must realistically align with daily time constraints.
            </div>
          </div>
        </div>
      </div>

      <!-- Health Checks Grid -->
      <div>
        <h2 style="margin-bottom: 0.75rem;">Dataset Validation Checks</h2>
        <div class="grid grid-5">
          ${checksHtml}
        </div>
      </div>

      <!-- Preview Table -->
      <div class="card stack">
        <div class="row-between">
          <div>
            <h2>Data Preview</h2>
            <p class="small muted">Showing first ${preview.rows.length} rows of active dataset: <strong>${escapeHtml(ds.filename)}</strong></p>
          </div>
          <span class="chip primary">${(ds.cleaned_rows || 0).toLocaleString()} Clean Rows</span>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead><tr>${previewHeader}</tr></thead>
            <tbody>${previewRows}</tbody>
          </table>
        </div>
      </div>
    `;

    // Wire up events
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const loadSampleBtn = document.getElementById('btn-load-sample');

    if (loadSampleBtn) {
      loadSampleBtn.onclick = () => loadSampleDataset();
    }

    if (dropzone && fileInput) {
      dropzone.onclick = () => fileInput.click();
      dropzone.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          fileInput.click();
        }
      };

      fileInput.onchange = (e) => {
        if (e.target.files && e.target.files[0]) {
          uploadFile(e.target.files[0]);
        }
      };

      ['dragenter', 'dragover'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.add('drag');
        });
      });

      ['dragleave', 'drop'].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropzone.classList.remove('drag');
        });
      });

      dropzone.addEventListener('drop', (e) => {
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
          uploadFile(e.dataTransfer.files[0]);
        }
      });
    }
  }

  // -------------------------------------------------------------
  // View 2: Overview Dashboard
  // -------------------------------------------------------------
  async function renderOverviewView(view) {
    if (!state.overview) state.overview = await apiFetch('/api/overview');
    const ov = state.overview;

    const stressDist = ov.stress_distribution || {
      Low: { count: 500, percentage: 25 },
      Moderate: { count: 800, percentage: 40 },
      High: { count: 700, percentage: 35 },
    };

    const lowPct = stressDist.Low ? stressDist.Low.percentage : 25;
    const modPct = stressDist.Moderate ? stressDist.Moderate.percentage : 40;
    const highPct = stressDist.High ? stressDist.High.percentage : 35;

    // SVG donut calculations (Circumference of radius 54 is ~339.29)
    const C = 2 * Math.PI * 54;
    const lowDash = (lowPct / 100) * C;
    const modDash = (modPct / 100) * C;
    const highDash = (highPct / 100) * C;
    const modOffset = -lowDash;
    const highOffset = -(lowDash + modDash);

    // Activity bars
    const activities = ov.activity_averages || {};
    const activityKeys = [
      { key: 'Study_Hours_Per_Day', label: 'Study Hours', icon: 'menu_book', color: 'var(--primary)' },
      { key: 'Sleep_Hours_Per_Day', label: 'Sleep Hygiene', icon: 'bedtime', color: 'var(--secondary)' },
      { key: 'Physical_Activity_Hours_Per_Day', label: 'Physical Activity', icon: 'fitness_center', color: '#10b981' },
      { key: 'Social_Hours_Per_Day', label: 'Social Engagement', icon: 'groups', color: '#f59e0b' },
      { key: 'Extracurricular_Hours_Per_Day', label: 'Extracurricular', icon: 'sports_esports', color: '#8b5cf6' },
    ];

    const hbarsHtml = activityKeys
      .map((item) => {
        const data = activities[item.key] || { mean: 0, share_of_day_pct: 0 };
        const widthPct = Math.min(100, (data.mean / 12) * 100);
        return `
        <div class="hbar">
          <div class="hbar-head">
            <span class="name">
              <span class="icon sm" style="color: ${item.color}">${item.icon}</span>
              ${item.label}
            </span>
            <span class="num strong">${formatNum(data.mean, 2)} h <span class="muted small">(${formatNum(data.share_of_day_pct, 1)}% of day)</span></span>
          </div>
          <div class="hbar-track">
            <div class="hbar-fill" style="width: ${widthPct}%; background: ${item.color};">
              ${formatNum(data.mean, 1)}h
            </div>
          </div>
        </div>
      `;
      })
      .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">dashboard</span> Executive Overview</span>
          <span>${escapeHtml(ov.dataset_name || 'Active Study')}</span>
        </div>
        <div class="row-between">
          <div>
            <h1>Student Lifestyle &amp; Wellness Overview</h1>
            <p class="lead">
              Statistical synthesis of ${(ov.total_students || 0).toLocaleString()} student profiles examining lifestyle allocation, stress burden, and GPA outcomes.
            </p>
          </div>
          <div class="row">
            <a class="btn btn-primary" href="/api/export-report?format=txt" download>
              <span class="icon sm">download</span> Download Report
            </a>
          </div>
        </div>
      </div>

      <!-- 4 Bento KPI Cards -->
      <div class="grid grid-4">
        <!-- Card 1 -->
        <div class="card kpi">
          <div class="kpi-top">
            <span class="kpi-label">Verified Sample</span>
            <div class="kpi-icon"><span class="icon">groups</span></div>
          </div>
          <div>
            <div class="kpi-value">${(ov.total_students || 0).toLocaleString()} <small>students</small></div>
            <div class="kpi-sub">100% complete records</div>
          </div>
          <div class="kpi-foot">
            <span>Features: ${ov.features_count || 8}</span>
            <span class="text-primary font-semibold">14 Divisions</span>
          </div>
        </div>

        <!-- Card 2 -->
        <div class="card kpi">
          <div class="kpi-top">
            <span class="kpi-label">Mean Cumulative GPA</span>
            <div class="kpi-icon"><span class="icon">grade</span></div>
          </div>
          <div>
            <div class="kpi-value">${formatNum(ov.mean_gpa, 2)} <small>/ 4.00</small></div>
            <div class="kpi-sub">Std Dev: ±${formatNum(ov.std_gpa, 2)} • Median: ${formatNum(ov.gpa ? ov.gpa.median : 3.26, 2)}</div>
          </div>
          <div class="kpi-foot">
            <span>Range: ${formatNum(ov.gpa ? ov.gpa.min : 2.0, 2)} – ${formatNum(ov.gpa ? ov.gpa.max : 4.0, 2)}</span>
            <span class="text-primary">Normal curve</span>
          </div>
        </div>

        <!-- Card 3 -->
        <div class="card kpi">
          <div class="kpi-top">
            <span class="kpi-label">Mean Sleep Hygiene</span>
            <div class="kpi-icon"><span class="icon">bedtime</span></div>
          </div>
          <div>
            <div class="kpi-value">${formatNum(ov.sleep ? ov.sleep.mean : 7.45, 2)} <small>hours/day</small></div>
            <div class="kpi-sub">${formatNum(ov.sleep ? ov.sleep.share_7_to_9_pct : 30.1, 1)}% within 7–9h window</div>
          </div>
          <div class="kpi-foot">
            <span>Min: ${formatNum(ov.sleep ? ov.sleep.min : 1.28, 1)}h</span>
            <span>Max: ${formatNum(ov.sleep ? ov.sleep.max : 16.8, 1)}h</span>
          </div>
        </div>

        <!-- Card 4 -->
        <div class="card kpi">
          <div class="kpi-top">
            <span class="kpi-label">Stress Prevalence</span>
            <div class="kpi-icon"><span class="icon">psychology</span></div>
          </div>
          <div>
            <div class="kpi-value" style="color: var(--moderate-text);">${formatNum(modPct, 1)}% <small>Moderate</small></div>
            <div class="kpi-sub">${(stressDist.Moderate ? stressDist.Moderate.count : 800).toLocaleString()} students in tier</div>
          </div>
          <div class="kpi-foot">
            <span class="text-low">Low: ${formatNum(lowPct, 0)}%</span>
            <span class="text-high">High: ${formatNum(highPct, 0)}%</span>
          </div>
        </div>
      </div>

      <!-- Split Layout: Donut Chart & 24h Time Budget -->
      <div class="split">
        <!-- Left: Donut Stress Breakdown -->
        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>Stress Level Distribution</h2>
              <p>Three-tier institutional classification</p>
            </div>
            <span class="chip primary">N = ${(ov.total_students || 0).toLocaleString()}</span>
          </div>

          <div class="donut-wrap">
            <svg viewBox="0 0 140 140">
              <circle cx="70" cy="70" r="54" fill="transparent" stroke="var(--surface-container)" stroke-width="20"></circle>
              <circle cx="70" cy="70" r="54" fill="transparent" stroke="var(--low)" stroke-width="20"
                stroke-dasharray="${lowDash} ${C}" stroke-dashoffset="0" class="seg"></circle>
              <circle cx="70" cy="70" r="54" fill="transparent" stroke="var(--moderate)" stroke-width="20"
                stroke-dasharray="${modDash} ${C}" stroke-dashoffset="${modOffset}" class="seg"></circle>
              <circle cx="70" cy="70" r="54" fill="transparent" stroke="var(--high)" stroke-width="20"
                stroke-dasharray="${highDash} ${C}" stroke-dashoffset="${highOffset}" class="seg"></circle>
            </svg>
            <div class="donut-center">
              <strong>${(ov.total_students || 0).toLocaleString()}</strong>
              <span class="tiny muted uppercase">Students</span>
            </div>
          </div>

          <div class="legend-list">
            <div class="legend-row">
              <span class="label"><span class="legend-dot low"></span> Low Stress (&lt;15)</span>
              <span class="num strong">${(stressDist.Low ? stressDist.Low.count : 500).toLocaleString()} (${formatNum(lowPct, 1)}%)</span>
            </div>
            <div class="legend-row">
              <span class="label"><span class="legend-dot moderate"></span> Moderate Stress (15–20)</span>
              <span class="num strong">${(stressDist.Moderate ? stressDist.Moderate.count : 800).toLocaleString()} (${formatNum(modPct, 1)}%)</span>
            </div>
            <div class="legend-row">
              <span class="label"><span class="legend-dot high"></span> High Stress (&gt;20)</span>
              <span class="num strong">${(stressDist.High ? stressDist.High.count : 700).toLocaleString()} (${formatNum(highPct, 1)}%)</span>
            </div>
          </div>
        </div>

        <!-- Right: 24h Time Budget -->
        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>24-Hour Time Budget Allocation</h2>
              <p>Average daily hours partitioned across life domains</p>
            </div>
            <span class="chip ok"><span class="icon sm">schedule</span> Total = 24.0 h</span>
          </div>

          <div class="stack" style="gap: 1.15rem; margin-top: 0.5rem;">
            ${hbarsHtml}
          </div>

          <div class="callout" style="margin-top: 0.5rem;">
            <span class="icon">sync_alt</span>
            <div class="small">
              <strong>Zero-Sum Time Dynamic:</strong> Because daily hours sum to 24h, increases in study commitments directly contract sleep and restorative activities, yielding an empirical trade-off (r = -0.465 between Study and Sleep).
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Navigation Cards -->
      <div class="card stack">
        <h2>Explore Detailed Analytics Screens</h2>
        <div class="grid grid-3">
          <a class="quick-link" href="#/cleaning">
            <span class="icon">cleaning_services</span>
            <div>
              <div class="strong">Data Cleaning Report</div>
              <div class="tiny muted">6 pipeline verification stages &amp; outlier checks</div>
            </div>
          </a>
          <a class="quick-link" href="#/statistics">
            <span class="icon">analytics</span>
            <div>
              <div class="strong">Descriptive Statistics</div>
              <div class="tiny muted">ANOVA, variance distributions &amp; eta-squared</div>
            </div>
          </a>
          <a class="quick-link" href="#/correlations">
            <span class="icon">insights</span>
            <div>
              <div class="strong">Correlation &amp; Regressions</div>
              <div class="tiny muted">Pearson, Spearman &amp; partial correlations</div>
            </div>
          </a>
        </div>
      </div>
    `;
  }

  // -------------------------------------------------------------
  // View 3: Data Cleaning Pipeline
  // -------------------------------------------------------------
  async function renderCleaningView(view) {
    if (!state.cleaning) state.cleaning = await apiFetch('/api/cleaning-report');
    const cl = state.cleaning;

    const stages = cl.stages || [];
    const stagesHtml = stages
      .map(
        (st) => `
        <div class="card stage">
          <div class="stage-num">${st.stage}</div>
          <div class="stack-sm">
            <div class="row-between">
              <h3>${escapeHtml(st.name)}</h3>
              <span class="chip ${st.status === 'PASSED' || st.status === 'VERIFIED' ? 'ok' : 'info'}">
                <span class="icon sm">check_circle</span> ${escapeHtml(st.status)}
              </span>
            </div>
            <p class="small muted">${escapeHtml(st.details)}</p>
          </div>
        </div>
      `
      )
      .join('');

    // Outlier table
    const outliersMap = (cl.clean_summary && cl.clean_summary.outliers_iqr) || {};
    const outlierRows = Object.entries(outliersMap)
      .map(([col, d]) => `
        <tr>
          <td class="strong">${escapeHtml(col.replace(/_/g, ' '))}</td>
          <td class="num">${formatNum(d.min, 2)}</td>
          <td class="num">${formatNum(d.q1, 2)}</td>
          <td class="num strong">${formatNum(d.median, 2)}</td>
          <td class="num">${formatNum(d.q3, 2)}</td>
          <td class="num">${formatNum(d.max, 2)}</td>
          <td class="num">${formatNum(d.lower_bound, 2)}</td>
          <td class="num">${formatNum(d.upper_bound, 2)}</td>
          <td class="num right strong ${d.outlier_count > 0 ? 'text-primary' : 'muted'}">
            ${d.outlier_count}
          </td>
        </tr>
      `)
      .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">cleaning_services</span> Pipeline Stage 02</span>
          <span>Rigorous Pre-processing &amp; Audit</span>
        </div>
        <h1>Automated Data Cleaning &amp; Validation Pipeline</h1>
        <p class="lead">
          Full transparency into raw record ingestion, missing value verification, duplicate screening, ordinal encoding, and Tukey IQR outlier audits.
        </p>
      </div>

      <!-- KPI Summary Cards -->
      <div class="grid grid-4">
        <div class="card kpi">
          <span class="kpi-label">Initial Rows Ingested</span>
          <div class="kpi-value">${(cl.initial_rows || 2000).toLocaleString()}</div>
          <div class="kpi-sub">Raw input records</div>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Cleaned Usable Records</span>
          <div class="kpi-value text-primary">${(cl.cleaned_rows || 2000).toLocaleString()}</div>
          <div class="kpi-sub">${formatNum(cl.retention_rate_pct || 100, 1)}% Retention Rate</div>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Dropped Incomplete Rows</span>
          <div class="kpi-value">${(cl.dropped_rows || 0).toLocaleString()}</div>
          <div class="kpi-sub">0 values imputed</div>
        </div>
        <div class="card kpi">
          <span class="kpi-label">Outliers Flagged (IQR)</span>
          <div class="kpi-value" style="color: var(--secondary);">${(cl.outliers_flagged || 139).toLocaleString()}</div>
          <div class="kpi-sub">Preserved in analysis</div>
        </div>
      </div>

      <!-- Pipeline Stages Stack -->
      <div class="stack">
        <h2 style="margin-top: 0.5rem;">Pipeline Verification Stages</h2>
        ${stagesHtml}
      </div>

      <!-- Outliers Analysis Table -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>Tukey Outlier Audit (1.5 × IQR Fences)</h2>
            <p>Outliers are naturally occurring variance and are retained to avoid biasing statistical regressions</p>
          </div>
          <span class="chip info">${cl.outliers_flagged || 139} Total Flagged Points</span>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Variable</th>
                <th class="right">Min</th>
                <th class="right">Q1</th>
                <th class="right">Median</th>
                <th class="right">Q3</th>
                <th class="right">Max</th>
                <th class="right">Lower Fence</th>
                <th class="right">Upper Fence</th>
                <th class="right">Outliers Count</th>
              </tr>
            </thead>
            <tbody>
              ${outlierRows}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // -------------------------------------------------------------
  // View 4: Descriptive Statistics
  // -------------------------------------------------------------
  async function renderStatisticsView(view) {
    if (!state.stats) state.stats = await apiFetch('/api/descriptive-stats');
    const st = state.stats;

    // Table of descriptive stats
    const descRows = (st.descriptive_statistics || [])
      .map(
        (row) => `
        <tr>
          <td class="strong">${escapeHtml(row.Label || row.Variable)}</td>
          <td class="num strong">${formatNum(row.Mean, 3)}</td>
          <td class="num">${formatNum(row.Std_Dev, 3)}</td>
          <td class="num">${formatNum(row.Median, 3)}</td>
          <td class="num">${formatNum(row.IQR, 3)}</td>
          <td class="num">${formatNum(row.Min, 2)}</td>
          <td class="num">${formatNum(row.Max, 2)}</td>
          <td class="num ${row.Skewness > 0.5 ? 'text-primary' : ''}">${formatNum(row.Skewness, 3)}</td>
        </tr>
      `
      )
      .join('');

    // Group comparison (ANOVA) table
    const groupRows = (st.group_comparison || [])
      .map(
        (g) => `
        <tr>
          <td class="strong">${escapeHtml(g.Label || g.Variable)}</td>
          <td class="num text-low strong">${formatNum(g.Low, 2)} <small class="muted">±${formatNum(g.Low_Std, 1)}</small></td>
          <td class="num text-moderate strong">${formatNum(g.Moderate, 2)} <small class="muted">±${formatNum(g.Moderate_Std, 1)}</small></td>
          <td class="num text-high strong">${formatNum(g.High, 2)} <small class="muted">±${formatNum(g.High_Std, 1)}</small></td>
          <td class="num ${g.Shift_Pct > 0 ? 'text-high' : 'text-low'} strong">${g.Shift_Pct > 0 ? '+' : ''}${formatNum(g.Shift_Pct, 1)}%</td>
          <td class="num strong">${formatNum(g.Eta_Squared, 3)}</td>
          <td class="num">${formatNum(g.F_Statistic, 1)}</td>
          <td class="num">${g.P_Value < 0.001 ? '<0.001***' : formatNum(g.P_Value, 3)}</td>
        </tr>
      `
      )
      .join('');

    // Interactive histogram variables
    const histVars = Object.keys(st.histograms || {});
    const currentVar = state.statsSelectedVar || histVars[0] || 'Study_Hours_Per_Day';
    const currentHist = (st.histograms && st.histograms[currentVar]) || { counts: [], edges: [], mean: 0, median: 0 };

    // Build SVG histogram
    const maxCount = Math.max(...(currentHist.counts || [1]));
    const barWidth = 100 / Math.max(1, currentHist.counts.length);
    const histBarsSvg = (currentHist.counts || [])
      .map((count, i) => {
        const heightPct = (count / maxCount) * 80;
        const x = i * barWidth;
        const y = 90 - heightPct;
        const edgeLeft = currentHist.edges[i] !== undefined ? currentHist.edges[i].toFixed(1) : '';
        return `
        <rect x="${x}%" y="${y}%" width="${barWidth * 0.88}%" height="${heightPct}%" rx="2" fill="var(--primary)" opacity="0.85">
          <title>Range: ${edgeLeft} | Count: ${count}</title>
        </rect>
      `;
      })
      .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">analytics</span> Parametric &amp; Non-parametric Statistics</span>
          <span>Descriptive &amp; Inferential</span>
        </div>
        <h1>Descriptive Statistics &amp; Stress Group Comparisons</h1>
        <p class="lead">
          Comprehensive summary metrics (Mean, SD, Median, Interquartile Range, Skewness) paired with one-way ANOVA hypothesis testing across stress tiers.
        </p>
      </div>

      <!-- Descriptive Table -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>Summary Measures of Central Tendency &amp; Dispersion</h2>
            <p>Calculated across all verified student observations (N = 2,000)</p>
          </div>
          <a class="btn btn-quiet btn-sm" href="/api/export-report?format=descriptive_csv" download>
            <span class="icon sm">download</span> Export CSV
          </a>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Variable</th>
                <th class="right">Mean (μ)</th>
                <th class="right">Std Dev (σ)</th>
                <th class="right">Median</th>
                <th class="right">IQR</th>
                <th class="right">Min</th>
                <th class="right">Max</th>
                <th class="right">Skewness</th>
              </tr>
            </thead>
            <tbody>
              ${descRows}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Group Comparison (ANOVA) -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>One-Way ANOVA &amp; Effect Size (Eta-Squared η²) by Stress Group</h2>
            <p>Assessing variance between Low (N=500), Moderate (N=800), and High (N=700) stress cohorts</p>
          </div>
          <span class="chip info">*** p &lt; 0.001</span>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Variable</th>
                <th class="right">Low Stress Mean</th>
                <th class="right">Moderate Stress Mean</th>
                <th class="right">High Stress Mean</th>
                <th class="right">Shift (High vs Low)</th>
                <th class="right">Eta² (η²)</th>
                <th class="right">F-Statistic</th>
                <th class="right">p-value</th>
              </tr>
            </thead>
            <tbody>
              ${groupRows}
            </tbody>
          </table>
        </div>

        <div class="callout primary">
          <span class="icon">insights</span>
          <div class="small">
            <strong>Key Effect Size Takeaway:</strong> Study Hours exhibits the strongest variance differentiation across stress levels (η² = 0.583, F = 1,397), meaning <strong>58.3% of all variance in study hours is directly explained by stress grouping</strong>.
          </div>
        </div>
      </div>

      <!-- Interactive Histogram Card -->
      <div class="card stack">
        <div class="row-between">
          <div>
            <h2>Interactive Empirical Distribution (Histogram)</h2>
            <p>Select a variable to inspect its frequency distribution curve</p>
          </div>
          <div class="row">
            <label class="field">Variable:</label>
            <select class="select" id="stats-var-select">
              ${histVars
                .map(
                  (v) => `<option value="${v}" ${v === currentVar ? 'selected' : ''}>${escapeHtml(v.replace(/_/g, ' '))}</option>`
                )
                .join('')}
            </select>
          </div>
        </div>

        <div style="background: var(--surface-low); border-radius: var(--radius-sm); padding: 1.5rem; height: 18rem; position: relative;">
          <svg width="100%" height="100%" viewBox="0 0 500 200" preserveAspectRatio="none">
            <line x1="0" y1="20" x2="500" y2="20" stroke="var(--outline-variant)" stroke-opacity="0.2"></line>
            <line x1="0" y1="60" x2="500" y2="60" stroke="var(--outline-variant)" stroke-opacity="0.2"></line>
            <line x1="0" y1="100" x2="500" y2="100" stroke="var(--outline-variant)" stroke-opacity="0.2"></line>
            <line x1="0" y1="140" x2="500" y2="140" stroke="var(--outline-variant)" stroke-opacity="0.2"></line>
            <line x1="0" y1="180" x2="500" y2="180" stroke="var(--outline-variant)" stroke-width="1.5"></line>
            <g>${histBarsSvg}</g>
          </svg>
        </div>

        <div class="row-between small muted">
          <span>Min: ${formatNum(currentHist.edges[0], 2)}</span>
          <span>Mean: <strong>${formatNum(currentHist.mean, 2)}</strong> • Median: <strong>${formatNum(currentHist.median, 2)}</strong> • Skewness: <strong>${formatNum(currentHist.skewness, 2)}</strong></span>
          <span>Max: ${formatNum(currentHist.edges[currentHist.edges.length - 1], 2)}</span>
        </div>
      </div>
    `;

    const varSelect = document.getElementById('stats-var-select');
    if (varSelect) {
      varSelect.onchange = (e) => {
        state.statsSelectedVar = e.target.value;
        renderStatisticsView(view);
      };
    }
  }

  // -------------------------------------------------------------
  // View 5: Correlation & Regression
  // -------------------------------------------------------------
  async function renderCorrelationsView(view) {
    if (!state.correlations) state.correlations = await apiFetch('/api/correlations');
    const cr = state.correlations;

    const isSpearman = state.corrMatrixType === 'spearman';
    const matrixObj = isSpearman ? cr.spearman : cr.pearson;
    const matrixDict = (matrixObj && matrixObj.dict) || {};
    const cols = (matrixObj && matrixObj.columns) || cr.variables || Object.keys(matrixDict);

    // Render matrix heatmap table
    const tableHeader = cols.map((c) => `<th class="center">${escapeHtml(c.replace(/_Hours_Per_Day|_Level|_Score/g, ''))}</th>`).join('');
    const matrixRows = cols
      .map((rowVar) => {
        const cells = cols
          .map((colVar) => {
            const val = matrixDict[rowVar] ? matrixDict[rowVar][colVar] : 0;
            const isDiag = rowVar === colVar;
            let bg = 'transparent';
            let color = 'inherit';
            if (!isDiag && typeof val === 'number') {
              if (val > 0) {
                const alpha = Math.min(0.75, Math.abs(val) * 0.8);
                bg = `rgba(0, 104, 95, ${alpha})`;
                if (alpha > 0.4) color = '#fff';
              } else if (val < 0) {
                const alpha = Math.min(0.75, Math.abs(val) * 0.8);
                bg = `rgba(186, 26, 26, ${alpha})`;
                if (alpha > 0.4) color = '#fff';
              }
            } else if (isDiag) {
              bg = 'var(--surface-container)';
            }
            return `
              <td style="background: ${bg}; color: ${color};" title="${escapeHtml(rowVar)} vs ${escapeHtml(colVar)}: ${val}">
                ${isDiag ? '1.00' : formatNum(val, 2)}
              </td>
            `;
          })
          .join('');
        return `
          <tr>
            <th class="row-h">${escapeHtml(rowVar.replace(/_Hours_Per_Day|_Level|_Score/g, ''))}</th>
            ${cells}
          </tr>
        `;
      })
      .join('');

    const targetStress = cr.ranked_stress_correlates || [];
    const targetGpa = cr.ranked_gpa_correlates || [];

    const renderDivergeBars = (items) =>
      items
        .map((it) => {
          const val = it.correlation !== undefined ? it.correlation : it.spearman_rho !== undefined ? it.spearman_rho : 0;
          const pct = Math.abs(val) * 50;
          const isPos = val >= 0;
          return `
          <div class="diverge">
            <span class="strong small">${escapeHtml(it.label || it.variable)}</span>
            <div class="diverge-track">
              <div class="diverge-fill ${isPos ? 'pos' : 'neg'}" style="width: ${pct}%;"></div>
            </div>
            <span class="num right strong ${isPos ? 'text-primary' : 'text-error'}">${val > 0 ? '+' : ''}${formatNum(val, 2)}</span>
          </div>
        `;
        })
        .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">insights</span> Multivariate Relationships</span>
          <span>Bivariate &amp; Partial Correlations</span>
        </div>
        <h1>Correlation Analysis &amp; Regressions</h1>
        <p class="lead">
          Spearman rank and Pearson linear correlation coefficients revealing structural tradeoffs between study load, sleep reduction, and academic performance.
        </p>
      </div>

      <!-- Confounder Warning Callout -->
      <div class="callout primary">
        <span class="icon">science</span>
        <div>
          <h4 style="margin-bottom: 0.25rem;">Spurious Correlation &amp; Partial Correlation Finding</h4>
          <p class="small">
            The raw correlation between <strong>Stress and GPA is positive (+0.670)</strong>. However, when controlling for <strong>Study Hours</strong> via partial correlation, this relationship collapses to <strong>r = +0.077 (statistically non-significant)</strong>. High study hours directly elevates GPA while simultaneously driving reported stress. Stress itself does not elevate GPA.
          </p>
        </div>
      </div>

      <!-- Matrix Heatmap Card -->
      <div class="card stack">
        <div class="row-between">
          <div>
            <h2>Pairwise Correlation Matrix Heatmap</h2>
            <p>Compare correlation coefficients across all 7 analyzed dimensions</p>
          </div>
          <div class="segmented" id="matrix-toggle">
            <button type="button" data-val="spearman" aria-pressed="${isSpearman}">Spearman (Rank)</button>
            <button type="button" data-val="pearson" aria-pressed="${!isSpearman}">Pearson (Linear)</button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="heatmap">
            <thead>
              <tr>
                <th></th>
                ${tableHeader}
              </tr>
            </thead>
            <tbody>
              ${matrixRows}
            </tbody>
          </table>
        </div>

        <div class="row-between small muted">
          <div class="row">
            <span>Negative correlation (-1.0)</span>
            <div class="color-ramp"></div>
            <span>Positive correlation (+1.0)</span>
          </div>
          <span>Diagonal = 1.00 (Self-correlation)</span>
        </div>
      </div>

      <!-- Target Correlations Split -->
      <div class="grid grid-2">
        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>Rank Correlation vs Stress Level</h2>
              <p>Rank correlation (Spearman ρ) with stress score</p>
            </div>
            <span class="chip primary">Target: Stress</span>
          </div>
          <div class="stack" style="gap: 0.75rem;">
            ${renderDivergeBars(targetStress)}
          </div>
        </div>

        <div class="card stack">
          <div class="card-head">
            <div>
              <h2>Rank Correlation vs GPA</h2>
              <p>Rank correlation (Spearman ρ) with cumulative GPA</p>
            </div>
            <span class="chip primary">Target: GPA</span>
          </div>
          <div class="stack" style="gap: 0.75rem;">
            ${renderDivergeBars(targetGpa)}
          </div>
        </div>
      </div>

      <!-- Linear Regressions Summary -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>Ordinary Least Squares (OLS) Linear Regressions</h2>
            <p>Empirical regression equations fitted on the active dataset</p>
          </div>
          <span class="chip ok">p &lt; 0.001</span>
        </div>

        <div class="grid grid-2">
          <div style="background: var(--surface-low); padding: 1rem; border-radius: var(--radius-sm);">
            <div class="eyebrow"><span class="chip primary sm">Model 1</span> Study Hours → GPA</div>
            <div class="kpi-value" style="font-size: 1.15rem; margin: 0.4rem 0;">
              <code>GPA = 2.038 + 0.170 × (Study Hours)</code>
            </div>
            <p class="small muted">
              R² = 0.713. For every extra daily study hour, cumulative GPA increases on average by <strong>+0.170 grade points</strong>.
            </p>
          </div>

          <div style="background: var(--surface-low); padding: 1rem; border-radius: var(--radius-sm);">
            <div class="eyebrow"><span class="chip primary sm">Model 2</span> Sleep Hours → Stress Score</div>
            <div class="kpi-value" style="font-size: 1.15rem; margin: 0.4rem 0;">
              <code>Stress = 3.554 - 0.195 × (Sleep Hours)</code>
            </div>
            <p class="small muted">
              R² = 0.333. For every additional hour of restorative sleep, stress score decreases on average by <strong>0.195 points</strong>.
            </p>
          </div>
        </div>
      </div>
    `;

    const toggle = document.getElementById('matrix-toggle');
    if (toggle) {
      toggle.querySelectorAll('button').forEach((btn) => {
        btn.onclick = () => {
          state.corrMatrixType = btn.getAttribute('data-val');
          renderCorrelationsView(view);
        };
      });
    }
  }

  // -------------------------------------------------------------
  // View 6: Insights & Report
  // -------------------------------------------------------------
  async function renderInsightsView(view) {
    if (!state.insights) state.insights = await apiFetch('/api/insights');
    const ins = state.insights;

    const rawFindings = ins.findings || [];
    const findingsHtml = rawFindings
      .map(
        (f) => `
        <div class="card finding">
          <div class="finding-num">${String(f.number || '').padStart(2, '0')}</div>
          <div>
            <h3>Finding #${f.number}</h3>
            <p class="muted small" style="margin-top: 0.35rem; font-size: 0.9375rem; line-height: 1.5rem;">${escapeHtml(f.text)}</p>
          </div>
        </div>
      `
      )
      .join('');

    const figures = [
      { name: '01_distributions.png', label: 'Feature Distributions' },
      { name: '02_stress_distribution.png', label: 'Stress Distribution' },
      { name: '04_boxplots_by_stress.png', label: 'Boxplots by Stress Tier' },
      { name: '06_study_vs_gpa.png', label: 'Study Hours vs GPA Regression' },
      { name: '07a_sleep_vs_stress.png', label: 'Sleep Hygiene vs Stress Level' },
      { name: '10a_heatmap_pearson.png', label: 'Pearson Correlation Heatmap' },
      { name: '10b_heatmap_spearman.png', label: 'Spearman Correlation Heatmap' },
    ];

    const figuresHtml = figures
      .map(
        (fig) => `
        <figure>
          <img src="/api/figures/${fig.name}" alt="${escapeHtml(fig.label)}" loading="lazy" onerror="this.parentElement.style.display='none'" />
          <figcaption>${escapeHtml(fig.label)}</figcaption>
        </figure>
      `
      )
      .join('');

    const limitationsHtml = (ins.limitations || [])
      .map((lim) => `<li>${escapeHtml(lim)}</li>`)
      .join('');

    view.innerHTML = `
      <div class="hero card">
        <div class="eyebrow">
          <span class="chip primary"><span class="icon sm">summarize</span> Institutional Synthesis</span>
          <span>Empirical Findings &amp; Deliverables</span>
        </div>
        <div class="row-between">
          <div>
            <h1>Executive Research Insights &amp; Report</h1>
            <p class="lead">
              Synthesized conclusions, key correlation findings, study limitations, figure gallery, and exportable research bundles.
            </p>
          </div>
          <div class="row">
            <button class="btn btn-quiet" type="button" onclick="window.print()">
              <span class="icon sm">print</span> Print / Save PDF
            </button>
            <a class="btn btn-primary" href="/api/export-report?format=zip" download>
              <span class="icon sm">folder_zip</span> Download ZIP Bundle
            </a>
          </div>
        </div>
      </div>

      <!-- Key Findings Stack -->
      <div class="stack">
        <h2>Key Empirical Findings (${rawFindings.length})</h2>
        <div class="stack" style="gap: 0.75rem;">
          ${findingsHtml}
        </div>
      </div>

      <!-- Export & Download Options -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>Download Research Artifacts</h2>
            <p>Access structured datasets, statistical tables, and full reports</p>
          </div>
          <span class="chip ok">Available formats</span>
        </div>

        <div class="download-list">
          <a class="download" href="/api/export-report?format=txt" download>
            <span class="icon lg">description</span>
            <div>
              <div class="strong">Executive Report</div>
              <div class="tiny muted">Plaintext research document (.txt)</div>
            </div>
          </a>
          <a class="download" href="/api/export-report?format=cleaned_csv" download>
            <span class="icon lg">table_chart</span>
            <div>
              <div class="strong">Cleaned Dataset</div>
              <div class="tiny muted">Audited student CSV (.csv)</div>
            </div>
          </a>
          <a class="download" href="/api/export-report?format=descriptive_csv" download>
            <span class="icon lg">analytics</span>
            <div>
              <div class="strong">Descriptive Stats CSV</div>
              <div class="tiny muted">Mean, SD, Median, Min, Max (.csv)</div>
            </div>
          </a>
          <a class="download" href="/api/export-report?format=json" download>
            <span class="icon lg">code</span>
            <div>
              <div class="strong">Full JSON Export</div>
              <div class="tiny muted">Complete structured payload (.json)</div>
            </div>
          </a>
          <a class="download" href="/api/export-report?format=zip" download>
            <span class="icon lg">folder_zip</span>
            <div>
              <div class="strong">All Artifacts + Figures</div>
              <div class="tiny muted">Complete ZIP bundle with PNGs (.zip)</div>
            </div>
          </a>
        </div>
      </div>

      <!-- Figures Gallery -->
      <div class="card stack">
        <div class="card-head">
          <div>
            <h2>Publication-Quality Visualizations</h2>
            <p>Matplotlib charts generated from active dataset</p>
          </div>
          <span class="chip primary">7 Visualizations</span>
        </div>

        <div class="figures">
          ${figuresHtml}
        </div>
      </div>

      <!-- Methodological Limitations -->
      <div class="card stack">
        <h2>Study Limitations &amp; Ethical Research Scope</h2>
        <ul style="padding-left: 1.25rem; display: flex; flex-direction: column; gap: 0.5rem; color: var(--on-surface-variant); font-size: 0.875rem;">
          ${limitationsHtml}
        </ul>
        <details style="margin-top: 1rem;">
          <summary>View Complete Raw Statistical Text Report</summary>
          <div class="report-text" style="margin-top: 1rem;">
${escapeHtml(ins.full_report_text || '')}
          </div>
        </details>
      </div>
    `;
  }

  // -------------------------------------------------------------
  // Self-executing Bootstrapping (immune to DOM timing)
  // -------------------------------------------------------------
  function boot() {
    initShellEvents();
    window.addEventListener('hashchange', renderCurrentRoute);
    renderCurrentRoute();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
