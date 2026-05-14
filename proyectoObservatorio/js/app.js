/* ═══════════════════════════════════════════════════════════════
   OBSERVATORIO DE INVESTIGACIÓN · UNAL BOGOTÁ
   app.js — Lógica principal
═══════════════════════════════════════════════════════════════ */

// ─── ESTADO GLOBAL ───────────────────────────────────────────
let allProjects    = [];
let allCategories  = {};
let filters        = { search: '', dept: '', group: '', macro: '', sub: '', year: '', estado: '', protection: '' };
let viewMode       = 'grid'; // 'grid' | 'table' | 'charts'
let apiAvailable   = false;
let importFile     = null;

// ─── PALETA DE COLORES POR MACROCATEGORÍA ────────────────────
const CAT_COLORS = {
  'M00': '#66728B', 'M01': '#162A63', 'M02': '#11897D',
  'M03': '#0F8C80', 'M04': '#B1C92E', 'M05': '#334368',
  'M06': '#16776F', 'M07': '#8FA329', 'M08': '#243B78',
  'M09': '#1F9D90', 'M10': '#6E7F22'
};

// ─── ARRANQUE ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadData();
  initFilters();
  initEventListeners();
  renderAll();
});

// ─── CARGA DE DATOS ───────────────────────────────────────────
async function loadData() {
  try {
    let [projRes, catRes] = await Promise.all([
      fetch('/api/projects'),
      fetch('/api/categories')
    ]);

    apiAvailable = projRes.ok && catRes.ok;

    if (!apiAvailable) {
      [projRes, catRes] = await Promise.all([
        fetch('data/dashboard/proyectos_from_db.json'),
        fetch('data/dashboard/categorias.json')
      ]);
    }

    allProjects   = await projRes.json();
    allCategories = await catRes.json();

    // Respaldo para cuando el dashboard se abre sin backend.
    if (!apiAvailable) {
      const localProjects = getSavedProjects();
      // Evitar duplicados por id
      const existingIds = new Set(allProjects.map(p => p.id));
      localProjects.forEach(p => {
        if (!existingIds.has(p.id)) allProjects.push(p);
      });
    }
  } catch (e) {
    console.error('Error cargando datos:', e);
    showToast('Error al cargar la base de datos.');
  }
}

// ─── INICIALIZACIÓN DE FILTROS ────────────────────────────────
function initFilters() {
  const depts  = [...new Set(allProjects.map(p => p.departamento).filter(Boolean))].sort();
  const groups = getResearchGroups();
  const years  = [...new Set(allProjects.map(p => p.año_inicio).filter(Boolean))].sort((a,b) => b - a);
  const states = getProjectStates();
  const protectionValues = getProtectionValues();
  const macros = allCategories.macrocategorias || [];

  resetSelect('filterDept', 'Todos');
  resetSelect('filterGroup', 'Todos');
  resetSelect('filterYear', 'Todos');
  resetSelect('filterMacro', 'Todas');
  resetSelect('filterProtection', 'Todos');
  resetSelect('filterEstado', 'Todos');
  resetSelect('f_departamento', 'Seleccionar…');
  resetSelect('f_estado', 'Seleccionar…');
  resetSelect('f_macro', 'Seleccionar…');
  document.getElementById('filterSub').innerHTML = '<option value="">Todas</option>';
  document.getElementById('f_sub').innerHTML = '<option value="">Seleccionar macrocategoría primero…</option>';

  populateSelect('filterDept',  depts,  d => ({ value: d, label: d }));
  populateSelect('filterGroup', groups, g => ({ value: g, label: g }));
  populateSelect('filterYear',  years,  y => ({ value: y, label: y }));
  populateSelect('filterMacro', macros, m => ({ value: m.id, label: `${m.id} — ${m.nombre}` }));
  populateSelect('filterProtection', protectionValues, value => ({ value, label: value }));
  populateSelect('filterEstado', states, s => ({ value: s, label: s }));

  // Selects del formulario
  populateSelect('f_departamento', allCategories.departamentos || depts, d => ({ value: d, label: d }));
  populateSelect('f_estado', states, s => ({ value: s, label: s }));
  populateMacroSelect('f_macro', macros);
}

