/**
 * AutoScanMind — 设置面板交互逻辑
 */

/* API 已在 app.js 中声明，此处直接使用 */
let currentSettings = null;
let selectedDrives = [];

// ── DOM ──────────────────────────────────────────────────────────
const settingsOverlay = document.getElementById('settings-overlay');
const settingsPanel   = document.getElementById('settings-panel');
const btnSettings     = document.getElementById('btn-settings');
const btnCloseSettings= document.getElementById('btn-close-settings');
const btnSaveSettings = document.getElementById('btn-save-settings');
const btnAddDir       = document.getElementById('btn-add-dir');
const dirInput        = document.getElementById('dir-input');
const dirList         = document.getElementById('dir-list');
const chkFullDisk     = document.getElementById('chk-full-disk');
const drivesSection   = document.getElementById('drives-section');
const drivesList      = document.getElementById('drives-list');
const alphaSlider     = document.getElementById('alpha-slider');
const alphaVal        = document.getElementById('alpha-val');
const ocrBar          = document.getElementById('ocr-bar');
const ocrVal          = document.getElementById('ocr-val');
const chkOcr          = document.getElementById('chk-ocr');
const btnOpenDataDir  = document.getElementById('btn-open-data-dir');
const btnOpenPurge    = document.getElementById('btn-open-purge');
const btnClosePurge   = document.getElementById('btn-close-purge');
const purgeModal      = document.getElementById('purge-modal');
const purgeBackdrop   = document.getElementById('purge-backdrop');
const btnOpenIndexMgr = document.getElementById('btn-open-index-mgr');
const btnCloseIndexMgr= document.getElementById('btn-close-index-mgr');
const indexMgrModal   = document.getElementById('index-mgr-modal');
const indexMgrBackdrop= document.getElementById('index-mgr-backdrop');

// ══════════════════════════════════════════════════════════════════
//  初始化
// ══════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  btnSettings.addEventListener('click', openSettings);
  btnCloseSettings.addEventListener('click', closeSettings);
  settingsOverlay.addEventListener('click', closeSettings);
  btnSaveSettings.addEventListener('click', saveSettings);
  btnAddDir.addEventListener('click', addDirectory);
  dirInput.addEventListener('keydown', e => { if (e.key === 'Enter') addDirectory(); });
  chkFullDisk.addEventListener('change', onFullDiskToggle);
  alphaSlider.addEventListener('input', onAlphaChange);
  btnOpenDataDir.addEventListener('click', e => {
    e.preventDefault();
    openDataDir();
  });
  // 索引清理弹窗
  btnOpenPurge.addEventListener('click', openPurgeModal);
  btnClosePurge.addEventListener('click', closePurgeModal);
  purgeBackdrop.addEventListener('click', closePurgeModal);
  initPurgeResize();
  // 索引管理弹窗
  btnOpenIndexMgr.addEventListener('click', openIndexMgrModal);
  btnCloseIndexMgr.addEventListener('click', closeIndexMgrModal);
  indexMgrBackdrop.addEventListener('click', closeIndexMgrModal);
  initIndexMgrResize();
});

// ══════════════════════════════════════════════════════════════════
//  打开 / 关闭设置面板
// ══════════════════════════════════════════════════════════════════
async function openSettings() {
  await loadSettings();
  settingsOverlay.style.display = '';
  settingsPanel.classList.add('open');
}

function closeSettings() {
  settingsPanel.classList.remove('open');
  setTimeout(() => { settingsOverlay.style.display = 'none'; }, 320);
}

// ══════════════════════════════════════════════════════════════════
//  加载设置
// ══════════════════════════════════════════════════════════════════
async function loadSettings() {
  try {
    const res = await fetch(`${API}/api/settings`);
    if (!res.ok) return;
    currentSettings = await res.json();
    applySettingsToUI(currentSettings);
  } catch (e) {
    console.warn('加载设置失败:', e);
  }
}

function applySettingsToUI(s) {
  // 目录列表
  renderDirList(s.scan_directories || []);

  // 全盘扫描
  chkFullDisk.checked = s.full_disk_scan || false;
  onFullDiskToggle();

  // 权重滑块
  const alpha = Math.round((s.alpha || 0.6) * 100);
  alphaSlider.value = alpha;
  updateAlphaDisplay(alpha);

  // OCR 开关
  chkOcr.checked = s.ocr_enabled !== false;
}

