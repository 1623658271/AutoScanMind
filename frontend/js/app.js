/**
 * AutoScanMind — 前端主逻辑
 * 搜索、结果渲染、预览弹窗、粒子背景、状态轮询
 */

const API = 'http://127.0.0.1:18765';
const PAGE_SIZE = 30;
const _APP_JS_VERSION = 'v22';

let allResults = [];
let displayedCount = 0;
let currentMode = 'hybrid';
let previewItem = null;
let progressTimer = null;

// 索引遮罩状态（保存设置触发自动索引时）
let _indexingBlockActive = false;
let _indexingBlockTimer  = null;

// 目录筛选状态
let indexedDirs = [];           // 已索引目录列表 [{"directory":..., "count":...}, ...]
let selectedDirSet = new Set();  // 选中的目录，空集合 = 不搜任何目录
let dirFilterOpen = false;

// ── DOM 引用 ──────────────────────────────────────────────────────
const searchInput    = document.getElementById('search-input');
const btnSearch      = document.getElementById('btn-search');
const btnClear       = document.getElementById('btn-clear');
const emptyState     = document.getElementById('empty-state');
const resultsSection = document.getElementById('results-section');
const resultsGrid    = document.getElementById('results-grid');
const resultCount    = document.getElementById('result-count');
const loadingOverlay = document.getElementById('loading-overlay');
const loadMoreWrap   = document.getElementById('load-more-wrap');
const btnLoadMore    = document.getElementById('btn-load-more');
const indexDot       = document.getElementById('index-dot');
const indexStatusTxt = document.getElementById('index-status-text');
const indexProgWrap  = document.getElementById('index-progress-bar-wrap');
const progressFill   = document.getElementById('progress-fill');
const progressTxt    = document.getElementById('progress-text');
const totalIndexed   = document.getElementById('total-indexed');
const lastUpdateTime = document.getElementById('last-update-time');

// ══════════════════════════════════════════════════════════════════
//  初始化
// ══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initSearchEvents();
  initModeSelector();
  initPreviewModal();
  initTipCards();
  initDirFilter();
  startProgressPolling();
});

// ══════════════════════════════════════════════════════════════════
//  搜索逻辑
// ══════════════════════════════════════════════════════════════════
function initSearchEvents() {
  btnSearch.addEventListener('click', doSearch);

  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
  });

  searchInput.addEventListener('input', () => {
    const has = searchInput.value.length > 0;
    btnClear.style.display = has ? '' : 'none';
  });

  btnClear.addEventListener('click', () => {
    searchInput.value = '';
    btnClear.style.display = 'none';
    clearResults();
    emptyState.style.display = '';
    resultsSection.style.display = 'none';
    searchInput.focus();
  });

  btnLoadMore.addEventListener('click', loadMore);
}