function resetSelect(id, placeholder) {
  const sel = document.getElementById(id);
  if (!sel) return;
  sel.innerHTML = `<option value="">${placeholder}</option>`;
}

function getProjectStates() {
  const states = [...new Set(allProjects.map(p => p.estado).filter(Boolean))].sort();
  const configuredStates = allCategories.estados || [];
  configuredStates.forEach(state => {
    if (state && !states.includes(state)) states.push(state);
  });
  return states;
}

function getResearchGroups() {
  return [...new Set(
    allProjects
      .map(p => p.grupo_de_investigacion)
      .filter(Boolean)
  )].sort();
}

function getProtectionValues() {
  return [...new Set(
    allProjects
      .map(p => p.proteccion_producto)
      .filter(Boolean)
  )].sort();
}

function populateSelect(id, items, mapper) {
  const sel = document.getElementById(id);
  if (!sel) return;
  items.forEach(item => {
    const { value, label } = mapper(item);
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = label;
    sel.appendChild(opt);
  });
}

function populateMacroSelect(id, macros) {
  const sel = document.getElementById(id);
  if (!sel) return;
  macros.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = `${m.id} — ${m.nombre}`;
    sel.appendChild(opt);
  });
}

// ─── LISTENERS ────────────────────────────────────────────────
function initEventListeners() {
  // Filtros
  document.getElementById('searchInput').addEventListener('input', e => {
    filters.search = e.target.value.toLowerCase();
    renderAll();
  });

  document.getElementById('filterDept').addEventListener('change', e => {
    filters.dept = e.target.value;
    renderAll();
  });

  document.getElementById('filterGroup').addEventListener('change', e => {
    filters.group = e.target.value;
    renderAll();
  });

  document.getElementById('filterMacro').addEventListener('change', e => {
    filters.macro = e.target.value;
    filters.sub   = '';
    updateSubcatFilter(e.target.value);
    document.getElementById('filterSub').value = '';
    renderAll();
  });

  document.getElementById('filterSub').addEventListener('change', e => {
    filters.sub = e.target.value;
    renderAll();
  });

  document.getElementById('filterYear').addEventListener('change', e => {
    filters.year = e.target.value ? parseInt(e.target.value) : '';
    renderAll();
  });

  document.getElementById('filterProtection').addEventListener('change', e => {
    filters.protection = e.target.value;
    renderAll();
  });

  document.getElementById('filterEstado').addEventListener('change', e => {
    filters.estado = e.target.value;
    renderAll();
  });

  document.getElementById('btnClearFilters').addEventListener('click', clearFilters);

  // Vista
  document.getElementById('btnGrid').addEventListener('click', () => setView('grid'));
  document.getElementById('btnTable').addEventListener('click', () => setView('table'));
  document.getElementById('btnCharts').addEventListener('click', () => setView('charts'));

  // Modal detalle
  document.getElementById('closeDetail').addEventListener('click', closeDetailModal);
  document.getElementById('detailModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeDetailModal();
  });

  // Modal agregar
  document.getElementById('btnOpenModal').addEventListener('click', openAddModal);
  document.getElementById('closeAdd').addEventListener('click', closeAddModal);
  document.getElementById('cancelAdd').addEventListener('click', closeAddModal);
  document.getElementById('addModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeAddModal();
  });

  // Macrocategoría en formulario → actualizar subcategorías
  document.getElementById('f_macro').addEventListener('change', e => {
    updateFormSubcats(e.target.value);
  });

  // Formulario submit
  document.getElementById('addProjectForm').addEventListener('submit', handleAddProject);

  // Importación Excel
  document.getElementById('btnOpenImport').addEventListener('click', openImportModal);
  document.getElementById('closeImport').addEventListener('click', closeImportModal);
  document.getElementById('cancelImport').addEventListener('click', closeImportModal);
  document.getElementById('btnResetImport').addEventListener('click', resetImportModal);
  document.getElementById('btnPreviewImport').addEventListener('click', previewExcelImport);
  document.getElementById('btnConfirmImport').addEventListener('click', confirmExcelImport);
  document.getElementById('importExcelFile').addEventListener('change', handleImportFileChange);
  document.getElementById('importModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeImportModal();
  });

  // Teclado ESC
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeDetailModal();
      closeAddModal();
      closeImportModal();
    }
  });
}