// ══════════════════════════════════════════════════════════════════
//  保存设置
// ══════════════════════════════════════════════════════════════════
async function saveSettings() {
  const dirs = getDisplayedDirs();
  const alpha = parseInt(alphaSlider.value) / 100;

  const settings = {
    scan_directories: dirs,
    full_disk_scan:   chkFullDisk.checked,
    alpha:            alpha,
    top_n:            30,
    ocr_enabled:      chkOcr.checked,
    auto_index_on_start: false,
    exclude_dirs:     [],
  };

  try {
    const res = await fetch(`${API}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    const data = await res.json();
    if (data.ok) {
      showToast('保存成功！', 'success');
      currentSettings = settings;
    } else {
      showToast(data.message || '保存失败', 'error');
    }
  } catch (e) {
    showToast('保存失败：' + e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════════
//  目录管理
// ══════════════════════════════════════════════════════════════════
function renderDirList(dirs) {
  dirList.innerHTML = '';
  if (!dirs.length) {
    dirList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:6px 0">暂未添加目录</div>';
    return;
  }
  dirs.forEach(d => {
    const item = document.createElement('div');
    item.className = 'dir-item';
    item.innerHTML = `
      <span class="dir-item-path" title="${escapeHtml(d)}">${escapeHtml(d)}</span>
      <button class="dir-item-remove" title="移除" onclick="removeDir(this,'${escapePath(d)}')">✕</button>
    `;
    dirList.appendChild(item);
  });
}

function getDisplayedDirs() {
  return Array.from(dirList.querySelectorAll('.dir-item-path'))
    .map(el => el.getAttribute('title'))
    .filter(Boolean);
}

function removeDir(btn, path) {
  const decoded = path.replace(/\\\\/g, '\\');
  const item = btn.closest('.dir-item');
  if (item) item.remove();
  if (!dirList.querySelectorAll('.dir-item').length) {
    dirList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:6px 0">暂未添加目录</div>';
  }
}

async function addDirectory() {
  let path = dirInput.value.trim();

  // 输入框为空时，弹出系统目录选择窗口
  if (!path) {
    try {
      const res = await fetch(`${API}/api/files/pick-folder`);
      if (!res.ok) { showToast('无法打开目录选择', 'error'); return; }
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); return; }
      path = (data.path || '').trim();
      if (!path) return; // 用户取消了选择
      dirInput.value = path;
    } catch {
      showToast('无法连接到后端服务', 'error');
      return;
    }
  }

  // 简单验证路径存在
  try {
    const res = await fetch(`${API}/api/settings/directories/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    if (data.ok) {
      dirInput.value = '';
      // 重新加载目录列表
      const dirs = getDisplayedDirs();
      if (!dirs.includes(path)) dirs.push(path);
      renderDirList(dirs);
      showToast('目录已添加', 'success');
    } else {
      showToast(data.message || '目录添加失败', 'error');
    }
  } catch {
    showToast('无法连接到后端服务', 'error');
  }
}

// ══════════════════════════════════════════════════════════════════
//  全盘扫描
// ══════════════════════════════════════════════════════════════════
async function onFullDiskToggle() {
  if (chkFullDisk.checked) {
    drivesSection.style.display = '';
    await loadDrives();
  } else {
    drivesSection.style.display = 'none';
    selectedDrives = [];
  }
}

async function loadDrives() {
  try {
    const res = await fetch(`${API}/api/files/drives`);
    const data = await res.json();
    renderDrives(data.drives || []);
  } catch {
    drivesList.innerHTML = '<span style="color:var(--text-muted);font-size:12px">无法获取磁盘列表</span>';
  }
}

function renderDrives(drives) {
  drivesList.innerHTML = '';
  drives.forEach(d => {
    const btn = document.createElement('button');
    btn.className = 'drive-btn';
    btn.textContent = d;
    btn.addEventListener('click', () => {
      btn.classList.toggle('selected');
      if (btn.classList.contains('selected')) {
        if (!selectedDrives.includes(d)) selectedDrives.push(d);
      } else {
        selectedDrives = selectedDrives.filter(x => x !== d);
      }
    });
    drivesList.appendChild(btn);
  });
}

// ── 索引管理弹窗 ─────────────────────────────────────────────────
const indexMgrResizeHandle = document.getElementById('index-mgr-resize-handle');

function openIndexMgrModal() {
  const content = indexMgrModal.querySelector('.purge-content');
  content.style.width = '';
  content.style.height = '';
  indexMgrModal.style.display = '';
  loadIndexMgrDirs();
}

function closeIndexMgrModal() {
  indexMgrModal.style.display = 'none';
}

async function loadIndexMgrDirs() {
  const container = document.getElementById('index-mgr-dirs-list');
  if (!container) return;
  container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-muted)">加载中…</div>';

  try {
    const res = await fetch(`${API}/api/index/indexed-dirs`);
    if (!res.ok) return;
    const data = await res.json();
    const dirs = data.directories || [];

    if (!dirs.length) {
      container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--text-muted)">暂无已索引的目录</div>';
      return;
    }

    container.innerHTML = '';
    dirs.forEach(d => {
      const item = document.createElement('div');
      item.className = 'purge-dir-item';
      item.innerHTML = `
        <div class="purge-dir-info">
          <span class="purge-dir-path" title="${escapeHtml(d.directory)}">${escapeHtml(d.directory)}</span>
          <span class="purge-dir-count">${d.count} 张图片</span>
        </div>
        <div class="index-mgr-dir-actions">
          <button class="index-mgr-btn-incremental" title="增量索引：仅扫描新增图片" data-dir="${escapeHtml(d.directory)}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            增量索引
          </button>
          <button class="index-mgr-btn-rebuild" title="重建索引：重新扫描此目录所有图片" data-dir="${escapeHtml(d.directory)}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            重建索引
          </button>
        </div>
      `;

      // 增量索引
      item.querySelector('.index-mgr-btn-incremental').addEventListener('click', async function() {
        const dir = this.getAttribute('data-dir');
        try {
          const r = await fetch(`${API}/api/index/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ directories: [dir], full_rebuild: false }),
          });
          const result = await r.json();
          showToast(result.message, result.ok ? 'success' : 'info');
          closeIndexMgrModal();
        } catch {
          showToast('启动索引失败', 'error');
        }
      });

      // 重建索引
      item.querySelector('.index-mgr-btn-rebuild').addEventListener('click', async function() {
        const dir = this.getAttribute('data-dir');
        if (!confirm(`确定重建以下目录的所有索引？\n\n${dir}\n\n将清除此目录现有索引并重新扫描。`)) return;
        try {
          const r = await fetch(`${API}/api/index/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ directories: [dir], full_rebuild: true }),
          });
          const result = await r.json();
          showToast(result.message, result.ok ? 'success' : 'info');
          closeIndexMgrModal();
        } catch {
          showToast('启动重建失败', 'error');
        }
      });

      container.appendChild(item);
    });
  } catch {
    container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--accent-red)">加载失败</div>';
  }
}

