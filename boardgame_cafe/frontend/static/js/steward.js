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

const RECENT_REALTIME_EVENTS = new Map();

function shouldHandleRealtimeEvent(eventKey){
    const now = Date.now();
    const lastSeen = RECENT_REALTIME_EVENTS.get(eventKey);
    if (lastSeen && (now - lastSeen) < 2000) {
        return false;
    }
    RECENT_REALTIME_EVENTS.set(eventKey, now);

    // Keep memory bounded.
    if (RECENT_REALTIME_EVENTS.size > 100) {
        const expiryThreshold = now - 15000;
        for (const [key, ts] of RECENT_REALTIME_EVENTS.entries()) {
            if (ts < expiryThreshold) {
                RECENT_REALTIME_EVENTS.delete(key);
            }
        }
    }

    return true;
}

function normalizeRealtimeEventType(payload){
    const raw = String((payload && (payload.event_type || payload.event)) || '').trim();
    if (!raw) return null;

    // Convert CamelCase event names (ReservationCreated) into dotted lowercase (reservation.created).
    if (raw.includes('.')) return raw.toLowerCase();
    return raw
        .replace(/([a-z0-9])([A-Z])/g, '$1.$2')
        .replace(/_/g, '.')
        .toLowerCase();
}

function getRealtimeNoticeContainer(){
    let container = document.getElementById('steward-realtime-notices');
    if (container) return container;

    const host = document.getElementById('steward-data');
    if (!host) return null;

    container = document.createElement('div');
    container.id = 'steward-realtime-notices';
    container.setAttribute('aria-live', 'polite');
    container.style.display = 'grid';
    container.style.gap = '8px';
    container.style.marginBottom = '12px';
    host.prepend(container);
    return container;
}

function showRealtimeNotice(message, tone='info'){
    const container = getRealtimeNoticeContainer();
    if (!container) return;

    const notice = document.createElement('div');
    notice.textContent = message;
    notice.style.padding = '10px 12px';
    notice.style.borderRadius = '8px';
    notice.style.border = '1px solid #cbd5e1';
    notice.style.background = tone === 'success' ? '#ecfdf5' : '#f8fafc';
    notice.style.color = '#111827';
    notice.style.fontSize = '14px';
    notice.style.fontWeight = '500';
    container.prepend(notice);

    while (container.children.length > 5) {
        container.removeChild(container.lastChild);
    }

    setTimeout(() => {
        if (notice.parentNode === container) {
            container.removeChild(notice);
        }
    }, 12000);
}

async function loadPending(){
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/reservations' + q);
        const container = document.getElementById('pending-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No pending reservations.'; return }
        const ul = document.createElement('ul');
        data.forEach(r=>{
            const li = document.createElement('li');
            li.textContent = `#${r.id} customer:${r.customer_id} ${r.start_ts} - ${r.status}`;
            // row is not clickable; use the Edit button to open the side panel
            const seatBtn = document.createElement('button'); seatBtn.textContent='Seat';
            seatBtn.onclick = async ()=>{
                await fetchJson(`/api/steward/reservations/${r.id}/seat`,{method:'PATCH'});
                await reloadAll();
            }
            seatBtn.addEventListener('click', (e)=>e.stopPropagation());
            li.appendChild(seatBtn);

            const editBtn = document.createElement('button'); editBtn.textContent='Edit';
            editBtn.onclick = (e) => { e.stopPropagation(); showReservationPanel(r); };
            li.appendChild(editBtn);

            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('pending-list').textContent='Error loading'; }
}

async function loadSeated(){
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/reservations/seated' + q);
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
            compBtn.addEventListener('click', (e)=>e.stopPropagation());
            li.appendChild(compBtn);

            const editBtn = document.createElement('button'); editBtn.textContent='Edit';
            editBtn.onclick = (e) => { e.stopPropagation(); showReservationPanel(r); };
            li.appendChild(editBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('seated-list').textContent='Error loading'; }
}

async function loadGameCopies(){
    try{
        // Game copies are global (no date filter)
        const data = await fetchJson('/api/steward/game-copies');
        const container = document.getElementById('game-copy-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No game copies.'; return }
        const ul = document.createElement('ul');
        data.forEach(c=>{
            const li = document.createElement('li');
            li.textContent = `#${c.id} ${c.copy_code} status:${c.status}`;
            const statusBtn = document.createElement('button');
            if (c.status === 'lost') {
                statusBtn.textContent = 'Remove Lost';
                statusBtn.onclick = async () => {
                    // 'return' action will set status back to available
                    await fetchJson(`/api/steward/game-copies/${c.id}/status`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:'return'})});
                    await reloadAll();
                }
            } else {
                statusBtn.textContent = 'Set Lost';
                statusBtn.onclick = async () => {
                    await fetchJson(`/api/steward/game-copies/${c.id}/status`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:'lost'})});
                    await reloadAll();
                }
            }
            li.appendChild(statusBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('game-copy-list').textContent='Error loading'; }
}