function updateSubcatFilter(macroId) {
  const sel = document.getElementById('filterSub');
  sel.innerHTML = '<option value="">Todas</option>';
  if (!macroId) return;
  const macro = allCategories.macrocategorias?.find(m => m.id === macroId);
  if (!macro) return;
  macro.subcategorias.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.nombre;
    sel.appendChild(opt);
  });
}

function updateFormSubcats(macroId) {
  const sel = document.getElementById('f_sub');
  sel.innerHTML = '<option value="">Seleccionar…</option>';
  if (!macroId) return;
  const macro = allCategories.macrocategorias?.find(m => m.id === macroId);
  if (!macro) return;
  macro.subcategorias.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.nombre;
    sel.appendChild(opt);
  });
}

// ─── FILTRADO ─────────────────────────────────────────────────
function getFiltered() {
  return allProjects.filter(p => {
    if (filters.search) {
      const haystack = [
        p.nombre, p.objetivo, p.departamento,
        p.grupo_de_investigacion, p.macrocategoria, p.subcategoria,
        ...(p.palabras_clave || [])
      ].join(' ').toLowerCase();
      if (!haystack.includes(filters.search)) return false;
    }
    if (filters.dept   && p.departamento       !== filters.dept)               return false;
    if (filters.group  && p.grupo_de_investigacion !== filters.group)          return false;
    if (filters.macro  && p.macrocategoria_id  !== filters.macro)              return false;
    if (filters.sub    && p.subcategoria_id    !== filters.sub)                return false;
    if (filters.year   && p.año_inicio         !== filters.year)               return false;
    if (filters.estado && p.estado             !== filters.estado)             return false;
    if (filters.protection && p.proteccion_producto !== filters.protection)     return false;
    return true;
  });
}

// ─── RENDER PRINCIPAL ─────────────────────────────────────────
function renderAll() {
  const filtered = getFiltered();
  updateStats(filtered);
  document.getElementById('resultsCount').textContent = filtered.length;

  if (viewMode === 'grid') renderGrid(filtered);
  else if (viewMode === 'table') renderTable(filtered);
  else renderCharts(filtered);

  const empty = document.getElementById('emptyState');
  if (filtered.length === 0) empty.classList.remove('hidden');
  else empty.classList.add('hidden');
}

function updateStats(filtered) {
  const total   = allProjects.length;
  const active  = allProjects.filter(p => p.estado === 'En ejecución').length;
  const depts   = new Set(allProjects.map(p => p.departamento)).size;
  const cats    = new Set(allProjects.map(p => p.macrocategoria_id)).size;

  animateNumber('statTotal',  total);
  animateNumber('statActive', active);
  animateNumber('statDepts',  depts);
  animateNumber('statCats',   cats);
}

function animateNumber(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const current = parseInt(el.textContent) || 0;
  const diff = target - current;
  if (diff === 0) return;
  const steps = 20;
  let step = 0;
  const interval = setInterval(() => {
    step++;
    const progress = step / steps;
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(current + diff * ease);
    if (step >= steps) { el.textContent = target; clearInterval(interval); }
  }, 16);
}

