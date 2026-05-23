// ─── ESTADO GLOBAL ───────────────────────────────────────────
let allProjects    = [];
let allCategories  = {};
let filters        = { search: '', dept: '', macro: '', sub: '', year: '', estado: '' };
let viewMode       = 'grid'; // 'grid' | 'table'
let apiAvailable   = false;

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
  const years  = [...new Set(allProjects.map(p => p.año_inicio).filter(Boolean))].sort((a,b) => b - a);
  const states = getProjectStates();
  const macros = allCategories.macrocategorias || [];

  populateSelect('filterDept',  depts,  d => ({ value: d, label: d }));
  populateSelect('filterYear',  years,  y => ({ value: y, label: y }));
  populateSelect('filterMacro', macros, m => ({ value: m.id, label: `${m.id} — ${m.nombre}` }));
  renderEstadoPills(states);

  // Selects del formulario
  populateSelect('f_departamento', allCategories.departamentos || depts, d => ({ value: d, label: d }));
  populateSelect('f_estado', states, s => ({ value: s, label: s }));
  populateMacroSelect('f_macro', macros);
}

function getProjectStates() {
  const states = [...new Set(allProjects.map(p => p.estado).filter(Boolean))].sort();
  const configuredStates = allCategories.estados || [];
  configuredStates.forEach(state => {
    if (state && !states.includes(state)) states.push(state);
  });
  return states;
}

function renderEstadoPills(states) {
  const wrap = document.getElementById('estadoPills');
  if (!wrap) return;
  wrap.innerHTML = '<button class="pill active" data-estado="">Todos</button>';
  states.forEach(state => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pill';
    btn.dataset.estado = state;
    btn.textContent = state;
    wrap.appendChild(btn);
  });
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

function resetFilterOptions() {
  const defaults = {
    filterDept: 'Todos',
    filterYear: 'Todos',
    filterMacro: 'Todas',
    filterSub: 'Todas',
    f_departamento: 'Seleccionar…',
    f_estado: 'Seleccionar…',
    f_macro: 'Seleccionar…',
    f_sub: 'Seleccionar macrocategoría primero…'
  };

  Object.entries(defaults).forEach(([id, label]) => {
    const sel = document.getElementById(id);
    if (sel) sel.innerHTML = `<option value="">${label}</option>`;
  });

  renderEstadoPills([]);
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

  // Estado pills
  document.getElementById('estadoPills').addEventListener('click', e => {
    const pill = e.target.closest('.pill');
    if (!pill) return;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    filters.estado = pill.dataset.estado;
    renderAll();
  });

  document.getElementById('btnClearFilters').addEventListener('click', clearFilters);

  // Vista
  document.getElementById('btnGrid').addEventListener('click', () => setView('grid'));
  document.getElementById('btnTable').addEventListener('click', () => setView('table'));

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

  // Modal importar datos
  document.getElementById('btnOpenImport').addEventListener('click', openImportModal);
  document.getElementById('closeImport').addEventListener('click', closeImportModal);
  document.getElementById('cancelImport').addEventListener('click', closeImportModal);
  document.getElementById('importModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeImportModal();
  });
  document.getElementById('importDataForm').addEventListener('submit', handleImportData);

  // Macrocategoría en formulario → actualizar subcategorías
  document.getElementById('f_macro').addEventListener('change', e => {
    updateFormSubcats(e.target.value);
  });

  // Formulario submit
  document.getElementById('addProjectForm').addEventListener('submit', handleAddProject);

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
        p.grupo_investigacion, p.investigador_principal,
        p.macrocategoria, p.subcategoria,
        ...(p.palabras_clave || []),
        ...(p.productos_esperados || []),
        ...(p.productos_logrados || []),
        ...(p.nombres_productos_logrados || [])
      ].join(' ').toLowerCase();
      if (!haystack.includes(filters.search)) return false;
    }
    if (filters.dept   && p.departamento       !== filters.dept)               return false;
    if (filters.macro  && p.macrocategoria_id  !== filters.macro)              return false;
    if (filters.sub    && p.subcategoria_id    !== filters.sub)                return false;
    if (filters.year   && p.año_inicio         !== filters.year)               return false;
    if (filters.estado && p.estado             !== filters.estado)             return false;
    return true;
  });
}

