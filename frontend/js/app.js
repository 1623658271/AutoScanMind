/**
 * AutoScanMind — 前端主逻辑
 * 搜索、结果渲染、预览弹窗、粒子背景、状态轮询
 */

const API = 'http://127.0.0.1:18765';
const PAGE_SIZE = 30;

let allResults = [];
let displayedCount = 0;
let currentMode = 'hybrid';
let previewItem = null;
let progressTimer = null;

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
    const res = await fetch(`${API}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        top_n: 200,
        mode: currentMode,
      }),
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