async function doSearch() {
  const query = searchInput.value.trim();
  if (!query) return;

  loadingOverlay.style.display = '';
  emptyState.style.display = 'none';
  resultsSection.style.display = 'none';

  try {
    const body = {
      query,
      top_n: 0,  // 0 = 不限制，返回所有匹配结果
      mode: currentMode,
    };
    // 只有在已成功加载目录列表且 selectedDirSet 非空时才限制搜索范围
    // selectedDirSet 为空说明选中状态异常，此时不限制目录（搜全部）
    if (indexedDirs.length > 0 && selectedDirSet.size > 0) {
      body.directories = [...selectedDirSet];
    }
    // TODO: 调试，确认后删除
    console.log('[doSearch] directories:', JSON.stringify(body.directories || null), 'selectedDirSet size:', selectedDirSet.size, 'indexedDirs count:', indexedDirs.length);

    const res = await fetch(`${API}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    clearResults();
    allResults = data.results || [];
    displayedCount = 0;
    renderResults(PAGE_SIZE);

    const count = allResults.length;
    resultCount.textContent = `找到 ${count} 张图片，耗时 ${data.elapsed_ms}ms`;

    resultsSection.style.display = '';

    if (allResults.length > PAGE_SIZE) {
      loadMoreWrap.style.display = '';
    }

    // 搜索结果为空且索引正在进行中，提示用户等待
    if (count === 0) {
      try {
        const prog = await fetch(`${API}/api/index/progress`);
        if (prog.ok) {
          const pd = await prog.json();
          if (pd.status && pd.status !== 'completed' && pd.status !== 'idle' && pd.indexed_count === 0) {
            showToast('索引正在构建中，请稍后再搜索…', 'info');
          }
        }
      } catch (_) { /* ignore */ }
    }

  } catch (err) {
    console.error('搜索失败:', err);
    showToast('搜索失败，请检查后端服务是否启动', 'error');
    emptyState.style.display = '';
  } finally {
    loadingOverlay.style.display = 'none';
  }
}

function clearResults() {
  resultsGrid.innerHTML = '';
  allResults = [];
  displayedCount = 0;
  resultCount.textContent = '';
  loadMoreWrap.style.display = 'none';
}

// ══════════════════════════════════════════════════════════════════
//  渲染结果卡片
// ══════════════════════════════════════════════════════════════════
function renderResults(count) {
  const end = Math.min(displayedCount + count, allResults.length);
  const frag = document.createDocumentFragment();

  for (let i = displayedCount; i < end; i++) {
    const item = allResults[i];
    frag.appendChild(createCard(item, i));
  }

  resultsGrid.appendChild(frag);
  displayedCount = end;

  if (displayedCount >= allResults.length) {
    loadMoreWrap.style.display = 'none';
  }
}

function loadMore() {
  renderResults(PAGE_SIZE);
}

function createCard(item, index) {
  const card = document.createElement('div');
  card.className = 'result-card';
  card.dataset.index = index;

  // 评分徽章样式
  const pct = Math.round(item.score * 100);
  const badgeClass = pct >= 70 ? 'badge-high' : pct >= 40 ? 'badge-medium' : 'badge-low';

  // OCR 文字徽章（仅当有 OCR 匹配时显示）
  const ocrBadge = item.ocr_score > 0.1
    ? `<div class="card-ocr-badge">文字</div>` : '';

  // 分数详情（CLIP + OCR 各自概率）
  const clipPct = Math.round(item.clip_score * 100);
  const ocrPct = Math.round(item.ocr_score * 100);
  const scoreDetail = (clipPct > 0 || ocrPct > 0)
    ? `<div class="card-score-detail">语义 ${clipPct}% · 文字 ${ocrPct}%</div>` : '';

  card.innerHTML = `
    <div class="card-img-wrap">
      <img class="card-img" src="${item.thumbnail_url || ''}" alt="${escapeHtml(item.file_name)}" loading="lazy" />
      <div class="card-score-badge ${badgeClass}">${pct}%</div>
      ${ocrBadge}
      <div class="card-overlay">
        <div class="card-filename">${escapeHtml(item.file_name)}</div>
        <div class="card-filepath">${escapeHtml(item.path)}</div>
        ${scoreDetail}
      </div>
    </div>
    <div class="card-footer">
      <span class="card-name" title="${escapeHtml(item.file_name)}">${escapeHtml(item.file_name)}</span>
      <div class="card-actions">
        <button class="card-action-btn" title="打开文件" onclick="openFile(event, '${escapePath(item.path)}')">🗂</button>
        <button class="card-action-btn" title="打开目录" onclick="openFolder(event, '${escapePath(item.path)}')">📁</button>
      </div>
    </div>
  `;

  card.addEventListener('click', (e) => {
    if (e.target.closest('.card-action-btn')) return;
    showPreview(item);
  });

  return card;
}

// ══════════════════════════════════════════════════════════════════
//  搜索模式选择
// ══════════════════════════════════════════════════════════════════
function initModeSelector() {
  document.querySelectorAll('.mode-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.mode;
    });
  });
}

// ══════════════════════════════════════════════════════════════════
//  预览弹窗
// ══════════════════════════════════════════════════════════════════
function initPreviewModal() {
  document.getElementById('preview-backdrop').addEventListener('click', closePreview);
  document.getElementById('btn-close-preview').addEventListener('click', closePreview);
  document.getElementById('btn-preview-open').addEventListener('click', () => {
    if (previewItem) openFile(null, previewItem.path);
  });
  document.getElementById('btn-preview-folder').addEventListener('click', () => {
    if (previewItem) openFolder(null, previewItem.path);
  });

  // ESC 关闭
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePreview();
  });
}

function showPreview(item) {
  previewItem = item;
  const modal = document.getElementById('preview-modal');
  const img   = document.getElementById('preview-img');
  const fname = document.getElementById('preview-filename');
  const meta  = document.getElementById('preview-meta');
  const ocrWrap = document.getElementById('preview-ocr');
  const ocrTxt  = document.getElementById('preview-ocr-text');

  fname.textContent = item.file_name;
  img.src = item.thumbnail_url || `${API}/api/files/thumbnail?path=${encodeURIComponent(item.path)}`;
  img.alt = item.file_name;

  const pct = Math.round(item.score * 100);
  const size = formatBytes(item.file_size);
  const dim  = item.width && item.height ? `${item.width}×${item.height}` : '';
  meta.innerHTML = `
    <span>相关度 <strong style="color:var(--accent-blue)">${pct}%</strong></span>
    ${dim ? `<span>尺寸 ${dim}</span>` : ''}
    ${size ? `<span>大小 ${size}</span>` : ''}
    <span title="${escapeHtml(item.path)}" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl">${escapeHtml(item.path)}</span>
  `;

  if (item.ocr_text && item.ocr_text.trim()) {
    ocrTxt.textContent = item.ocr_text;
    ocrWrap.style.display = '';
  } else {
    ocrWrap.style.display = 'none';
  }

  modal.style.display = '';
  requestAnimationFrame(() => modal.style.opacity = 1);
}

function closePreview() {
  const modal = document.getElementById('preview-modal');
  modal.style.display = 'none';
  previewItem = null;
}

// ══════════════════════════════════════════════════════════════════
//  文件操作
// ══════════════════════════════════════════════════════════════════
async function openFile(event, path) {
  if (event) event.stopPropagation();
  try {
    const res = await fetch(`${API}/api/files/open`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    if (!data.ok) showToast(data.message, 'error');
  } catch (e) {
    showToast('打开文件失败', 'error');
  }
}

async function openFolder(event, path) {
  if (event) event.stopPropagation();
  try {
    const res = await fetch(`${API}/api/files/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    if (!data.ok) showToast(data.message, 'error');
  } catch (e) {
    showToast('打开目录失败', 'error');
  }
}

// ══════════════════════════════════════════════════════════════════
//  搜索目录筛选器
// ══════════════════════════════════════════════════════════════════
function initDirFilter() {
  const toggle = document.getElementById('search-dir-toggle');
  const dropdown = document.getElementById('search-dir-dropdown');
  const checkAll = document.getElementById('search-dir-checkall');

  if (!toggle || !dropdown || !checkAll) {
    console.error('[initDirFilter] 元素缺失!');
    return;
  }

  // ── 渲染函数（闭包内，避免外部引用问题）───────────────────
  function renderDirItems() {
    const listEl = document.getElementById('search-dir-list');
    if (!listEl) return;

    listEl.innerHTML = '';

    if (indexedDirs.length === 0) {
      listEl.innerHTML = '<div style="padding:16px;color:var(--text-muted);font-size:12px;text-align:center">暂无已索引的目录</div>';
      return;
    }

    indexedDirs.forEach(d => {
      const dir = d.directory;
      const isSelected = selectedDirSet.has(dir);
      const item = document.createElement('label');
      item.className = 'search-dir-item';
      item.innerHTML =
        '<input type="checkbox" ' + (isSelected ? 'checked' : '') + ' />' +
        '<span class="check-box"></span>' +
        '<span class="search-dir-item-path" title="' + dir + '">' + dir + '</span>' +
        '<span class="search-dir-item-count">' + d.count + ' 张</span>';

      const cb = item.querySelector('input[type="checkbox"]');
      cb.addEventListener('change', () => {
        if (cb.checked) {
          selectedDirSet.add(dir);
        } else {
          selectedDirSet.delete(dir);
        }
        checkAll.checked = selectedDirSet.size === indexedDirs.length;
        renderDirItems();
        updateDirCountBadge();
      });

      listEl.appendChild(item);
    });

    checkAll.checked = selectedDirSet.size === indexedDirs.length;
    updateDirCountBadge();
  }

  // ── 加载已索引目录（展开下拉时调用）───────────────────────
  async function loadDirs() {
    const listEl = document.getElementById('search-dir-list');
    if (!listEl) return;

    // 缓存命中，直接渲染
    if (indexedDirs.length > 0) {
      renderDirItems();
      return;
    }

    listEl.innerHTML = '<div style="padding:12px;color:var(--text-muted);font-size:12px;text-align:center">加载中…</div>';

    try {
      const res = await fetch(API + '/api/index/indexed-dirs');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      indexedDirs = data.directories || [];

      // 获取设置目录用于初始化 selectedDirSet
      let configDirsLower = [];
      try {
        const sRes = await fetch(API + '/api/settings');
        if (sRes.ok) {
          const settings = await sRes.json();
          configDirsLower = (settings.scan_directories || []).map(function(d) { return d.toLowerCase(); });
        }
      } catch (e) { /* 忽略 */ }

      _rebuildSelectedDirSet(configDirsLower);

      if (!indexedDirs.length) {
        listEl.innerHTML = '<div style="padding:16px;color:var(--text-muted);font-size:12px;text-align:center">暂无已索引的目录</div>';
        return;
      }

      renderDirItems();
    } catch (e) {
      listEl.innerHTML = '<div style="padding:16px;color:var(--accent-red);font-size:12px;text-align:center">加载失败: ' + (e.message || e) + '</div>';
    }
  }

  // ── 事件绑定 ───────────────────────────────────────────────
  toggle.addEventListener('click', function(e) {
    e.stopPropagation();
    dirFilterOpen = !dirFilterOpen;
    dropdown.style.display = dirFilterOpen ? '' : 'none';
    toggle.classList.toggle('active', dirFilterOpen);
    if (dirFilterOpen) loadDirs();
  });

  // 点击外部关闭
  document.addEventListener('click', function(e) {
    if (dirFilterOpen && !e.target.closest('.search-dir-filter')) {
      dirFilterOpen = false;
      dropdown.style.display = 'none';
      toggle.classList.remove('active');
    }
  });

  // 全选/取消全选
  checkAll.addEventListener('change', function() {
    if (checkAll.checked) {
      selectedDirSet = new Set(indexedDirs.map(function(d) { return d.directory; }));
    } else {
      selectedDirSet = new Set();
    }
    renderDirItems();
  });

  // 初始后台加载（最多重试5次）
  var _silentRetryCount = 0;
  async function tryLoadSilent() {
    await loadIndexedDirsSilent();
    if (indexedDirs.length === 0 && _silentRetryCount < 5) {
      _silentRetryCount++;
      setTimeout(tryLoadSilent, 2000);
    }
  }
  setTimeout(tryLoadSilent, 1000);
}

async function loadIndexedDirsSilent() {
  try {
    // 获取已索引目录
    let indexedRes;
    try {
      indexedRes = await fetch(`${API}/api/index/indexed-dirs`);
    } catch (e) {
      console.error('loadIndexedDirsSilent: indexed-dirs fetch 失败', e);
      return;
    }
    if (!indexedRes.ok) return;

    const indexedData = await indexedRes.json();
    indexedDirs = indexedData.directories || [];

    // 获取设置中配置的目录（转小写用于比较）
    let configDirsLower = [];
    try {
      const settingsRes = await fetch(`${API}/api/settings`);
      if (settingsRes.ok) {
        const settings = await settingsRes.json();
        configDirsLower = (settings.scan_directories || []).map(d => d.toLowerCase());
      }
    } catch (e) {
      console.warn('loadIndexedDirsSilent: 获取设置失败', e);
    }

    if (indexedDirs.length > 0) {
      _rebuildSelectedDirSet(configDirsLower);

      document.getElementById('search-dir-filter').style.display = '';
      updateDirCountBadge();
    }
  } catch (e) {
    console.error('loadIndexedDirsSilent 失败:', e);
  }
}

/**
 * 根据 configDirsLower 和当前 indexedDirs 重建 selectedDirSet
 * 规则：已索引且在配置目录下的 → 选中；都没有匹配的 → 全选（回退）
 */
function _rebuildSelectedDirSet(configDirsLower) {
  const newSelected = new Set();
  if (configDirsLower.length > 0 && indexedDirs.length > 0) {
    indexedDirs.forEach(d => {
      const dirLower = d.directory.toLowerCase().replace(/\\/g, '/');
      const matched = configDirsLower.some(cfg => {
        const cfgNorm = cfg.replace(/\\/g, '/');
        return dirLower === cfgNorm || dirLower.startsWith(cfgNorm + '/');
      });
      if (matched) newSelected.add(d.directory);
    });
    // 如果配置目录都还没索引（全是新添加的），回退到全选已索引目录
    if (newSelected.size === 0) {
      indexedDirs.forEach(d => newSelected.add(d.directory));
    }
  } else {
    // 没有配置目录：全选已索引目录
    indexedDirs.forEach(d => newSelected.add(d.directory));
  }
  selectedDirSet = newSelected;
}

function updateDirCountBadge() {
  const badge = document.getElementById('search-dir-count');
  if (!selectedDirSet || selectedDirSet.size === indexedDirs.length) {
    badge.textContent = indexedDirs.length > 0 ? '全部' : '';
  } else {
    badge.textContent = selectedDirSet.size > 0 ? selectedDirSet.size : '';
  }
}

// ══════════════════════════════════════════════════════════════════
//  提示词卡片（快捷搜索）
// ══════════════════════════════════════════════════════════════════
function initTipCards() {
  document.querySelectorAll('.tip-card').forEach(card => {
    card.addEventListener('click', () => {
      const text = card.querySelector('span:last-child').textContent.trim();
      searchInput.value = text;
      btnClear.style.display = '';
      doSearch();
    });
  });
}

// ══════════════════════════════════════════════════════════════════
//  进度轮询（每 2 秒查一次索引状态）
// ══════════════════════════════════════════════════════════════════
function startProgressPolling() {
  pollProgress();
  progressTimer = setInterval(pollProgress, 2000);
}

async function pollProgress() {
  try {
    const res = await fetch(`${API}/api/index/progress`);
    if (!res.ok) return;
    const data = await res.json();
    updateStatusBar(data);
  } catch {
    // 后端未就绪时静默忽略
  }
}

function updateStatusBar(data) {
  const { status, total_files, processed_files, progress_pct, error_msg,
          indexed_count, last_update_time: lut } = data;

  // 状态点颜色
  indexDot.className = 'status-dot ' + (status || 'idle');

  // 状态文字
  const labels = {
    idle: '就绪',
    scanning: '扫描文件中…',
    indexing: `索引中 ${processed_files}/${total_files}`,
    saving:   '保存索引…',
    completed:'索引完成',
    error:    `错误: ${error_msg || '未知错误'}`,
  };
  indexStatusTxt.textContent = labels[status] || '就绪';

  // 进度条
  if (['scanning','indexing','saving'].includes(status)) {
    indexProgWrap.style.display = '';
    const pct = progress_pct || 0;
    progressFill.style.width = `${pct}%`;
    progressTxt.textContent = `${Math.round(pct)}%`;
  } else {
    indexProgWrap.style.display = 'none';
  }

  // 已索引总数
  totalIndexed.innerHTML = `已索引 <strong>${indexed_count || 0}</strong> 张图片`;

  // 上次更新时间
  if (lut) {
    lastUpdateTime.textContent = `上次更新: ${lut}`;
  }
}

// ══════════════════════════════════════════════════════════════════
//  Toast 通知
// ══════════════════════════════════════════════════════════════════
function showToast(msg, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ══════════════════════════════════════════════════════════════════
//  粒子背景
// ══════════════════════════════════════════════════════════════════
function initParticles() {
  const canvas = document.getElementById('bg-canvas');
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function createParticles(n = 60) {
    particles = Array.from({ length: n }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.8 + 0.4,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.4 + 0.05,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // 渐变背景
    const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W,H)/1.5);
    grad.addColorStop(0,   'rgba(15,23,42,0)');
    grad.addColorStop(0.5, 'rgba(30,27,75,0.15)');
    grad.addColorStop(1,   'rgba(6,8,15,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // 粒子
    for (const p of particles) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(56,189,248,${p.alpha})`;
      ctx.fill();

      p.x += p.dx;
      p.y += p.dy;
      if (p.x < 0 || p.x > W) p.dx *= -1;
      if (p.y < 0 || p.y > H) p.dy *= -1;
    }

    // 连线
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(129,140,248,${0.08 * (1 - dist/120)})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(draw);
  }

  resize();
  createParticles();
  draw();
  window.addEventListener('resize', () => { resize(); createParticles(); });
}

// ══════════════════════════════════════════════════════════════════
//  工具函数
// ══════════════════════════════════════════════════════════════════
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapePath(str) {
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024*1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/(1024*1024)).toFixed(1)} MB`;
}

// ══════════════════════════════════════════════════════════════════
//  索引进行中 — 搜索遮罩（保存设置自动触发索引时使用）
// ══════════════════════════════════════════════════════════════════

/**
 * 显示搜索遮罩并开始轮询进度，直到索引完成
 * @param {string} label - 正在索引的目录名提示
 */
function showIndexingBlock(label) {
  _indexingBlockActive = true;
  // 记录遮罩启动时间，避免在后台线程还未切换状态时就提前关闭
  const startedAt = Date.now();
  const MIN_WATCH_MS = 3000; // 至少观察 3 秒再允许因 idle/completed 退出

  const block  = document.getElementById('indexing-search-block');
  const title  = document.getElementById('isb-title');
  const sub    = document.getElementById('isb-subtitle');
  const fill   = document.getElementById('isb-prog-fill');
  const pct    = document.getElementById('isb-prog-pct');
  const stopBtn= document.getElementById('isb-stop-btn');

  title.textContent = `正在为「${label}」建立索引…`;
  sub.textContent   = '索引完成后即可开始搜索';
  fill.style.width  = '0%';
  pct.textContent   = '0%';
  block.style.display = '';
  if (stopBtn) stopBtn.style.display = '';

  // 停止按钮
  if (stopBtn) {
    const newBtn = stopBtn.cloneNode(true); // 移除旧事件
    stopBtn.parentNode.replaceChild(newBtn, stopBtn);
    newBtn.addEventListener('click', async () => {
      try {
        await fetch(`${API}/api/index/stop`, { method: 'POST' });
        newBtn.style.display = 'none';
        sub.textContent = '正在停止索引…';
      } catch { /* 静默忽略 */ }
    });
  }

  // 禁用搜索输入
  _setSearchDisabled(true);

  if (_indexingBlockTimer) clearInterval(_indexingBlockTimer);
  _indexingBlockTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API}/api/index/progress`);
      if (!res.ok) return;
      const data = await res.json();
      const p = data.progress_pct || 0;
      fill.style.width = `${p}%`;
      pct.textContent  = `${Math.round(p)}%`;

      const s = data.status || 'idle';
      const labels = {
        scanning: '扫描文件中…',
        indexing: `索引中 ${data.processed_files || 0}/${data.total_files || 0}`,
        saving:   '保存索引数据…',
        completed:'索引完成！',
        error:    `错误: ${data.error_msg || '未知'}`,
        idle:     '就绪',
      };
      sub.textContent = labels[s] || sub.textContent;

      // 只有 completed 或 error 才结束；idle 需等 MIN_WATCH_MS 后才允许退出
      // 避免后台线程尚未启动时 idle 状态导致遮罩立刻消失
      const elapsed = Date.now() - startedAt;
      const shouldExit =
        s === 'completed' ||
        s === 'error' ||
        (s === 'idle' && elapsed > MIN_WATCH_MS);

      if (shouldExit && _indexingBlockActive) {
        // 先停止轮询、标记非活跃，防止 800ms 内再次触发
        _indexingBlockActive = false;
        clearInterval(_indexingBlockTimer);
        _indexingBlockTimer = null;
        if (s === 'completed' || s === 'idle') {
          fill.style.width = '100%';
          pct.textContent  = '100%';
        }
        // 延迟 800ms 后隐藏，让用户看到完成状态
        setTimeout(() => hideIndexingBlock(), 800);
      }
    } catch { /* 静默忽略 */ }
  }, 1000);
}

function hideIndexingBlock() {
  _indexingBlockActive = false;
  if (_indexingBlockTimer) { clearInterval(_indexingBlockTimer); _indexingBlockTimer = null; }
  const block = document.getElementById('indexing-search-block');
  block.style.display = 'none';
  const stopBtn = document.getElementById('isb-stop-btn');
  if (stopBtn) stopBtn.style.display = '';
  _setSearchDisabled(false);
  // 刷新目录筛选器
  indexedDirs = [];
  loadIndexedDirsSilent();
}

function _setSearchDisabled(disabled) {
  const input   = document.getElementById('search-input');
  const btnSrch = document.getElementById('btn-search');
  if (input)   { input.disabled   = disabled; input.placeholder = disabled ? '索引建立中，请稍候…' : '输入任何描述，例如「猫」「合同」「海边日落」…'; }
  if (btnSrch) { btnSrch.disabled = disabled; }
}
