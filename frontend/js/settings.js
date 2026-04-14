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
const deviceSelect    = document.getElementById('device-select');
const deviceStatus    = document.getElementById('device-status');
const deviceHint      = document.getElementById('device-hint');
const btnOpenDataDir  = document.getElementById('btn-open-data-dir');
const btnOpenPurge    = document.getElementById('btn-open-purge');
const btnClosePurge   = document.getElementById('btn-close-purge');
const purgeModal      = document.getElementById('purge-modal');
const purgeBackdrop   = document.getElementById('purge-backdrop');
const btnOpenIndexMgr   = document.getElementById('btn-open-index-mgr');
const btnCloseIndexMgr  = document.getElementById('btn-close-index-mgr');
const indexMgrModal     = document.getElementById('index-mgr-modal');
const indexMgrBackdrop  = document.getElementById('index-mgr-backdrop');
const indexMgrDirInput  = document.getElementById('index-mgr-dir-input');
const indexMgrBtnBrowse = document.getElementById('index-mgr-btn-browse');
const indexMgrBtnAddQueue = document.getElementById('index-mgr-btn-add-queue');
const indexMgrBtnScan   = document.getElementById('index-mgr-btn-scan');
const indexMgrQueueList = document.getElementById('index-mgr-queue-list');
const indexMgrQueueFooter = document.getElementById('index-mgr-queue-footer');
const indexMgrScanProg  = document.getElementById('index-mgr-scan-progress');
const indexMgrProgFill  = document.getElementById('index-mgr-prog-fill');
const indexMgrProgTxt   = document.getElementById('index-mgr-prog-txt');
const indexMgrProgStatus= document.getElementById('index-mgr-prog-status');

// 模型路径相关 DOM
const clipModelPath     = document.getElementById('clip-model-path');
const ocrModelPath      = document.getElementById('ocr-model-path');
const clipModelStatus    = document.getElementById('clip-model-status');
const ocrModelStatus     = document.getElementById('ocr-model-status');
const clipModelHint      = document.getElementById('clip-model-hint');
const ocrModelHint       = document.getElementById('ocr-model-hint');
const btnBrowseClipModel = document.getElementById('btn-browse-clip-model');
const btnBrowseOcrModel  = document.getElementById('btn-browse-ocr-model');

let _indexMgrScanTimer  = null;  // 弹窗内进度轮询定时器
let _indexMgrQueue      = [];    // 增量索引任务队列（路径字符串数组）
let _indexMgrScanLabel  = '';    // 当前正在索引的目录提示标签

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
  // 设备选择
  deviceSelect.addEventListener('change', onDeviceChange);
  // 索引清理弹窗
  btnOpenPurge.addEventListener('click', openPurgeModal);
  btnClosePurge.addEventListener('click', closePurgeModal);
  purgeBackdrop.addEventListener('click', closePurgeModal);
  initPurgeResize();
  // 索引管理弹窗
  btnOpenIndexMgr.addEventListener('click', openIndexMgrModal);
  btnCloseIndexMgr.addEventListener('click', closeIndexMgrModal);
  indexMgrBackdrop.addEventListener('click', closeIndexMgrModal);
  indexMgrBtnBrowse.addEventListener('click', indexMgrBrowseFolder);
  indexMgrBtnAddQueue.addEventListener('click', indexMgrAddToQueue);
  indexMgrBtnScan.addEventListener('click', indexMgrStartScan);
  indexMgrDirInput.addEventListener('keydown', e => { if (e.key === 'Enter') indexMgrAddToQueue(); });
  initIndexMgrResize();
  // 模型路径浏览按钮
  btnBrowseClipModel.addEventListener('click', browseClipModel);
  btnBrowseOcrModel.addEventListener('click', browseOcrModel);
});

// ══════════════════════════════════════════════════════════════════
//  打开 / 关闭设置面板
// ══════════════════════════════════════════════════════════════════
async function openSettings() {
  // 无论加载成功与否都打开面板，避免后端无响应时设置打不开
  settingsOverlay.style.display = '';
  settingsPanel.classList.add('open');
  loadSettings();  // 异步加载，不阻塞面板显示
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
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000); // 5秒超时
    const res = await fetch(`${API}/api/settings`, { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) return;
    currentSettings = await res.json();
    await applySettingsToUI(currentSettings);
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.warn('加载设置失败:', e);
    }
  }
}

