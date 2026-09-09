// The VM supplies only browser APIs. All workflow logic comes from core.workbench.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const script = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const elements = new Map(), requests = [], blobs = new Map(), revoked = [], timers = new Map();
let nextTimer = 0, nextBlob = 0;
function element() {
  return {value:'',textContent:'',innerHTML:'',disabled:false,children:[],attrs:{},handlers:{},
    focus(){this.focused=true},setAttribute(k,v){this.attrs[k]=v}, addEventListener(k,v){this.handlers[k]=v},
    append(...nodes){this.children.push(...nodes)},replaceChildren(){this.children=[];this.innerHTML=''}};
}
const document = {querySelector(id){
  if (!elements.has(id)) elements.set(id, element());
  return elements.get(id);
},createElement:element};
const get = id => document.querySelector('#' + id);
get('source').value = 'original enclosure';
get('sourceType').value = 'enclosure';
get('compileBudget').value = '30';
const window = {handlers:{},confirm:()=>true,addEventListener(k,v){this.handlers[k]=v}};
const context = vm.createContext({document,window,AbortController,TextEncoder,Blob,Error,
  URL:{createObjectURL(blob){const url='blob:'+ ++nextBlob;blobs.set(url,blob);return url},
    revokeObjectURL(url){revoked.push(url);blobs.delete(url)}},
  setTimeout(callback){const id=++nextTimer;timers.set(id,callback);return id},
  clearTimeout(id){timers.delete(id)},
  fetch(url, options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))}
});
const flush = () => new Promise(resolve => setImmediate(resolve));
const payload = (name='fixture') => ({mode:'enclosure',project:{project_id:name,revision:2},
  spec:{wall_mm:2.4,outer_size_mm:[80,60,30]},ir:{body:{version:'ir'}},scad:{body:'cube([1,2,3]);'},
  preview_svg:'<svg></svg>',validation:{valid:true},evaluation:{structural_validity:true,
    kernel_validity:null,editable_nodes:1,evaluation_latency_ms:1}});
const resolve = (request, data=payload()) => request.resolve({ok:true,json:async()=>data});
const fail = request => request.resolve({ok:false,json:async()=>({error:'bad project'})});

