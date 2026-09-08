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
    body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,sans-serif; }
    main { max-width:1280px; margin:auto; padding:28px 24px 56px; }
    header { display:flex; justify-content:space-between; gap:28px; align-items:center; margin-bottom:24px; }
    h1 { font-size:32px; line-height:1.1; margin:0; letter-spacing:-.04em; }
    h1 span, a { color:var(--cyan); }
    header p { max-width:660px; color:var(--muted); margin:0; }
    h2 { font-size:18px; margin:0 0 16px; }
    .grid { display:grid; grid-template-columns:minmax(0,.9fr) minmax(0,1.3fr); gap:20px; align-items:start; }
    .panel { min-width:0; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:20px; }
    label { display:block; margin:16px 0 6px; font-weight:600; }
    textarea, select, input[type=file] { width:100%; min-width:0; border:1px solid var(--line); border-radius:6px;
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
    .hint { font-size:13px; margin:7px 0; }
    .status { min-height:24px; margin:16px 0 0; overflow-wrap:anywhere; }
    .error { color:var(--red); }
    .notice { border-left:2px solid var(--cyan); padding-left:12px; font-size:13px; }
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
      <label for="projectFile">Open saved enclosure project</label>
      <input id="projectFile" type="file" accept=".json,application/json" aria-describedby="fileHint">
      <p id="fileHint" class="hint">Canonical project JSON, at most 1 MiB (also subject to the API's 1 MiB request limit).
        Invalid files leave the current design intact. Nothing is uploaded to a cloud service.</p>
      <p id="status" class="status" role="status" aria-live="polite"></p>
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
const fileInput = document.querySelector('#projectFile');
const status = document.querySelector('#status');
const result = document.querySelector('#result');
const preview = document.querySelector('#preview');
const downloads = document.querySelector('#downloads');
const metrics = document.querySelector('#metrics');
const ir = document.querySelector('#ir');
const scad = document.querySelector('#scad');
const validation = document.querySelector('#validation');
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

function setStatus(message, error = false) {
  status.className = error ? 'status error' : 'status';
  status.setAttribute('role', error ? 'alert' : 'status');
  status.textContent = message;
}

function setBusy(busy) {
  button.disabled = busy;
  compileButton.disabled = busy;
  result.setAttribute('aria-busy', busy ? 'true' : 'false');
}

function releaseDownloads() {
  for (const url of downloadURLs) URL.revokeObjectURL(url);
  downloadURLs = [];
  downloads.replaceChildren();
}

function clearOutput(message) {
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
  generation++;
  if (pending) {
    pending.controller.abort();
    clearTimeout(pending.timer);
    pending = null;
  }
  setBusy(false);
}

function markDirty() {
  drafts[activeMode] = source.value;
  invalidateRequest();
  setStatus('Input changed; run validation before using any output.');
  clearOutput('No current validated output.');
}

function beginRequest(message) {
  invalidateRequest();
  const request = {id: generation, controller: new AbortController(), timedOut: false};
  request.timer = setTimeout(() => {
    request.timedOut = true;
    request.controller.abort();
  }, 90000);
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

async function generate(input, mode, compileMesh, request) {
  const body = JSON.stringify({source: input, source_type: mode, compile_mesh: compileMesh});
  if (new TextEncoder().encode(body).length > MAX_BYTES) {
    throw new Error('Encoded request exceeds 1 MiB. Use the CLI for this input or reduce its size.');
  }
  const response = await fetch('/api/generate', {
    method: 'POST', headers: {'content-type': 'application/json'}, body,
    signal: request.controller.signal
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The local server returned an unreadable response. Check that NeuroCAD is still running.'); }
  if (!response.ok) throw new Error(data.error || `Generation failed (HTTP ${response.status}).`);
  return data;
}

function addDownload(label, filename, content, mediaType) {
  const url = URL.createObjectURL(new Blob([content], {type: mediaType}));
  downloadURLs.push(url);
  const link = document.createElement('a');
  link.textContent = label;
  link.href = url;
  link.download = filename;
  downloads.append(link);
}

function render(data) {
  releaseDownloads();
  // SVGs are generated by our local geometry renderer, never by source text.
  preview.innerHTML = data.preview_svg;
  if (data.project) {
    addDownload('Save project · revision ' + data.project.revision,
      data.project.project_id + '-r' + data.project.revision + '.neurocad.json',
      JSON.stringify(data.project, null, 2) + '\n', 'application/json');
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
  const request = beginRequest(compileMesh ? 'Compiling and verifying the mesh…' : 'Validating the current input…');
  clearOutput('Validating the current input…');
  try {
    const data = await generate(source.value, type.value, compileMesh, request);
    if (!isCurrent(request)) return;
    render(data);
    setStatus(compileMesh
      ? 'Compiled mesh verified; downloads contain the exact previewed STL. Downloads expire after 10 minutes or cache eviction. Physical fit remains unverified.'
      : 'Validated source is ready to download. Compile an STL for kernel geometry verification; review fabrication warnings.');
  } catch (error) {
    if (!isCurrent(request)) return;
    clearOutput('No validated output was generated. Correct the input and try again.');
    setStatus(requestError(error, request), true);
  } finally { finishRequest(request); }
}

async function openProject(file) {
  if (!file) return;
  const request = beginRequest('Validating project file; the current design is retained until validation succeeds…');
  try {
    if (file.size > MAX_BYTES) throw new Error('Project file exceeds the 1 MiB input limit.');
    const text = await file.text();
    if (!isCurrent(request)) return;
    const data = await generate(text, 'project', false, request);
    if (!isCurrent(request)) return;
    drafts[activeMode] = source.value;
    drafts.project = text;
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

compileButton.addEventListener('click', () => run(true));
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
  markDirty();
});
fileInput.addEventListener('change', () => openProject(fileInput.files[0]));
run();
</script>
</body>
</html>"""
