/**
 * EduWell Analytics - Shared API Client & UI Navigation Layer
 * Connects frontend screens to FastAPI backend (http://127.0.0.1:8000).
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const exports = factory();
    root.EduWellApiClient = exports.EduWellApiClient;
    root.apiClient = exports.apiClient;
    root.EduWellUI = exports.EduWellUI;
  }
})(typeof self !== 'undefined' ? self : this, function () {

  const DEFAULT_API_BASE = 'http://127.0.0.1:8000';
  const STORAGE_KEY = 'eduwell_active_dataset';

  const ROUTE_MAP = {
    'upload-validation': '../1._upload_validation/code.html',
    'overview': '../2._overview_dashboard/code.html',
    'data-cleaning': '../3._data_cleaning/code.html',
    'descriptive-statistics': '../4._descriptive_statistics/code.html',
    'correlation-regressions': '../5._correlation_regressions/code.html',
    'insights-report': '../6._insights_report/code.html'
  };

  class EduWellApiClient {
    constructor(baseUrl) {
      this.baseUrl = baseUrl || (typeof window !== 'undefined' && window.EDUWELL_API_BASE) || DEFAULT_API_BASE;
    }

    setBaseUrl(url) {
      this.baseUrl = url.replace(/\/+$/, '');
    }

    getActiveDatasetMeta() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    }

    setActiveDatasetMeta(meta) {
      if (!meta) return;
      try {
        const json = JSON.stringify(meta);
        localStorage.setItem(STORAGE_KEY, json);
        sessionStorage.setItem(STORAGE_KEY, json);
      } catch (e) {
        console.warn('Could not persist dataset meta to storage', e);
      }
    }

    clearActiveDatasetMeta() {
      try {
        localStorage.removeItem(STORAGE_KEY);
        sessionStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
    }

    async getRoot() {
      const res = await fetch(`${this.baseUrl}/`);
      if (!res.ok) throw new Error(`API offline or returned ${res.status}`);
      return await res.json();
    }

    uploadCSV(file, onProgress) {
      return new Promise((resolve, reject) => {
        if (!file) {
          return reject(new Error('No file provided for upload.'));
        }
        if (!file.name.toLowerCase().endsWith('.csv')) {
          return reject(new Error('Invalid file format. Please upload a .csv file.'));
        }

        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        if (xhr.upload && typeof onProgress === 'function') {
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
              const pct = Math.round((e.loaded / e.total) * 100);
              onProgress(pct, e.loaded, e.total);
            }
          });
        }

        xhr.onreadystatechange = () => {
          if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const data = JSON.parse(xhr.responseText);
                this.setActiveDatasetMeta(data);
                resolve(data);
              } catch (e) {
                reject(new Error('Server returned an invalid JSON response.'));
              }
            } else {
              let detail = `Server returned status ${xhr.status}`;
              try {
                const errJson = JSON.parse(xhr.responseText);
                if (errJson.detail) detail = errJson.detail;
              } catch (_) {
                if (xhr.statusText) detail += `: ${xhr.statusText}`;
              }
              reject(new Error(detail));
            }
          }
        };

        xhr.onerror = () => {
          reject(new Error('Network error. Unable to connect to API at ' + this.baseUrl));
        };

        xhr.open('POST', `${this.baseUrl}/api/upload`);
        xhr.send(formData);
      });
    }

    async loadSample() {
      const res = await fetch(`${this.baseUrl}/api/sample`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to load sample dataset (${res.status})`);
      }
      const data = await res.json();
      this.setActiveDatasetMeta(data);
      return data;
    }

    async getOverview() {
      const res = await fetch(`${this.baseUrl}/api/overview`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to fetch overview (${res.status})`);
      }
      const data = await res.json();
      this.setActiveDatasetMeta({
        filename: data.dataset_name,
        is_synthetic: data.is_synthetic,
        raw_rows: data.total_students,
        cleaned_rows: data.total_students,
        features_analyzed: data.features_count
      });
      return data;
    }

    async getCleaningReport() {
      const res = await fetch(`${this.baseUrl}/api/cleaning-report`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to fetch cleaning report (${res.status})`);
      }
      const data = await res.json();
      this.setActiveDatasetMeta({
        filename: data.filename,
        is_synthetic: data.is_synthetic,
        raw_rows: data.initial_rows,
        cleaned_rows: data.cleaned_rows,
        dropped_rows: data.dropped_rows
      });
      return data;
    }

    async getDescriptiveStats() {
      const res = await fetch(`${this.baseUrl}/api/descriptive-stats`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to fetch descriptive statistics (${res.status})`);
      }
      return await res.json();
    }

    async getCorrelations() {
      const res = await fetch(`${this.baseUrl}/api/correlations`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to fetch correlation matrix (${res.status})`);
      }
      return await res.json();
    }

    async getInsights() {
      const res = await fetch(`${this.baseUrl}/api/insights`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Failed to fetch insights (${res.status})`);
      }
      return await res.json();
    }

    async getExportReport(format = 'txt') {
      const url = `${this.baseUrl}/api/export-report?format=${encodeURIComponent(format)}`;
      if (format === 'json') {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Export JSON failed (${res.status})`);
        return await res.json();
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      return await res.text();
    }

    getExportUrl(format = 'txt') {
      return `${this.baseUrl}/api/export-report?format=${encodeURIComponent(format)}`;
    }

    getFigureUrl(figureName) {
      return `${this.baseUrl}/api/figures/${encodeURIComponent(figureName)}`;
    }
  }

  const apiClient = new EduWellApiClient();

  const EduWellUI = {
    ROUTE_MAP,

    initNavigation(currentPath) {
      if (typeof document === 'undefined') return;

      // 1. Wire all data-path anchors and buttons
      document.querySelectorAll('[data-path]').forEach((el) => {
        const targetPath = el.getAttribute('data-path');
        if (ROUTE_MAP[targetPath]) {
          el.style.cursor = 'pointer';
          el.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = ROUTE_MAP[targetPath];
          });
        }
      });

      // 2. Wire "Change dataset" buttons
      document.querySelectorAll('button, a').forEach((el) => {
        const text = (el.textContent || '').trim().toLowerCase();
        if (text.includes('change dataset') || text.includes('re-upload csv')) {
          el.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = ROUTE_MAP['upload-validation'];
          });
        }
        if (text.includes('download report') || text.includes('export validation log')) {
          el.addEventListener('click', (e) => {
            e.preventDefault();
            window.open(apiClient.getExportUrl('txt'), '_blank');
          });
        }
      });

      // 3. Highlight current nav item in sidebar
      const nav = document.querySelector('aside nav');
      if (nav) {
        nav.querySelectorAll('a[data-path]').forEach((link) => {
          const path = link.getAttribute('data-path');
          if (path === currentPath) {
            link.className = 'flex items-center gap-3 px-space-md py-space-sm transition-colors bg-primary-container text-on-primary-container font-semibold rounded-lg shadow-sm';
            link.setAttribute('aria-current', 'page');
          } else {
            link.className = 'flex items-center gap-3 px-space-md py-space-sm rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md';
            link.removeAttribute('aria-current');
          }
        });
      }

      // 4. Populate sidebar from stored metadata if present
      const meta = apiClient.getActiveDatasetMeta();
      if (meta) {
        this.syncSidebar(meta);
      }
    },

    syncSidebar(meta) {
      if (!meta || typeof document === 'undefined') return;

      const filename = meta.filename || 'student_lifestyle_dataset.csv';
      const rows = meta.cleaned_rows || meta.raw_rows || meta.total_students || 2000;
      const isSynthetic = !!meta.is_synthetic;

      // Update sidebar dataset info box
      const aside = document.querySelector('aside');
      if (aside) {
        const filenameEl = aside.querySelector('.truncate, [data-sidebar-filename]');
        if (filenameEl) {
          filenameEl.textContent = filename;
          filenameEl.title = filename;
        }

        const subtitleEl = aside.querySelector('.text-on-surface-variant.mb-2, [data-sidebar-meta]');
        if (subtitleEl) {
          const features = meta.features_count || meta.features_analyzed || 8;
          subtitleEl.innerHTML = `${Number(rows).toLocaleString()} rows • ${features} features` +
            (isSynthetic ? '<br><span class="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">SYNTHETIC SAMPLE</span>' : '<br><span class="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">USER VERIFIED</span>');
        }
      }

      // Update header top bar
      const header = document.querySelector('header');
      if (header) {
        const recordCounter = header.querySelector('.font-medium.text-on-surface');
        if (recordCounter) {
          recordCounter.textContent = `${Number(rows).toLocaleString()} Verified Student Records`;
        }
        const readyBadge = header.querySelector('.text-primary.font-semibold');
        if (readyBadge) {
          if (isSynthetic) {
            readyBadge.textContent = 'Synthetic Cohort';
            readyBadge.className = 'font-label-sm text-label-sm text-amber-700 font-semibold';
          } else {
            readyBadge.textContent = 'Cleaned & Ready';
            readyBadge.className = 'font-label-sm text-label-sm text-primary font-semibold';
          }
        }
      }
    },

    showToast(message, type = 'info', duration = 4000) {
      if (typeof document === 'undefined') return;

      let toastContainer = document.getElementById('eduwell-toast-container');
      if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'eduwell-toast-container';
        toastContainer.className = 'fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-md pointer-events-none';
        document.body.appendChild(toastContainer);
      }

      const toast = document.createElement('div');
      toast.className = 'pointer-events-auto transform translate-y-4 opacity-0 transition-all duration-300 p-4 rounded-xl shadow-lg border flex items-start gap-3 ';

      const icons = {
        success: { icon: 'check_circle', border: 'border-emerald-300', bg: 'bg-emerald-50 text-emerald-900', iconColor: 'text-emerald-600' },
        error: { icon: 'error', border: 'border-rose-300', bg: 'bg-rose-50 text-rose-900', iconColor: 'text-rose-600' },
        warning: { icon: 'warning', border: 'border-amber-300', bg: 'bg-amber-50 text-amber-900', iconColor: 'text-amber-600' },
        info: { icon: 'info', border: 'border-sky-300', bg: 'bg-sky-50 text-sky-900', iconColor: 'text-sky-600' }
      };

      const style = icons[type] || icons.info;
      toast.className += `${style.bg} ${style.border}`;

      toast.innerHTML = `
        <span class="material-symbols-outlined ${style.iconColor} text-xl shrink-0 mt-0.5">${style.icon}</span>
        <div class="flex-1 text-sm font-medium leading-snug">${message}</div>
        <button class="shrink-0 text-slate-400 hover:text-slate-700 transition-colors" type="button" aria-label="Close">
          <span class="material-symbols-outlined text-base">close</span>
        </button>
      `;

      toast.querySelector('button').addEventListener('click', () => {
        toast.classList.add('opacity-0', 'translate-y-4');
        setTimeout(() => toast.remove(), 300);
      });

      toastContainer.appendChild(toast);
      requestAnimationFrame(() => {
        toast.classList.remove('opacity-0', 'translate-y-4');
      });

      if (duration > 0) {
        setTimeout(() => {
          if (toast.parentElement) {
            toast.classList.add('opacity-0', 'translate-y-4');
            setTimeout(() => toast.remove(), 300);
          }
        }, duration);
      }
    },

    showErrorBanner(container, message, onRetry) {
      if (!container) return;
      container.innerHTML = `
        <div class="p-6 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm my-4">
          <div class="flex items-start gap-3">
            <span class="material-symbols-outlined text-rose-600 text-2xl shrink-0 mt-0.5">error</span>
            <div>
              <h4 class="font-bold text-base">Unable to Load Analysis Data</h4>
              <p class="text-sm text-rose-700 mt-1">${message}</p>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            ${onRetry ? '<button id="eduwell-retry-btn" class="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium text-sm transition-colors shadow-sm">Retry Request</button>' : ''}
            <a href="${ROUTE_MAP['upload-validation']}" class="px-4 py-2 rounded-lg bg-white border border-rose-300 hover:bg-rose-50 text-rose-900 font-medium text-sm transition-colors">Go to Upload</a>
          </div>
        </div>
      `;
      if (onRetry) {
        const btn = container.querySelector('#eduwell-retry-btn');
        if (btn) btn.addEventListener('click', onRetry);
      }
    },

    showEmptyState(container, message, actionText = 'Load Sample Dataset', onAction = null) {
      if (!container) return;
      container.innerHTML = `
        <div class="p-12 rounded-xl bg-surface-container-lowest border border-dashed border-outline-variant/60 text-center flex flex-col items-center justify-center my-6">
          <div class="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center text-primary mb-4">
            <span class="material-symbols-outlined text-3xl">dataset</span>
          </div>
          <h3 class="font-headline-md text-headline-md font-semibold text-on-surface mb-2">No Active Dataset Loaded</h3>
          <p class="font-body-md text-body-md text-on-surface-variant max-w-md mb-6">${message || 'Please upload a CSV dataset or load the verified sample cohort to inspect statistical insights.'}</p>
          <div class="flex items-center gap-3">
            <button id="eduwell-empty-action" class="px-5 py-2.5 rounded-lg bg-primary hover:bg-primary-container text-on-primary font-semibold text-sm transition-colors shadow-sm flex items-center gap-2">
              <span class="material-symbols-outlined text-lg">database</span>
              <span>${actionText}</span>
            </button>
            <a href="${ROUTE_MAP['upload-validation']}" class="px-4 py-2.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-medium text-sm transition-colors">
              Upload CSV
            </a>
          </div>
        </div>
      `;

      const btn = container.querySelector('#eduwell-empty-action');
      if (btn) {
        btn.addEventListener('click', async () => {
          if (onAction) {
            onAction();
          } else {
            btn.disabled = true;
            btn.innerHTML = '<span class="material-symbols-outlined text-lg animate-spin">refresh</span><span>Loading Sample...</span>';
            try {
              await apiClient.loadSample();
              EduWellUI.showToast('Sample dataset loaded successfully!', 'success');
              window.location.reload();
            } catch (err) {
              btn.disabled = false;
              btn.innerHTML = '<span>Retry</span>';
              EduWellUI.showToast(err.message, 'error');
            }
          }
        });
      }
    }
  };

  return {
    EduWellApiClient,
    apiClient,
    EduWellUI
  };
});
