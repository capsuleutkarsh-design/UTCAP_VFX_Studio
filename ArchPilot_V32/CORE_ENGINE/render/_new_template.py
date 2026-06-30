NEW_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UTCAP System Brain V32</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        :root {
            --bg-base: #050710;
            --bg-panel: rgba(9,12,24,0.96);
            --bg-surface: rgba(15,20,36,0.9);
            --border-subtle: rgba(255,255,255,0.07);
            --border-glow: rgba(59,130,246,0.3);
            --text-main: #e2e8f0;
            --text-muted: #475569;
            --text-dim: #94a3b8;
            --accent: #3b82f6;
            --accent-cyan: #22d3ee;
            --accent-purple: #a78bfa;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
            --sidebar-w: 310px;
        }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { width: 100%; height: 100%; overflow: hidden; }
        body { font-family: 'Inter', sans-serif; background: var(--bg-base); color: var(--text-main); display: flex; flex-direction: column; }

        #pcv { position: fixed; inset: 0; z-index: 0; pointer-events: none; }

        #hud {
            position: fixed; top: 0; left: 0; right: 0; height: 50px;
            background: rgba(5,7,16,0.9); backdrop-filter: blur(24px);
            border-bottom: 1px solid var(--border-subtle);
            display: flex; align-items: center; padding: 0 18px; gap: 15px;
            z-index: 100;
        }
        .hud-brand { font-size: 11px; font-weight: 900; letter-spacing: 2px; white-space: nowrap; }
        .hud-brand span { background: linear-gradient(90deg,#3b82f6,#a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        
        #breadcrumb { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
        #breadcrumb b { color: var(--accent-cyan); font-weight: 700; opacity: 0.8; }

        .hud-stats { display: flex; align-items: center; gap: 0; }
        .hud-stat { display: flex; flex-direction: column; align-items: center; padding: 0 12px; }
        .hud-val { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: var(--accent-cyan); line-height: 1; }
        .hud-lbl { font-size: 7px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
        .hud-sep { width: 1px; height: 22px; background: var(--border-subtle); }

        .hud-ctrls { display: flex; gap: 8px; margin-left: 10px; }
        .hbtn { background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle); color: var(--text-dim); padding: 4px 10px; border-radius: 4px; font-size: 9px; font-weight: 700; cursor: pointer; transition: all 0.15s; }
        .hbtn:hover { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; }

        #layout { display: flex; flex: 1; margin-top: 50px; height: calc(100vh - 50px); position: relative; z-index: 1; }

        #sidebar {
            width: var(--sidebar-w); min-width: var(--sidebar-w);
            background: var(--bg-panel); border-right: 1px solid var(--border-subtle);
            display: flex; flex-direction: column; z-index: 10; overflow-y: auto;
            transition: transform 0.3s ease;
        }
        #sidebar.collapsed { transform: translateX(-100%); width: 0; min-width: 0; }
        #sbtoggle {
            position: absolute; top: 50%; left: var(--sidebar-w); transform: translateY(-50%);
            width: 16px; height: 50px; background: var(--bg-surface);
            border: 1px solid var(--border-subtle); border-left: none;
            color: var(--text-muted); cursor: pointer; font-size: 8px;
            display: flex; align-items: center; justify-content: center;
            z-index: 50; border-radius: 0 4px 4px 0; transition: left 0.3s ease;
        }
        #sidebar.collapsed + #sbtoggle { left: 0; }

        .dock-hdr { padding: 15px 18px; border-bottom: 1px solid var(--border-subtle); }
        .dock-hdr h1 { font-size: 12px; font-weight: 900; letter-spacing: 1.5px; }
        .dock-sub { font-size: 8px; color: var(--text-muted); text-transform: uppercase; margin-top: 2px; }
        
        .dock-sec { padding: 12px 15px; border-bottom: 1px solid var(--border-subtle); }
        .sec-ttl { font-size: 8px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 9px; }

        #searchBar {
            width: 100%; padding: 7px 10px; border: 1px solid var(--border-subtle);
            border-radius: 5px; background: rgba(0,0,0,0.3); color: var(--text-main); font-size: 11px; outline: none;
        }

        .btn-grp { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
        .btn {
            width: 100%; padding: 6px 10px; background: transparent;
            border: 1px solid var(--border-subtle); color: var(--text-dim);
            border-radius: 4px; cursor: pointer; font-size: 9px; font-weight: 700; transition: all 0.15s; text-align: left;
        }
        .btn:hover { background: rgba(255,255,255,0.03); color: #fff; }
        .btn.active { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; box-shadow: 0 0 10px rgba(59,130,246,0.1); }

        .f-chips { display: flex; flex-wrap: wrap; gap: 4px; }
        .f-chip { padding: 3px 8px; border-radius: 12px; font-size: 8px; font-weight: 800; border: 1px solid var(--border-subtle); cursor: pointer; transition: all 0.15s; opacity: 0.6; }
        .f-chip:hover { opacity: 1; }
        .f-chip.active { opacity: 1; box-shadow: 0 0 8px currentColor; }

        .legend-list { display: flex; flex-direction: column; gap: 5px; }
        .lg-item { display: flex; align-items: center; gap: 8px; font-size: 9px; color: var(--text-dim); }
        .lg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .lg-bar { width: 12px; height: 4px; border-radius: 2px; flex-shrink: 0; }

        #netbox { flex-grow: 1; position: relative; }
        #netmap { width: 100%; height: 100%; outline: none; }

        #inspector {
            position: fixed; top: 50px; right: -420px; width: 400px;
            height: calc(100vh - 50px); background: var(--bg-panel);
            backdrop-filter: blur(30px); border-left: 1px solid var(--border-subtle);
            transition: right 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
            z-index: 200; display: flex; flex-direction: column;
        }
        #inspector.open { right: 0; }
        /* Inspector styles same as before... */
        .ins-hdr { padding: 16px 18px; border-bottom: 1px solid var(--border-subtle); flex-shrink: 0; position: relative; }
        .ins-close { position: absolute; right: 15px; top: 15px; cursor: pointer; color: var(--text-muted); background: none; border: none; font-size: 18px; }
        .ins-title { font-size: 18px; font-weight: 900; margin-bottom: 6px; }
        
        .tag { background: rgba(255,255,255,0.05); border: 1px solid var(--border-subtle); border-radius: 4px; padding: 2px 7px; font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--text-dim); cursor: pointer; transition: all 0.15s; margin-right: 4px; margin-bottom: 4px; display: inline-block; }
        .tag:hover { background: rgba(59,130,246,0.15); border-color: var(--accent); color: #fff; }
        .ins-body { padding: 15px 18px; overflow-y: auto; flex-grow: 1; }
        .doc-box { background: rgba(0,0,0,0.2); border: 1px solid var(--border-subtle); padding: 9px 12px; border-radius: 6px; font-size: 11px; color: var(--text-dim); margin-bottom: 15px; white-space: pre-wrap; line-height: 1.5; }
        .cpx-bar { margin-bottom: 15px; }
        .cpx-hdr { display: flex; justify-content: space-between; font-size: 9px; font-weight: 700; color: var(--text-muted); margin-bottom: 5px; }
        .cpx-track { height: 5px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
        .cpx-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg,var(--accent),var(--accent-purple)); transition: width 0.8s; }
        details { background: rgba(0,0,0,0.15); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 10px; margin-bottom: 10px; }
        summary { font-size: 10px; font-weight: 800; color: var(--text-dim); cursor: pointer; list-style: none; display: flex; justify-content: space-between; }
        summary::after { content: '＋'; color: var(--text-muted); }
        details[open] summary::after { content: '－'; }
        .tag-list { margin-top: 8px; }

        /* MODAL */
        #code-viewer { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 40px; }
        #code-viewer.open { display: flex; }
        .modal { width: 100%; max-width: 1100px; height: 85vh; background: #1e1e1e; border-radius: 12px; border: 1px solid var(--border-glow); display: flex; flex-direction: column; overflow: hidden; }
        .modal-hdr { padding: 12px 20px; background: #252526; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .modal-body { flex: 1; overflow: auto; padding: 0; }
        .modal-body pre { margin:0; }
        .modal-body code { font-family:'JetBrains Mono'; font-size: 13px; padding: 25px !important; }

        /* CHAT */
        #ai-fab { position: fixed; bottom: 20px; right: 20px; width: 48px; height: 48px; border-radius: 50%; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 20px; z-index: 500; box-shadow: 0 8px 30px rgba(59,130,246,0.4); }
        #ai-panel { position: fixed; bottom: 80px; right: 20px; width: 350px; height: 450px; background: var(--bg-panel); backdrop-filter: blur(30px); border: 1px solid var(--border-glow); border-radius: 14px; display: none; flex-direction: column; z-index: 500; box-shadow: 0 20px 80px rgba(0,0,0,0.8); }
        #ai-panel.open { display: flex; }
        .msgs { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { padding: 8px 12px; border-radius: 10px; font-size: 12px; line-height: 1.5; max-width: 90%; }
        .msg.user { align-self: flex-end; background: var(--accent); color: #fff; }
        .msg.bot { align-self: flex-start; background: rgba(59,130,246,0.1); border: 1px solid var(--border-subtle); }
        .inp-area { padding: 10px; border-top: 1px solid var(--border-subtle); display: flex; gap: 8px; }
        #ai_input { flex: 1; background: rgba(0,0,0,0.2); border: 1px solid var(--border-subtle); border-radius: 6px; color: #fff; padding: 8px 12px; font-size: 12px; outline: none; }
        #ai_send { background: var(--accent); border: none; color:#fff; width: 34px; border-radius: 6px; cursor: pointer; }
    </style>
</head>
<body>
<canvas id="pcv"></canvas>

<div id="hud">
    <div class="hud-brand">&#x2B22; UTCAP <span>SYSTEM BRAIN</span></div>
    <div id="breadcrumb">Select a node to begin exploration...</div>
    <div class="hud-stats">
        <div class="hud-stat"><span class="hud-val" id="h_mod">0</span><span class="hud-lbl">Modules</span></div>
        <div class="hud-sep"></div>
        <div class="hud-stat"><span class="hud-val" id="h_files">0</span><span class="hud-lbl">Files</span></div>
        <div class="hud-sep"></div>
        <div class="hud-stat"><span class="hud-val" id="h_orp">0</span><span class="hud-lbl">Orphans</span></div>
        <div class="hud-sep"></div>
        <div class="hud-stat"><span class="hud-val" id="h_circ">0</span><span class="hud-lbl">Circular</span></div>
        <div class="hud-sep"></div>
        <div class="hud-stat"><span class="hud-val" id="h_cls">0</span><span class="hud-lbl">Classes</span></div>
        <div class="hud-sep"></div>
        <div class="hud-stat" style="border:none"><span class="hud-val" id="h_fn">0</span><span class="hud-lbl">Functions</span></div>
    </div>
    <div class="hud-ctrls">
        <button class="hbtn" onclick="net.expandAll()">Expand All</button>
        <button class="hbtn" onclick="net.collapseAll()">Collapse All</button>
        <button class="hbtn" onclick="resetView()">Reset</button>
    </div>
</div>

<div id="layout">
    <div id="sidebar">
        <div class="dock-hdr"><h1>ARCH-PILOT</h1><div class="dock-sub">Comprehensive Analysis V32</div></div>
        <div class="dock-sec"><input type="text" id="searchBar" placeholder="Search modules, files, classes..."></div>
        
        <div class="dock-sec">
            <div class="sec-ttl">Trace Mode</div>
            <div class="btn-grp">
                <button class="btn active" id="tm_ins" onclick="setTrace('ins')">Inspector</button>
                <button class="btn" id="tm_path" onclick="setTrace('path')">Pathfinder (Up)</button>
                <button class="btn" id="tm_blast" onclick="setTrace('blast')">Blast (Down)</button>
            </div>
        </div>

        <div class="dock-sec">
            <div class="sec-ttl">Heatmap</div>
            <div class="btn-grp">
                <button class="btn" id="hm_cpx" onclick="setHeat('cpx')">Complexity</button>
                <button class="btn" id="hm_risk" onclick="setHeat('risk')">Risk / Churn</button>
                <button class="btn active" id="hm_norm" onclick="setHeat('norm')">Normal Colors</button>
                <button class="btn" id="hm_circ" onclick="setHeat('circ')">Cycle Alert</button>
            </div>
        </div>

        <div class="dock-sec">
            <div class="sec-ttl">Filter by Layer</div>
            <div class="f-chips" id="fchips"></div>
        </div>

        <div class="dock-sec" style="border:none">
            <div class="sec-ttl">Legend</div>
            <div class="legend-list" id="legend"></div>
        </div>
    </div>
    <button id="sbtoggle" onclick="toggleSidebar()">&#9664;</button>
    <div id="netbox"><div id="netmap"></div></div>
</div>

<div id="code-viewer">
    <div class="modal">
        <div class="modal-hdr"><span id="m_path" style="font-family:'JetBrains Mono'; font-size:12px; color:#aaa"></span><button style="background:none; border:none; color:#888; cursor:pointer; font-size:18px;" onclick="closeCode()">&#x2715;</button></div>
        <div class="modal-body"><pre><code id="m_code" class="language-python"></code></pre></div>
    </div>
</div>

<div id="inspector">
    <div class="ins-hdr"><button class="ins-close" onclick="closeIns()">&#10005;</button><div class="ins-title" id="i_title">Module Name</div><div id="i_group" class="tag">GROUP</div></div>
    <div class="ins-body">
        <div id="i_doc" class="doc-box"></div>
        <div class="cpx-bar"><div class="cpx-hdr"><span>Architectural Complexity</span><span id="i_cpx_v">0</span></div><div class="cpx-track"><div id="i_cpx_f" class="cpx-fill" style="width:0%"></div></div></div>
        <details open><summary><span>Source Files</span><span id="i_f_c" style="color:var(--text-muted)">0</span></summary><div id="i_files" class="tag-list"></div></details>
        <details><summary><span>Internal Classes</span><span id="i_c_c" style="color:var(--text-muted)">0</span></summary><div id="i_classes" class="tag-list"></div></details>
        <details><summary><span>Internal Functions</span><span id="i_fn_c" style="color:var(--text-muted)">0</span></summary><div id="i_funcs" class="tag-list"></div></details>
    </div>
</div>

<div id="ai-fab" onclick="toggleAI()">&#129302;</div>
<div id="ai-panel">
    <div class="msgs" id="ai_msgs"></div>
    <div class="inp-area"><input type="text" id="ai_input" placeholder="Ask System Brain..."><button id="ai_send" onclick="sendAI()">&#x27A4;</button></div>
</div>

<script type="application/json" id="gd">__JSON_PAYLOAD__</script>
<script>
const RAW=JSON.parse(document.getElementById('gd').textContent), MAIN=RAW.main_nodes, SUBS=RAW.sub_nodes_dict, EDGES=RAW.main_edges;
const GCOL={ entry:'#ef4444',ui:'#3b82f6',core:'#10b981',db:'#8b5cf6',messenger:'#a855f7',workers:'#f59e0b',external:'#eab308',ai:'#22d3ee',tools:'#a78bfa' };
const GICO={ entry:'🚪',ui:'🖥',core:'⚙️',db:'🗃',messenger:'💬',workers:'⚡',ai:'🤖',tools:'🛠' };

let nodesDS=new vis.DataSet(MAIN.map(n=>sNode(n, true))), edgesDS=new vis.DataSet(EDGES.map(e=>({id:e.id, from:e.from, to:e.to, arrows:'to', color:{color:'rgba(255,255,255,0.15)'}, dashes:true, smooth:{type:'curvedCW', roundness:0.2}})));
const net=new vis.Network(document.getElementById('netmap'), {nodes:nodesDS, edges:edgesDS}, { physics:{solver:'forceAtlas2Based', stabilization:true}, interaction:{hover:true}});

let traceMode='ins', heatMode='norm', hiddenGroups=new Set();

function sNode(raw, isM){
    const i=raw.info||{}, base=GCOL[raw.group]||'#3b82f6', c=i.complexity||0;
    let bdr=base;
    if(heatMode==='cpx') bdr=c>1000?'#ef4444':c>500?'#f59e0b':'#10b981';
    if(heatMode==='risk') bdr=i.risk_score>80?'#ef4444':i.risk_score>40?'#f59e0b':'#10b981';
    if(heatMode==='circ') bdr=i.circular_count>0?'#ef4444':base;

    return { 
        id:raw.id, 
        label:(GICO[raw.group]||'○')+' '+raw.label, 
        shape:isM?'box':'dot', 
        size:isM?25:12, 
        color:{background:'#080b18', border:bdr, highlight:{background:'#0f1425',border:bdr}}, 
        font:{color:'#e2e8f0', size:isM?13:10, face:'Inter'}, 
        borderWidth:isM?3:1,
        shadow:{enabled:true, color:bdr, size:10, x:0, y:0},
        _raw:raw 
    };
}

// DASH ANIMATION
let offset=0;
function animate(){
    offset++; if(offset>100) offset=0;
    const flows=edgesDS.get({filter:e=>e.arrows==='to'});
    edgesDS.update(flows.map(e=>({id:e.id, dashOffset:-offset})));
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

function setTrace(m){ traceMode=m; document.querySelectorAll('[id^=tm_]').forEach(b=>b.classList.remove('active')); document.getElementById('tm_'+m).classList.add('active'); }
function setHeat(m){ heatMode=m; document.querySelectorAll('[id^=hm_]').forEach(b=>b.classList.remove('active')); document.getElementById('hm_'+m).classList.add('active'); refreshNodes(); }

function refreshNodes(){
    nodesDS.update(nodesDS.get().map(n=>sNode(n._raw, n.shape==='box')));
}

function showIns(node){
    const i=node.info||{};
    document.getElementById('i_title').innerText=node.label;
    document.getElementById('i_group').innerText=node.group.toUpperCase();
    document.getElementById('i_doc').innerText=i.doc||'No documentation.';
    document.getElementById('i_cpx_v').innerText=i.complexity||0;
    document.getElementById('i_cpx_f').style.width=Math.min(100, (i.complexity/1500)*100)+'%';
    document.getElementById('breadcrumb').innerHTML=`Project <b>/</b> ${node.group.toUpperCase()} <b>/</b> ${node.label}`;
    
    renderTags('i_files', i.files||[], true);
    renderTags('i_classes', i.classes||[]);
    renderTags('i_funcs', i.funcs||[]);
    document.querySelector('#i_f_c').innerText=i.files?.length||0;
    document.querySelector('#i_c_c').innerText=i.classes?.length||0;
    document.querySelector('#i_fn_c').innerText=i.funcs?.length||0;
    if(traceMode==='ins') document.getElementById('inspector').classList.add('open');
    if(traceMode==='path') runTrace(node.id, 'up');
    if(traceMode==='blast') runTrace(node.id, 'down');
}

function runTrace(nodeId, dir){
    const traceSet=new Set([nodeId]);
    const queue=[nodeId];
    while(queue.length){
        const curr=queue.shift();
        const neighbors=dir==='up'?net.getConnectedNodes(curr, 'to'):net.getConnectedNodes(curr, 'from');
        neighbors.forEach(n=>{ if(!traceSet.has(n)){traceSet.add(n); queue.push(n);} });
    }
    nodesDS.update(nodesDS.get().map(n=>({id:n.id, opacity:traceSet.has(n.id)?1:0.1})));
}

function resetView(){ 
    nodesDS.update(nodesDS.get().map(n=>({id:n.id, opacity:1}))); 
    net.fit(); 
}

function renderTags(id, items, link=false){
    const box=document.getElementById(id); 
    box.innerHTML=items.map(v=>`<div class="tag" ${link?`onclick="viewSource('${v}')"`:''}>${v}</div>`).join('')||'None';
}

async function viewSource(p){
    const m=document.getElementById('code-viewer'), c=document.getElementById('m_code');
    document.getElementById('m_path').innerText=p; c.innerText='Loading...'; m.classList.add('open');
    try {
        const resp=await fetch(`/api/file?path=${encodeURIComponent(p)}`), d=await resp.json();
        if(d.error) throw new Error(d.error);
        c.innerText=d.content; hljs.highlightElement(c);
    } catch(e){ c.innerText='Error: '+e.message; }
}

function closeCode(){ document.getElementById('code-viewer').classList.remove('open'); }
function closeIns(){ document.getElementById('inspector').classList.remove('open'); }
function toggleSidebar(){ document.getElementById('sidebar').classList.toggle('collapsed'); }
function toggleAI(){ document.getElementById('ai-panel').classList.toggle('open'); }

// FILTER & LEGEND
const fbox=document.getElementById('fchips'), lbox=document.getElementById('legend');
Object.keys(GCOL).forEach(g=>{
    fbox.innerHTML+=`<div class="f-chip active" style="color:${GCOL[g]}" onclick="toggleLayer('${g}', this)">${g.toUpperCase()}</div>`;
    lbox.innerHTML+=`<div class="lg-item"><div class="lg-bar" style="background:${GCOL[g]};box-shadow:0 0 5px ${GCOL[g]}"></div><span>${g.toUpperCase()}</span></div>`;
});

function toggleLayer(g, el){
    el.classList.toggle('active');
    if(hiddenGroups.has(g)) hiddenGroups.delete(g); else hiddenGroups.add(g);
    nodesDS.update(nodesDS.get().map(n=>({id:n.id, hidden:hiddenGroups.has(n._raw.group)})));
}

net.on('click', p=>{ if(p.nodes[0]) showIns(nodesDS.get(p.nodes[0])._raw); else resetView(); });

// STATS
let orp=0, circ=0, cls=0, fns=0;
MAIN.forEach(n=>{
    if(n.info?.orphan) orp++;
    if(n.info?.circular_count) circ++;
    cls+=n.info?.classes?.length||0;
    fns+=n.info?.funcs?.length||0;
});
document.getElementById('h_mod').innerText=MAIN.length;
document.getElementById('h_files').innerText=RAW.total_files||0;
document.getElementById('h_orp').innerText=orp;
document.getElementById('h_circ').innerText=circ;
document.getElementById('h_cls').innerText=cls;
document.getElementById('h_fn').innerText=fns;
</script>
</body>
</html>"""