async function loadFloorplan(){
    try{
        const date = (document.getElementById('live-date') || {}).value;
        if(!date) return;
        // use full day window
        const start = new Date(date + 'T00:00:00');
        const end = new Date(date + 'T23:59:59');
        const qs = `?start_ts=${encodeURIComponent(start.toISOString())}&end_ts=${encodeURIComponent(end.toISOString())}&party_size=1`;
        const resp = await fetchJson('/api/tables/availability' + qs);

        const floorSelect = document.getElementById('floor-select');
        const floorplan = document.getElementById('floorplan');
        floorplan.innerHTML = '';
        floorSelect.innerHTML = '';

        const floors = resp.floors || [];
        if (!floors.length) { floorplan.textContent = 'No tables defined.'; return }

        // populate floor dropdown
        floors.forEach((f, idx)=>{
            const opt = document.createElement('option'); opt.value = String(f.floor); opt.textContent = 'Floor ' + String(f.floor);
            floorSelect.appendChild(opt);
        });

        // render chosen floor (default first)
        const render = (floorNum) => {
            floorplan.innerHTML = '';
            const floor = floors.find(x => String(x.floor) === String(floorNum)) || floors[0];
            floor.zones.forEach(zone => {
                const zdiv = document.createElement('div');
                zdiv.style.marginBottom = '8px';
                const zh = document.createElement('div'); zh.textContent = zone.zone; zh.style.fontWeight='600';
                zdiv.appendChild(zh);
                const grid = document.createElement('div');
                grid.style.display='flex'; grid.style.flexWrap='wrap'; grid.style.gap='8px';
                zone.tables.forEach(t => {
                    const box = document.createElement('div');
                    box.style.width='80px'; box.style.height='50px'; box.style.border='1px solid #bbb'; box.style.display='flex'; box.style.flexDirection='column'; box.style.alignItems='center'; box.style.justifyContent='center'; box.style.borderRadius='4px';
                    box.style.background = t.available ? '#d4ffd4' : '#ffd6d6';
                    box.title = `Table ${t.table_nr} (cap ${t.capacity})` + (t.available ? ' — available' : ' — reserved/unavailable');
                    const tn = document.createElement('div'); tn.textContent = 'T' + t.table_nr; tn.style.fontWeight='600';
                    const cap = document.createElement('div'); cap.textContent = t.capacity + 'p'; cap.style.fontSize='12px';
                    box.appendChild(tn); box.appendChild(cap);
                    grid.appendChild(box);
                });
                zdiv.appendChild(grid);
                floorplan.appendChild(zdiv);
            });
        };

        floorSelect.addEventListener('change', ()=>render(floorSelect.value));
        render(floorSelect.value || floors[0].floor);
    }catch(e){ console.error(e); document.getElementById('floorplan').textContent='Error loading floorplan'; }
}

async function loadIncidents(){
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/incidents' + q);
        const container = document.getElementById('incident-list');
        container.innerHTML='';
        if(!data.length) { container.textContent='No incidents.'; return }
        const ul = document.createElement('ul');
        data.forEach(i=>{
            const li = document.createElement('li');
            li.textContent = `#${i.id} copy:${i.game_copy_id} type:${i.incident_type} note:${i.note}`;
            const delBtn = document.createElement('button'); delBtn.textContent='Delete';
            delBtn.onclick = async ()=>{
                if(!confirm('Delete incident #' + i.id + '?')) return;
                await fetchJson(`/api/steward/incidents/${i.id}`,{method:'DELETE'});
                await reloadAll();
            }
            li.appendChild(delBtn);
            ul.appendChild(li);
        });
        container.appendChild(ul);
    }catch(e){ console.error(e); document.getElementById('incident-list').textContent='Error loading'; }
}