// 索引管理弹窗拖拽调整大小
function initIndexMgrResize() {
  const handle = indexMgrResizeHandle;
  const content = indexMgrModal.querySelector('.purge-content');
  if (!handle || !content) return;

  let startX, startY, startW, startH;

  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    e.stopPropagation();
    startX = e.clientX;
    startY = e.clientY;
    const rect = content.getBoundingClientRect();
    startW = rect.width;
    startH = rect.height;

    document.addEventListener('mousemove', onResize);
    document.addEventListener('mouseup', onStop);
    document.body.style.userSelect = 'none';
  });

  function onResize(e) {
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    content.style.width = Math.max(480, startW + dx) + 'px';
    content.style.height = Math.max(200, startH + dy) + 'px';
    content.style.maxHeight = (window.innerHeight * 0.9) + 'px';
  }

  function onStop() {
    document.removeEventListener('mousemove', onResize);
    document.removeEventListener('mouseup', onStop);
    document.body.style.userSelect = '';
  }
}

// ── 索引清理弹窗 ─────────────────────────────────────────────────
const purgeResizeHandle = document.getElementById('purge-resize-handle');

function openPurgeModal() {
  // 重置为自适应宽度
  const content = purgeModal.querySelector('.purge-content');
  content.style.width = '';
  content.style.height = '';
  purgeModal.style.display = '';
  loadPurgeDirs();
}

function closePurgeModal() {
  purgeModal.style.display = 'none';
}

async function loadPurgeDirs() {
  const container = document.getElementById('purge-dirs-list');
  if (!container) return;
  container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-muted)">加载中…</div>';

  try {
    const res = await fetch(`${API}/api/index/indexed-dirs`);
    if (!res.ok) return;
    const data = await res.json();
    const dirs = data.directories || [];

    if (!dirs.length) {
      container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--text-muted)">暂无已索引的目录</div>';
      return;
    }

    container.innerHTML = '';
    dirs.forEach(d => {
      const item = document.createElement('div');
      item.className = 'purge-dir-item';
      item.innerHTML = `
        <div class="purge-dir-info">
          <span class="purge-dir-path" title="${escapeHtml(d.directory)}">${escapeHtml(d.directory)}</span>
          <span class="purge-dir-count">${d.count} 张图片</span>
        </div>
        <button class="purge-dir-btn" title="清理此目录索引" data-dir="${escapeHtml(d.directory)}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
          </svg>
          清理
        </button>
      `;
      item.querySelector('.purge-dir-btn').addEventListener('click', async function() {
        const dir = this.getAttribute('data-dir');
        if (!confirm(`确定清理以下目录的所有索引数据？\n\n${dir}\n\n此操作不可撤销。`)) return;
        try {
          const r = await fetch(`${API}/api/index/purge-directory`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ directory: dir }),
          });
          const result = await r.json();
          showToast(result.message, result.ok ? 'success' : 'info');
          setTimeout(() => loadPurgeDirs(), 500);
        } catch {
          showToast('清理失败', 'error');
        }
      });
      container.appendChild(item);
    });
  } catch {
    container.innerHTML = '<div style="text-align:center;padding:32px;color:var(--accent-red)">加载失败</div>';
  }
}