async function applySettingsToUI(s) {
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

  // 设备选择 - 先获取实际设备状态，如果设置与实际不符则修正显示
  const savedDevice = s.device || 'cpu';

  try {
    const res = await fetch(`${API}/api/settings/device-status`).catch(() => null);
    if (res && res.ok) {
      const status = await res.json();
      const actualDevice = status.actual_device;
      // 如果设置是 GPU 但实际是 CPU（CUDA 不可用），下拉框显示实际设备
      if (savedDevice === 'cuda' && actualDevice === 'cpu') {
        deviceSelect.value = 'cpu';
        deviceHint.textContent = 'CUDA 不可用，已自动切换为 CPU';
        deviceHint.style.color = '#ef4444';
      } else {
        deviceSelect.value = savedDevice;
      }
      updateDeviceStatusUI(savedDevice, actualDevice);
    } else {
      deviceSelect.value = savedDevice;
      updateDeviceHint(savedDevice);
    }
  } catch (e) {
    deviceSelect.value = savedDevice;
    updateDeviceHint(savedDevice);
  }

  // 模型路径
  await loadModelPaths(s);
}

async function loadModelPaths(s) {
  try {
    const res = await fetch(`${API}/api/settings/model-paths`).catch(() => null);
    if (!res || !res.ok) return;
    const data = await res.json();

    // CLIP 模型
    const clipCustom = s.clip_model_path || '';
    clipModelPath.value = clipCustom;
    if (clipCustom) {
      clipModelHint.textContent = `当前: ${clipCustom}`;
    } else {
      clipModelHint.textContent = `默认: ${data.clip.default}`;
    }
    if (data.clip.exists) {
      clipModelStatus.textContent = '✓ 已就绪';
      clipModelStatus.style.color = '#4ade80';
    } else {
      clipModelStatus.textContent = '⚠ 缺失';
      clipModelStatus.style.color = '#fbbf24';
    }

    // OCR 模型
    const ocrCustom = s.ocr_model_path || '';
    ocrModelPath.value = ocrCustom;
    if (ocrCustom) {
      ocrModelHint.textContent = `当前: ${ocrCustom}`;
    } else {
      ocrModelHint.textContent = `默认: ${data.ocr.default}`;
    }
    if (data.ocr.exists) {
      ocrModelStatus.textContent = '✓ 已就绪';
      ocrModelStatus.style.color = '#4ade80';
    } else {
      ocrModelStatus.textContent = '⚠ 缺失';
      ocrModelStatus.style.color = '#fbbf24';
    }
  } catch (e) {
    console.warn('加载模型路径失败:', e);
  }
}