// ─── RENDER PRINCIPAL ─────────────────────────────────────────
function renderAll() {
  const filtered = getFiltered();
  updateStats(filtered);
  document.getElementById('resultsCount').textContent = filtered.length;

  if (viewMode === 'grid') renderGrid(filtered);
  else renderTable(filtered);

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
      ${p.grupo_investigacion ? `<p class="card-group">${p.grupo_investigacion}</p>` : ''}
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
      <td class="td-cat" title="${p.macrocategoria}">${p.macrocategoria_id} · ${shortCat(p.macrocategoria)}</td>
      <td>${p.año_inicio}</td>
      <td><span class="card-estado ${estadoClass(p.estado)}">${p.estado}</span></td>
    `;
    tr.addEventListener('click', () => openDetailModal(p));
    tbody.appendChild(tr);
  });
}

// ─── MODAL DETALLE ────────────────────────────────────────────
function openDetailModal(p) {
  const color  = CAT_COLORS[p.macrocategoria_id] || '#11897D';
  const modal  = document.getElementById('detailModal');
  const content = document.getElementById('detailContent');

  const kwHTML = (p.palabras_clave || []).map(k => `<span class="detail-kw">${k}</span>`).join('');
  const prodEsperadosHTML = (p.productos_esperados || []).map(pr => `<li>${pr}</li>`).join('');
  const prodLogradosHTML = (p.productos_logrados || []).map(pr => `<li>${pr}</li>`).join('');
  const nombresLogradosHTML = (p.nombres_productos_logrados || []).map(pr => `<li>${pr}</li>`).join('');

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
      ${p.grupo_investigacion ? `
      <div class="meta-item">
        <div class="meta-item-label">Grupo de investigación</div>
        <div class="meta-item-val">${p.grupo_investigacion}</div>
      </div>` : ''}
      ${p.investigador_principal ? `
      <div class="meta-item">
        <div class="meta-item-label">Investigador principal</div>
        <div class="meta-item-val">${p.investigador_principal}</div>
      </div>` : ''}
      <div class="meta-item">
        <div class="meta-item-label">Período</div>
        <div class="meta-item-val">${p.año_inicio}${p.año_fin ? ' — ' + p.año_fin : ' — en curso'}</div>
      </div>
      <div class="meta-item">
        <div class="meta-item-label">Subcategoría</div>
        <div class="meta-item-val">${p.subcategoria_id} · ${p.subcategoria}</div>
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

    ${prodEsperadosHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Productos esperados</div>
      <ul class="detail-products-list">${prodEsperadosHTML}</ul>
    </div>` : ''}

    ${prodLogradosHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Productos logrados</div>
      <ul class="detail-products-list">${prodLogradosHTML}</ul>
    </div>` : ''}

    ${nombresLogradosHTML ? `
    <div class="detail-section">
      <div class="detail-section-label">Nombres de productos logrados</div>
      <ul class="detail-products-list">${nombresLogradosHTML}</ul>
    </div>` : ''}

    ${p.cumplio_con_la_entrega_del_producto ? `
    <div class="detail-section">
      <div class="detail-section-label">Cumplió con la entrega del producto</div>
      <p class="detail-section-text">${p.cumplio_con_la_entrega_del_producto}</p>
    </div>` : ''}

    ${p.es_suceptible_de_proteccion_producto ? `
    <div class="detail-section">
      <div class="detail-section-label">Susceptible de protección</div>
      <p class="detail-section-text">${p.es_suceptible_de_proteccion_producto}</p>
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
  const productos = document.getElementById('f_productos').value
    .split(',').map(s => s.trim()).filter(Boolean);

  const newProject = {
    id:               Date.now(),
    codigo_hermes:    document.getElementById('f_codigo').value.trim() || '—',
    nombre:           document.getElementById('f_nombre').value.trim(),
    objetivo:         document.getElementById('f_objetivo').value.trim(),
    grupo_investigacion: document.getElementById('f_grupo').value.trim(),
    investigador_principal: document.getElementById('f_investigador').value.trim(),
    email_investigador_principal: '',
    departamento:     document.getElementById('f_departamento').value,
    facultad:         document.getElementById('f_facultad').value.trim(),
    macrocategoria_id: macroId,
    macrocategoria:   macroData?.nombre || '',
    subcategoria_id:  subId,
    subcategoria:     subData?.nombre || '',
    año_inicio:       parseInt(document.getElementById('f_año_inicio').value),
    año_fin:          parseInt(document.getElementById('f_año_fin').value) || null,
    estado:           document.getElementById('f_estado').value,
    ods_principal:    document.getElementById('f_ods').value.trim(),
    palabras_clave:   palabrasClave,
    productos_esperados: productos
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

// ─── MODAL IMPORTAR DATOS ─────────────────────────────────────
function openImportModal() {
  if (!apiAvailable) {
    showToast('La actualización de Excel requiere ejecutar la app con FastAPI.');
    return;
  }
  document.getElementById('importModal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeImportModal() {
  document.getElementById('importModal').classList.add('hidden');
  document.body.style.overflow = '';
  document.getElementById('importDataForm').reset();
  setImportLoading(false);
}

function setImportLoading(isLoading) {
  const submit = document.getElementById('submitImport');
  submit.disabled = isLoading;
  submit.textContent = isLoading ? 'Actualizando…' : 'Actualizar Base';
}

async function handleImportData(e) {
  e.preventDefault();

  const projectsFile = document.getElementById('projectsFile').files[0];
  const productsFile = document.getElementById('productsFile').files[0];

  if (!projectsFile || !productsFile) {
    showToast('Selecciona los dos archivos Excel antes de actualizar.');
    return;
  }

  const formData = new FormData();
  formData.append('projects_file', projectsFile);
  formData.append('products_file', productsFile);

  try {
    setImportLoading(true);
    const response = await fetch('/api/import-data', {
      method: 'POST',
      body: formData
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || 'No se pudo actualizar la base de datos.');
    }

    allProjects = payload.projects || [];
    resetFilterOptions();
    initFilters();
    closeImportModal();
    clearFilters();
    showToast(`Base actualizada: ${payload.projects_count || allProjects.length} proyectos cargados.`);
  } catch (error) {
    console.error('Error importando datos:', error);
    showToast(error.message || 'Error al importar los archivos.');
  } finally {
    setImportLoading(false);
  }
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
  renderAll();
}

// ─── LIMPIAR FILTROS ──────────────────────────────────────────
function clearFilters() {
  filters = { search: '', dept: '', macro: '', sub: '', year: '', estado: '' };
  document.getElementById('searchInput').value = '';
  document.getElementById('filterDept').value  = '';
  document.getElementById('filterMacro').value = '';
  document.getElementById('filterSub').value   = '';
  document.getElementById('filterYear').value  = '';
  document.getElementById('filterSub').innerHTML = '<option value="">Todas</option>';
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  document.querySelector('.pill[data-estado=""]').classList.add('active');
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
  if (estado === 'En ejecución') return 'estado-ejecucion';
  if (estado === 'Finalizado')   return 'estado-finalizado';
  if (estado === 'Suspendido')   return 'estado-suspendido';
  return 'estado-otro';
}

function shortCat(name) {
  if (!name) return '';
  return name.length > 28 ? name.substring(0, 28) + '…' : name;
}