async function reloadAll(){
    await Promise.all([loadPending(), loadSeated(), loadGameCopies(), loadIncidents(), loadFloorplan()]);
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
    // initialize date picker to today
    const dateInput = document.getElementById('live-date');
    if (dateInput) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth()+1).padStart(2,'0');
        const dd = String(today.getDate()).padStart(2,'0');
        dateInput.value = `${yyyy}-${mm}-${dd}`;
        dateInput.addEventListener('change', () => reloadAll());
    }

    // initial load
    reloadAll();
    // subscribe to realtime domain events to update dashboard live
    try {
        const es = new EventSource('/api/events/stream');
        es.addEventListener('domain_event', (e) => {
            try {
                const payload = JSON.parse(e.data);
                const et = normalizeRealtimeEventType(payload);
                if (!et) return;

                if (et === 'reservation.payment.completed') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `reservation.payment.completed:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    const tables = Array.isArray(data.table_numbers) && data.table_numbers.length
                        ? ` (tables ${data.table_numbers.join(', ')})`
                        : '';
                    showRealtimeNotice(`Payment received for booking #${reservationId}${tables}.`, 'success');
                    reloadAll();
                    return;
                }

                if (et === 'reservation.cancelled') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `reservation.cancelled:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    const cancelledBy = data.cancelled_by_role ? ` by ${data.cancelled_by_role}` : '';
                    showRealtimeNotice(`Booking #${reservationId} was cancelled${cancelledBy}.`, 'info');
                    reloadAll();
                    return;
                }

                if (et.startsWith('game.copy') || et.startsWith('game_copy') || et.startsWith('incident') || et.startsWith('reservation') || et.startsWith('waitlist')) {
                    // For simplicity, reload the lists that may be affected
                    reloadAll();
                }
            } catch (err) {
                console.error('Failed to handle domain_event', err);
            }
        });
        es.addEventListener('ready', (e) => console.debug('realtime stream connected'));
    } catch (err) {
        console.warn('Realtime events not available', err);
    }
    // Reservation side panel helpers
    window.showReservationPanel = function(reservation) {
        const panel = document.getElementById('reservation-panel-content');
        if (!panel) return;
        panel.innerHTML = '';

        const form = document.createElement('form');

        const idLine = document.createElement('div'); idLine.textContent = `Reservation #${reservation.id}`;
        form.appendChild(idLine);

        const custLine = document.createElement('div'); custLine.textContent = `Customer: ${reservation.customer_id}`;
        form.appendChild(custLine);

        const tableLabel = document.createElement('label'); tableLabel.textContent = 'Table ID: '; 
        const tableInput = document.createElement('input'); tableInput.type='number'; tableInput.value = reservation.table_id || '';
        form.appendChild(tableLabel); form.appendChild(tableInput); form.appendChild(document.createElement('br'));

        const startLabel = document.createElement('label'); startLabel.textContent = 'Start: ';
        const startInput = document.createElement('input'); startInput.type='datetime-local';
        if (reservation.start_ts) startInput.value = toLocalInputValue(reservation.start_ts);
        form.appendChild(startLabel); form.appendChild(startInput); form.appendChild(document.createElement('br'));

        const endLabel = document.createElement('label'); endLabel.textContent = 'End: ';
        const endInput = document.createElement('input'); endInput.type='datetime-local';
        if (reservation.end_ts) endInput.value = toLocalInputValue(reservation.end_ts);
        form.appendChild(endLabel); form.appendChild(endInput); form.appendChild(document.createElement('br'));

        const partyLabel = document.createElement('label'); partyLabel.textContent = 'Party size: ';
        const partyInput = document.createElement('input'); partyInput.type='number'; partyInput.value = reservation.party_size || 1;
        form.appendChild(partyLabel); form.appendChild(partyInput); form.appendChild(document.createElement('br'));

        const notesLabel = document.createElement('label'); notesLabel.textContent = 'Notes: ';
        const notesInput = document.createElement('textarea'); notesInput.rows=4; notesInput.cols=30; notesInput.value = reservation.notes || '';
        form.appendChild(notesLabel); form.appendChild(document.createElement('br')); form.appendChild(notesInput); form.appendChild(document.createElement('br'));

        const saveBtn = document.createElement('button'); saveBtn.type='button'; saveBtn.textContent='Save';
        saveBtn.onclick = async () => {
            const payload = {
                table_id: tableInput.value ? Number(tableInput.value) : null,
                start_ts: startInput.value ? new Date(startInput.value).toISOString() : null,
                end_ts: endInput.value ? new Date(endInput.value).toISOString() : null,
                party_size: partyInput.value ? Number(partyInput.value) : null,
                notes: notesInput.value,
            };
            try {
                const updated = await fetchJson(`/api/steward/reservations/${reservation.id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
                // reflect update
                showReservationPanel(updated);
                await reloadAll();
            } catch (err) {
                alert('Failed to save: ' + err);
            }
        };
        const cancelBtn = document.createElement('button'); cancelBtn.type='button'; cancelBtn.textContent='Close';
        cancelBtn.onclick = () => { panel.innerHTML = 'Select a reservation to view/edit.' };

        form.appendChild(saveBtn); form.appendChild(cancelBtn);
        panel.appendChild(form);
    }

    function toLocalInputValue(iso) {
        try {
            const d = new Date(iso);
            if (isNaN(d.getTime())) return '';
            // get local datetime in YYYY-MM-DDTHH:MM format
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth()+1).padStart(2,'0');
            const dd = String(d.getDate()).padStart(2,'0');
            const hh = String(d.getHours()).padStart(2,'0');
            const min = String(d.getMinutes()).padStart(2,'0');
            return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
        } catch (e) { return '' }
    }
});
