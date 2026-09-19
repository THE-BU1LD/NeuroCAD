"""Loopback-only live workbench for a persistent agent project."""

from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agentic import AgentWorkspace

MAX_EVENT_BYTES = 1_048_576

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NeuroCAD Agent Studio</title>
<style>
:root{color-scheme:dark;--ink:#e8f0f2;--muted:#8ca0a8;--line:#26363d;--panel:#10191e;--bg:#081014;--teal:#2dd4bf;--gold:#f5c451;--rose:#fb7185}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif;letter-spacing:0}
body{height:100vh;overflow:hidden}.topbar{height:56px;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 18px;gap:14px;background:#0b1418}
.mark{width:28px;height:28px;display:grid;place-items:center;border:1px solid var(--teal);color:var(--teal);font-weight:800}.brand{font-weight:750}.project{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.state{margin-left:auto;font-size:12px;text-transform:uppercase;color:var(--gold)}.layout{height:calc(100vh - 56px);display:grid;grid-template-columns:minmax(210px,280px) minmax(420px,1fr) minmax(250px,340px)}
.rail,.inspector{position:relative;z-index:1;background:var(--panel);overflow:auto}.rail{border-right:1px solid var(--line)}.inspector{border-left:1px solid var(--line)}.section{padding:16px;border-bottom:1px solid var(--line)}
h1,h2,p{margin:0}h1{font-size:15px}h2{font-size:11px;text-transform:uppercase;color:var(--muted);margin-bottom:12px}.summary{font-size:13px;line-height:1.55;color:#c9d5d9}
.component,.event,.assumption{padding:9px 0;border-bottom:1px solid #1b292f;font-size:12px}.component:last-child,.event:last-child,.assumption:last-child{border-bottom:0}.component strong{display:block;font-size:12px}.meta{color:var(--muted);margin-top:3px}
.stage{display:flex;gap:8px;align-items:flex-start}.dot{width:7px;height:7px;background:var(--teal);margin-top:5px;flex:0 0 auto}.event time{display:block;color:var(--muted);font-size:10px;margin-top:3px}
.canvas{min-width:0;display:grid;grid-template-rows:1fr 46px;background:#081018}.viewport{position:relative;display:grid;place-items:center;overflow:hidden;contain:strict;isolation:isolate}.viewport canvas{position:absolute;z-index:0;inset:0;width:100%;height:100%;touch-action:none}.empty{position:relative;z-index:1;color:var(--muted);font-size:13px;pointer-events:none}
.progress{border-top:1px solid var(--line);display:flex;align-items:center;padding:0 16px;gap:12px;background:#0b1418}.track{height:4px;background:#223138;flex:1}.fill{height:100%;background:var(--teal);width:0;transition:width .25s}.count{font-variant-numeric:tabular-nums;font-size:12px;color:var(--muted)}
.assumption strong{color:var(--gold);display:block}.assumption span{display:block;margin-top:3px;line-height:1.4}.assumption small{display:block;color:var(--muted);margin-top:4px}.artifact{display:block;color:var(--teal);text-decoration:none;padding:7px 0;font-size:12px}.artifact:hover{text-decoration:underline}
@media(max-width:900px){body{height:auto;overflow:auto}.layout{height:auto;grid-template-columns:1fr}.rail,.inspector{border:0}.canvas{height:60vh;order:-1}.topbar{position:sticky;top:0;z-index:2}.project{display:none}}
</style>
</head>
<body>
<header class="topbar"><div class="mark">N</div><div class="brand">NeuroCAD Agent Studio</div><div class="project" id="project">Waiting for project</div><div class="state" id="state">idle</div></header>
<main class="layout">
  <aside class="rail"><section class="section"><h2>Plan</h2><h1 id="title">No active design</h1><p class="summary" id="summary"></p></section><section class="section"><h2>Components</h2><div id="components"></div></section></aside>
  <section class="canvas"><div class="viewport" id="viewport"><canvas id="cad"></canvas><p class="empty" id="empty">Waiting for the first geometry stage</p></div><div class="progress"><div class="track"><div class="fill" id="fill"></div></div><div class="count" id="count">0 / 0</div></div></section>
  <aside class="inspector"><section class="section"><h2>Assumptions</h2><div id="assumptions"></div></section><section class="section"><h2>Activity</h2><div id="events"></div></section><section class="section"><h2>Artifacts</h2><a class="artifact" href="/design.scad">OpenSCAD source</a><a class="artifact" href="/design.ncad.json">Canonical IR</a><a class="artifact" href="/project.json">Project state</a></section></aside>
</main>
<script type="module" nonce="__NONCE__">
'use strict';
import * as THREE from '/static/three.module.min.js';
let lastKey='';
const byId=id=>document.getElementById(id);
const text=(tag,value,cls)=>{const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node};
const canvas=byId('cad'),viewport=byId('viewport');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1);
renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();scene.background=new THREE.Color(0x081018);
const camera=new THREE.PerspectiveCamera(42,1,.1,100000);camera.up.set(0,0,1);
scene.add(new THREE.HemisphereLight(0xd7f9f4,0x15242b,2.2));
const keyLight=new THREE.DirectionalLight(0xffffff,2.8);keyLight.position.set(2,-3,5);scene.add(keyLight);
const fillLight=new THREE.DirectionalLight(0x5eead4,1.2);fillLight.position.set(-4,2,2);scene.add(fillLight);
const grid=new THREE.GridHelper(2000,40,0x36515a,0x18272d);grid.rotation.x=Math.PI/2;scene.add(grid);
let assembly=new THREE.Group();scene.add(assembly);
let target=new THREE.Vector3(),distance=400,azimuth=-.9,elevation=.45,drag=null,userMoved=false;
function primitive(item){
  const p=item.parameters||{};let geometry;
  if(item.shape==='box'||item.shape==='rounded_box')geometry=new THREE.BoxGeometry(...p.size);
  else if(item.shape==='sphere')geometry=new THREE.SphereGeometry(p.radius,48,32);
  else if(item.shape==='cylinder'){geometry=new THREE.CylinderGeometry(p.radius,p.radius,p.height,48);geometry.rotateX(Math.PI/2)}
  else if(item.shape==='cone'){geometry=new THREE.CylinderGeometry(p.r2,p.r1,p.height,48);geometry.rotateX(Math.PI/2)}
  else if(item.shape==='torus')geometry=new THREE.TorusGeometry(p.major_radius,p.minor_radius,18,64);
  else return null;
  const subtract=item.operation==='subtract';
  const material=subtract?new THREE.MeshBasicMaterial({color:0xfb7185,wireframe:true,transparent:true,opacity:.58}):new THREE.MeshStandardMaterial({color:0x2dd4bf,roughness:.34,metalness:.18,transparent:true,opacity:.86,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(geometry,material),move=item.translate||[0,0,0],turn=item.rotate||[0,0,0];
  mesh.position.set(...move);mesh.rotation.set(...turn.map(THREE.MathUtils.degToRad));return mesh;
}
function disposeAssembly(){for(const child of assembly.children){child.geometry.dispose();child.material.dispose()}scene.remove(assembly);assembly=new THREE.Group();scene.add(assembly)}
function fitCamera(){
  const bounds=new THREE.Box3().setFromObject(assembly);if(bounds.isEmpty())return;
  const size=bounds.getSize(new THREE.Vector3());bounds.getCenter(target);distance=Math.max(size.length()*1.3,80);userMoved=false;updateCamera();
  grid.position.z=bounds.min.z;
}
function updateCamera(){const flat=distance*Math.cos(elevation);camera.position.set(target.x+flat*Math.cos(azimuth),target.y+flat*Math.sin(azimuth),target.z+distance*Math.sin(elevation));camera.lookAt(target)}
function rebuild(items,complete){disposeAssembly();for(const item of items.slice(0,complete)){const mesh=primitive(item);if(mesh)assembly.add(mesh)}byId('empty').hidden=assembly.children.length>0;if(assembly.children.length)fitCamera()}
function resize(){const width=Math.max(viewport.clientWidth,1),height=Math.max(viewport.clientHeight,1);renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix()}
new ResizeObserver(resize).observe(viewport);resize();
canvas.addEventListener('pointerdown',event=>{drag=[event.clientX,event.clientY];userMoved=true;canvas.setPointerCapture(event.pointerId)});
canvas.addEventListener('pointermove',event=>{if(!drag)return;azimuth-=(event.clientX-drag[0])*.008;elevation=Math.max(-1.25,Math.min(1.25,elevation+(event.clientY-drag[1])*.006));drag=[event.clientX,event.clientY];updateCamera()});
canvas.addEventListener('pointerup',()=>{drag=null});canvas.addEventListener('pointercancel',()=>{drag=null});
canvas.addEventListener('wheel',event=>{event.preventDefault();distance=Math.max(5,Math.min(100000,distance*Math.exp(event.deltaY*.001)));userMoved=true;updateCamera()},{passive:false});
function animate(){if(!drag&&!userMoved&&assembly.children.length){azimuth+=.001;updateCamera()}renderer.render(scene,camera);requestAnimationFrame(animate)}animate();
function render(state,events){
  if(!state)return;
  const plan=state.plan||{components:[],assumptions:[]};
  byId('project').textContent=state.project_id+' / revision '+state.revision+' / '+state.provider;
  byId('state').textContent=state.status==='draft_complete'?'draft':state.status;
  byId('title').textContent=state.title;
  byId('summary').textContent=plan.summary||'';
  const snapshot=state.current_snapshot||{};
  const complete=snapshot.stage||0,total=snapshot.stages_total||plan.components.length||0;
  byId('fill').style.width=(total?100*complete/total:0)+'%';byId('count').textContent=complete+' / '+total;
  const key=state.revision+':'+complete;
  if(key!==lastKey){rebuild(plan.components||[],complete);lastKey=key}
  const components=(plan.components||[]).map((item,index)=>{const row=text('div','', 'component');const name=text('strong',(index<complete?'[done] ':'')+item.label);row.append(name,text('div',item.part+' / '+item.operation+' '+item.shape,'meta'));return row});byId('components').replaceChildren(...components);
  const assumptions=(plan.assumptions||[]).map(item=>{const row=text('div','', 'assumption');row.append(text('strong',item.name+': '+item.value),text('span',item.reason),text('small',item.source));return row});byId('assumptions').replaceChildren(...assumptions);
  const activity=(events||[]).slice(-30).reverse().map(item=>{const row=text('div','', 'event');const stage=text('div','', 'stage');stage.append(text('span','', 'dot'),text('span',item.message));row.append(stage,text('time',item.at));return row});byId('events').replaceChildren(...activity);
}
async function refresh(){try{const response=await fetch('/api/state',{cache:'no-store'});if(response.ok){const data=await response.json();render(data.state,data.events)}}catch{}finally{setTimeout(refresh,500)}}
refresh();
</script>
</body></html>"""


class AgentWorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], workspace: AgentWorkspace):
        self.workspace = workspace
        super().__init__(address, AgentWorkbenchHandler)


class AgentWorkbenchHandler(BaseHTTPRequestHandler):
    server: AgentWorkbenchServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _headers(self, status: int, media_type: str, length: int, *, nonce: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        if nonce is not None:
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'none'; img-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'self' 'nonce-{nonce}'",
            )
        self.end_headers()

    def _send_bytes(self, body: bytes, media_type: str, status: int = HTTPStatus.OK) -> None:
        self._headers(status, media_type, len(body))
        self.wfile.write(body)

    def _events(self) -> list[dict[str, Any]]:
        path = self.server.workspace.events_path
        if not path.exists():
            return []
        with path.open("rb") as handle:
            size = path.stat().st_size
            if size > MAX_EVENT_BYTES:
                handle.seek(size - MAX_EVENT_BYTES)
                handle.readline()
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
        events: list[dict[str, Any]] = []
        for line in lines[-200:]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
        return events

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            nonce = secrets.token_urlsafe(18)
            body = HTML.replace("__NONCE__", nonce).encode("utf-8")
            self._headers(HTTPStatus.OK, "text/html; charset=utf-8", len(body), nonce=nonce)
            self.wfile.write(body)
            return
        if self.path == "/api/state":
            body = json.dumps({"state": self.server.workspace.read_state(), "events": self._events()}).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8")
            return
        files = {
            "/preview.svg": (self.server.workspace.root / "preview.svg", "image/svg+xml"),
            "/design.scad": (self.server.workspace.root / "design.scad", "text/plain; charset=utf-8"),
            "/design.ncad.json": (self.server.workspace.root / "design.ncad.json", "application/json; charset=utf-8"),
            "/project.json": (self.server.workspace.project_path, "application/json; charset=utf-8"),
            "/static/three.module.min.js": (
                Path(__file__).with_name("static") / "three.module.min.js",
                "text/javascript; charset=utf-8",
            ),
            "/static/three.core.min.js": (
                Path(__file__).with_name("static") / "three.core.min.js",
                "text/javascript; charset=utf-8",
            ),
        }
        route = self.path.split("?", 1)[0]
        if route in files and files[route][0].is_file():
            self._send_bytes(files[route][0].read_bytes(), files[route][1])
            return
        self._send_bytes(b'{"error":"not found"}', "application/json; charset=utf-8", HTTPStatus.NOT_FOUND)


def start_agent_workbench(
    workspace: AgentWorkspace,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    open_browser: bool = False,
) -> tuple[AgentWorkbenchServer, threading.Thread, str]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("agent workbench is loopback-only")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be an integer from 0 through 65535")
    workspace.initialize()
    server = AgentWorkbenchServer((host, port), workspace)
    address = server.server_address
    actual_host_raw, actual_port = address[0], int(address[1])
    actual_host = actual_host_raw.decode("ascii") if isinstance(actual_host_raw, bytes) else str(actual_host_raw)
    url_host = "[::1]" if actual_host == "::1" else actual_host
    url = f"http://{url_host}:{actual_port}/"
    thread = threading.Thread(target=server.serve_forever, name="neurocad-agent-workbench", daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(url)
    return server, thread, url