// ══════════════════════════════════════════════════════════════════
//  保存设置
// ══════════════════════════════════════════════════════════════════
async function saveSettings() {
  const dirs = getDisplayedDirs();
  const alpha = parseInt(alphaSlider.value) / 100;
  const device = deviceSelect.value;
  const clipPath = clipModelPath.value.trim() || null;
  const ocrPath = ocrModelPath.value.trim() || null;

  const settings = {
    scan_directories: dirs,
    full_disk_scan:   chkFullDisk.checked,
    alpha:            alpha,
    top_n:            30,
    ocr_enabled:      chkOcr.checked,
    auto_index_on_start: false,
    exclude_dirs:     [],
    device:           device,
    clip_model_path:  clipPath,
    ocr_model_path:   ocrPath,
  };

  try {
    const res = await fetch(`${API}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!res.ok) {
      _settingsToast(`保存失败 (HTTP ${res.status})`, 'error');
      return;
    }
    const data = await res.json();
    if (data.ok) {
      // 显示设备切换和模型加载结果
      if (data.message) {
        // 如果消息包含换行，分行显示
        const messages = data.message.split('\n');
        if (messages.length > 1) {
          messages.forEach(msg => {
            if (msg.trim()) _settingsToast(msg.trim(), 'success');
          });
        } else {
          _settingsToast(data.message, 'success');
        }
        // 更新 UI 显示实际使用的设备
        if (data.message.includes('设备')) {
          updateDeviceStatusFromMessage(data.message);
        }
      } else {
        _settingsToast('保存成功！', 'success');
      }
      currentSettings = settings;
      closeSettings();

      // ── 检测是否有目录尚未建立索引，若有则自动触发扫描 ──
      await autoIndexUnindexedDirs(dirs);

    } else {
      _settingsToast(data.message || '保存失败', 'error');
    }
  } catch (e) {
    console.error('saveSettings 失败:', e);
    _settingsToast('保存失败：' + e.message, 'error');
  }
}

// 浏览 CLIP 模型路径
async function browseClipModel() {
  try {
    const res = await fetch(`${API}/api/settings/model-paths/browse-clip`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.ok && data.path) {
      clipModelPath.value = data.path;
      clipModelHint.textContent = `当前: ${data.path}`;
      // 检查模型是否存在
      const statusRes = await fetch(`${API}/api/settings/model-paths`);
      const statusData = await statusRes.json();
      if (statusData.clip && statusData.clip.exists) {
        clipModelStatus.textContent = '✓ 已就绪';
        clipModelStatus.style.color = '#4ade80';
      } else {
        clipModelStatus.textContent = '⚠ 缺失';
        clipModelStatus.style.color = '#fbbf24';
      }
    }
  } catch (e) {
    _settingsToast('无法打开目录选择', 'error');
  }
}

// 浏览 OCR 模型路径
async function browseOcrModel() {
  try {
    const res = await fetch(`${API}/api/settings/model-paths/browse-ocr`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.ok && data.path) {
      ocrModelPath.value = data.path;
      ocrModelHint.textContent = `当前: ${data.path}`;
      // 检查模型是否存在
      const statusRes = await fetch(`${API}/api/settings/model-paths`);
      const statusData = await statusRes.json();
      if (statusData.ocr && statusData.ocr.exists) {
        ocrModelStatus.textContent = '✓ 已就绪';
        ocrModelStatus.style.color = '#4ade80';
      } else {
        ocrModelStatus.textContent = '⚠ 缺失';
        ocrModelStatus.style.color = '#fbbf24';
      }
    }
  } catch (e) {
    _settingsToast('无法打开目录选择', 'error');
  }
}

/**
 * 检查 dirs 中哪些目录还没有索引，若有则自动启动索引扫描
 * 并在主界面展示索引进行中遮罩，完成后隐藏并刷新搜索目录
 *
 * 注意：indexed-dirs 返回的是图片文件的父目录，可能比配置扫描根目录更深。
 * 因此判断"是否已索引"需用路径前缀包含：配置目录下任意子目录有索引即视为已索引。
 *
 * 需求2：若目录已在索引管理中有索引 → 显示主界面遮罩轮询进度即可（不重启扫描）
 *        若目录尚未索引 → 启动新的增量扫描并显示遮罩
 */
async function autoIndexUnindexedDirs(dirs) {
  if (!dirs || !dirs.length) {
    _refreshDirFilter();
    return;
  }

  try {
    // 获取当前已索引目录列表（每个图片文件所在父目录）
    const res = await fetch(`${API}/api/index/indexed-dirs`).catch(() => null);
    // indexedPrefixes: 所有已索引目录的小写路径，带尾部分隔符以防前缀误判
    const indexedPrefixes = [];
    if (res && res.ok) {
      const data = await res.json();
      (data.directories || []).forEach(d => {
        const p = d.directory.toLowerCase().replace(/\\/g, '/');
        indexedPrefixes.push(p.endsWith('/') ? p : p + '/');
      });
    }

    /**
     * 判断某个配置目录是否"已有索引"：
     * 条件：indexedPrefixes 中存在某项以该目录路径为前缀
     * 即 indexedDir.startsWith(configDir/) ← 说明 configDir 下有已索引的子目录
     */
    function _isIndexed(configDir) {
      const normalized = configDir.toLowerCase().replace(/\\/g, '/');
      const prefix = normalized.endsWith('/') ? normalized : normalized + '/';
      // 已索引目录以 configDir 开头 → configDir 下有索引
      return indexedPrefixes.some(p => p.startsWith(prefix) || p === prefix);
    }

    // 分类：已有索引 vs 尚未索引
    const alreadyIndexed = dirs.filter(d => _isIndexed(d));
    const unindexed = dirs.filter(d => !_isIndexed(d));

    if (!unindexed.length && !alreadyIndexed.length) {
      // 无任何目录，直接刷新
      _refreshDirFilter();
      return;
    }

    if (!unindexed.length) {
      // 所有目录已有索引，无需扫描，直接刷新筛选器
      _refreshDirFilter();
      return;
    }

    // 有未索引目录 → 启动扫描
    const startRes = await fetch(`${API}/api/index/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directories: unindexed, full_rebuild: false }),
    }).catch(() => null);

    if (!startRes || !startRes.ok) {
      _refreshDirFilter();
      return;
    }
    const startData = await startRes.json();
    if (!startData.ok) {
      // 已有扫描在运行或无需更新，直接刷新
      _refreshDirFilter();
      return;
    }

    // 成功启动 → 显示搜索遮罩，轮询进度
    const label = unindexed.length === 1 ? unindexed[0] : `${unindexed.length} 个目录`;
    showIndexingBlock(label);

  } catch (e) {
    console.error('autoIndexUnindexedDirs 失败:', e);
    _refreshDirFilter();
  }
}