// ══════════════════════════════════════════════════════════════════
//  权重滑块
// ══════════════════════════════════════════════════════════════════
function onAlphaChange() {
  updateAlphaDisplay(parseInt(alphaSlider.value));
}

function updateAlphaDisplay(alpha) {
  alpha = Math.max(0, Math.min(100, alpha));
  const ocr = 100 - alpha;
  alphaVal.textContent = alpha;
  ocrVal.textContent   = ocr;
  ocrBar.style.width   = `${ocr}%`;
  // 动态更新 range 背景
  alphaSlider.style.background = `linear-gradient(to right, var(--accent-blue) 0%, var(--accent-blue) ${alpha}%, var(--bg-layer2) ${alpha}%)`;
}

// ── 双击百分比数字可手动输入 ──────────────────────────────────────
function makeEditablePercentage(spanEl, partnerSpanEl, isAlpha) {
  spanEl.style.cursor = 'text';
  spanEl.title = '双击手动输入';

  spanEl.addEventListener('dblclick', () => {
    const currentVal = parseInt(spanEl.textContent) || 0;
    const input = document.createElement('input');
    input.type = 'number';
    input.min = 0;
    input.max = 100;
    input.value = currentVal;
    input.className = 'pct-input';
    input.style.width = Math.max(32, spanEl.offsetWidth) + 'px';

    // 替换文字为输入框
    spanEl.textContent = '';
    spanEl.appendChild(input);
    input.focus();
    input.select();

    const commit = () => {
      let val = parseInt(input.value);
      if (isNaN(val)) val = currentVal;
      val = Math.max(0, Math.min(100, val));
      spanEl.textContent = '';

      if (isAlpha) {
        alphaSlider.value = val;
        updateAlphaDisplay(val);
      } else {
        // OCR 百分比是反算的
        alphaSlider.value = 100 - val;
        updateAlphaDisplay(100 - val);
      }
    };

    input.addEventListener('blur', commit);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      if (e.key === 'Escape') { input.value = currentVal; input.blur(); }
    });
  });
}

// 初始化可编辑百分比
makeEditablePercentage(alphaVal, ocrVal, true);
makeEditablePercentage(ocrVal, alphaVal, false);

// ══════════════════════════════════════════════════════════════════
//  打开数据目录
// ══════════════════════════════════════════════════════════════════
async function openDataDir() {
  try {
    await fetch(`${API}/api/files/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: '.' }), // 后端会处理为 data 目录
    });
  } catch {}
}

// ══════════════════════════════════════════════════════════════════
//  工具（局部引用全局函数）
// ══════════════════════════════════════════════════════════════════
function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escapePath(s) {
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
}
function showToast(msg, type='info') {
  if (typeof window.showToast === 'function') {
    window.showToast(msg, type);
    return;
  }
  let c = document.querySelector('.toast-container');
  if (!c) { c = document.createElement('div'); c.className='toast-container'; document.body.appendChild(c); }
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transition='opacity .3s'; setTimeout(()=>t.remove(),300); }, 3000);
}

// ── 弹窗拖拽调整大小 ──────────────────────────────────────────
function initPurgeResize() {
  const handle = purgeResizeHandle;
  const content = purgeModal.querySelector('.purge-content');
  if (!handle || !content) return;

  let startX, startY, startW, startH;

  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    e.stopPropagation();
    startX = e.clientX;
    startY = e.clientY;
    const rect = content.getBoundingClientRect();
    startW = rect.width;
    startH = rect.height;

    document.addEventListener('mousemove', onResize);
    document.addEventListener('mouseup', onStop);
    document.body.style.userSelect = 'none';
  });

  function onResize(e) {
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    content.style.width = Math.max(480, startW + dx) + 'px';
    content.style.height = Math.max(200, startH + dy) + 'px';
    content.style.maxHeight = (window.innerHeight * 0.9) + 'px';
  }

  function onStop() {
    document.removeEventListener('mousemove', onResize);
    document.removeEventListener('mouseup', onStop);
    document.body.style.userSelect = '';
  }
}
