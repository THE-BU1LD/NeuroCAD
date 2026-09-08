// The VM supplies only browser APIs. All workflow logic comes from core.workbench.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const script = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const elements = new Map(), requests = [], blobs = new Map(), revoked = [], timers = new Map();
let nextTimer = 0, nextBlob = 0;
function element() {
  return {value:'',textContent:'',innerHTML:'',disabled:false,children:[],attrs:{},handlers:{},
    setAttribute(k,v){this.attrs[k]=v}, addEventListener(k,v){this.handlers[k]=v},
    append(...nodes){this.children.push(...nodes)},replaceChildren(){this.children=[];this.innerHTML=''}};
}
const document = {querySelector(id){
  if (!elements.has(id)) elements.set(id, element());
  return elements.get(id);
},createElement:element};
const get = id => document.querySelector('#' + id);
get('source').value = 'original enclosure';
get('sourceType').value = 'enclosure';
const context = vm.createContext({document,AbortController,TextEncoder,Blob,Error,
  URL:{createObjectURL(blob){const url='blob:'+ ++nextBlob;blobs.set(url,blob);return url},
    revokeObjectURL(url){revoked.push(url);blobs.delete(url)}},
  setTimeout(callback){const id=++nextTimer;timers.set(id,callback);return id},
  clearTimeout(id){timers.delete(id)},
  fetch(url, options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))}
});
const flush = () => new Promise(resolve => setImmediate(resolve));
const payload = (name='fixture') => ({mode:'enclosure',project:{project_id:name,revision:2},
  spec:{wall_mm:2.4},ir:{body:{version:'ir'}},scad:{body:'cube([1,2,3]);'},
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

  // An invalid import keeps the existing input and usable output/downloads intact.
  const previousInput = get('source').value, previousOutput = get('scad').textContent;
  let task = vm.runInContext("openProject({size:2,text:async()=> '{}'})", context);
  await flush(); fail(requests.at(-1)); await task;
  assert.equal(get('source').value, previousInput);
  assert.equal(get('scad').textContent, previousOutput);
  assert.equal(get('downloads').children[0], projectLink);
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