function _refreshDirFilter() {
  if (typeof indexedDirs !== 'undefined') indexedDirs = [];
  if (typeof loadIndexedDirsSilent === 'function') loadIndexedDirsSilent();
}

// ══════════════════════════════════════════════════════════════════
//  设备选择
// ══════════════════════════════════════════════════════════════════
function onDeviceChange() {
  const device = deviceSelect.value;
  updateDeviceHint(device);
}

function updateDeviceHint(device) {
  const hints = {
    cpu: '使用 CPU 推理，兼容性最好，但速度较慢',
    cuda: '使用 NVIDIA GPU 加速，速度显著提升（需要 CUDA 驱动）',
    auto: '自动检测：有 NVIDIA 显卡则使用 GPU，否则使用 CPU'
  };
  deviceHint.textContent = hints[device] || hints.cpu;
  
  // 显示当前实际使用的设备状态
  updateDeviceStatusUI(device);
}

function updateDeviceStatusUI(device, actualDevice) {
  /**
   * 更新设备状态显示
   * @param device: 用户选择的设备 (cpu/cuda/auto)
   * @param actualDevice: 实际使用的设备 (可选，用于 auto 模式显示)
   */
  if (device === 'cuda') {
    deviceStatus.textContent = '⚡ GPU 模式';
    deviceStatus.style.color = '#4ade80';
  } else if (device === 'auto') {
    if (actualDevice === 'cuda') {
      deviceStatus.textContent = '🔄 自动 → GPU';
      deviceStatus.style.color = '#4ade80';
    } else {
      deviceStatus.textContent = '🔄 自动 → CPU';
      deviceStatus.style.color = '#fbbf24';
    }
  } else {
    deviceStatus.textContent = '💻 CPU 模式';
    deviceStatus.style.color = '#94a3b8';
  }
}

