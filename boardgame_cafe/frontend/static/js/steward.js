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

    // Some endpoints return 204 No Content or plain text — handle gracefully.
    if (res.status === 204) return {};
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        // Return raw text for non-JSON successful responses.
        try {
            const txt = await res.text();
            return txt;
        } catch (_e) {
            return {};
        }
    }

    return res.json();
}

function extractApiErrorMessage(error, fallback){
    const fallbackMessage = fallback || 'Operation failed.';
    if (!error || !error.message) return fallbackMessage;

    const raw = String(error.message || '').trim();
    if (!raw) return fallbackMessage;

    try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed.error === 'string' && parsed.error.trim()) {
            return parsed.error.trim();
        }
        if (parsed && typeof parsed.message === 'string' && parsed.message.trim()) {
            return parsed.message.trim();
        }
    } catch (_e) {
        // Not JSON. Continue with raw text.
    }

    return raw;
}

function showPopupMessage(message){
    window.alert(String(message || 'Operation failed.'));
}

const DASHBOARD_SUMMARY = {
    pending: 0,
    seated: 0,
    incidents: 0,
    lostCopies: 0,
    lastUpdated: null,
};

function formatIsoDateTime(iso){
    try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return String(iso || '');
        return d.toLocaleString([], {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch (_e) {
        return String(iso || '');
    }
}

function updateSummaryUI(){
    const map = [
        ['metric-pending', DASHBOARD_SUMMARY.pending],
        ['metric-seated', DASHBOARD_SUMMARY.seated],
        ['metric-incidents', DASHBOARD_SUMMARY.incidents],
        ['metric-lost-copies', DASHBOARD_SUMMARY.lostCopies],
    ];
    map.forEach(([id, value]) => {
        const node = document.getElementById(id);
        if (node) node.textContent = String(value);
    });

    const updated = document.getElementById('metric-last-updated');
    if (updated) {
        const ts = DASHBOARD_SUMMARY.lastUpdated;
        updated.textContent = ts ? `Last updated: ${ts.toLocaleTimeString()}` : 'Last updated: --';
    }
}

function updateRealtimeConnectionStatus(text){
    const node = document.getElementById('realtime-connection-status');
    if (node) node.textContent = text;
}

function reservationMatchesSearch(reservation, searchText){
    const q = String(searchText || '').trim().toLowerCase();
    if (!q) return true;

    const haystack = [
        reservation.id,
        reservation.customer_id,
        reservation.customer_name,
        reservation.customer_email,
        reservation.status,
        reservation.start_ts,
        reservation.end_ts,
        reservation.notes,
    ]
        .map((v) => String(v || '').toLowerCase())
        .join(' ');

    return haystack.includes(q);
}

function hydrateGameCopyGameFilter(copies){
    const select = document.getElementById('game-copy-game-filter');
    if (!select) return;

    const current = select.value;
    const games = new Map();
    copies.forEach((copy) => {
        const id = Number(copy.game_id);
        if (!id) return;
        const title = (copy.game_title || `Game #${id}`).trim();
        if (!games.has(id)) games.set(id, title);
    });

    const sorted = Array.from(games.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    select.innerHTML = '';

    const allOpt = document.createElement('option');
    allOpt.value = '';
    allOpt.textContent = 'All games';
    select.appendChild(allOpt);

    sorted.forEach(([id, title]) => {
        const opt = document.createElement('option');
        opt.value = String(id);
        opt.textContent = title;
        select.appendChild(opt);
    });

    if (current && Array.from(select.options).some((opt) => opt.value === current)) {
        select.value = current;
    }
}

const GAME_COPY_EDIT_STATE = {
    copy: null,
};

function setGameCopyMessage(message, isError = false) {
    const node = document.getElementById('game-copy-message');
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function getGameCopyStatusLabel(status) {
    const normalized = String(status || '').trim().toLowerCase();
    if (normalized === 'in_use') return 'Checked out';
    if (normalized === 'available') return 'Checked in';
    if (normalized === 'maintenance') return 'Maintenance';
    if (normalized === 'reserved') return 'Reserved';
    return normalized || 'Unknown';
}

function closeGameCopyModal() {
    const overlay = document.getElementById('game-copy-modal');
    if (overlay) overlay.hidden = true;
    document.body.classList.remove('modal-open');
    GAME_COPY_EDIT_STATE.copy = null;
}

function openGameCopyModal(copy) {
    const overlay = document.getElementById('game-copy-modal');
    const title = document.getElementById('game-copy-modal-title');
    const meta = document.getElementById('game-copy-modal-meta');
    const statusSelect = document.getElementById('game-copy-modal-status');
    if (!overlay || !title || !meta || !statusSelect) return;

    GAME_COPY_EDIT_STATE.copy = {
        id: Number(copy.id),
        copy_code: String(copy.copy_code || ''),
        game_title: String(copy.game_title || `Game #${copy.game_id}`),
        status: String(copy.status || 'available'),
    };

    title.textContent = `Edit ${GAME_COPY_EDIT_STATE.copy.copy_code || `Copy #${GAME_COPY_EDIT_STATE.copy.id}`}`;
    meta.textContent = `${GAME_COPY_EDIT_STATE.copy.game_title} · ${getGameCopyStatusLabel(GAME_COPY_EDIT_STATE.copy.status)}`;
    statusSelect.value = GAME_COPY_EDIT_STATE.copy.status;
    overlay.hidden = false;
    document.body.classList.add('modal-open');
    statusSelect.focus();
}

async function submitGameCopyModal(event) {
    event.preventDefault();
    const copy = GAME_COPY_EDIT_STATE.copy;
    if (!copy) return;

    const statusSelect = document.getElementById('game-copy-modal-status');
    const status = String(statusSelect?.value || '').trim().toLowerCase();
    if (!status || status === copy.status) {
        setGameCopyMessage(`No changes to save for copy #${copy.id}.`);
        closeGameCopyModal();
        return;
    }

    let action = null;
    if (status === 'available') action = 'return';
    if (status === 'in_use') action = 'use';
    if (status === 'reserved') action = 'reserve';
    if (status === 'maintenance') action = 'maintenance';

    if (!action) {
        setGameCopyMessage('Unsupported status selected.', true);
        return;
    }

    try {
        await fetchJson(`/api/steward/game-copies/${copy.id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action }),
        });
        setGameCopyMessage(`Copy #${copy.id} updated.`);
        closeGameCopyModal();
        await reloadAll();
    } catch (error) {
        console.error(error);
        setGameCopyMessage(`Could not update copy #${copy.id}.`, true);
    }
}

function ensureGameCopyModalHandlers() {
    const form = document.getElementById('game-copy-modal-form');
    form?.addEventListener('submit', submitGameCopyModal);

    document.querySelectorAll('[data-game-copy-modal-close]').forEach((button) => {
        button.addEventListener('click', closeGameCopyModal);
    });

    const overlay = document.getElementById('game-copy-modal');
    overlay?.addEventListener('click', (event) => {
        if (event.target === overlay) {
            closeGameCopyModal();
        }
    });
}

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

function getStewardTableDisplayStatus(table, reservedTableIds = new Set()){
    const persisted = String(table?.status || '').trim().toLowerCase();
    const reasons = Array.isArray(table?.unavailable_reasons)
        ? table.unavailable_reasons.map((reason) => String(reason || '').trim().toLowerCase())
        : [];

    if (persisted === 'available' && reservedTableIds.has(Number(table?.id))) {
        return 'reserved';
    }

    if (persisted === 'available' && reasons.includes('reservation_overlap')) {
        return 'reserved';
    }

    return persisted || (table?.available ? 'available' : 'unavailable');
}

function getStewardTableTileClass(status){
    const normalized = String(status || '').trim().toLowerCase();
    if (normalized === 'available') {
        return 'table-tile-available';
    }
    if (normalized === 'reserved') {
        return 'table-tile-reserved';
    }
    if (normalized === 'occupied') {
        return 'table-tile-alert';
    }
    return 'table-tile-unavailable';
}

async function loadPending(){
    const container = document.getElementById('pending-list');
    if (!container) return;
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/reservations' + q);
        const searchText = String((document.getElementById('pending-search') || {}).value || '');
        const filtered = data.filter((r) => reservationMatchesSearch(r, searchText));
        container.innerHTML='';
        DASHBOARD_SUMMARY.pending = data.length;
        if(!filtered.length) { container.textContent='No pending reservations match this search.'; updateSummaryUI(); return }
        const list = document.createElement('div');
        list.className = 'steward-item-list';
        filtered.forEach(r=>{
            const item = document.createElement('article');
            item.className = 'steward-item';

            const head = document.createElement('div');
            head.className = 'steward-item-head';

            const title = document.createElement('p');
            title.className = 'steward-item-title';
            title.textContent = `Booking #${r.id}`;

            const status = document.createElement('span');
            status.className = `status-pill status-${String(r.status || '').replace('-', '_')}`;
            status.textContent = String(r.status || 'unknown');

            head.appendChild(title);
            head.appendChild(status);
            item.appendChild(head);

            const meta = document.createElement('p');
            meta.className = 'steward-item-meta';
            meta.textContent = `Customer ${r.customer_id} · ${formatIsoDateTime(r.start_ts)} · Party ${r.party_size}`;
            item.appendChild(meta);

            const actions = document.createElement('div');
            actions.className = 'steward-item-actions';

            const seatBtn = document.createElement('button'); seatBtn.textContent='Seat'; seatBtn.className='button button-secondary';
            seatBtn.onclick = async ()=>{
                try {
                    await fetchJson(`/api/steward/reservations/${r.id}/seat`,{method:'PATCH'});
                    await reloadAll();
                } catch (err) {
                    showPopupMessage(
                        extractApiErrorMessage(
                            err,
                            'Unable to seat reservation right now.'
                        )
                    );
                }
            }
            seatBtn.addEventListener('click', (e)=>e.stopPropagation());
            actions.appendChild(seatBtn);

            const editBtn = document.createElement('button'); editBtn.textContent='Edit'; editBtn.className='button button-subtle';
            editBtn.onclick = (e) => { e.stopPropagation(); showReservationPanel(r); };
            actions.appendChild(editBtn);

            const cancelBtn = document.createElement('button'); cancelBtn.textContent='Cancel'; cancelBtn.className='button button-subtle';
            cancelBtn.onclick = async (e) => {
                e.stopPropagation();
                if (!confirm(`Cancel booking #${r.id}?`)) return;
                await fetchJson(`/api/reservations/${r.id}/cancel`, {method:'PATCH'});
                await reloadAll();
            };
            actions.appendChild(cancelBtn);

            item.appendChild(actions);

            list.appendChild(item);
        });
        container.appendChild(list);
        updateSummaryUI();
    }catch(e){
        console.error(e);
        if (container) container.textContent='Error loading';
    }
}

async function loadSeated(){
    const container = document.getElementById('seated-list');
    if (!container) return;
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/reservations/seated' + q);
        const searchText = String((document.getElementById('seated-search') || {}).value || '');
        const filtered = data.filter((r) => reservationMatchesSearch(r, searchText));
        container.innerHTML='';
        DASHBOARD_SUMMARY.seated = data.length;
        if(!filtered.length) { container.textContent='No seated reservations match this search.'; updateSummaryUI(); return }
        const list = document.createElement('div');
        list.className = 'steward-item-list';
        filtered.forEach(r=>{
            const item = document.createElement('article');
            item.className = 'steward-item';

            const head = document.createElement('div');
            head.className = 'steward-item-head';
            const title = document.createElement('p');
            title.className = 'steward-item-title';
            title.textContent = `Booking #${r.id}`;
            const status = document.createElement('span');
            status.className = `status-pill status-${String(r.status || '').replace('-', '_')}`;
            status.textContent = String(r.status || 'unknown');
            head.appendChild(title);
            head.appendChild(status);
            item.appendChild(head);

            const meta = document.createElement('p');
            meta.className = 'steward-item-meta';
            meta.textContent = `Customer ${r.customer_id} · ${formatIsoDateTime(r.start_ts)} · Party ${r.party_size}`;
            item.appendChild(meta);

            const actions = document.createElement('div');
            actions.className = 'steward-item-actions';

            const compBtn = document.createElement('button'); compBtn.textContent='Complete'; compBtn.className='button button-secondary';
            compBtn.onclick = async ()=>{
                await fetchJson(`/api/steward/reservations/${r.id}/complete`,{method:'PATCH'});
                await reloadAll();
            }
            compBtn.addEventListener('click', (e)=>e.stopPropagation());
            actions.appendChild(compBtn);

            const editBtn = document.createElement('button'); editBtn.textContent='Edit'; editBtn.className='button button-subtle';
            editBtn.onclick = (e) => { e.stopPropagation(); showReservationPanel(r); };
            actions.appendChild(editBtn);

            item.appendChild(actions);
            list.appendChild(item);
        });
        container.appendChild(list);
        updateSummaryUI();
    }catch(e){
        console.error(e);
        if (container) container.textContent='Error loading';
    }
}

async function loadGameCopies(){
    const container = document.getElementById('game-copy-list');
    if (!container) return;
    try{
        // Game copies are global (no date filter)
        const data = await fetchJson('/api/steward/game-copies');
        hydrateGameCopyGameFilter(data);

        const selectedGame = (document.getElementById('game-copy-game-filter') || {}).value || '';
        const searchText = String((document.getElementById('game-copy-search') || {}).value || '').trim().toLowerCase();
        const filtered = data.filter((copy) => {
            if (selectedGame && String(copy.game_id) !== String(selectedGame)) return false;
            if (!searchText) return true;
            const title = String(copy.game_title || '').toLowerCase();
            const code = String(copy.copy_code || '').toLowerCase();
            return title.includes(searchText) || code.includes(searchText);
        });

        container.innerHTML='';
        DASHBOARD_SUMMARY.lostCopies = data.filter((c)=>c.status === 'lost').length;
        if(!filtered.length) { container.textContent='No game copies match this filter.'; updateSummaryUI(); return }
        const list = document.createElement('div');
        list.className = 'steward-item-list';
        filtered.forEach(c=>{
            const item = document.createElement('article');
            item.className = 'steward-item';

            const head = document.createElement('div');
            head.className = 'steward-item-head';

            const title = document.createElement('p');
            title.className = 'steward-item-title';
            title.textContent = `${c.copy_code} (#${c.id})`;

            const status = document.createElement('span');
            status.className = `status-pill status-${String(c.status || '').replace('-', '_')}`;
            status.textContent = String(c.status || 'unknown');
            head.appendChild(title);
            head.appendChild(status);
            item.appendChild(head);

            const meta = document.createElement('p');
            meta.className = 'steward-item-meta';
            meta.textContent = `${c.game_title || `Game #${c.game_id}`} · ${c.location || 'No location set'} · ${getGameCopyStatusLabel(c.status)}`;
            item.appendChild(meta);

            const actions = document.createElement('div');
            actions.className = 'steward-item-actions';

            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'button button-secondary';
            editBtn.textContent = 'Edit';
            editBtn.addEventListener('click', () => openGameCopyModal(c));
            actions.appendChild(editBtn);

            item.appendChild(actions);
            list.appendChild(item);
        });
        container.appendChild(list);
        updateSummaryUI();
    }catch(e){
        console.error(e);
        if (container) container.textContent='Error loading';
    }
}

async function loadFloorplan(){
    const floorSelect = document.getElementById('floor-select');
    const floorplan = document.getElementById('floorplan');
    if (!floorSelect || !floorplan) return;
    try{
        const date = (document.getElementById('live-date') || {}).value;
        if(!date) return;
        // use full day window
        const start = new Date(date + 'T00:00:00');
        const end = new Date(date + 'T23:59:59');
        const qs = `?start_ts=${encodeURIComponent(start.toISOString())}&end_ts=${encodeURIComponent(end.toISOString())}&party_size=1`;
        const [resp, confirmedReservations] = await Promise.all([
            fetchJson('/api/tables/availability' + qs),
            fetchJson('/api/steward/reservations').catch(() => []),
        ]);

        const reservedTableIds = new Set();
        (Array.isArray(confirmedReservations) ? confirmedReservations : []).forEach((reservation) => {
            const ts = Date.parse(String(reservation?.start_ts || ''));
            if (!Number.isFinite(ts) || ts <= Date.now()) {
                return;
            }

            const primaryTableId = Number(reservation?.table_id);
            if (Number.isFinite(primaryTableId) && primaryTableId > 0) {
                reservedTableIds.add(primaryTableId);
            }

            const linkedTableIds = Array.isArray(reservation?.table_ids) ? reservation.table_ids : [];
            linkedTableIds.forEach((tableIdRaw) => {
                const tableId = Number(tableIdRaw);
                if (Number.isFinite(tableId) && tableId > 0) {
                    reservedTableIds.add(tableId);
                }
            });
        });

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
            const floorCard = document.createElement('article');
            floorCard.className = 'steward-item admin-floor-tree-item';

            const floorHead = document.createElement('div');
            floorHead.className = 'steward-item-head';

            const floorTitle = document.createElement('p');
            floorTitle.className = 'steward-item-title';
            floorTitle.textContent = `Floor ${floor.floor}`;
            floorHead.appendChild(floorTitle);
            floorCard.appendChild(floorHead);

            const zoneList = document.createElement('div');
            zoneList.className = 'steward-item-list';

            floor.zones.forEach(zone => {
                const zoneSection = document.createElement('section');
                zoneSection.className = 'floor-zone';

                const zoneHead = document.createElement('div');
                zoneHead.className = 'steward-item-head';

                const zoneTitle = document.createElement('h5');
                zoneTitle.className = 'floor-zone-title';
                zoneTitle.textContent = `Zone ${zone.zone}`;
                zoneHead.appendChild(zoneTitle);
                zoneSection.appendChild(zoneHead);

                const grid = document.createElement('div');
                grid.className = 'floor-zone-grid';

                zone.tables.forEach(t => {
                    const tile = document.createElement('article');
                    const displayStatus = getStewardTableDisplayStatus(t, reservedTableIds);
                    const tileClass = getStewardTableTileClass(displayStatus);
                    tile.className = `table-tile ${tileClass}`;
                    tile.title = `Table ${t.table_nr} (cap ${t.capacity}) - ${displayStatus}`;

                    const tableNumber = document.createElement('span');
                    tableNumber.className = 'table-tile-name';
                    tableNumber.textContent = `T${t.table_nr}`;

                    const tableCapacity = document.createElement('span');
                    tableCapacity.className = 'table-tile-cap';
                    tableCapacity.textContent = `Cap ${t.capacity}`;

                    const tableStatus = document.createElement('span');
                    tableStatus.className = 'table-tile-status';
                    tableStatus.textContent = displayStatus;

                    tile.appendChild(tableNumber);
                    tile.appendChild(tableCapacity);
                    tile.appendChild(tableStatus);
                    grid.appendChild(tile);
                });

                if (!zone.tables.length) {
                    const empty = document.createElement('p');
                    empty.className = 'steward-item-meta';
                    empty.textContent = 'No tables in this zone.';
                    grid.appendChild(empty);
                }

                zoneSection.appendChild(grid);
                zoneList.appendChild(zoneSection);
            });

            if (!floor.zones.length) {
                const emptyZones = document.createElement('p');
                emptyZones.className = 'steward-item-meta';
                emptyZones.textContent = 'No zones in this floor.';
                zoneList.appendChild(emptyZones);
            }

            floorCard.appendChild(zoneList);
            floorplan.appendChild(floorCard);
        };

        floorSelect.onchange = () => render(floorSelect.value);
        render(floorSelect.value || floors[0].floor);
    }catch(e){
        console.error(e);
        if (floorplan) floorplan.textContent='Error loading floorplan';
    }
}

async function loadIncidents(){
    const container = document.getElementById('incident-list');
    if (!container) return;
    try{
        const date = (document.getElementById('live-date') || {}).value;
        const q = date ? `?date=${encodeURIComponent(date)}` : '';
        const data = await fetchJson('/api/steward/incidents' + q);
        container.innerHTML='';
        DASHBOARD_SUMMARY.incidents = data.length;
        if(!data.length) { container.textContent='No incidents.'; updateSummaryUI(); return }
        const list = document.createElement('div');
        list.className = 'steward-item-list';
        data.forEach(i=>{
            const item = document.createElement('article');
            item.className = 'steward-item';

            const title = document.createElement('p');
            title.className = 'steward-item-title';
            title.textContent = `Incident #${i.id} · ${i.incident_type}`;
            item.appendChild(title);

            const meta = document.createElement('p');
            meta.className = 'steward-item-meta';
            meta.textContent = `Copy ${i.game_copy_id} · ${formatIsoDateTime(i.created_at)} · ${i.note || 'No note'}`;
            item.appendChild(meta);

            list.appendChild(item);
        });
        container.appendChild(list);
        updateSummaryUI();
    }catch(e){
        console.error(e);
        if (container) container.textContent='Error loading';
    }
}

async function reloadAll(){
    const loaders = [];
    if (document.getElementById('pending-list')) loaders.push(loadPending());
    if (document.getElementById('seated-list')) loaders.push(loadSeated());
    if (document.getElementById('game-copy-list')) loaders.push(loadGameCopies());
    if (document.getElementById('incident-list')) loaders.push(loadIncidents());
    if (document.getElementById('floorplan') && document.getElementById('floor-select')) loaders.push(loadFloorplan());

    if (!loaders.length) return;
    await Promise.all(loaders);
    DASHBOARD_SUMMARY.lastUpdated = new Date();
    updateSummaryUI();
}

window.addEventListener('DOMContentLoaded', ()=>{
    ensureGameCopyModalHandlers();
    const gameFilter = document.getElementById('game-copy-game-filter');
    if (gameFilter) gameFilter.addEventListener('change', () => loadGameCopies());
    const gameSearch = document.getElementById('game-copy-search');
    if (gameSearch) gameSearch.addEventListener('input', () => loadGameCopies());
    const refreshBtn = document.getElementById('steward-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', () => reloadAll());
    const pendingSearch = document.getElementById('pending-search');
    if (pendingSearch) pendingSearch.addEventListener('input', () => loadPending());
    const seatedSearch = document.getElementById('seated-search');
    if (seatedSearch) seatedSearch.addEventListener('input', () => loadSeated());
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
        updateRealtimeConnectionStatus('Realtime: connected');
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

                if (et === 'reservation.seated') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `reservation.seated:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    const seatedBy = data.seated_by_role ? ` by ${data.seated_by_role}` : '';
                    showRealtimeNotice(`Booking #${reservationId} was seated${seatedBy}.`, 'success');
                    reloadAll();
                    return;
                }

                if (et === 'reservation.completed') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `reservation.completed:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    const completedBy = data.completed_by_role ? ` by ${data.completed_by_role}` : '';
                    showRealtimeNotice(`Booking #${reservationId} was completed${completedBy}.`, 'info');
                    reloadAll();
                    return;
                }

                if (et === 'reservation.updated') {
                    const data = payload.data || {};
                    const reservationId = data.id || data.reservation_id || 'unknown';
                    const eventKey = `reservation.updated:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    const updatedBy = data.updated_by_role ? ` by ${data.updated_by_role}` : '';
                    showRealtimeNotice(`Booking #${reservationId} was updated${updatedBy}.`, 'info');
                    reloadAll();
                    return;
                }

                if (et.startsWith('incident')) {
                    const data = payload.data || {};
                    const incidentId = data.id || 'unknown';
                    const eventKey = `incident:${incidentId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    if (et === 'incident.created') {
                        showRealtimeNotice(`Incident reported for copy ${data.game_copy_id || 'unknown'}.`, 'success');
                    } else if (et === 'incident.deleted') {
                        showRealtimeNotice(`Incident #${incidentId} deleted.`, 'info');
                    } else {
                        showRealtimeNotice('Incident updated.', 'info');
                    }

                    // If the incidents list UI exists, refresh it specifically; otherwise reload everything.
                    if (document.getElementById('incident-list')) {
                        loadIncidents().catch((err) => console.error('Failed to reload incidents', err));
                    } else {
                        reloadAll();
                    }
                    return;
                }

                if (et === 'game_copy.updated') {
                    const data = payload.data || {};
                    const eventKey = `game_copy.updated:${data.id || 'unknown'}:${data.action || 'update'}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    showRealtimeNotice(`Game copy ${data.copy_code || data.id || 'unknown'} updated.`, 'info');
                    reloadAll();
                    return;
                }

                if (et === 'reservation.game.swap') {
                    const data = payload.data || {};
                    const eventKey = `reservation.game.swap:${data.reservation_game_id || 'unknown'}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    showRealtimeNotice(`Game copy swapped for booking #${data.reservation_id || 'unknown'}.`, 'success');
                    reloadAll();
                    return;
                }

                if (et.startsWith('game.copy') || et.startsWith('game_copy') || et.startsWith('reservation')) {
                    // For simplicity, reload the lists that may be affected
                    reloadAll();
                }
            } catch (err) {
                console.error('Failed to handle domain_event', err);
            }
        });
        es.addEventListener('ready', (_e) => {
            updateRealtimeConnectionStatus('Realtime: connected');
            console.debug('realtime stream connected');
        });
        es.addEventListener('error', (_e) => {
            updateRealtimeConnectionStatus('Realtime: reconnecting...');
        });
    } catch (err) {
        updateRealtimeConnectionStatus('Realtime: unavailable');
        console.warn('Realtime events not available', err);
    }
    // Reservation side panel helpers
    window.showReservationPanel = function(reservation) {
        const panel = document.getElementById('reservation-panel-content');
        if (!panel) return;
        panel.innerHTML = '';

        const form = document.createElement('form');
        form.className = 'steward-edit-form';

        const idLine = document.createElement('div'); idLine.textContent = `Reservation #${reservation.id}`;
        form.appendChild(idLine);

        const custLine = document.createElement('div'); custLine.textContent = `Customer: ${reservation.customer_id}`;
        form.appendChild(custLine);

        const tableWrap = document.createElement('div'); tableWrap.className = 'steward-edit-grid';
        const tableLabel = document.createElement('label'); tableLabel.className='form-label'; tableLabel.textContent = 'Table ID';
        const tableInput = document.createElement('input'); tableInput.type='number'; tableInput.className='form-input'; tableInput.value = reservation.table_id || '';
        tableWrap.appendChild(tableLabel); tableWrap.appendChild(tableInput); form.appendChild(tableWrap);

        const startWrap = document.createElement('div'); startWrap.className = 'steward-edit-grid';
        const startLabel = document.createElement('label'); startLabel.className='form-label'; startLabel.textContent = 'Start';
        const startInput = document.createElement('input'); startInput.type='datetime-local'; startInput.className='form-input';
        if (reservation.start_ts) startInput.value = toLocalInputValue(reservation.start_ts);
        startWrap.appendChild(startLabel); startWrap.appendChild(startInput); form.appendChild(startWrap);

        const endWrap = document.createElement('div'); endWrap.className = 'steward-edit-grid';
        const endLabel = document.createElement('label'); endLabel.className='form-label'; endLabel.textContent = 'End';
        const endInput = document.createElement('input'); endInput.type='datetime-local'; endInput.className='form-input';
        if (reservation.end_ts) endInput.value = toLocalInputValue(reservation.end_ts);
        endWrap.appendChild(endLabel); endWrap.appendChild(endInput); form.appendChild(endWrap);

        const partyWrap = document.createElement('div'); partyWrap.className = 'steward-edit-grid';
        const partyLabel = document.createElement('label'); partyLabel.className='form-label'; partyLabel.textContent = 'Party Size';
        const partyInput = document.createElement('input'); partyInput.type='number'; partyInput.className='form-input'; partyInput.value = reservation.party_size || 1;
        partyWrap.appendChild(partyLabel); partyWrap.appendChild(partyInput); form.appendChild(partyWrap);

        const notesWrap = document.createElement('div'); notesWrap.className = 'steward-edit-grid';
        const notesLabel = document.createElement('label'); notesLabel.className='form-label'; notesLabel.textContent = 'Notes';
        const notesInput = document.createElement('textarea'); notesInput.rows=4; notesInput.value = reservation.notes || ''; notesInput.className='form-input';
        notesWrap.appendChild(notesLabel); notesWrap.appendChild(notesInput); form.appendChild(notesWrap);

        const buttonRow = document.createElement('div');
        buttonRow.className = 'steward-item-actions';

        const saveBtn = document.createElement('button'); saveBtn.type='button'; saveBtn.textContent='Save'; saveBtn.className='button';
        saveBtn.onclick = async () => {
            const payload = {
                table_id: tableInput.value ? Number(tableInput.value) : null,
                // Keep datetime-local values as typed to avoid timezone shifts.
                start_ts: startInput.value || null,
                end_ts: endInput.value || null,
                party_size: partyInput.value ? Number(partyInput.value) : null,
                notes: notesInput.value,
            };
            try {
                await fetchJson(`/api/steward/reservations/${reservation.id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
                panel.innerHTML = 'Select a reservation to view/edit.';
                showRealtimeNotice(`Booking #${reservation.id} updated.`, 'success');
                await reloadAll();
            } catch (err) {
                alert('Failed to save: ' + err);
            }
        };
        const cancelBtn = document.createElement('button'); cancelBtn.type='button'; cancelBtn.textContent='Close'; cancelBtn.className='button button-subtle';
        cancelBtn.onclick = () => { panel.innerHTML = 'Select a reservation to view/edit.' };

        buttonRow.appendChild(saveBtn);
        buttonRow.appendChild(cancelBtn);
        form.appendChild(buttonRow);
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
