"""Execute the shipped UI script with a deliberately delayed response."""

import json
import re
import shutil
import subprocess

import pytest

from core.demo_server import HTML


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable for browser-script contract")
@pytest.mark.parametrize("failure", [False, True])
def test_late_response_cannot_revalidate_edited_input(failure: bool) -> None:
    script = re.search(r'<script nonce="__NONCE__">(.*?)</script>', HTML, re.DOTALL)
    assert script is not None
    harness = r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
function element(){return {value:'original',textContent:'',innerHTML:'',disabled:false,
 attrs:{},handlers:{},setAttribute(k,v){this.attrs[k]=v},
 addEventListener(k,v){this.handlers[k]=v},append(){},replaceChildren(){}}}
const document={querySelector(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element};
let finish;
const context={document,fetch:()=>new Promise((resolve,reject)=>{finish={resolve,reject}})};
vm.runInNewContext(SCRIPT,context);
elements.get('#source').value='changed';elements.get('#source').handlers.input();
if(FAILURE)finish.reject(new Error('obsolete failure'));
else finish.resolve({ok:true,json:async()=>({scad:'STALE GEOMETRY',preview_svg:'stale',ir:{},validation:{},evaluation:{kernel_validity:null,structural_validity:true,editable_nodes:1,evaluation_latency_ms:1}})});
setImmediate(()=>{
 assert.equal(elements.get('#scad').textContent,'');
 assert.equal(elements.get('#status').textContent,'Input changed; run validation before using any output.');
 assert.equal(elements.get('#generate').disabled,false);
 assert.equal(elements.get('#result').attrs['aria-busy'],'false');
});
'''
    harness = harness.replace("SCRIPT", json.dumps(script.group(1))).replace("FAILURE", json.dumps(failure))
    completed = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=10, check=False)
    assert completed.returncode == 0, completed.stderr