function updateDeviceStatusFromMessage(message) {
  /**
   * 从后端返回的消息中解析实际设备并更新 UI
   * 消息格式: "设置已保存！设备已切换为 CPU/GPU（自动检测）"
   */
  const device = deviceSelect.value;
  
  if (message.includes('自动检测')) {
    // auto 模式，解析实际使用的设备
    const actualDevice = message.includes('GPU') || message.includes('CUDA') ? 'cuda' : 'cpu';
    updateDeviceStatusUI(device, actualDevice);
  } else if (message.includes('失败') || message.includes('不可用')) {
    // 切换失败，将下拉框改回 CPU 并显示 CPU 模式
    // 直接修改 value 并强制刷新 UI
    deviceSelect.value = 'cpu';
    // 强制刷新 select 的显示（WebView2 兼容）
    const selectedOption = deviceSelect.querySelector('option[value="cpu"]');
    if (selectedOption) {
      selectedOption.selected = true;
    }
    // 触发 blur 再 focus 强制重绘
    deviceSelect.blur();
    
    updateDeviceStatusUI('cpu', 'cpu');
    deviceHint.textContent = 'CUDA 不可用，已自动切换为 CPU';
    deviceHint.style.color = '#ef4444';
  } else {
    // 普通切换成功
    updateDeviceStatusUI(device);
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
      if (!res.ok) { _settingsToast('无法打开目录选择', 'error'); return; }
      const data = await res.json();
      if (data.error) { _settingsToast(data.error, 'error'); return; }
      path = (data.path || '').trim();
      if (!path) return; // 用户取消了选择
      dirInput.value = path;
    } catch {
      _settingsToast('无法连接到后端服务', 'error');
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
      _settingsToast('目录已添加', 'success');
    } else {
      _settingsToast(data.message || '目录添加失败', 'error');
    }
  } catch {
    _settingsToast('无法连接到后端服务', 'error');
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
  // 重置输入和队列
  indexMgrDirInput.value = '';
  _indexMgrQueue = [];
  _renderIndexMgrQueue();
  indexMgrProgFill.style.width = '0%';
  indexMgrProgTxt.textContent = '0%';
  indexMgrProgStatus.textContent = '准备中…';
  indexMgrScanProg.style.display = 'none';
  indexMgrBtnScan.disabled = false;
  indexMgrModal.style.display = '';
  loadIndexMgrDirs();

  // 检查后端是否正在索引，是则恢复进度显示
  _resumeIndexMgrProgressIfNeeded();
}

function closeIndexMgrModal() {
  // 不停止轮询（后台索引仍在继续），只隐藏弹窗
  // 轮询在完成/停止/出错时自动停止
  indexMgrModal.style.display = 'none';
}

/** 打开弹窗时，若后端正在索引则恢复进度轮询 */
async function _resumeIndexMgrProgressIfNeeded() {
  try {
    const res = await fetch(`${API}/api/index/progress`);
    if (!res.ok) return;
    const data = await res.json();
    const status = data.status || 'idle';
    const activeStatuses = ['scanning', 'indexing', 'saving'];

    if (activeStatuses.includes(status)) {
      // 正在索引 → 显示进度条并恢复轮询
      const dirs = data.indexing_directories || [];
      _indexMgrScanLabel = dirs.length === 1 ? dirs[0].split(/[\\/]/).pop() : `${dirs.length} 个目录`;
      indexMgrScanProg.style.display = '';
      indexMgrBtnScan.disabled = true;
      // 立即更新一次进度
      indexMgrProgFill.style.width = `${data.progress_pct || 0}%`;
      indexMgrProgTxt.textContent = `${Math.round(data.progress_pct || 0)}%`;
      const statusLabels = {
        scanning: '扫描文件中…',
        indexing: `索引中 ${data.processed_files || 0}/${data.total_files || 0}`,
        saving:   '保存索引…',
      };
      indexMgrProgStatus.textContent = statusLabels[status] || status;
      startIndexMgrProgressPoll();
    }
  } catch { /* 静默忽略 */ }
}

// ── 队列管理 ─────────────────────────────────────────────────────

/** 渲染队列列表 UI */
function _renderIndexMgrQueue() {
  if (!_indexMgrQueue.length) {
    indexMgrQueueList.style.display = 'none';
    indexMgrQueueFooter.style.display = 'none';
    return;
  }
  indexMgrQueueList.style.display = '';
  indexMgrQueueFooter.style.display = '';
  indexMgrQueueList.innerHTML = '';
  _indexMgrQueue.forEach((dir, idx) => {
    const item = document.createElement('div');
    item.className = 'index-mgr-queue-item';
    item.innerHTML = `
      <svg class="qi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <span class="qi-path" title="${escapeHtml(dir)}">${escapeHtml(dir)}</span>
      <button class="qi-remove" data-idx="${idx}" title="移除">✕</button>
    `;
    item.querySelector('.qi-remove').addEventListener('click', function() {
      const i = parseInt(this.getAttribute('data-idx'));
      _indexMgrQueue.splice(i, 1);
      _renderIndexMgrQueue();
    });
    indexMgrQueueList.appendChild(item);
  });
}