// ─── GRID ─────────────────────────────────────────────────────
function renderGrid(projects) {
  const grid = document.getElementById('projectsGrid');
  grid.innerHTML = '';
  grid.classList.remove('hidden');
  document.getElementById('projectsTableWrap').classList.add('hidden');
  document.getElementById('chartsView').classList.add('hidden');

  projects.forEach((p, i) => {
    const color = CAT_COLORS[p.macrocategoria_id] || '#11897D';
    const card  = document.createElement('div');
    card.className = 'project-card';
    card.style.cssText = `--card-accent:${color}; animation-delay:${Math.min(i * 30, 200)}ms`;

    card.innerHTML = `
      <div class="card-top">
        <span class="card-code">HERMES ${p.codigo_hermes || '—'}</span>
        <span class="card-estado ${estadoClass(p.estado)}">${p.estado}</span>
      </div>
      <p class="card-name">${p.nombre}</p>
      <p class="card-dept">${p.departamento}</p>
      <p class="card-group">${p.grupo_de_investigacion || 'Sin grupo registrado'}</p>
      <div class="card-tags">
        <span class="card-tag tag-cat">${p.macrocategoria_id} · ${shortCat(p.macrocategoria)}</span>
        ${(p.palabras_clave || []).slice(0,2).map(k => `<span class="card-tag">${k}</span>`).join('')}
      </div>
      <div class="card-footer">
        <span class="card-year">${p.año_inicio}${p.año_fin ? ' — ' + p.año_fin : ''}</span>
        <span class="card-arrow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
        </span>
      </div>
    `;

    card.addEventListener('click', () => openDetailModal(p));
    grid.appendChild(card);
  });
}

