async function fetchJson(path, opts={}){
    // ensure cookies are sent for session auth
    opts.credentials = opts.credentials || 'same-origin';

    // attach CSRF token for unsafe methods
    const method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const token = meta ? meta.getAttribute('content') : null;
        opts.headers = Object.assign({'X-CSRFToken': token, 'X-CSRF-Token': token, 'X-Requested-With': 'XMLHttpRequest'}, opts.headers || {});
    }

    const res = await fetch(path, opts);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

function el(tag, text){ const d=document.createElement(tag); if(text!==undefined) d.textContent=text; return d }

async function loadPending(){
    try{
        const data = await fetchJson('/api/steward/reservations');
        const container = document.getElementById('pending-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No pending reservations.'; return }
        const ul = document.createElement('ul');
        data.forEach(r=>{
            const li = document.createElement('li');
            li.textContent = `#${r.id} customer:${r.customer_id} ${r.start_ts} - ${r.status}`;
            const seatBtn = document.createElement('button'); seatBtn.textContent='Seat';
            seatBtn.onclick = async ()=>{
                await fetchJson(`/api/steward/reservations/${r.id}/seat`,{method:'PATCH'});
                await reloadAll();
            }
            li.appendChild(seatBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('pending-list').textContent='Error loading'; }
}

async function loadSeated(){
    try{
        const data = await fetchJson('/api/steward/reservations/seated');
        const container = document.getElementById('seated-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No seated reservations.'; return }
        const ul = document.createElement('ul');
        data.forEach(r=>{
            const li = document.createElement('li');
            li.textContent = `#${r.id} customer:${r.customer_id} ${r.start_ts} - ${r.status}`;
            const compBtn = document.createElement('button'); compBtn.textContent='Complete';
            compBtn.onclick = async ()=>{
                await fetchJson(`/api/steward/reservations/${r.id}/complete`,{method:'PATCH'});
                await reloadAll();
            }
            li.appendChild(compBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('seated-list').textContent='Error loading'; }
}

async function loadGameCopies(){
    try{
        const data = await fetchJson('/api/steward/game-copies');
        const container = document.getElementById('game-copy-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No game copies.'; return }
        const ul = document.createElement('ul');
        data.forEach(c=>{
            const li = document.createElement('li');
            li.textContent = `#${c.id} ${c.copy_code} status:${c.status}`;
            const statusBtn = document.createElement('button'); statusBtn.textContent='Set Lost';
            statusBtn.onclick = async ()=>{
                await fetchJson(`/api/steward/game-copies/${c.id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'lost'})});
                await reloadAll();
            }
            li.appendChild(statusBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('game-copy-list').textContent='Error loading'; }
}

async function loadIncidents(){
    try{
        const data = await fetchJson('/api/steward/incidents');
        const container = document.getElementById('incident-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No incidents.'; return }
        const ul = document.createElement('ul');
        data.forEach(i=>{
            const li = document.createElement('li');
            li.textContent = `#${i.id} copy:${i.game_copy_id} type:${i.incident_type} note:${i.note}`;
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('incident-list').textContent='Error loading'; }
}

async function reloadAll(){
    await Promise.all([loadPending(), loadSeated(), loadGameCopies(), loadIncidents()]);
}

window.addEventListener('DOMContentLoaded', ()=>{
    const bindLink = (id, fn) => {
        const a = document.getElementById(id);
        if (!a) return;
        a.addEventListener('click', (e) => {
            const href = a.getAttribute('href') || '';
            // If the link points to a real path, allow normal navigation so the server renders page.
            if (href.startsWith('/')) return;
            e.preventDefault();
            fn();
        });
    };

    bindLink('link-pending', loadPending);
    bindLink('link-seated', loadSeated);
    bindLink('link-game-copies', loadGameCopies);
    bindLink('link-incidents', loadIncidents);
    // initial load
    reloadAll();
});