/** 添加路径到队列 */
async function indexMgrAddToQueue() {
  let path = indexMgrDirInput.value.trim();
  if (!path) {
    // 输入框为空时调用目录选择
    try {
      const res = await fetch(`${API}/api/files/pick-folder`);
      if (!res.ok) { _settingsToast('无法打开目录选择', 'error'); return; }
      const data = await res.json();
      if (data.error) { _settingsToast(data.error, 'error'); return; }
      path = (data.path || '').trim();
      if (!path) return;
      indexMgrDirInput.value = path;
    } catch {
      _settingsToast('无法连接到后端服务', 'error');
      return;
    }
  }
  // 去重
  if (_indexMgrQueue.includes(path)) {
    _settingsToast('该路径已在队列中', 'info');
    return;
  }
  _indexMgrQueue.push(path);
  indexMgrDirInput.value = '';
  _renderIndexMgrQueue();
  _settingsToast(`已添加到队列：${path.split(/[\\/]/).pop()}`, 'success');
}

// 浏览文件夹（在索引管理弹窗内）
async function indexMgrBrowseFolder() {
  try {
    const res = await fetch(`${API}/api/files/pick-folder`);
    if (!res.ok) { _settingsToast('无法打开目录选择', 'error'); return; }
    const data = await res.json();
    if (data.error) { _settingsToast(data.error, 'error'); return; }
    const path = (data.path || '').trim();
    if (path) indexMgrDirInput.value = path;
  } catch {
    _settingsToast('无法连接到后端服务', 'error');
  }
}

// 开始增量索引（处理队列中的所有目录）
async function indexMgrStartScan() {
  // 如果队列为空但输入框有内容，先加入队列
  if (!_indexMgrQueue.length) {
    const path = indexMgrDirInput.value.trim();
    if (path) {
      _indexMgrQueue.push(path);
      _renderIndexMgrQueue();
    } else {
      _settingsToast('请先添加需要索引的文件夹路径', 'info');
      indexMgrDirInput.focus();
      return;
    }
  }

  const dirs = [..._indexMgrQueue];

  // 禁用按钮，防止重复提交
  indexMgrBtnScan.disabled = true;

  try {
    const r = await fetch(`${API}/api/index/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directories: dirs, full_rebuild: false }),
    });
    const result = await r.json();
    if (!result.ok) {
      _settingsToast(result.message || '启动索引失败', 'error');
      indexMgrBtnScan.disabled = false;
      return;
    }

    // 显示进度条并开始轮询
    indexMgrScanProg.style.display = '';
    const label = dirs.length === 1 ? dirs[0].split(/[\\/]/).pop() : `${dirs.length} 个目录`;
    _indexMgrScanLabel = label;
    _settingsToast(`正在为「${label}」建立索引…`, 'success');
    startIndexMgrProgressPoll();
    _bindImgrStopBtn();
  } catch {
    _settingsToast('启动索引失败，请检查后端服务', 'error');
    indexMgrBtnScan.disabled = false;
  }
}

// 索引管理弹窗内进度轮询
function startIndexMgrProgressPoll() {
  if (_indexMgrScanTimer) clearInterval(_indexMgrScanTimer);
  _bindImgrStopBtn();
  _indexMgrScanTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API}/api/index/progress`);
      if (!res.ok) return;
      const data = await res.json();
      const pct = data.progress_pct || 0;
      const status = data.status || 'idle';

      indexMgrProgFill.style.width = `${pct}%`;
      indexMgrProgTxt.textContent = `${Math.round(pct)}%`;

      const statusLabels = {
        scanning: '扫描文件中…',
        indexing: `索引中 ${data.processed_files || 0}/${data.total_files || 0}`,
        saving:   '保存索引…',
        completed:'索引完成 ✓',
        error:    `错误: ${data.error_msg || '未知'}`,
        idle:     '就绪',
      };
      indexMgrProgStatus.textContent = statusLabels[status] || status;

      // 隐藏停止按钮（完成/停止/出错时）
      const stopBtn = document.getElementById('imsp-stop-btn');
      if (stopBtn && (status === 'completed' || status === 'error' || status === 'idle')) {
        stopBtn.style.display = 'none';
      }

      // 完成或出错时停止轮询，恢复按钮
      if (status === 'completed' || status === 'error' || status === 'idle') {
        clearInterval(_indexMgrScanTimer);
        _indexMgrScanTimer = null;
        indexMgrBtnScan.disabled = false;

        if (status === 'completed' && _indexMgrScanLabel) {
          _settingsToast(`「${_indexMgrScanLabel}」索引完成`, 'success');
        } else if (status === 'idle') {
          _settingsToast(`「${_indexMgrScanLabel}」索引已停止`, 'info');
        }

        // 刷新已索引目录列表
        setTimeout(() => {
          loadIndexMgrDirs();
          // 同步主界面的目录筛选器
          if (typeof indexedDirs !== 'undefined') indexedDirs = [];
          if (typeof loadIndexedDirsSilent === 'function') loadIndexedDirsSilent();
        }, 800);
      }
    } catch { /* 静默忽略 */ }
  }, 1000);
}