(async () => {
  vm.runInContext(script, context);
  assert.equal(requests.length, 1);
  assert.equal(get('result').attrs['aria-busy'], 'true');
  resolve(requests[0]); await flush();
  assert.equal(get('downloads').children.length, 3);
  const projectLink = get('downloads').children[0];
  assert.equal(projectLink.download, 'fixture-r2.neurocad.json');
  assert.equal(JSON.parse(await blobs.get(projectLink.href).text()).revision, 2);

  // An unavailable kernel leaves already validated project/SCAD downloads usable.
  let compileTask = vm.runInContext('run(true)', context);
  assert.equal(get('downloads').children[0], projectLink);
  requests.at(-1).resolve({ok:false,status:503,json:async()=>({error:'OpenSCAD was not found'})});
  await compileTask;
  assert.equal(get('downloads').children[0], projectLink);
  assert.match(get('status').textContent, /Previous validated output retained/);
  assert.equal(get('compile').disabled, false);

  // An edit during the failed compilation still invalidates all previous output.
  compileTask = vm.runInContext('run(true)', context);
  const obsoleteCompile = requests.at(-1);
  get('source').handlers.input();
  fail(obsoleteCompile); await compileTask;
  assert.equal(get('downloads').children.length, 0);
  const restore = vm.runInContext('run()', context);
  resolve(requests.at(-1)); await restore;
  const restoredProjectLink = get('downloads').children[0];

  // An invalid import keeps the existing input and usable output/downloads intact.
  const previousInput = get('source').value, previousOutput = get('scad').textContent;
  let task = vm.runInContext("openProject({size:2,text:async()=> '{}'})", context);
  await flush(); fail(requests.at(-1)); await task;
  assert.equal(get('source').value, previousInput);
  assert.equal(get('scad').textContent, previousOutput);
  assert.equal(get('downloads').children[0], restoredProjectLink);
  assert.match(get('status').textContent, /Current input and output retained/);

  // Refuse oversized files before reading them or issuing a request.
  const count = requests.length;
  await vm.runInContext("openProject({size:1048577,text:()=>{throw new Error('must not read')}})", context);
  assert.equal(requests.length, count);
  assert.match(get('status').textContent, /1 MiB/);

  task = vm.runInContext("openProject({size:2,text:async()=> '{}'})", context);
  await flush(); resolve(requests.at(-1), payload('reopened')); await task;
  assert.equal(get('sourceType').value, 'project');
  assert.equal(get('source').value, '{}');
  assert.match(get('status').textContent, /revision 2/);
  assert.ok(revoked.includes(projectLink.href));

  // Mode changes preserve each draft, invalidate outputs, and leave JSON inputs empty.
  get('sourceType').value = 'enclosure'; get('sourceType').handlers.change();
  assert.equal(get('source').value, previousInput);
  get('source').value = 'my edited enclosure'; get('source').handlers.input();
  get('sourceType').value = 'ir'; get('sourceType').handlers.change();
  assert.equal(get('source').value, '');
  get('sourceType').value = 'enclosure'; get('sourceType').handlers.change();
  assert.equal(get('source').value, 'my edited enclosure');
  assert.equal(blobs.size, 0);

  // Out-of-order completion cannot unlock the newer request or install obsolete output.
  const first = vm.runInContext('run()', context), firstRequest = requests.at(-1);
  const second = vm.runInContext('run()', context), secondRequest = requests.at(-1);
  assert.equal(firstRequest.options.signal.aborted, true);
  resolve(firstRequest); await first;
  assert.equal(get('generate').disabled, true);
  assert.equal(get('scad').textContent, '');
  resolve(secondRequest); await second;
  assert.equal(get('generate').disabled, false);

  // Edit proposals are read-only until confirmed. Bad edits retain good outputs.
  get('editInstruction').value = 'set wall thickness to 2.4 mm';
  const originalSource = get('source').value;
  task = vm.runInContext('previewEdit()', context);
  assert.equal(requests.at(-1).url, '/api/edit');
  fail(requests.at(-1)); await task;
  assert.equal(get('source').value, originalSource);
  assert.match(get('status').textContent, /Current project retained/);
  task = vm.runInContext('previewEdit()', context);
  const proposal = payload('fixture'); proposal.project.revision = 3;
  proposal.edit = {changes:[{field:'wall_mm',before:2,after:2.4}]};
  resolve(requests.at(-1), proposal); await task;
  assert.equal(get('source').value, originalSource);
  assert.equal(get('editReview').hidden, false);
  assert.match(get('editChanges').children[0].textContent, /wall_mm: 2 → 2.4/);
  assert.equal(get('applyEdit').disabled, false);
  vm.runInContext('applyEdit()', context);
  assert.equal(JSON.parse(get('source').value).revision, 3);
  assert.equal(get('sourceType').value, 'project');
  assert.equal(get('editReview').hidden, true);
  assert.match(get('saveState').textContent, /Unsaved/);
  assert.match(get('status').textContent, /compile to verify/);
  let prevented = false;
  window.handlers.beforeunload({preventDefault(){prevented=true}});
  assert.equal(prevented, true);
  get('downloads').children[0].handlers.click();
  assert.match(get('saveState').textContent, /Confirm it was saved/);

  // A different edit instruction invalidates an in-flight proposal.
  task = vm.runInContext('previewEdit()', context);
  const staleEdit = requests.at(-1);
  get('editInstruction').value = 'set wall thickness to 3 mm';
  get('editInstruction').handlers.input();
  resolve(staleEdit, proposal); await task;
  vm.runInContext('applyEdit()', context);
  assert.equal(JSON.parse(get('source').value).revision, 3);
  assert.equal(get('editReview').hidden, true);

  // Declining replacement must not even read a file or issue a request.
  window.confirm = () => false;
  const beforeDecline = requests.length;
  await vm.runInContext("openProject({size:2,text:()=>{throw new Error('must not read')}})", context);
  assert.equal(requests.length, beforeDecline);
  window.confirm = () => true;

  // An edit made while a file is being read wins over that file's later completion.
  let finishRead;
  context.file = {size:2,text:()=>new Promise(resolve=>{finishRead=resolve})};
  task = vm.runInContext('openProject(file)', context);
  get('source').value = 'latest edit'; get('source').handlers.input();
  const beforeReadFinished = requests.length;
  finishRead('{}'); await task;
  assert.equal(requests.length, beforeReadFinished);
  assert.equal(get('source').value, 'latest edit');

  // A validated but obsolete import response must also not replace a newer edit.
  task = vm.runInContext("openProject({size:2,text:async()=> '{}'})", context);
  await flush();
  const obsolete = requests.at(-1);
  get('source').value = 'newer edit'; get('source').handlers.input();
  resolve(obsolete); await task;
  assert.equal(get('source').value, 'newer edit');
  assert.equal(get('downloads').children.length, 0);

  // The timeout aborts the browser request and gives accurate server-cancellation semantics.
  task = vm.runInContext('run()', context);
  const timedRequest = requests.at(-1);
  [...timers.values()][0]();
  assert.equal(timedRequest.options.signal.aborted, true);
  timedRequest.reject(new Error('aborted')); await task;
  assert.match(get('status').textContent, /server may still be compiling/);
  assert.equal(timers.size, 0);
  assert.equal(get('result').attrs['aria-busy'], 'false');

  get('source').value = 'x'.repeat(1048576);
  const beforeOversize = requests.length;
  await vm.runInContext('run()', context);
  assert.equal(requests.length, beforeOversize);
  assert.match(get('status').textContent, /Encoded request exceeds/);
})().catch(error => { console.error(error); process.exitCode=1; });
