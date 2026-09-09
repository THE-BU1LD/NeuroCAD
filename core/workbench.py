"""Self-contained local workbench. No CDN, remote assets, or browser persistence.

Kept as a Python module so wheels and source-provenance manifests include the
exact interface without an additional asset build or package-data convention.
The HTTP handler supplies a fresh CSP nonce for each page load.
"""

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NeuroCAD Enclosure Workbench</title>
  <style nonce="__NONCE__">
    :root { color-scheme:dark; --bg:#05090d; --panel:#0b131c; --line:#324657;
      --text:#e8f1f8; --muted:#a6b8c8; --cyan:#26c6da; --red:#ff9a93; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 system-ui,sans-serif; }
    [hidden] { display:none !important; }
    main { max-width:1280px; margin:auto; padding:28px 24px 56px; }
    header { display:flex; justify-content:space-between; gap:28px; align-items:center; margin-bottom:24px; }
    h1 { font-size:32px; line-height:1.1; margin:0; letter-spacing:-.04em; }
    h1 span, a { color:var(--cyan); }
    header p { max-width:660px; color:var(--muted); margin:0; }
    h2 { font-size:18px; margin:0 0 16px; }
    .grid { display:grid; grid-template-columns:minmax(0,.9fr) minmax(0,1.3fr); gap:20px; align-items:start; }
    .panel { min-width:0; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:20px; }
    label { display:block; margin:16px 0 6px; font-weight:600; }
    textarea, select, input { width:100%; min-width:0; border:1px solid var(--line); border-radius:6px;
      background:#071018; color:var(--text); padding:10px; font:14px/1.5 system-ui,sans-serif; }
    textarea { min-height:220px; resize:vertical; font-family:ui-monospace,monospace; }
    button, input::file-selector-button { padding:11px 14px; border:1px solid var(--line); border-radius:6px;
      background:#162734; color:var(--text); font:600 14px/1.3 system-ui,sans-serif; cursor:pointer; }
    input::file-selector-button { margin-right:10px; }
    button:hover:not(:disabled), input::file-selector-button:hover { background:#223d4e; }
    button.primary { background:var(--cyan); color:#031014; border-color:var(--cyan); }
    button.primary:hover:not(:disabled) { background:#76e3ee; }
    button:disabled { opacity:.55; cursor:wait; }
    :focus-visible { outline:3px solid #c1f9ff; outline-offset:3px; }
    .actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }
    .actions button { flex:1 1 180px; }
    .hint, .status, .notice { color:var(--muted); }
    .hint { font-size:14px; margin:7px 0; }
    .status { min-height:24px; margin:16px 0 0; overflow-wrap:anywhere; }
    .error { color:var(--red); }
    .notice { border-left:2px solid var(--cyan); padding-left:12px; font-size:13px; }
    #editPanel { margin-top:24px; padding-top:20px; border-top:1px solid var(--line); }
    #editChanges, #projectSummary, #featureSummary, code { overflow-wrap:anywhere; }
    #editChanges { padding-left:20px; font-size:14px; }
    #editChanges li { margin-bottom:10px; }
    .empty { min-height:180px; display:grid; place-items:center; text-align:center; color:var(--muted);
      border:1px dashed var(--line); border-radius:6px; padding:24px; }
    #preview svg { width:100%; height:auto; display:block; }
    #downloads { display:flex; flex-wrap:wrap; align-items:center; gap:10px 16px; margin-top:16px; }
    #downloads a { overflow-wrap:anywhere; padding:5px 0; }
    .metrics { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; margin-top:16px; }
    .metric { background:#071018; border:1px solid var(--line); border-radius:6px; padding:10px; }
    .metric b { display:block; font-size:17px; color:var(--cyan); overflow-wrap:anywhere; }
    .metric small { color:var(--muted); }
    details { margin-top:16px; border-top:1px solid var(--line); padding-top:14px; }
    summary { cursor:pointer; font-weight:600; }
    pre { overflow:auto; max-height:320px; background:#050a0f; border-radius:6px; padding:13px;
      font:12px/1.5 ui-monospace,monospace; color:#c4d7e8; }
    @media(max-width:800px) { main { padding:20px 14px 36px; } header { display:block; }
      header p { margin-top:12px; } .grid { grid-template-columns:1fr; } .panel { padding:16px; } }
    @media(prefers-reduced-motion:reduce) { * { scroll-behavior:auto; } }
  </style>
</head>
<body>
<main>
  <header>
    <h1>Neuro<span>CAD</span></h1>
    <p>Local enclosure workbench. Turn explicit dimensions into editable geometry, inspect the specification,
      then compile and verify the mesh.</p>
  </header>
  <div class="grid">
    <section class="panel" aria-labelledby="inputHeading">
      <h2 id="inputHeading">Design input</h2>
      <label for="sourceType">Input contract</label>
      <select id="sourceType">
        <option value="enclosure">Electronics enclosure requirements</option>
        <option value="prompt">Basic supported geometry prompt</option>
        <option value="ir">Canonical NeuroCAD IR JSON</option>
        <option value="project">Saved enclosure project JSON</option>
      </select>
      <label for="source">Input</label>
      <textarea id="source" spellcheck="false" aria-describedby="status">80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C; title controller case</textarea>
      <p class="hint">Drafts survive mode changes in this tab only. Download your project before closing or reloading.
        Ctrl/⌘ + Enter validates without compiling.</p>
      <div class="actions">
        <button id="generate" class="primary">Interpret, validate &amp; preview</button>
        <button id="compile">Compile verified mesh &amp; download STL</button>
      </div>
      <label for="compileBudget">Compile time limit per part</label>
      <select id="compileBudget" aria-describedby="budgetHint">
        <option value="30">30 seconds (default)</option>
        <option value="60">60 seconds</option>
        <option value="120">120 seconds (complex enclosures)</option>
      </select>
      <p id="budgetHint" class="hint">Body and lid compile separately. A longer limit changes waiting time, not geometry or verification.</p>
      <label for="projectFile">Open saved enclosure project</label>
      <input id="projectFile" type="file" accept=".json,application/json" aria-describedby="fileHint">
      <p id="fileHint" class="hint">Canonical project JSON, at most 1 MiB (also subject to the API's 1 MiB request limit).
        Invalid files leave the current design intact. Nothing is uploaded to a cloud service.</p>
      <p id="status" class="status" role="status" aria-live="polite"></p>
      <p id="saveState" class="hint" role="status">No browser autosave. Keep a downloaded project as your backup.</p>
      <section id="editPanel" aria-labelledby="editHeading" hidden>
        <h2 id="editHeading">Edit the validated project</h2>
        <p id="projectSummary"></p>
        <a id="saveProjectShortcut">Download current project</a>
        <p id="featureSummary" class="hint"></p>
        <label for="editInstruction">One explicit edit</label>
        <input id="editInstruction" type="text" maxlength="512" placeholder="set wall thickness to 2.4 mm"
          aria-describedby="editHint status" autocomplete="off">
        <p id="editHint" class="hint">Review the proposed change before applying it. Existing geometry stays intact until you confirm.</p>
        <label for="editReason">Reason (optional)</label>
        <input id="editReason" type="text" maxlength="512" placeholder="Why this revision is needed"
          aria-describedby="status" autocomplete="off">
        <details><summary>Supported edit examples</summary>
          <p class="hint"><code>resize enclosure to 90 x 65 x 32 mm</code><br>
            <code>set lid clearance to 0.4 mm</code><br>
            <code>add circular cutout power 8 mm diameter on rear at 12 x 9 mm</code><br>
            <code>move cutout power to 10 x 9 mm</code><br><code>remove cutout power</code><br>
            Use the feature IDs above for existing cutouts, vents and standoffs.</p>
        </details>
        <div class="actions"><button id="previewEdit">Review proposed edit</button></div>
        <div id="editReview" hidden>
          <p id="editReviewHeading" role="status"></p>
          <ul id="editChanges"></ul>
          <div class="actions">
            <button id="applyEdit" class="primary">Apply reviewed revision</button>
            <button id="cancelEdit">Discard proposal</button>
          </div>
        </div>
      </section>
    </section>
    <section id="result" class="panel" aria-labelledby="outputHeading" aria-busy="false">
      <h2 id="outputHeading">Validated design output</h2>
      <p class="notice">A schematic is not a compiled solid. Kernel verification checks the exported mesh;
        physical fit, strength, and manufacturing safety still require independent validation.</p>
      <div id="preview"></div>
      <div id="downloads" aria-label="Validated output downloads"></div>
      <div id="metrics" class="metrics"></div>
      <details open><summary>Interpreted specification / canonical IR</summary><pre id="ir"></pre></details>
      <details><summary>OpenSCAD exports</summary><pre id="scad"></pre></details>
      <details><summary>Validation and fabrication preflight</summary><pre id="validation"></pre></details>
    </section>
  </div>
</main>
<script nonce="__NONCE__">
'use strict';
const source = document.querySelector('#source');
const type = document.querySelector('#sourceType');
const button = document.querySelector('#generate');
const compileButton = document.querySelector('#compile');
const compileBudget = document.querySelector('#compileBudget');
const fileInput = document.querySelector('#projectFile');
const status = document.querySelector('#status');
const result = document.querySelector('#result');
const preview = document.querySelector('#preview');
const downloads = document.querySelector('#downloads');
const metrics = document.querySelector('#metrics');
const ir = document.querySelector('#ir');
const scad = document.querySelector('#scad');
const validation = document.querySelector('#validation');
const editPanel = document.querySelector('#editPanel');
const editInstruction = document.querySelector('#editInstruction');
const editReason = document.querySelector('#editReason');
const previewEditButton = document.querySelector('#previewEdit');
const applyEditButton = document.querySelector('#applyEdit');
const editReview = document.querySelector('#editReview');
const editChanges = document.querySelector('#editChanges');
const saveState = document.querySelector('#saveState');
const MAX_BYTES = 1048576;
const drafts = {
  enclosure: source.value,
  prompt: 'a 120 x 80 x 4 mm plate with four 4 mm holes',
  ir: '', project: ''
};
let activeMode = type.value;
let generation = 0;
let pending = null;
let downloadURLs = [];
let currentProject = null;
let editProposal = null;
const unsavedModes = new Set();

function updateSaveState() {
  saveState.textContent = unsavedModes.size
    ? 'Unsaved work in this tab. Download projects before leaving; there is no browser autosave.'
    : 'No browser autosave. Keep a downloaded project as your backup.';
}

function discardProposal() {
  editProposal = null;
  editReview.hidden = true;
  editChanges.replaceChildren();
}

function setStatus(message, error = false) {
  status.className = error ? 'status error' : 'status';
  status.setAttribute('role', error ? 'alert' : 'status');
  status.textContent = message;
}

function setBusy(busy) {
  button.disabled = busy;
  compileButton.disabled = busy;
  previewEditButton.disabled = busy || !currentProject;
  applyEditButton.disabled = busy || !editProposal;
  result.setAttribute('aria-busy', busy ? 'true' : 'false');
}

function releaseDownloads() {
  for (const url of downloadURLs) URL.revokeObjectURL(url);
  downloadURLs = [];
  downloads.replaceChildren();
}

function clearOutput(message) {
  currentProject = null;
  editPanel.hidden = true;
  discardProposal();
  preview.replaceChildren();
  releaseDownloads();
  const empty = document.createElement('p');
  empty.className = 'empty';
  empty.textContent = message;
  preview.append(empty);
  metrics.replaceChildren();
  ir.textContent = '';
  scad.textContent = '';
  validation.textContent = '';
}

function invalidateRequest() {
  discardProposal();
  generation++;
  if (pending) {
    pending.controller.abort();
    clearTimeout(pending.timer);
    pending = null;
  }
  setBusy(false);
}

function markDirty(userEdit = true) {
  drafts[activeMode] = source.value;
  if (userEdit) {
    if (source.value.trim()) unsavedModes.add(activeMode);
    else unsavedModes.delete(activeMode);
  }
  updateSaveState();
  invalidateRequest();
  setStatus('Input changed; run validation before using any output.');
  clearOutput('No current validated output.');
}

function beginRequest(message, deadlineMs = 90000) {
  invalidateRequest();
  const request = {id: generation, controller: new AbortController(), timedOut: false};
  request.timer = setTimeout(() => {
    request.timedOut = true;
    request.controller.abort();
  }, deadlineMs);
  pending = request;
  setBusy(true);
  setStatus(message);
  return request;
}

function isCurrent(request) { return request.id === generation; }

function finishRequest(request) {
  clearTimeout(request.timer);
  // An obsolete request must not unlock controls belonging to a newer one.
  if (isCurrent(request)) { pending = null; setBusy(false); }
}

async function postJSON(endpoint, value, request) {
  const body = JSON.stringify(value);
  if (new TextEncoder().encode(body).length > MAX_BYTES) {
    throw new Error('Encoded request exceeds 1 MiB. Use the CLI for this input or reduce its size.');
  }
  const response = await fetch(endpoint, {
    method: 'POST', headers: {'content-type': 'application/json'}, body,
    signal: request.controller.signal
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The local server returned an unreadable response. Check that NeuroCAD is still running.'); }
  if (!response.ok) {
    const error = new Error(data.error || `Generation failed (HTTP ${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function generate(input, mode, compileMesh, request) {
  return postJSON('/api/generate', {
    source: input, source_type: mode, compile_mesh: compileMesh,
    timeout_seconds: Number(compileBudget.value)
  }, request);
}

function addDownload(label, filename, content, mediaType) {
  const url = URL.createObjectURL(new Blob([content], {type: mediaType}));
  downloadURLs.push(url);
  const link = document.createElement('a');
  link.textContent = label;
  link.href = url;
  link.download = filename;
  downloads.append(link);
  return link;
}

function render(data) {
  currentProject = data.project || null;
  editPanel.hidden = !currentProject;
  discardProposal();
  if (currentProject) {
    document.querySelector('#projectSummary').textContent = currentProject.project_id +
      ' · revision ' + currentProject.revision + ' · ' + data.spec.outer_size_mm.join(' × ') +
      ' mm · walls ' + data.spec.wall_mm + ' mm';
    document.querySelector('#featureSummary').textContent = ['cutouts', 'vents', 'standoffs'].map(kind =>
      kind + ': ' + ((data.spec[kind] || []).map(feature => feature.id).join(', ') || 'none')).join(' · ');
  }
  releaseDownloads();
  // SVGs are generated by our local geometry renderer, never by source text.
  preview.innerHTML = data.preview_svg;
  if (data.project) {
    const projectLink = addDownload('Save project · revision ' + data.project.revision,
      data.project.project_id + '-r' + data.project.revision + '.neurocad.json',
      JSON.stringify(data.project, null, 2) + '\n', 'application/json');
    const shortcut = document.querySelector('#saveProjectShortcut');
    shortcut.href = projectLink.href;
    shortcut.download = projectLink.download;
    // A click requests a download; it cannot prove the browser saved the file.
    projectLink.addEventListener('click', () => {
      saveState.textContent = 'Project download requested. Confirm it was saved in your browser; unsaved-work warnings remain active.';
    });
  }
  const parts = typeof data.scad === 'string' ? {model: data.scad} : data.scad;
  for (const [part, code] of Object.entries(parts)) {
    addDownload(part + ' OpenSCAD', part + '.scad', code, 'text/plain');
    addDownload(part + ' canonical IR', part + '.ncad.json',
      JSON.stringify(data.mode === 'enclosure' ? data.ir[part] : data.ir, null, 2) + '\n', 'application/json');
  }
  for (const [part, artifact] of Object.entries(data.mesh_artifacts || {})) {
    const link = document.createElement('a');
    link.textContent = 'Download ' + part + ' STL (SHA-256 ' + artifact.sha256.slice(0, 12) + '…)';
    link.href = artifact.download_url;
    link.download = artifact.filename;
    downloads.append(link);
    const view = document.createElement('button');
    view.textContent = 'View ' + part + ' mesh';
    view.addEventListener('click', () => { preview.innerHTML = artifact.preview_svg; });
    downloads.append(view);
  }
  const e = data.evaluation;
  metrics.replaceChildren();
  for (const [label, value] of [
    ['Structurally valid', e.structural_validity],
    ['Kernel geometry', e.kernel_validity === null ? 'unverified' : e.kernel_validity],
    ['Editable nodes', e.editable_nodes], ['Latency', e.evaluation_latency_ms.toFixed(2) + ' ms']
  ]) {
    const box = document.createElement('div');
    box.className = 'metric';
    const number = document.createElement('b');
    number.textContent = String(value);
    const caption = document.createElement('small');
    caption.textContent = label;
    box.append(number, caption);
    metrics.append(box);
  }
  ir.textContent = JSON.stringify(data.spec || data.ir, null, 2);
  scad.textContent = typeof data.scad === 'string' ? data.scad : JSON.stringify(data.scad, null, 2);
  validation.textContent = JSON.stringify({
    validation: data.validation, manufacturing: data.manufacturing || null,
    mesh_verification: Object.fromEntries(Object.entries(data.mesh_artifacts || {}).map(([part, a]) =>
      [part, {sha256: a.sha256, verification: a.verification}]))
  }, null, 2);
}

function requestError(error, request) {
  if (request.timedOut) return 'Request timed out. The server may still be compiling; wait before retrying.';
  return error instanceof Error ? error.message : 'Request failed. Check that the local server is running.';
}

async function run(compileMesh = false) {
  // Input edits already invalidate output. A compiler outage must not discard
  // source/project downloads that were validated for this unchanged input.
  const retainOutput = compileMesh && downloads.children.length > 0;
  const request = beginRequest(compileMesh ? 'Compiling and verifying the mesh…' : 'Validating the current input…',
    compileMesh ? Number(compileBudget.value) * 2000 + 30000 : 90000);
  if (!retainOutput) clearOutput('Validating the current input…');
  try {
    const data = await generate(source.value, type.value, compileMesh, request);
    if (!isCurrent(request)) return;
    render(data);
    setStatus(compileMesh
      ? 'Compiled mesh verified; downloads contain the exact previewed STL. Downloads expire after 10 minutes or cache eviction. Physical fit remains unverified.'
      : 'Validated source is ready to download. Compile an STL for kernel geometry verification; review fabrication warnings.');
  } catch (error) {
    if (!isCurrent(request)) return;
    if (!retainOutput) clearOutput('No validated output was generated. Correct the input and try again.');
    setStatus((retainOutput ? 'No new mesh was generated. Previous validated output retained. ' : '') + requestError(error, request), true);
  } finally { finishRequest(request); }
}

async function openProject(file) {
  if (!file) return;
  if (unsavedModes.has('project') && !window.confirm('Replace the unsaved project draft? Download it first if you need to keep it.')) {
    fileInput.value = '';
    return;
  }
  const request = beginRequest('Validating project file; the current design is retained until validation succeeds…');
  try {
    if (file.size > MAX_BYTES) throw new Error('Project file exceeds the 1 MiB input limit.');
    const text = await file.text();
    if (!isCurrent(request)) return;
    const data = await generate(text, 'project', false, request);
    if (!isCurrent(request)) return;
    drafts[activeMode] = source.value;
    drafts.project = text;
    unsavedModes.delete('project');
    updateSaveState();
    activeMode = type.value = 'project';
    source.value = text;
    source.placeholder = '';
    render(data);
    setStatus('Opened project ' + data.project.project_id + ', revision ' + data.project.revision +
      '. History preserved; kernel geometry is unverified until you compile.');
  } catch (error) {
    if (isCurrent(request)) setStatus('Project not opened. Current input and output retained. ' + requestError(error, request), true);
  } finally {
    if (isCurrent(request)) fileInput.value = '';
    finishRequest(request);
  }
}

async function previewEdit() {
  if (!currentProject) return;
  editInstruction.setAttribute('aria-invalid', 'false');
  const base = currentProject;
  const request = beginRequest('Checking the proposed edit; your current project is unchanged…');
  try {
    const data = await postJSON('/api/edit', {
      source: JSON.stringify(base), instruction: editInstruction.value,
      reason: editReason.value.trim() || null
    }, request);
    if (!isCurrent(request) || currentProject !== base) return;
    editProposal = {data, base};
    document.querySelector('#editReviewHeading').textContent =
      'Review revision ' + base.revision + ' → ' + data.project.revision + '. No change has been applied yet.';
    for (const change of data.edit.changes) {
      const row = document.createElement('li');
      row.textContent = change.field + ': ' + JSON.stringify(change.before) + ' → ' + JSON.stringify(change.after);
      editChanges.append(row);
    }
    editReview.hidden = false;
    setStatus('Proposed edit validated. Review the changes, then apply or discard.');
  } catch (error) {
    if (isCurrent(request)) {
      editInstruction.setAttribute('aria-invalid', error.status === 400 ? 'true' : 'false');
      setStatus('Edit not applied. Current project retained. ' + requestError(error, request), true);
    }
  } finally {
    finishRequest(request);
    if (isCurrent(request) && editProposal) applyEditButton.focus();
  }
}

function applyEdit() {
  if (!editProposal || pending || editProposal.base !== currentProject) return;
  // Do not discard a different project draft when converting a prompt to a project.
  if (activeMode !== 'project' && unsavedModes.has('project') &&
      !window.confirm('Replace the unsaved project draft with this reviewed revision?')) return;
  const data = editProposal.data;
  drafts[activeMode] = source.value;
  invalidateRequest();
  source.value = drafts.project = JSON.stringify(data.project, null, 2) + '\n';
  activeMode = type.value = 'project';
  source.placeholder = '';
  unsavedModes.add('project');
  updateSaveState();
  render(data);
  setBusy(false);
  setStatus('Applied revision ' + data.project.revision + '. Save the project and compile to verify the updated mesh.');
  compileButton.focus();
}

previewEditButton.addEventListener('click', previewEdit);
applyEditButton.addEventListener('click', applyEdit);
document.querySelector('#cancelEdit').addEventListener('click', () => {
  discardProposal();
  setStatus('Proposal discarded. Current project unchanged.');
  previewEditButton.focus();
});
for (const input of [editInstruction, editReason]) input.addEventListener('input', () => {
  editInstruction.setAttribute('aria-invalid', 'false');
  invalidateRequest();
  setStatus('Edit instruction changed; review it before applying.');
});
window.addEventListener('beforeunload', event => {
  if (unsavedModes.size) { event.preventDefault(); event.returnValue = ''; }
});
document.querySelector('#saveProjectShortcut').addEventListener('click', () => {
  saveState.textContent = 'Project download requested. Confirm it was saved in your browser; unsaved-work warnings remain active.';
});

compileButton.addEventListener('click', () => run(true));
compileBudget.addEventListener('change', () => {
  invalidateRequest();
  setStatus('Compile budget changed. An already running server compilation may continue; retry when it finishes.');
});
button.addEventListener('click', () => run(false));
source.addEventListener('input',markDirty);
source.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); run(false); }
});
type.addEventListener('change', () => {
  drafts[activeMode] = source.value;
  activeMode = type.value;
  source.value = drafts[activeMode];
  source.placeholder = activeMode === 'ir' ? 'Paste canonical NeuroCAD IR JSON here' :
    activeMode === 'project' ? 'Paste a saved NeuroCAD enclosure project, or open its file below' : '';
  markDirty(false);
});
fileInput.addEventListener('change', () => openProject(fileInput.files[0]));
run();
</script>
</body>
</html>"""