/** 绑定索引管理弹窗停止按钮事件 */
function _bindImgrStopBtn() {
  const stopBtn = document.getElementById('imsp-stop-btn');
  if (!stopBtn) return;
  stopBtn.style.display = '';
  const newBtn = stopBtn.cloneNode(true);
  stopBtn.parentNode.replaceChild(newBtn, stopBtn);
  newBtn.addEventListener('click', async () => {
    try {
      await fetch(`${API}/api/index/stop`, { method: 'POST' });
      newBtn.style.display = 'none';
      indexMgrProgStatus.textContent = '正在停止索引…';
    } catch { /* 静默忽略 */ }
  });
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
      const total = d.total_images != null ? d.total_images : null;
      const indexed = d.count || 0;
      const hasNew = total !== null && total > indexed;
      const newCount = hasNew ? total - indexed : 0;
      const countLabel = total !== null
        ? `<span class="purge-dir-count">${indexed}/${total} 张图片</span>`
        : `<span class="purge-dir-count">${indexed} 张图片</span>`;
      const newTip = hasNew
        ? `<span class="index-mgr-new-tip" title="有 ${newCount} 张新图片未索引，点击可增量索引">${newCount} 张新图片 ↻</span>`
        : '';
      const item = document.createElement('div');
      item.className = 'purge-dir-item' + (hasNew ? ' has-new-images' : '');
      item.innerHTML = `
        <div class="purge-dir-info">
          <span class="purge-dir-path" title="${escapeHtml(d.directory)}">${escapeHtml(d.directory)}</span>
          ${countLabel}
          ${newTip}
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

      // 增量索引（将该目录加入队列并立即开始）
      item.querySelector('.index-mgr-btn-incremental').addEventListener('click', async function() {
        const dir = this.getAttribute('data-dir');
        // 加入队列（去重）
        if (!_indexMgrQueue.includes(dir)) {
          _indexMgrQueue.push(dir);
          _renderIndexMgrQueue();
        }
        // 滚动到顶部让用户看到队列
        indexMgrQueueList.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        _settingsToast(`已添加到队列：${dir.split(/[\\/]/).pop()}`, 'success');
      });

      // 双击路径打开文件夹
      item.querySelector('.purge-dir-path').addEventListener('dblclick', async function() {
        const dir = this.getAttribute('title');
        if (!dir) return;
        try {
          await fetch(`${API}/api/files/open-folder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: dir }),
          });
        } catch { /* 静默忽略 */ }
      });

      // 点击"新图片"提示直接加入队列
      const newTipEl = item.querySelector('.index-mgr-new-tip');
      if (newTipEl) {
        newTipEl.addEventListener('click', function() {
          const dir = d.directory;
          if (!_indexMgrQueue.includes(dir)) {
            _indexMgrQueue.push(dir);
            _renderIndexMgrQueue();
          }
          // 隐藏提示
          this.style.display = 'none';
          item.classList.remove('has-new-images');
          indexMgrQueueList.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          _settingsToast(`已添加到队列：${dir.split(/[\\/]/).pop()}`, 'success');
        });
      }

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
          _settingsToast(result.message, result.ok ? 'success' : 'info');
          closeIndexMgrModal();
        } catch {
          _settingsToast('启动重建失败', 'error');
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
          _settingsToast(result.message, result.ok ? 'success' : 'info');
          setTimeout(() => loadPurgeDirs(), 500);
        } catch {
          _settingsToast('清理失败', 'error');
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
// settings.js 内部 toast 辅助（避免与 app.js 全局 showToast 冲突）
function _settingsToast(msg, type='info') {
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