// ─── TABLE ────────────────────────────────────────────────────
function renderTable(projects) {
  document.getElementById('projectsGrid').classList.add('hidden');
  document.getElementById('chartsView').classList.add('hidden');
  const wrap = document.getElementById('projectsTableWrap');
  wrap.classList.remove('hidden');

  const tbody = document.getElementById('projectsTableBody');
  tbody.innerHTML = '';

  projects.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="td-code">HERMES ${p.codigo_hermes || '—'}</td>
      <td class="td-name" title="${p.nombre}">${p.nombre}</td>
      <td class="td-dept" title="${p.departamento}">${p.departamento}</td>
      <td class="td-group" title="${p.grupo_de_investigacion || '—'}">${p.grupo_de_investigacion || '—'}</td>
      <td class="td-cat" title="${p.macrocategoria}">${p.macrocategoria_id} · ${shortCat(p.macrocategoria)}</td>
      <td class="td-protection" title="${p.proteccion_producto || '—'}">${p.proteccion_producto || '—'}</td>
      <td>${p.año_inicio}</td>
      <td><span class="card-estado ${estadoClass(p.estado)}">${p.estado}</span></td>
    `;
    tr.addEventListener('click', () => openDetailModal(p));
    tbody.appendChild(tr);
  });
}

// ─── CHARTS ───────────────────────────────────────────────────
function renderCharts(projects) {
  document.getElementById('projectsGrid').classList.add('hidden');
  document.getElementById('projectsTableWrap').classList.add('hidden');
  document.getElementById('chartsView').classList.remove('hidden');

  document.getElementById('chartDeptTotal').textContent = `${projects.length} proyectos`;
  renderBarChart('chartDepartments', countBy(projects, p => p.departamento || 'Sin departamento'), {
    limit: 8,
    colorFor: (_, index) => chartColor(index)
  });
  renderBarChart('chartYears', countBy(projects, p => p.año_inicio || 'Sin año'), {
    sort: 'key-desc',
    limit: 12,
    colorFor: (_, index) => chartColor(index + 3)
  });
  renderBarChart('chartCategories', countBy(projects, p => `${p.macrocategoria_id || 'M00'} · ${shortCat(p.macrocategoria || 'Sin asignar')}`), {
    limit: 10,
    colorFor: label => CAT_COLORS[label.split(' · ')[0]] || chartColor(0)
  });
  renderPieChart('chartStatus', countBy(projects, p => p.estado || 'Sin estado'), label => statusColor(label));
  renderPieChart('chartProtection', countBy(projects, p => p.proteccion_producto || 'Sin dato'), label => protectionColor(label));
}

function countBy(items, getter) {
  return items.reduce((acc, item) => {
    const key = String(getter(item));
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function sortedEntries(counts, options = {}) {
  const entries = Object.entries(counts);
  if (options.sort === 'key-desc') {
    entries.sort((a, b) => String(b[0]).localeCompare(String(a[0])));
  } else {
    entries.sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
  }
  return entries.slice(0, options.limit || entries.length);
}

function renderBarChart(id, counts, options = {}) {
  const el = document.getElementById(id);
  const entries = sortedEntries(counts, options);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  if (!entries.length) {
    el.innerHTML = '<p class="chart-empty">Sin datos para visualizar.</p>';
    return;
  }

  el.innerHTML = entries.map(([label, value], index) => {
    const width = Math.max((value / max) * 100, 2);
    const color = options.colorFor ? options.colorFor(label, index) : chartColor(index);
    return `
      <div class="bar-row">
        <div class="bar-label" title="${label}">${label}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${width}%;background:${color}"></div>
        </div>
        <div class="bar-value">${value}</div>
      </div>
    `;
  }).join('');
}

function renderPieChart(id, counts, colorFor) {
  const el = document.getElementById(id);
  const entries = sortedEntries(counts);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  if (!entries.length || total === 0) {
    el.innerHTML = '<p class="chart-empty">Sin datos para visualizar.</p>';
    return;
  }

  let start = 0;
  const segments = entries.map(([label, value], index) => {
    const end = start + (value / total) * 100;
    const color = colorFor ? colorFor(label, index) : chartColor(index);
    const segment = `${color} ${start}% ${end}%`;
    start = end;
    return segment;
  }).join(', ');

  const legend = entries.map(([label, value], index) => {
    const color = colorFor ? colorFor(label, index) : chartColor(index);
    const pct = Math.round((value / total) * 100);
    return `
      <div class="pie-legend-row">
        <span class="legend-dot" style="background:${color}"></span>
        <span class="legend-label" title="${label}">${label}</span>
        <strong>${value} · ${pct}%</strong>
      </div>
    `;
  }).join('');

  el.innerHTML = `
    <div class="pie-chart" style="background:conic-gradient(${segments})">
      <span>${total}</span>
    </div>
    <div class="pie-legend">${legend}</div>
  `;
}

// ─── MODAL DETALLE ────────────────────────────────────────────
function openDetailModal(p) {
  const color  = CAT_COLORS[p.macrocategoria_id] || '#11897D';
  const modal  = document.getElementById('detailModal');
  const content = document.getElementById('detailContent');

  const kwHTML = (p.palabras_clave || []).map(k => `<span class="detail-kw">${k}</span>`).join('');
  const proposedProducts = p.productos_propuestos || p.productos_esperados || [];
  const achievedProducts = p.productos_logrados || [];
  const proposedHTML = proposedProducts.map(pr => `<li>${pr}</li>`).join('');
  const achievedHTML = achievedProducts.map(pr => `<li>${pr}</li>`).join('');

  content.innerHTML = `
    <div class="detail-category-bar">
      <span class="detail-cat-badge" style="background:${color}22;color:${color}">
        ${p.macrocategoria_id}
      </span>
      <span style="font-size:13px;color:#666">${p.macrocategoria}</span>
    </div>

    <h2 class="detail-title">${p.nombre}</h2>

    <div class="detail-meta">
      <div class="meta-item">
        <div class="meta-item-label">Código HERMES</div>
        <div class="meta-item-val">${p.codigo_hermes || '—'}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Estado</div>
        <div class="meta-item-val">
          <span class="card-estado ${estadoClass(p.estado)}">${p.estado}</span>
        </div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Departamento / Instituto</div>
        <div class="meta-item-val">${p.departamento}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Grupo de investigación</div>
        <div class="meta-item-val">${p.grupo_de_investigacion || '—'}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Período</div>
        <div class="meta-item-val">${p.año_inicio || '—'}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Subcategoría</div>
        <div class="meta-item-val">${p.subcategoria_id} · ${p.subcategoria}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Es susceptible de protección - producto</div>
        <div class="meta-item-val">${p.proteccion_producto || '—'}</div>
      </div>
    </div>

    ${p.objetivo ? `
    <div class="detail-section">
      <div class="detail-section-label">Objetivo General</div>
      <p class="detail-section-text">${p.objetivo}</p>
    </div>` : ''}

    ${p.ods_principal ? `
    <div class="detail-section">
      <div class="detail-section-label">ODS Principal</div>
      <p class="detail-section-text">${p.ods_principal}</p>
    </div>` : ''}

    ${kwHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Palabras clave</div>
      <div class="detail-keywords">${kwHTML}</div>
    </div>` : ''}

    ${proposedHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Productos propuestos</div>
      <ul class="detail-products-list">${proposedHTML}</ul>
    </div>` : ''}

    ${achievedHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Productos logrados</div>
      <ul class="detail-products-list">${achievedHTML}</ul>
    </div>` : ''}
  `;

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeDetailModal() {
  document.getElementById('detailModal').classList.add('hidden');
  document.body.style.overflow = '';
}

// ─── MODAL AGREGAR ────────────────────────────────────────────
function openAddModal() {
  document.getElementById('addModal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeAddModal() {
  document.getElementById('addModal').classList.add('hidden');
  document.body.style.overflow = '';
  document.getElementById('addProjectForm').reset();
  document.getElementById('f_sub').innerHTML = '<option value="">Seleccionar macrocategoría primero…</option>';
}

async function handleAddProject(e) {
  e.preventDefault();

  const macroId   = document.getElementById('f_macro').value;
  const subId     = document.getElementById('f_sub').value;
  const macroData = allCategories.macrocategorias?.find(m => m.id === macroId);
  const subData   = macroData?.subcategorias?.find(s => s.id === subId);

  const palabrasClave = document.getElementById('f_palabras').value
    .split(',').map(s => s.trim()).filter(Boolean);
  const productosPropuestos = document.getElementById('f_productos_propuestos').value
    .split(',').map(s => s.trim()).filter(Boolean);
  const productosLogrados = document.getElementById('f_productos_logrados').value
    .split(',').map(s => s.trim()).filter(Boolean);

  const newProject = {
    id:               Date.now(),
    codigo_hermes:    document.getElementById('f_codigo').value.trim() || '—',
    nombre:           document.getElementById('f_nombre').value.trim(),
    objetivo:         document.getElementById('f_objetivo').value.trim(),
    departamento:     document.getElementById('f_departamento').value,
    facultad:         document.getElementById('f_facultad').value.trim(),
    grupo_de_investigacion: document.getElementById('f_grupo').value.trim(),
    macrocategoria_id: macroId,
    macrocategoria:   macroData?.nombre || '',
    subcategoria_id:  subId,
    subcategoria:     subData?.nombre || '',
    año_inicio:       parseInt(document.getElementById('f_año_inicio').value),
    año_fin:          parseInt(document.getElementById('f_año_fin').value) || null,
    estado:           document.getElementById('f_estado').value,
    ods_principal:    document.getElementById('f_ods').value.trim(),
    proteccion_producto: '',
    palabras_clave:   palabrasClave,
    productos_propuestos: productosPropuestos,
    productos_logrados: productosLogrados,
    productos_esperados: [...new Set([...productosPropuestos, ...productosLogrados])]
  };

  try {
    const savedProject = apiAvailable ? await createProject(newProject) : newProject;
    allProjects.push(savedProject);
    if (!apiAvailable) saveProject(savedProject);
    closeAddModal();
    renderAll();
    showToast(`✓ Proyecto "${savedProject.nombre.substring(0,40)}${savedProject.nombre.length > 40 ? '…' : ''}" guardado.`);
  } catch (error) {
    console.error('Error guardando proyecto:', error);
    showToast(error.message || 'Error al guardar el proyecto.');
  }
}

async function createProject(project) {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(project)
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'No se pudo guardar el proyecto en la base de datos.');
  }

  return response.json();
}

// ─── IMPORTACIÓN EXCEL ────────────────────────────────────────
function openImportModal() {
  if (!apiAvailable) {
    showToast('La importación requiere ejecutar el backend FastAPI.');
    return;
  }
  resetImportModal();
  document.getElementById('importModal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeImportModal() {
  document.getElementById('importModal').classList.add('hidden');
  document.body.style.overflow = '';
}

function resetImportModal() {
  importFile = null;
  document.getElementById('importExcelFile').value = '';
  document.getElementById('importFileName').textContent = 'Formato permitido: .xlsx o .xls';
  document.getElementById('importSummary').classList.add('hidden');
  document.getElementById('importSummary').innerHTML = '';
  document.getElementById('importConfirmActions').classList.add('hidden');
}

function handleImportFileChange(e) {
  importFile = e.target.files?.[0] || null;
  document.getElementById('importFileName').textContent = importFile
    ? importFile.name
    : 'Formato permitido: .xlsx o .xls';
}

async function previewExcelImport() {
  if (!importFile) {
    showToast('Selecciona primero un archivo Excel.');
    return;
  }

  setImportLoading(true, 'Analizando…');
  try {
    const summary = await sendExcelImport(true);
    renderImportSummary(summary);
    document.getElementById('importConfirmActions').classList.remove('hidden');
  } catch (error) {
    console.error('Error importando Excel:', error);
    showToast(error.message || 'No se pudo analizar el Excel.');
  } finally {
    setImportLoading(false, 'Vista previa');
  }
}

async function confirmExcelImport() {
  if (!importFile) {
    showToast('Selecciona primero un archivo Excel.');
    return;
  }

  setImportLoading(true, 'Actualizando…');
  document.getElementById('btnConfirmImport').disabled = true;
  try {
    const summary = await sendExcelImport(false);
    if (Array.isArray(summary.projects)) {
      allProjects = summary.projects;
    } else {
      await loadData();
    }
    initFilters();
    renderAll();
    renderImportSummary(summary);
    showToast('Base de proyectos actualizada desde Excel.');
  } catch (error) {
    console.error('Error confirmando importación:', error);
    showToast(error.message || 'No se pudo actualizar la base.');
  } finally {
    setImportLoading(false, 'Vista previa');
    document.getElementById('btnConfirmImport').disabled = false;
  }
}

async function sendExcelImport(dryRun) {
  const formData = new FormData();
  formData.append('file', importFile);

  const response = await fetch(`/api/projects/import-excel?dry_run=${dryRun}`, {
    method: 'POST',
    body: formData
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'No se pudo procesar el Excel.');
  }
  return data;
}

function renderImportSummary(summary) {
  const labels = [
    ['archivo_procesado', 'Archivo'],
    ['proyectos_en_excel', 'Proyectos en Excel'],
    ['proyectos_nuevos', 'Proyectos nuevos'],
    ['proyectos_actualizados', 'Proyectos actualizados'],
    ['proyectos_sin_cambios', 'Proyectos sin cambios'],
    ['proyectos_sin_codigo', 'Proyectos sin código'],
    ['proyectos_autoclasificados', 'Pendientes de clasificación'],
    ['clasificaciones_revisadas_conservadas', 'Clasificaciones revisadas conservadas'],
    ['actualiza_productos_propuestos', 'Actualiza productos propuestos'],
    ['actualiza_productos_logrados', 'Actualiza productos logrados'],
    ['actualiza_proteccion_producto', 'Actualiza susceptible de protección'],
    ['dry_run', 'Modo vista previa']
  ];

  const html = labels.map(([key, label]) => `
    <div class="import-summary-row">
      <span>${label}</span>
      <strong>${formatSummaryValue(summary[key])}</strong>
    </div>
  `).join('');

  const errors = (summary.errores || []).map(err => `
    <div class="import-summary-row">
      <span>Error</span>
      <strong>${err}</strong>
    </div>
  `).join('');
  const warnings = (summary.advertencias || []).map(warning => `
    <div class="import-summary-row">
      <span>Advertencia</span>
      <strong>${warning}</strong>
    </div>
  `).join('');

  const box = document.getElementById('importSummary');
  box.innerHTML = html + warnings + errors;
  box.classList.remove('hidden');
}

function formatSummaryValue(value) {
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (value === null || value === undefined || value === '') return '—';
  return value;
}

function setImportLoading(isLoading, label) {
  const btn = document.getElementById('btnPreviewImport');
  btn.disabled = isLoading;
  btn.textContent = label;
}

// ─── PERSISTENCIA LOCAL ───────────────────────────────────────
function getSavedProjects() {
  try {
    return JSON.parse(localStorage.getItem('unal_proyectos_extra') || '[]');
  } catch { return []; }
}

function saveProject(project) {
  const saved = getSavedProjects();
  saved.push(project);
  localStorage.setItem('unal_proyectos_extra', JSON.stringify(saved));
}

// ─── VISTA ────────────────────────────────────────────────────
function setView(mode) {
  viewMode = mode;
  document.getElementById('btnGrid').classList.toggle('active',  mode === 'grid');
  document.getElementById('btnTable').classList.toggle('active', mode === 'table');
  document.getElementById('btnCharts').classList.toggle('active', mode === 'charts');
  renderAll();
}

// ─── LIMPIAR FILTROS ──────────────────────────────────────────
function clearFilters() {
  filters = { search: '', dept: '', group: '', macro: '', sub: '', year: '', estado: '', protection: '' };
  document.getElementById('searchInput').value = '';
  document.getElementById('filterDept').value  = '';
  document.getElementById('filterGroup').value = '';
  document.getElementById('filterMacro').value = '';
  document.getElementById('filterSub').value   = '';
  document.getElementById('filterYear').value  = '';
  document.getElementById('filterProtection').value = '';
  document.getElementById('filterEstado').value = '';
  document.getElementById('filterSub').innerHTML = '<option value="">Todas</option>';
  renderAll();
}

// ─── TOAST ────────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3800);
}

// ─── HELPERS ──────────────────────────────────────────────────
function estadoClass(estado) {
  const classes = {
    'Aprobado': 'estado-aprobado',
    'Aprobado por OCAD': 'estado-aprobado-ocad',
    'Banco Financiable': 'estado-banco-financiable',
    'Cancelado': 'estado-cancelado',
    'Elegible': 'estado-elegible',
    'En ejecución': 'estado-ejecucion',
    'En Legalización': 'estado-legalizacion',
    'Finalizado': 'estado-finalizado',
    'Ingresando Proyecto': 'estado-ingresando',
    'No aprobado': 'estado-no-aprobado',
    'No cumplió requisitos': 'estado-no-requisitos',
    'Propuesto': 'estado-propuesto',
    'Suspendido': 'estado-suspendido'
  };
  return classes[estado] || 'estado-otro';
}

function chartColor(index) {
  const colors = ['#11897D', '#162A63', '#B1C92E', '#0F8C80', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#10b981', '#f97316'];
  return colors[index % colors.length];
}

function statusColor(label) {
  const colors = {
    'Aprobado': '#16a34a',
    'Aprobado por OCAD': '#059669',
    'Banco Financiable': '#ca8a04',
    'Cancelado': '#dc2626',
    'Elegible': '#65a30d',
    'En ejecución': '#0d9488',
    'En Legalización': '#0284c7',
    'Finalizado': '#4f46e5',
    'Ingresando Proyecto': '#9333ea',
    'No aprobado': '#e11d48',
    'No cumplió requisitos': '#64748b',
    'Propuesto': '#ea580c',
    'Suspendido': '#d97706'
  };
  return colors[label] || '#6b7280';
}

function protectionColor(label) {
  if (label === 'Si') return '#11897D';
  if (label === 'No') return '#66728B';
  if (label === 'No ; Si') return '#B1C92E';
  return '#cbd5e1';
}

function shortCat(name) {
  if (!name) return '';
  return name.length > 28 ? name.substring(0, 28) + '…' : name;
}
