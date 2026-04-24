async function fetchJson(path, opts = {}) {
    opts.credentials = opts.credentials || 'same-origin';

    const method = (opts.method || 'GET').toUpperCase();
    if (method === 'GET' && !opts.cache) {
        opts.cache = 'no-store';
    }
    if (method !== 'GET' && method !== 'HEAD') {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const token = meta ? meta.getAttribute('content') : null;
        opts.headers = Object.assign({
            'X-CSRFToken': token,
            'X-CSRF-Token': token,
            'X-Requested-With': 'XMLHttpRequest',
        }, opts.headers || {});
    }

    const res = await fetch(path, opts);
    if (!res.ok) throw new Error(await res.text());

    if (res.status === 204) {
        return {};
    }

    const contentType = String(res.headers.get('content-type') || '').toLowerCase();
    if (!contentType.includes('application/json')) {
        try {
            const text = await res.text();
            return text ? { text } : {};
        } catch (_error) {
            return {};
        }
    }

    return res.json();
}

const ADMIN_SUMMARY = {
    users: 0,
    games: 0,
    copies: 0,
    tables: 0,
    openBookings: 0,
    openIncidents: 0,
    publishedAnnouncements: 0,
    lastUpdated: null,
};

const ADMIN_CATALOGUE = {
    games: [],
    copies: [],
};

const ADMIN_ANNOUNCEMENTS = {
    items: [],
};

const ADMIN_LOCATION_STATE = {
    floors: [],
    zones: [],
    tables: [],
    reservedTableIds: new Set(),
    selectedFloor: null,
};

const ADMIN_LOCATION_MODAL = {
    kind: null,
    id: null,
};

function centsToNok(cents) {
    return (Number(cents || 0) / 100).toFixed(2);
}

function nokToCents(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
        return null;
    }
    return Math.round(parsed * 100);
}

function isoToDatetimeLocal(iso) {
    if (!iso) {
        return '';
    }

    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
        return '';
    }

    const pad = (num) => String(num).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function datetimeLocalToIso(value) {
    if (!value) {
        return null;
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return null;
    }
    return date.toISOString();
}

function setAdminConnection(text) {
    const node = document.getElementById('admin-connection-status');
    if (node) node.textContent = text;
}

function setUserManagementMessage(message, isError = false) {
    const node = document.getElementById('admin-user-message');
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function setAnnouncementMessage(message, isError = false) {
    const node = document.getElementById('admin-announcement-message');
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function setLocationMessage(id, message, isError = false) {
    const node = document.getElementById(id);
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function locationErrorMessage(error, fallback) {
    const raw = String(error?.message || '').trim();
    if (!raw) return fallback;
    try {
        const parsed = JSON.parse(raw);
        if (parsed?.error) {
            return String(parsed.error);
        }
    } catch (_ignored) {
        // Response was plain text.
    }
    return raw.length > 180 ? fallback : raw;
}

function updateFloorSelectOptions() {
    const select = document.getElementById('admin-floor-select');
    const floors = ADMIN_LOCATION_STATE.floors || [];

    if (floors.length === 0) {
        ADMIN_LOCATION_STATE.selectedFloor = null;
        if (select) {
            select.innerHTML = '<option value="">No floors</option>';
        }
        return;
    }

    if (!floors.some((floor) => Number(floor.number) === Number(ADMIN_LOCATION_STATE.selectedFloor))) {
        ADMIN_LOCATION_STATE.selectedFloor = Number(floors[0].number);
    }

    if (!select) return;

    select.innerHTML = floors
        .map((floor) => `<option value="${floor.number}">${floor.number} - ${floor.name}</option>`)
        .join('');
    select.value = String(ADMIN_LOCATION_STATE.selectedFloor);
}

function getFloorById(floorId) {
    return ADMIN_LOCATION_STATE.floors.find((floor) => Number(floor.id) === Number(floorId)) || null;
}

function getZoneById(zoneId) {
    return ADMIN_LOCATION_STATE.zones.find((zone) => Number(zone.id) === Number(zoneId)) || null;
}

function getTableById(tableId) {
    return ADMIN_LOCATION_STATE.tables.find((table) => Number(table.id) === Number(tableId)) || null;
}

function getAdminTableTileClass(status) {
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

function getAdminTableDisplayStatus(table) {
    const persisted = String(table?.status || '').trim().toLowerCase();
    if (persisted === 'available' && ADMIN_LOCATION_STATE.reservedTableIds.has(Number(table?.id))) {
        return 'reserved';
    }
    return persisted || 'unknown';
}

function isAdminTableMovable(table) {
    const persisted = String(table?.status || '').trim().toLowerCase();
    return persisted !== 'occupied';
}

function deriveLocationStateFromTables(tables) {
    const floorMap = new Map();
    const zoneMap = new Map();

    tables.forEach((table) => {
        const floorNr = Number(table.floor || 1);
        const zoneName = String(table.zone || 'main').trim() || 'main';

        if (!floorMap.has(floorNr)) {
            floorMap.set(floorNr, {
                id: null,
                number: floorNr,
                name: `Floor ${floorNr}`,
                active: true,
                notes: null,
            });
        }

        const zoneKey = `${floorNr}:${zoneName}`;
        if (!zoneMap.has(zoneKey)) {
            zoneMap.set(zoneKey, {
                id: null,
                floor: floorNr,
                name: zoneName,
                active: true,
                notes: null,
            });
        }
    });

    return {
        floors: Array.from(floorMap.values()).sort((a, b) => a.number - b.number),
        zones: Array.from(zoneMap.values()).sort((a, b) => (a.floor - b.floor) || a.name.localeCompare(b.name)),
    };
}

async function materializeLocationRecordsFromTables(tables, existingFloors = [], existingZones = []) {
    const derived = deriveLocationStateFromTables(tables || []);
    const existingFloorNumbers = new Set((existingFloors || []).map((floor) => Number(floor.number)));
    const existingZoneKeys = new Set((existingZones || []).map((zone) => `${Number(zone.floor)}:${String(zone.name || '').trim().toLowerCase()}`));
    let createdCount = 0;

    for (const floor of derived.floors) {
        if (existingFloorNumbers.has(Number(floor.number))) {
            continue;
        }

        try {
            await fetchJson('/api/admin/floors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    number: Number(floor.number),
                    name: String(floor.name || `Floor ${floor.number}`),
                    active: true,
                    notes: null,
                }),
            });
            createdCount += 1;
            existingFloorNumbers.add(Number(floor.number));
        } catch (_error) {
            // Ignore duplicates and continue creating missing records.
        }
    }

    for (const zone of derived.zones) {
        const zoneKey = `${Number(zone.floor)}:${String(zone.name || '').trim().toLowerCase()}`;
        if (existingZoneKeys.has(zoneKey)) {
            continue;
        }

        try {
            await fetchJson('/api/admin/zones', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    floor: Number(zone.floor),
                    name: String(zone.name || 'main'),
                    active: true,
                    notes: null,
                }),
            });
            createdCount += 1;
            existingZoneKeys.add(zoneKey);
        } catch (_error) {
            // Ignore duplicates and continue creating missing records.
        }
    }

    return createdCount;
}

function renderLocationFloorplan() {
    const map = document.getElementById('admin-floorplan-map');
    if (!map) return;

    const floors = [...(ADMIN_LOCATION_STATE.floors || [])].sort((a, b) => Number(a.number) - Number(b.number));
    if (!floors.length) {
        map.innerHTML = '<p class="game-state">No floors available yet.</p>';
        return;
    }

    map.innerHTML = floors
        .map((floor) => {
            const zonesForFloor = ADMIN_LOCATION_STATE.zones
                .filter((zone) => Number(zone.floor) === Number(floor.number))
                .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));

            const zonesMarkup = zonesForFloor.length
                ? zonesForFloor
                    .map((zone) => {
                        const zoneTables = ADMIN_LOCATION_STATE.tables
                            .filter((table) => Number(table.floor) === Number(floor.number) && String(table.zone) === String(zone.name))
                            .sort((a, b) => Number(a.number) - Number(b.number));

                        const tablesMarkup = zoneTables.length
                            ? zoneTables.map((table) => `
                                <article class="table-tile ${getAdminTableTileClass(getAdminTableDisplayStatus(table))}" draggable="${isAdminTableMovable(table) ? 'true' : 'false'}" data-dnd-table-id="${table.id}">
                                    <span class="table-tile-name">T${escapeHtml(table.number)}</span>
                                    <span class="table-tile-cap">Cap ${escapeHtml(table.capacity)}</span>
                                    <span class="table-tile-status">${escapeHtml(getAdminTableDisplayStatus(table))}</span>
                                    <button class="button button-subtle" type="button" data-location-edit="table" data-location-id="${table.id}">Edit</button>
                                </article>
                            `).join('')
                            : '<p class="steward-item-meta">No tables in this zone.</p>';

                        return `
                            <section class="floor-zone admin-drop-zone" data-target-floor="${floor.number}" data-target-zone="${escapeHtml(zone.name)}">
                                <div class="steward-item-head">
                                    <h5 class="floor-zone-title">Zone ${escapeHtml(zone.name)}</h5>
                                    <button class="button button-subtle" type="button" data-location-edit="zone" data-location-id="${zone.id}">Edit</button>
                                </div>
                                <div class="floor-zone-grid">${tablesMarkup}</div>
                            </section>
                        `;
                    })
                    .join('')
                : '<p class="steward-item-meta">No zones in this floor.</p>';

            return `
                <article class="steward-item admin-floor-tree-item">
                    <div class="steward-item-head">
                        <p class="steward-item-title">Floor ${floor.number} - ${escapeHtml(floor.name)}</p>
                        <button class="button button-subtle" type="button" data-location-edit="floor" data-location-id="${floor.id}">Edit</button>
                    </div>
                    <div class="steward-item-list">${zonesMarkup}</div>
                </article>
            `;
        })
        .join('');

    bindLocationOverviewActions();
    bindLocationDragAndDrop();
}

async function moveTableToZone(tableId, targetFloorRaw, targetZoneRaw) {
    const row = getTableById(tableId);
    if (!row) {
        setLocationMessage('admin-location-action-message', 'Selected table no longer exists.', true);
        return;
    }

    const targetFloor = Number(targetFloorRaw);
    const targetZone = String(targetZoneRaw || '').trim();
    if (!targetFloor || !targetZone) {
        setLocationMessage('admin-location-action-message', 'Invalid drop target.', true);
        return;
    }

    if (Number(row.floor) === targetFloor && String(row.zone) === targetZone) {
        return;
    }

    const payload = {
        number: Number(row.number),
        capacity: Number(row.capacity),
        floor: targetFloor,
        zone: targetZone,
        status: String(row.status || 'available'),
        features: row.features || {},
        width: row.width || null,
        height: row.height || null,
        rotation: row.rotation || null,
    };

    try {
        await fetchJson(`/api/admin/tables/${tableId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        setLocationMessage('admin-location-action-message', `Moved table T${row.number} to floor ${targetFloor}, zone ${targetZone}.`);
        await loadLocationOverview();
    } catch (error) {
        console.error(error);
        setLocationMessage('admin-location-action-message', locationErrorMessage(error, 'Could not move table.'), true);
    }
}

function bindLocationDragAndDrop() {
    const map = document.getElementById('admin-floorplan-map');
    if (!map) return;

    const tableTiles = document.querySelectorAll('[data-dnd-table-id]');
    const dropZones = Array.from(document.querySelectorAll('.admin-drop-zone'));
    let activeZone = null;

    const clearDropHints = () => {
        document.querySelectorAll('.admin-drop-hint').forEach((hint) => hint.remove());
        dropZones.forEach((zone) => zone.classList.remove('admin-drop-active'));
        activeZone = null;
    };

    const attachDropHint = (zone) => {
        const grid = zone.querySelector('.floor-zone-grid');
        if (!grid) {
            return;
        }

        let hint = grid.querySelector('.admin-drop-hint');
        if (!hint) {
            hint = document.createElement('div');
            hint.className = 'admin-drop-hint';
            hint.textContent = 'Drop table here';
            grid.appendChild(hint);
        }
    };

    tableTiles.forEach((tile) => {
        tile.addEventListener('dragstart', (event) => {
            const tableId = String(tile.getAttribute('data-dnd-table-id') || '');
            const table = getTableById(tableId);
            if (!tableId || !event.dataTransfer || !isAdminTableMovable(table)) {
                event.preventDefault();
                return;
            }
            event.dataTransfer.setData('text/plain', tableId);
            event.dataTransfer.effectAllowed = 'move';
            tile.classList.add('admin-dragging');
        });

        tile.addEventListener('dragend', () => {
            tile.classList.remove('admin-dragging');
            clearDropHints();
        });
    });

    map.addEventListener('dragover', (event) => {
        event.preventDefault();
        const zone = event.target instanceof Element
            ? event.target.closest('.admin-drop-zone')
            : null;
        if (!zone || !dropZones.includes(zone)) {
            if (activeZone) {
                clearDropHints();
            }
            return;
        }

        if (activeZone !== zone) {
            clearDropHints();
            activeZone = zone;
            zone.classList.add('admin-drop-active');
            attachDropHint(zone);
        }
    });

    map.addEventListener('dragleave', (event) => {
        const related = event.relatedTarget;
        if (!(related instanceof Element) || !map.contains(related)) {
            clearDropHints();
        }
    });

    map.addEventListener('drop', async (event) => {
        event.preventDefault();
        const hoveredZone = event.target instanceof Element
            ? event.target.closest('.admin-drop-zone')
            : null;
        const zone = (hoveredZone && dropZones.includes(hoveredZone))
            ? hoveredZone
            : activeZone;

        if (!zone || !dropZones.includes(zone)) {
            clearDropHints();
            return;
        }

        const tableIdRaw = event.dataTransfer ? event.dataTransfer.getData('text/plain') : '';
        const tableId = Number(tableIdRaw);
        const targetFloor = zone.getAttribute('data-target-floor');
        const targetZone = zone.getAttribute('data-target-zone');
        clearDropHints();
        if (!tableId || !targetFloor || !targetZone) {
            return;
        }

        await moveTableToZone(tableId, targetFloor, targetZone);
    });
}

function renderLocationOverview() {
    renderLocationFloorplan();
}

async function updateFloorRecord(floorId, nextName) {
    const existing = getFloorById(floorId);
    if (!existing) {
        setLocationMessage('admin-location-action-message', 'Floor not found.', true);
        return;
    }

    const payload = {
        number: Number(existing.number),
        name: String(nextName || '').trim(),
        notes: existing.notes || null,
        active: Boolean(existing.active),
    };

    try {
        await fetchJson(`/api/admin/floors/${floorId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        setLocationMessage('admin-location-action-message', 'Floor updated.');
        await loadLocationOverview();
    } catch (error) {
        console.error(error);
        setLocationMessage('admin-location-action-message', locationErrorMessage(error, 'Could not update floor.'), true);
    }
}

async function deleteFloorRecord(floorId) {
    if (!window.confirm(`Delete floor #${floorId}?`)) return;

    try {
        await fetchJson(`/api/admin/floors/${floorId}`, { method: 'DELETE' });
        setLocationMessage('admin-location-action-message', 'Floor deleted.');
        await loadLocationOverview();
    } catch (error) {
        const reason = locationErrorMessage(error, 'Could not delete floor.');
        const requiresForce = reason.toLowerCase().includes('cannot delete floor with tables assigned');
        if (requiresForce && window.confirm('Floor still has zones/tables. Force delete floor and all assigned records?')) {
            try {
                await fetchJson(`/api/admin/floors/${floorId}?force=1`, { method: 'DELETE' });
                setLocationMessage('admin-location-action-message', 'Floor force deleted with its zones/tables.');
                await loadLocationOverview();
                await loadAdminStats();
                return;
            } catch (forceError) {
                console.error(forceError);
                setLocationMessage('admin-location-action-message', locationErrorMessage(forceError, 'Could not force delete floor.'), true);
                return;
            }
        }
        console.error(error);
        setLocationMessage('admin-location-action-message', reason, true);
    }
}

async function updateZoneRecord(zoneId, nextName) {
    const existing = getZoneById(zoneId);
    if (!existing) {
        setLocationMessage('admin-location-action-message', 'Zone not found.', true);
        return;
    }

    const payload = {
        name: String(nextName || '').trim(),
        floor: Number(existing.floor),
        notes: existing.notes || null,
        active: Boolean(existing.active),
    };

    try {
        await fetchJson(`/api/admin/zones/${zoneId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        setLocationMessage('admin-location-action-message', 'Zone updated.');
        await loadLocationOverview();
    } catch (error) {
        console.error(error);
        setLocationMessage('admin-location-action-message', locationErrorMessage(error, 'Could not update zone.'), true);
    }
}

async function deleteZoneRecord(zoneId) {
    if (!window.confirm(`Delete zone #${zoneId}?`)) return;

    try {
        await fetchJson(`/api/admin/zones/${zoneId}`, { method: 'DELETE' });
        setLocationMessage('admin-location-action-message', 'Zone deleted.');
        await loadLocationOverview();
    } catch (error) {
        const reason = locationErrorMessage(error, 'Could not delete zone.');
        const requiresForce = reason.toLowerCase().includes('cannot delete zone with tables assigned');
        if (requiresForce && window.confirm('Zone still has tables assigned. Force delete zone and those tables?')) {
            try {
                await fetchJson(`/api/admin/zones/${zoneId}?force=1`, { method: 'DELETE' });
                setLocationMessage('admin-location-action-message', 'Zone force deleted with assigned tables.');
                await loadLocationOverview();
                await loadAdminStats();
                return;
            } catch (forceError) {
                console.error(forceError);
                setLocationMessage('admin-location-action-message', locationErrorMessage(forceError, 'Could not force delete zone.'), true);
                return;
            }
        }
        console.error(error);
        setLocationMessage('admin-location-action-message', reason, true);
    }
}

async function updateTableRecord(tableId, nextNumberRaw, nextStatusRaw) {
    const row = getTableById(tableId);
    if (!row) {
        setLocationMessage('admin-location-action-message', 'Table record not found.', true);
        return;
    }

    const nextNumber = Number(nextNumberRaw);
    if (!Number.isInteger(nextNumber) || nextNumber <= 0) {
        setLocationMessage('admin-location-action-message', 'Table number must be a positive integer.', true);
        return;
    }
    const allowedStatuses = new Set(['available', 'maintenance']);
    const normalizedStatus = String(nextStatusRaw || row.status || 'available').trim().toLowerCase();
    const nextStatus = allowedStatuses.has(normalizedStatus) ? normalizedStatus : 'available';

    const payload = {
        number: nextNumber,
        capacity: Number(row.capacity),
        floor: Number(row.floor),
        zone: String(row.zone || '').trim(),
        status: nextStatus,
        features: row.features || {},
        width: row.width || null,
        height: row.height || null,
        rotation: row.rotation || null,
    };

    try {
        await fetchJson(`/api/admin/tables/${tableId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        setLocationMessage('admin-location-action-message', 'Table updated.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setLocationMessage('admin-location-action-message', locationErrorMessage(error, 'Could not update table.'), true);
    }
}

async function deleteTableRecord(tableId) {
    if (!window.confirm(`Delete table #${tableId}?`)) return;

    try {
        await fetchJson(`/api/admin/tables/${tableId}`, { method: 'DELETE' });
        setLocationMessage('admin-location-action-message', 'Table deleted.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        const reason = locationErrorMessage(error, 'Could not delete table.');
        if (reason.toLowerCase().includes('while it is occupied')) {
            window.alert(reason);
        }
        const requiresForce = reason.toLowerCase().includes('future reservations');
        if (requiresForce && window.confirm('Table has future reservations. Force delete table and remove table reservations?')) {
            try {
                await fetchJson(`/api/admin/tables/${tableId}?force=1`, { method: 'DELETE' });
                setLocationMessage('admin-location-action-message', 'Table force deleted.');
                await loadLocationOverview();
                await loadAdminStats();
                return;
            } catch (forceError) {
                console.error(forceError);
                setLocationMessage('admin-location-action-message', locationErrorMessage(forceError, 'Could not force delete table.'), true);
                return;
            }
        }
        console.error(error);
        setLocationMessage('admin-location-action-message', reason, true);
    }
}

function closeLocationModal() {
    const overlay = document.getElementById('admin-location-modal');
    const statusField = document.getElementById('admin-location-modal-status-field');
    const statusInput = document.getElementById('admin-location-modal-status-input');
    if (overlay) {
        overlay.hidden = true;
    }
    if (statusField) {
        statusField.hidden = true;
    }
    if (statusInput) {
        statusInput.value = 'available';
    }
    ADMIN_LOCATION_MODAL.kind = null;
    ADMIN_LOCATION_MODAL.id = null;
}

function openLocationModal(kind, id) {
    const overlay = document.getElementById('admin-location-modal');
    const title = document.getElementById('admin-location-modal-title');
    const label = document.getElementById('admin-location-modal-name-label');
    const meta = document.getElementById('admin-location-modal-meta');
    const input = document.getElementById('admin-location-modal-name-input');
    const statusField = document.getElementById('admin-location-modal-status-field');
    const statusInput = document.getElementById('admin-location-modal-status-input');
    if (!overlay || !title || !label || !meta || !input || !statusField || !statusInput) return;

    ADMIN_LOCATION_MODAL.kind = kind;
    ADMIN_LOCATION_MODAL.id = Number(id);

    if (kind === 'floor') {
        const floor = getFloorById(id);
        if (!floor) return;
        statusField.hidden = true;
        title.textContent = `Edit Floor ${floor.number}`;
        label.textContent = 'Floor name';
        meta.textContent = `Floor ${floor.number}`;
        input.type = 'text';
        input.min = '';
        input.step = '';
        input.value = floor.name || '';
    } else if (kind === 'zone') {
        const zone = getZoneById(id);
        if (!zone) return;
        statusField.hidden = true;
        title.textContent = `Edit Zone ${zone.name}`;
        label.textContent = 'Zone name';
        meta.textContent = `Floor ${zone.floor}`;
        input.type = 'text';
        input.min = '';
        input.step = '';
        input.value = zone.name || '';
    } else {
        const table = getTableById(id);
        if (!table) return;
        statusField.hidden = false;
        title.textContent = `Edit Table ${table.number}`;
        label.textContent = 'Table number';
        meta.textContent = `Floor ${table.floor} · Zone ${table.zone}`;
        input.type = 'number';
        input.min = '1';
        input.step = '1';
        input.value = String(table.number || '');
        statusInput.value = String(table.status || 'available').trim().toLowerCase() === 'maintenance'
            ? 'maintenance'
            : 'available';
    }

    overlay.hidden = false;
    window.setTimeout(() => input.focus(), 0);
}

async function submitLocationModal(event) {
    event.preventDefault();
    const input = document.getElementById('admin-location-modal-name-input');
    const statusInput = document.getElementById('admin-location-modal-status-input');
    if (!input || !statusInput) return;

    const kind = ADMIN_LOCATION_MODAL.kind;
    const id = Number(ADMIN_LOCATION_MODAL.id);
    const value = String(input.value || '').trim();
    if (!kind || !id || !value) {
        return;
    }

    if ((kind === 'floor' || kind === 'zone') && value.length > 100) {
        setLocationMessage('admin-location-action-message', 'Name is too long.', true);
        return;
    }

    if (kind === 'floor') {
        await updateFloorRecord(id, value);
    } else if (kind === 'zone') {
        await updateZoneRecord(id, value);
    } else {
        await updateTableRecord(id, value, statusInput.value);
    }

    closeLocationModal();
}

async function deleteFromLocationModal() {
    const kind = ADMIN_LOCATION_MODAL.kind;
    const id = Number(ADMIN_LOCATION_MODAL.id);
    if (!kind || !id) return;

    if (kind === 'floor') {
        await deleteFloorRecord(id);
    } else if (kind === 'zone') {
        await deleteZoneRecord(id);
    } else {
        await deleteTableRecord(id);
    }

    closeLocationModal();
}

function bindLocationOverviewActions() {
    document.querySelectorAll('[data-location-edit]').forEach((button) => {
        button.addEventListener('click', () => {
            const kind = String(button.getAttribute('data-location-edit') || '');
            const id = Number(button.getAttribute('data-location-id'));
            if (!kind) return;
            if (!id) {
                setLocationMessage(
                    'admin-location-action-message',
                    'This location has not been synced yet. Refresh once and try again.',
                    true,
                );
                return;
            }
            openLocationModal(kind, id);
        });
    });
}

async function loadLocationOverview(options = {}) {
    const skipMaterialize = Boolean(options.skipMaterialize);
    try {
        const [floors, zones, tables, confirmedReservations] = await Promise.all([
            fetchJson('/api/admin/floors'),
            fetchJson('/api/admin/zones'),
            fetchJson('/api/admin/tables'),
            fetchJson('/api/steward/reservations').catch(() => []),
        ]);

        ADMIN_LOCATION_STATE.floors = Array.isArray(floors) ? floors : [];
        ADMIN_LOCATION_STATE.zones = Array.isArray(zones) ? zones : [];
        ADMIN_LOCATION_STATE.tables = Array.isArray(tables) ? tables : [];
        const now = Date.now();
        ADMIN_LOCATION_STATE.reservedTableIds = new Set(
            (Array.isArray(confirmedReservations) ? confirmedReservations : [])
                .filter((reservation) => {
                    const ts = Date.parse(String(reservation?.start_ts || ''));
                    return Number.isFinite(ts) && ts > now;
                })
                .map((reservation) => Number(reservation?.table_id))
                .filter((tableId) => Number.isFinite(tableId) && tableId > 0),
        );

        // Backward-compatible bootstrap: materialize any missing floor/zone records implied by tables.
        if (!skipMaterialize && ADMIN_LOCATION_STATE.tables.length > 0) {
            const createdCount = await materializeLocationRecordsFromTables(
                ADMIN_LOCATION_STATE.tables,
                ADMIN_LOCATION_STATE.floors,
                ADMIN_LOCATION_STATE.zones,
            );
            if (createdCount > 0) {
                await loadLocationOverview({ skipMaterialize: true });
                return;
            }
        }

        // Fallback merge (read-only): keep API data, append derived rows if still missing.
        if (ADMIN_LOCATION_STATE.tables.length > 0) {
            const derived = deriveLocationStateFromTables(ADMIN_LOCATION_STATE.tables);
            const floorNumbers = new Set(ADMIN_LOCATION_STATE.floors.map((floor) => Number(floor.number)));
            const mergedFloors = [...ADMIN_LOCATION_STATE.floors];
            derived.floors.forEach((floor) => {
                if (!floorNumbers.has(Number(floor.number))) {
                    mergedFloors.push(floor);
                }
            });
            ADMIN_LOCATION_STATE.floors = mergedFloors.sort((a, b) => Number(a.number) - Number(b.number));

            const zoneKeys = new Set(
                ADMIN_LOCATION_STATE.zones.map((zone) => `${Number(zone.floor)}:${String(zone.name || '').trim().toLowerCase()}`),
            );
            const mergedZones = [...ADMIN_LOCATION_STATE.zones];
            derived.zones.forEach((zone) => {
                const zoneKey = `${Number(zone.floor)}:${String(zone.name || '').trim().toLowerCase()}`;
                if (!zoneKeys.has(zoneKey)) {
                    mergedZones.push(zone);
                }
            });
            ADMIN_LOCATION_STATE.zones = mergedZones.sort((a, b) => (Number(a.floor) - Number(b.floor)) || String(a.name || '').localeCompare(String(b.name || '')));
        }

        updateFloorSelectOptions();
        renderLocationOverview();
        renderLocationFloorplan();

        const zoneFloorInput = document.getElementById('zone-floor');
        if (zoneFloorInput && !zoneFloorInput.value) {
            zoneFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || '');
        }

        const tableFloorInput = document.getElementById('table-floor');
        if (tableFloorInput && !tableFloorInput.value) {
            tableFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || '');
        }
    } catch (error) {
        console.error(error);
        setLocationMessage('create-floor-message', 'Could not load floor overview.', true);
    }
}

async function createFloor(form) {
    const payload = {
        number: Number(form.elements.namedItem('number')?.value),
        name: String(form.elements.namedItem('name')?.value || '').trim(),
        active: true,
        notes: null,
    };

    try {
        await fetchJson('/api/admin/floors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        setLocationMessage('create-floor-message', 'Floor created.');
        await loadLocationOverview();
        const selectedFloorInput = document.getElementById('zone-floor');
        if (selectedFloorInput) {
            selectedFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || '');
        }
    } catch (error) {
        console.error(error);
        setLocationMessage('create-floor-message', locationErrorMessage(error, 'Could not create floor.'), true);
    }
}

async function createZone(form) {
    const payload = {
        floor: Number(form.elements.namedItem('floor')?.value),
        name: String(form.elements.namedItem('name')?.value || '').trim(),
        active: true,
        notes: String(form.elements.namedItem('notes')?.value || '').trim() || null,
    };

    try {
        await fetchJson('/api/admin/zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        setLocationMessage('create-zone-message', 'Zone created.');
        await loadLocationOverview();
        const selectedFloorInput = document.getElementById('table-floor');
        if (selectedFloorInput) {
            selectedFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || payload.floor || '');
        }
    } catch (error) {
        console.error(error);
        setLocationMessage('create-zone-message', locationErrorMessage(error, 'Could not create zone.'), true);
    }
}

async function createTable(form) {
    const payload = {
        number: Number(form.elements.namedItem('number')?.value),
        capacity: Number(form.elements.namedItem('capacity')?.value),
        floor: Number(form.elements.namedItem('floor')?.value),
        zone: String(form.elements.namedItem('zone')?.value || '').trim(),
        status: 'available',
        features: {},
    };

    try {
        await fetchJson('/api/admin/tables', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        setLocationMessage('create-table-message', 'Table created.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setLocationMessage('create-table-message', locationErrorMessage(error, 'Could not create table.'), true);
    }
}

function renderAnnouncements(announcements) {
    const container = document.getElementById('admin-announcements-list');
    if (!container) return;

    if (!Array.isArray(announcements) || announcements.length === 0) {
        container.textContent = 'No announcements yet.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    announcements.forEach((announcement) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        const publishMeta = announcement.is_published
            ? `Published ${announcement.published_at ? new Date(announcement.published_at).toLocaleString() : ''}`
            : 'Draft';

        item.innerHTML = `
            <div class="steward-item-head">
                <p class="steward-item-title">${announcement.title}</p>
                <span class="steward-item-meta">${publishMeta}</span>
            </div>
            <p class="steward-item-meta">${announcement.body}</p>
            <p class="steward-item-meta">CTA: ${announcement.cta_label && announcement.cta_url ? `${announcement.cta_label} -> ${announcement.cta_url}` : 'none'}</p>
            <div class="steward-item-actions">
                <button class="button button-secondary" type="button" data-announcement-toggle="${announcement.id}">${announcement.is_published ? 'Unpublish' : 'Publish'}</button>
                <button class="button button-subtle" type="button" data-announcement-delete="${announcement.id}">Delete</button>
            </div>
        `;

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);

    container.querySelectorAll('[data-announcement-toggle]').forEach((button) => {
        button.addEventListener('click', async () => {
            const announcementId = Number(button.getAttribute('data-announcement-toggle'));
            const row = ADMIN_ANNOUNCEMENTS.items.find((item) => item.id === announcementId);
            if (!row) return;

            const endpoint = row.is_published
                ? `/api/admin/content/announcements/${announcementId}/unpublish`
                : `/api/admin/content/announcements/${announcementId}/publish`;

            try {
                await fetchJson(endpoint, { method: 'POST' });
                await loadAnnouncements();
            } catch (error) {
                console.error(error);
                setAnnouncementMessage('Could not update announcement state.', true);
            }
        });
    });

    container.querySelectorAll('[data-announcement-delete]').forEach((button) => {
        button.addEventListener('click', async () => {
            const announcementId = Number(button.getAttribute('data-announcement-delete'));
            if (!window.confirm(`Delete announcement #${announcementId}?`)) return;

            try {
                await fetchJson(`/api/admin/content/announcements/${announcementId}`, { method: 'DELETE' });
                setAnnouncementMessage('Announcement deleted.');
                await loadAnnouncements();
            } catch (error) {
                console.error(error);
                setAnnouncementMessage('Could not delete announcement.', true);
            }
        });
    });
}

async function loadAnnouncements() {
    try {
        const items = await fetchJson('/api/admin/content/announcements');
        ADMIN_ANNOUNCEMENTS.items = Array.isArray(items) ? items : [];
        renderAnnouncements(ADMIN_ANNOUNCEMENTS.items);
    } catch (error) {
        console.error(error);
        setAnnouncementMessage('Could not load announcements.', true);
        const container = document.getElementById('admin-announcements-list');
        if (container) container.textContent = 'Could not load announcements.';
    }
}

async function createAnnouncementFromAdminForm(form) {
    const payload = {
        title: form.elements.namedItem('title')?.value,
        body: form.elements.namedItem('body')?.value,
        cta_label: form.elements.namedItem('cta_label')?.value || null,
        cta_url: form.elements.namedItem('cta_url')?.value || null,
        publish_now: Boolean(form.elements.namedItem('publish_now')?.checked),
    };

    try {
        await fetchJson('/api/admin/content/announcements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        form.reset();
        const publishNowInput = form.elements.namedItem('publish_now');
        if (publishNowInput) publishNowInput.checked = true;
        setAnnouncementMessage('Announcement saved.');
        await loadAnnouncements();
    } catch (error) {
        console.error(error);
        setAnnouncementMessage('Could not save announcement.', true);
    }
}

function widgetCollapseStorageKey(groupId) {
    return `admin.widget.group.collapsed.${groupId}`;
}

function setWidgetCollapsedState(section, toggle, collapsed) {
    const widgetTitle = section.dataset.widgetTitle || 'widget';
    section.classList.toggle('widget-collapsed', collapsed);
    toggle.textContent = collapsed ? '+' : '-';
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.setAttribute('aria-label', collapsed ? `Expand ${widgetTitle}` : `Collapse ${widgetTitle}`);
}

function setupAdminWidgetCollapse() {
    const dashboard = document.getElementById('admin-data');
    if (!dashboard) return;

    const widgets = dashboard.querySelectorAll('.steward-main-grid > section.card[id]');
    const entries = [];

    widgets.forEach((section) => {
        const heading = section.querySelector('h3');
        if (!heading) {
            return;
        }

        section.dataset.widgetTitle = (heading.textContent || 'widget').trim();
        heading.classList.add('dashboard-widget-title');

        let toggle = section.querySelector('.dashboard-widget-toggle');
        if (!toggle) {
            toggle = document.createElement('button');
            toggle.type = 'button';
            toggle.className = 'dashboard-widget-toggle';
            heading.appendChild(toggle);
        }

        entries.push({ section, toggle });
    });

    const groupsByTop = new Map();
    entries.forEach((entry) => {
        const topKey = String(entry.section.offsetTop);
        const group = groupsByTop.get(topKey) || [];
        group.push(entry);
        groupsByTop.set(topKey, group);
    });

    groupsByTop.forEach((groupEntries) => {
        const groupId = groupEntries
            .map((entry) => entry.section.id)
            .sort()
            .join('|');

        let isCollapsed = false;
        try {
            isCollapsed = window.localStorage.getItem(widgetCollapseStorageKey(groupId)) === '1';
        } catch (_error) {
            isCollapsed = false;
        }

        const applyGroupState = (collapsed) => {
            groupEntries.forEach(({ section, toggle }) => {
                setWidgetCollapsedState(section, toggle, collapsed);
            });
        };

        applyGroupState(isCollapsed);

        groupEntries.forEach(({ section, toggle }) => {
            toggle.addEventListener('click', () => {
                const next = !section.classList.contains('widget-collapsed');
                applyGroupState(next);
                try {
                    window.localStorage.setItem(widgetCollapseStorageKey(groupId), next ? '1' : '0');
                } catch (_error) {
                    // Storage can be unavailable in strict browser modes.
                }
            });
        });
    });
}

function updateAdminSummaryUI() {
    const map = [
        ['metric-users', ADMIN_SUMMARY.users],
        ['metric-games', ADMIN_SUMMARY.games],
        ['metric-copies', ADMIN_SUMMARY.copies],
        ['metric-tables', ADMIN_SUMMARY.tables],
        ['metric-open-bookings', ADMIN_SUMMARY.openBookings],
        ['metric-open-incidents', ADMIN_SUMMARY.openIncidents],
        ['metric-published-announcements', ADMIN_SUMMARY.publishedAnnouncements],
    ];

    map.forEach(([id, value]) => {
        const node = document.getElementById(id);
        if (node) node.textContent = String(value);
    });

    const updated = document.getElementById('admin-last-updated');
    if (updated) {
        updated.textContent = ADMIN_SUMMARY.lastUpdated
            ? `Last updated: ${ADMIN_SUMMARY.lastUpdated.toLocaleTimeString()}`
            : 'Last updated: --';
    }
}

const ADMIN_USERS = { all: [] };

function renderUsers(users) {
    const container = document.getElementById('admin-user-list');
    if (!container) return;

    if (!Array.isArray(users) || users.length === 0) {
        container.textContent = 'No users found.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    users.forEach((user) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        const head = document.createElement('div');
        head.className = 'steward-item-head';

        const title = document.createElement('p');
        title.className = 'steward-item-title';
        title.textContent = `${user.name} (${user.email})`;

        const role = document.createElement('span');
        role.className = 'status-pill';
        role.textContent = String(user.role || 'unknown');

        head.appendChild(title);
        head.appendChild(role);
        item.appendChild(head);

        const meta = document.createElement('p');
        meta.className = 'steward-item-meta';
        const statusBits = [];
        statusBits.push(user.force_password_change ? 'Password reset required' : 'Password status: normal');
        statusBits.push(user.is_suspended ? 'Account suspended' : 'Account active');
        meta.textContent = statusBits.join(' · ');
        item.appendChild(meta);

        const actions = document.createElement('div');
        actions.className = 'steward-item-actions';

        if (!user.force_password_change) {
            const resetBtn = document.createElement('button');
            resetBtn.className = 'button button-subtle';
            resetBtn.textContent = 'Force password reset';
            resetBtn.addEventListener('click', async () => {
                try {
                    await fetchJson(`/api/admin/users/${user.id}/force-password-reset`, { method: 'POST' });
                    setUserManagementMessage('Password reset required on next login.');
                    await loadUsers();
                } catch (error) {
                    console.error(error);
                    setUserManagementMessage('Could not force password reset.', true);
                }
            });

            actions.appendChild(resetBtn);
        }

        const suspendBtn = document.createElement('button');
        suspendBtn.className = 'button button-subtle';
        const nextSuspended = !Boolean(user.is_suspended);
        suspendBtn.textContent = nextSuspended ? 'Suspend user' : 'Unsuspend user';
        suspendBtn.addEventListener('click', async () => {
            const promptText = nextSuspended
                ? `Suspend user ${user.email}? They will no longer be able to sign in.`
                : `Unsuspend user ${user.email}?`;
            if (!window.confirm(promptText)) return;
            try {
                await fetchJson(`/api/admin/users/${user.id}/suspension`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ suspended: nextSuspended }),
                });
                setUserManagementMessage(nextSuspended ? 'User suspended.' : 'User unsuspended.');
                await loadUsers();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setUserManagementMessage('Could not update suspension status.', true);
            }
        });

        actions.appendChild(suspendBtn);
        item.appendChild(actions);

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);
}

async function loadUsers() {
    try {
        const users = await fetchJson('/api/admin/users');
        ADMIN_USERS.all = Array.isArray(users) ? users : [];
        const query = (document.getElementById('admin-user-search')?.value || '').trim().toLowerCase();
        renderUsers(query ? ADMIN_USERS.all.filter((u) => _userMatchesSearch(u, query)) : ADMIN_USERS.all);
    } catch (error) {
        console.error(error);
        const container = document.getElementById('admin-user-list');
        if (container) container.textContent = 'Error loading users';
    }
}

function _userMatchesSearch(user, query) {
    return (
        String(user.name || '').toLowerCase().includes(query) ||
        String(user.email || '').toLowerCase().includes(query) ||
        String(user.role || '').toLowerCase().includes(query)
    );
}

async function createSteward(form) {
    const message = document.getElementById('create-steward-message');
    if (message) message.textContent = '';

    const nameInput = form.elements.namedItem('name');
    const emailInput = form.elements.namedItem('email');
    const phoneInput = form.elements.namedItem('phone');
    const passwordInput = form.elements.namedItem('password');

    const payload = {
        name: nameInput ? nameInput.value : '',
        email: emailInput ? emailInput.value : '',
        phone: phoneInput ? (phoneInput.value || null) : null,
        password: passwordInput ? passwordInput.value : '',
    };

    try {
        await fetchJson('/api/admin/stewards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        if (message) message.textContent = 'Steward account created.';
        await loadUsers();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        if (message) message.textContent = 'Could not create steward account.';
    }
}

async function loadAdminStats() {
    try {
        setAdminConnection('Loading admin stats...');
        const data = await fetchJson('/api/admin/dashboard/stats');

        ADMIN_SUMMARY.users = data.users_total || 0;
        ADMIN_SUMMARY.games = data.games_total || 0;
        ADMIN_SUMMARY.copies = data.copies_total || 0;
        ADMIN_SUMMARY.tables = data.tables_total || 0;
        ADMIN_SUMMARY.openBookings = data.open_bookings || 0;
        ADMIN_SUMMARY.openIncidents = data.open_incidents || 0;
        ADMIN_SUMMARY.publishedAnnouncements = data.published_announcements || 0;
        ADMIN_SUMMARY.lastUpdated = new Date();

        updateAdminSummaryUI();
        setAdminConnection('Admin stats loaded');
    } catch (error) {
        console.error(error);
        setAdminConnection('Error loading admin stats');
    }
}

function renderTablePricing(tables) {
    const container = document.getElementById('admin-table-pricing-list');
    if (!container) return;

    if (!Array.isArray(tables) || tables.length === 0) {
        container.textContent = 'No tables found.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    tables.forEach((table) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        item.innerHTML = `
            <div class="steward-item-head">
                <p class="steward-item-title">Table ${table.table_nr} (Floor ${table.floor})</p>
                <span class="steward-item-meta">Cap ${table.capacity}</span>
            </div>
            <div class="steward-item-actions">
                <input class="form-input" type="number" min="0" step="0.01" value="${centsToNok(table.price_cents)}" data-table-price-input="${table.id}" style="max-width: 140px;">
                <button class="button button-secondary" type="button" data-table-price-save="${table.id}">Save</button>
            </div>
        `;

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);

    container.querySelectorAll('[data-table-price-save]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const tableId = Number(btn.getAttribute('data-table-price-save'));
            const input = container.querySelector(`[data-table-price-input="${tableId}"]`);
            const cents = nokToCents(input?.value);
            if (cents === null) {
                setPricingMessage('Table price must be a non-negative number.', true);
                return;
            }

            try {
                await fetchJson(`/api/admin/pricing/tables/${tableId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ price_cents: cents }),
                });
                setPricingMessage('Table price updated.');
                await loadPricing();
            } catch (error) {
                console.error(error);
                setPricingMessage('Could not update table price.', true);
            }
        });
    });
}

function renderGamePricing(games) {
    const container = document.getElementById('admin-game-pricing-list');
    if (!container) return;

    if (!Array.isArray(games) || games.length === 0) {
        container.textContent = 'No games found.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    games.forEach((game) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        item.innerHTML = `
            <div class="steward-item-head">
                <p class="steward-item-title">${game.title}</p>
            </div>
            <div class="steward-item-actions">
                <input class="form-input" type="number" min="0" step="0.01" value="${centsToNok(game.price_cents)}" data-game-price-input="${game.id}" style="max-width: 140px;">
                <button class="button button-secondary" type="button" data-game-price-save="${game.id}">Save</button>
            </div>
        `;

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);

    container.querySelectorAll('[data-game-price-save]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const gameId = Number(btn.getAttribute('data-game-price-save'));
            const input = container.querySelector(`[data-game-price-input="${gameId}"]`);
            const cents = nokToCents(input?.value);
            if (cents === null) {
                setPricingMessage('Game price must be a non-negative number.', true);
                return;
            }

            try {
                await fetchJson(`/api/admin/pricing/games/${gameId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ price_cents: cents }),
                });
                setPricingMessage('Game price updated.');
                await loadPricing();
            } catch (error) {
                console.error(error);
                setPricingMessage('Could not update game price.', true);
            }
        });
    });
}

function setPricingMessage(message, isError = false) {
    const node = document.getElementById('pricing-message');
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function setCatalogueMessage(message, isError = false) {
    const node = document.getElementById('catalogue-message');
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? '#8d2430' : '';
}

function normalizedSearchValue(value) {
    return String(value || '').trim().toLowerCase();
}

function formatCopyCount(count) {
    return count === 1 ? '1 copy' : `${count} copies`;
}

function slugifyCopyCodePrefix(title, gameId) {
    const normalized = String(title || '')
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .replace(/[^A-Z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');

    return normalized || `GAME${gameId}`;
}

function buildSuggestedCopyCode(gameId, games, copies) {
    const numericGameId = Number(gameId);
    if (!numericGameId) {
        return '';
    }

    const game = (Array.isArray(games) ? games : []).find((item) => Number(item.id) === numericGameId);
    const prefix = slugifyCopyCodePrefix(game?.title, numericGameId);

    const highestSequence = (Array.isArray(copies) ? copies : []).reduce((max, copy) => {
        if (Number(copy.game_id) !== numericGameId) {
            return max;
        }

        const match = String(copy.copy_code || '').match(/(\d+)$/);
        if (!match) {
            return max;
        }

        return Math.max(max, Number(match[1]));
    }, 0);

    return `${prefix}-${String(highestSequence + 1).padStart(3, '0')}`;
}

function updateSuggestedCopyCode({ force = false } = {}) {
    const gameSelect = document.getElementById('admin-copy-game-id');
    const codeInput = document.getElementById('admin-copy-code');
    if (!gameSelect || !codeInput) return;

    const suggestion = buildSuggestedCopyCode(gameSelect.value, ADMIN_CATALOGUE.games, ADMIN_CATALOGUE.copies);
    const currentValue = codeInput.value.trim();
    const lastSuggested = codeInput.dataset.suggestedValue || '';

    if (force || !currentValue || currentValue === lastSuggested) {
        codeInput.value = suggestion;
    }

    codeInput.dataset.suggestedValue = suggestion;
    codeInput.placeholder = suggestion || '';
}

function renderCopyGameSelect(games, copies) {
    const select = document.getElementById('admin-copy-game-id');
    if (!select) return;

    const selected = select.value;
    const sorted = [...games].sort((a, b) => String(a.title || '').localeCompare(String(b.title || '')));
    const copyCounts = new Map();

    (Array.isArray(copies) ? copies : []).forEach((copy) => {
        const gameId = Number(copy.game_id);
        copyCounts.set(gameId, (copyCounts.get(gameId) || 0) + 1);
    });

    select.innerHTML = '';

    sorted.forEach((game) => {
        const option = document.createElement('option');
        option.value = String(game.id);
        const copyCount = copyCounts.get(Number(game.id)) || 0;
        option.textContent = `${game.title} (#${game.id}) - ${formatCopyCount(copyCount)}`;
        select.appendChild(option);
    });

    if (selected && Array.from(select.options).some((opt) => opt.value === selected)) {
        select.value = selected;
    }

    updateSuggestedCopyCode();
}

function renderCatalogueGames(games) {
    const container = document.getElementById('admin-catalogue-games');
    if (!container) return;

    const query = normalizedSearchValue(document.getElementById('admin-catalogue-game-search')?.value);
    const filteredGames = !query
        ? games
        : games.filter((game) => {
            const haystack = normalizedSearchValue([
                game.title,
                game.id,
                game.description,
            ].join(' '));
            return haystack.includes(query);
        });

    if (!Array.isArray(games) || games.length === 0) {
        container.textContent = 'No games found.';
        return;
    }

    if (filteredGames.length === 0) {
        container.textContent = 'No games match your search.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    filteredGames.forEach((game) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        item.innerHTML = `
            <div class="steward-item-head">
                <p class="steward-item-title">${game.title} (#${game.id})</p>
                <span class="steward-item-meta">${game.min_players}-${game.max_players} players · ${game.playtime_min} min</span>
            </div>
            <div class="form-grid-two">
                <div><label class="form-label">Title</label><input class="form-input" data-game-field="title" data-game-id="${game.id}" value="${game.title || ''}"></div>
                <div><label class="form-label">Price (NOK)</label><input class="form-input" type="number" min="0" step="0.01" data-game-field="price_nok" data-game-id="${game.id}" value="${centsToNok(game.price_cents)}"></div>
                <div><label class="form-label">Min players</label><input class="form-input" type="number" min="1" data-game-field="min_players" data-game-id="${game.id}" value="${game.min_players}"></div>
                <div><label class="form-label">Max players</label><input class="form-input" type="number" min="1" data-game-field="max_players" data-game-id="${game.id}" value="${game.max_players}"></div>
                <div><label class="form-label">Playtime min</label><input class="form-input" type="number" min="0" data-game-field="playtime_min" data-game-id="${game.id}" value="${game.playtime_min}"></div>
                <div><label class="form-label">Complexity</label><input class="form-input" type="number" min="0" max="5" step="0.1" data-game-field="complexity" data-game-id="${game.id}" value="${Number(game.complexity || 0)}"></div>
            </div>
            <div class="form-grid-two">
                <div><label class="form-label">Image URL</label><input class="form-input" data-game-field="image_url" data-game-id="${game.id}" value="${game.image_url || ''}"></div>
                <div><label class="form-label">Description</label><input class="form-input" data-game-field="description" data-game-id="${game.id}" value="${game.description || ''}"></div>
            </div>
            <div class="steward-item-actions">
                <button class="button button-secondary" type="button" data-game-save="${game.id}">Save</button>
                <button class="button button-subtle" type="button" data-game-delete="${game.id}">Delete game</button>
            </div>
        `;

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);

    container.querySelectorAll('[data-game-save]').forEach((button) => {
        button.addEventListener('click', async () => {
            const gameId = Number(button.getAttribute('data-game-save'));
            const q = (field) => container.querySelector(`[data-game-field="${field}"][data-game-id="${gameId}"]`);
            const priceCents = nokToCents(q('price_nok')?.value);
            if (priceCents === null) {
                setCatalogueMessage('Game price must be a non-negative number.', true);
                return;
            }

            const payload = {
                title: q('title')?.value,
                min_players: Number(q('min_players')?.value),
                max_players: Number(q('max_players')?.value),
                playtime_min: Number(q('playtime_min')?.value),
                complexity: Number(q('complexity')?.value),
                price_cents: priceCents,
                image_url: q('image_url')?.value || null,
                description: q('description')?.value || null,
            };

            try {
                await fetchJson(`/api/admin/catalogue/games/${gameId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                setCatalogueMessage('Game updated.');
                await loadCatalogue();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setCatalogueMessage('Could not update game.', true);
            }
        });
    });

    container.querySelectorAll('[data-game-delete]').forEach((button) => {
        button.addEventListener('click', async () => {
            const gameId = Number(button.getAttribute('data-game-delete'));
            if (!window.confirm(`Delete game #${gameId}?`)) return;

            try {
                await fetchJson(`/api/admin/catalogue/games/${gameId}`, { method: 'DELETE' });
                setCatalogueMessage('Game deleted.');
                await loadCatalogue();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setCatalogueMessage('Could not delete game. Delete copies first.', true);
            }
        });
    });
}

function renderCatalogueCopies(copies) {
    const container = document.getElementById('admin-catalogue-copies');
    if (!container) return;

    const query = normalizedSearchValue(document.getElementById('admin-catalogue-copy-search')?.value);
    const filteredCopies = !query
        ? copies
        : copies.filter((copy) => {
            const haystack = normalizedSearchValue([
                copy.copy_code,
                copy.id,
                copy.game_title,
                copy.game_id,
                copy.location,
                copy.status,
                copy.condition_note,
            ].join(' '));
            return haystack.includes(query);
        });

    if (!Array.isArray(copies) || copies.length === 0) {
        container.textContent = 'No copies found.';
        return;
    }

    if (filteredCopies.length === 0) {
        container.textContent = 'No copies match your search.';
        return;
    }

    const list = document.createElement('div');
    list.className = 'steward-item-list';

    filteredCopies.forEach((copy) => {
        const item = document.createElement('article');
        item.className = 'steward-item';

        item.innerHTML = `
            <div class="steward-item-head">
                <p class="steward-item-title">${copy.copy_code} (#${copy.id})</p>
                <span class="steward-item-meta">${copy.game_title || `Game #${copy.game_id}`}</span>
            </div>
            <div class="form-grid-two">
                <div><label class="form-label">Code</label><input class="form-input" data-copy-field="copy_code" data-copy-id="${copy.id}" value="${copy.copy_code || ''}"></div>
                <div><label class="form-label">Location</label><input class="form-input" data-copy-field="location" data-copy-id="${copy.id}" value="${copy.location || ''}"></div>
                <div><label class="form-label">Status</label>
                    <select class="form-input" data-copy-field="status" data-copy-id="${copy.id}">
                        <option value="available" ${copy.status === 'available' ? 'selected' : ''}>available</option>
                        <option value="reserved" ${copy.status === 'reserved' ? 'selected' : ''}>reserved</option>
                        <option value="in_use" ${copy.status === 'in_use' ? 'selected' : ''}>in_use</option>
                        <option value="maintenance" ${copy.status === 'maintenance' ? 'selected' : ''}>unavailable</option>
                        <option value="lost" ${copy.status === 'lost' ? 'selected' : ''}>lost</option>
                        <option value="occupied" ${copy.status === 'occupied' ? 'selected' : ''}>occupied</option>
                    </select>
                </div>
                <div><label class="form-label">Condition</label><input class="form-input" data-copy-field="condition_note" data-copy-id="${copy.id}" value="${copy.condition_note || ''}"></div>
            </div>
            <div class="steward-item-actions">
                <button class="button button-secondary" type="button" data-copy-save="${copy.id}">Save</button>
                <button class="button button-subtle" type="button" data-copy-delete="${copy.id}">Delete copy</button>
            </div>
        `;

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);

    container.querySelectorAll('[data-copy-save]').forEach((button) => {
        button.addEventListener('click', async () => {
            const copyId = Number(button.getAttribute('data-copy-save'));
            const q = (field) => container.querySelector(`[data-copy-field="${field}"][data-copy-id="${copyId}"]`);
            const payload = {
                copy_code: q('copy_code')?.value,
                status: q('status')?.value,
                location: q('location')?.value || null,
                condition_note: q('condition_note')?.value || null,
            };

            try {
                await fetchJson(`/api/admin/catalogue/copies/${copyId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                setCatalogueMessage('Copy updated.');
                await loadCatalogue();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setCatalogueMessage('Could not update copy.', true);
            }
        });
    });

    container.querySelectorAll('[data-copy-delete]').forEach((button) => {
        button.addEventListener('click', async () => {
            const copyId = Number(button.getAttribute('data-copy-delete'));
            if (!window.confirm(`Delete copy #${copyId}?`)) return;

            try {
                await fetchJson(`/api/admin/catalogue/copies/${copyId}`, { method: 'DELETE' });
                setCatalogueMessage('Copy deleted.');
                await loadCatalogue();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setCatalogueMessage('Could not delete copy.', true);
            }
        });
    });

}

async function loadCopyIncidents() {
    const container = document.getElementById('admin-copy-incidents');
    if (!container) return;
    container.textContent = 'Loading incidents...';

    try {
        const incidents = await fetchJson('/api/admin/catalogue/incidents');
        if (!Array.isArray(incidents) || incidents.length === 0) {
            container.textContent = 'There are no incidents.';
            return;
        }

        const list = document.createElement('div');
        list.className = 'steward-item-list';
        incidents.forEach((incident) => {
            const item = document.createElement('article');
            item.className = 'steward-item';
            item.innerHTML = `
                <div class="steward-item-head">
                    <p class="steward-item-title">Incident #${incident.id} · ${incident.incident_type}</p>
                    <span class="steward-item-meta">${incident.created_at ? new Date(incident.created_at).toLocaleString() : ''}</span>
                </div>
                <p class="steward-item-meta">Copy: ${incident.game_copy_code || `#${incident.game_copy_id}`} · ${incident.game_title || 'Unknown game'}</p>
                <p class="steward-item-meta">Reported by: ${incident.reported_by_name || `User #${incident.reported_by}`}</p>
                <p class="steward-item-meta">${incident.note || ''}</p>
                <div class="steward-item-actions">
                    <button class="button button-secondary" type="button" data-incident-resolve="${incident.id}">Resolved</button>
                </div>
            `;
            list.appendChild(item);
        });

        container.innerHTML = '';
        container.appendChild(list);

        container.querySelectorAll('[data-incident-resolve]').forEach((button) => {
            button.addEventListener('click', async () => {
                const incidentId = Number(button.getAttribute('data-incident-resolve'));
                if (!window.confirm(`Resolve incident #${incidentId}? This will set the copy status to available.`)) {
                    return;
                }

                try {
                    await fetchJson(`/api/admin/catalogue/incidents/${incidentId}/resolve`, { method: 'POST' });
                    await loadCatalogue();
                    await loadAdminStats();
                } catch (resolveError) {
                    console.error(resolveError);
                    setCatalogueMessage('Could not resolve incident.', true);
                }
            });
        });
    } catch (error) {
        console.error(error);
        container.textContent = 'Could not load incidents.';
    }
}

async function loadCatalogue() {
    try {
        const data = await fetchJson('/api/admin/catalogue');
        ADMIN_CATALOGUE.games = Array.isArray(data.games) ? data.games : [];
        ADMIN_CATALOGUE.copies = Array.isArray(data.copies) ? data.copies : [];

        renderCopyGameSelect(ADMIN_CATALOGUE.games, ADMIN_CATALOGUE.copies);
        renderCatalogueGames(ADMIN_CATALOGUE.games);
        renderCatalogueCopies(ADMIN_CATALOGUE.copies);
        await loadCopyIncidents();
    } catch (error) {
        console.error(error);
        setCatalogueMessage('Could not load catalogue.', true);
        const gamesContainer = document.getElementById('admin-catalogue-games');
        const copiesContainer = document.getElementById('admin-catalogue-copies');
        const incidentsContainer = document.getElementById('admin-copy-incidents');
        if (gamesContainer) gamesContainer.textContent = 'Error loading games.';
        if (copiesContainer) copiesContainer.textContent = 'Error loading copies.';
        if (incidentsContainer) incidentsContainer.textContent = 'Could not load incidents.';
    }
}

async function createGameFromAdminForm(form) {
    const payload = {
        title: form.elements.namedItem('title')?.value,
        min_players: Number(form.elements.namedItem('min_players')?.value),
        max_players: Number(form.elements.namedItem('max_players')?.value),
        playtime_min: Number(form.elements.namedItem('playtime_min')?.value),
        complexity: Number(form.elements.namedItem('complexity')?.value),
        image_url: form.elements.namedItem('image_url')?.value || null,
        description: form.elements.namedItem('description')?.value || null,
    };

    const priceCents = nokToCents(form.elements.namedItem('price_nok')?.value);
    if (priceCents === null) {
        setCatalogueMessage('Game price must be a non-negative number.', true);
        return;
    }
    payload.price_cents = priceCents;

    try {
        await fetchJson('/api/admin/catalogue/games', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        setCatalogueMessage('Game created.');
        await loadCatalogue();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setCatalogueMessage('Could not create game.', true);
    }
}

async function createCopyFromAdminForm(form) {
    const payload = {
        game_id: Number(form.elements.namedItem('game_id')?.value),
        copy_code: form.elements.namedItem('copy_code')?.value,
        status: form.elements.namedItem('status')?.value,
        location: form.elements.namedItem('location')?.value || null,
        condition_note: form.elements.namedItem('condition_note')?.value || null,
    };

    try {
        await fetchJson('/api/admin/catalogue/copies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        form.reset();
        const statusInput = form.elements.namedItem('status');
        if (statusInput) statusInput.value = 'available';
        setCatalogueMessage('Copy created.');
        await loadCatalogue();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setCatalogueMessage('Could not create copy.', true);
    }
}

async function loadPricing() {
    try {
        const data = await fetchJson('/api/admin/pricing');
        const baseInput = document.getElementById('pricing-base-fee');
        const untilInput = document.getElementById('pricing-base-fee-until');
        const priorityInput = document.getElementById('pricing-base-fee-priority');
        const cancelLimitInput = document.getElementById('pricing-cancel-time-limit');
        if (baseInput) {
            baseInput.value = centsToNok(data.booking_base_fee_cents);
        }
        if (untilInput) {
            untilInput.value = isoToDatetimeLocal(data.booking_base_fee_active_until);
        }
        if (priorityInput) {
            priorityInput.value = String(data.booking_base_fee_priority ?? 0);
        }
        if (cancelLimitInput) {
            cancelLimitInput.value = String(data.booking_cancel_time_limit_hours ?? 24);
        }

        if (data.booking_base_fee_has_temporary_override && data.booking_base_fee_active_until) {
            setPricingMessage(`Temporary base fee active until ${new Date(data.booking_base_fee_active_until).toLocaleString()}.`);
        }

        renderTablePricing(data.tables || []);
        renderGamePricing(data.games || []);
    } catch (error) {
        console.error(error);
        setPricingMessage('Could not load pricing data.', true);
    }
}

async function saveBaseFee(form) {
    const input = form.elements.namedItem('booking_base_fee');
    const untilInput = form.elements.namedItem('booking_base_fee_active_until');
    const priorityInput = form.elements.namedItem('booking_base_fee_priority');
    const cancelLimitInput = form.elements.namedItem('booking_cancel_time_limit_hours');
    const cents = nokToCents(input ? input.value : null);
    const activeUntilIso = datetimeLocalToIso(untilInput ? untilInput.value : '');
    const priorityRaw = priorityInput ? priorityInput.value : '0';
    const cancelLimitRaw = cancelLimitInput ? cancelLimitInput.value : '24';
    const priority = Number(priorityRaw);
    const cancelLimitHours = Number(cancelLimitRaw);

    if (cents === null) {
        setPricingMessage('Base fee must be a non-negative number.', true);
        return;
    }

    if (untilInput && untilInput.value && !activeUntilIso) {
        setPricingMessage('Active-until timestamp must be a valid datetime.', true);
        return;
    }

    if (!Number.isInteger(priority) || priority < 0) {
        setPricingMessage('Priority must be a non-negative whole number.', true);
        return;
    }

    if (!Number.isInteger(cancelLimitHours) || cancelLimitHours < 0) {
        setPricingMessage('Cancel time limit must be a non-negative whole number.', true);
        return;
    }

    try {
        await fetchJson('/api/admin/pricing/base-fee', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                booking_base_fee_cents: cents,
                booking_base_fee_active_until: activeUntilIso,
                booking_base_fee_priority: priority,
                booking_cancel_time_limit_hours: cancelLimitHours,
            }),
        });
        setPricingMessage('Base fee saved.');
        await loadPricing();
    } catch (error) {
        console.error(error);
        setPricingMessage('Could not save base fee.', true);
    }
}

function bindAdminDashboard() {
    setupAdminWidgetCollapse();

    const refresh = document.getElementById('admin-refresh');
    refresh?.addEventListener('click', () => {
        loadAdminStats();
    });

    const snapshotDate = document.getElementById('admin-snapshot-date');
    if (snapshotDate) {
        snapshotDate.valueAsDate = new Date();
        snapshotDate.addEventListener('change', () => {
            loadAdminStats();
        });
    }

    const stewardForm = document.getElementById('create-steward-form');
    stewardForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createSteward(stewardForm);
    });

    const baseFeeForm = document.getElementById('pricing-base-fee-form');
    baseFeeForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        saveBaseFee(baseFeeForm);
    });

    const gameCreateForm = document.getElementById('admin-game-create-form');
    gameCreateForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createGameFromAdminForm(gameCreateForm);
    });

    const copyCreateForm = document.getElementById('admin-copy-create-form');
    copyCreateForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createCopyFromAdminForm(copyCreateForm);
    });

    const copyGameSelect = document.getElementById('admin-copy-game-id');
    copyGameSelect?.addEventListener('change', () => {
        updateSuggestedCopyCode({ force: true });
    });

    const gameSearchInput = document.getElementById('admin-catalogue-game-search');
    gameSearchInput?.addEventListener('input', () => {
        renderCatalogueGames(ADMIN_CATALOGUE.games);
    });

    const copySearchInput = document.getElementById('admin-catalogue-copy-search');
    copySearchInput?.addEventListener('input', () => {
        renderCatalogueCopies(ADMIN_CATALOGUE.copies);
    });

    const announcementForm = document.getElementById('admin-announcement-form');
    announcementForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createAnnouncementFromAdminForm(announcementForm);
    });

    const floorForm = document.getElementById('create-floor-form');
    floorForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createFloor(floorForm);
    });

    const zoneForm = document.getElementById('create-zone-form');
    zoneForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createZone(zoneForm);
    });

    const tableForm = document.getElementById('create-table-form');
    tableForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createTable(tableForm);
    });

    const floorSelect = document.getElementById('admin-floor-select');
    floorSelect?.addEventListener('change', () => {
        ADMIN_LOCATION_STATE.selectedFloor = Number(floorSelect.value);
        renderLocationOverview();

        const zoneFloorInput = document.getElementById('zone-floor');
        if (zoneFloorInput) {
            zoneFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || '');
        }

        const tableFloorInput = document.getElementById('table-floor');
        if (tableFloorInput) {
            tableFloorInput.value = String(ADMIN_LOCATION_STATE.selectedFloor || '');
        }
    });

    const locationModalForm = document.getElementById('admin-location-modal-form');
    locationModalForm?.addEventListener('submit', submitLocationModal);

    const locationModalDelete = document.getElementById('admin-location-modal-delete');
    locationModalDelete?.addEventListener('click', deleteFromLocationModal);

    document.querySelectorAll('[data-location-modal-close]').forEach((button) => {
        button.addEventListener('click', closeLocationModal);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeLocationModal();
        }
    });

    loadAdminStats();
    loadUsers();

    const userSearch = document.getElementById('admin-user-search');
    userSearch?.addEventListener('input', () => {
        const query = userSearch.value.trim().toLowerCase();
        renderUsers(query ? ADMIN_USERS.all.filter((u) => _userMatchesSearch(u, query)) : ADMIN_USERS.all);
    });

    loadPricing();
    loadCatalogue();
    loadAnnouncements();
    loadLocationOverview();

    try {
        const es = new EventSource('/api/events/stream');
        setAdminConnection('Realtime: connected');
        es.addEventListener('domain_event', (e) => {
            try {
                const payload = JSON.parse(e.data);
                const et = normalizeRealtimeEventType(payload);
                if (!et) return;

                if (et === 'reservation.seated' || et === 'reservation.completed') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `${et}:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    loadLocationOverview();
                    loadAdminStats();
                    return;
                }

                if (et === 'reservation.cancelled' || et === 'reservation.updated' || et === 'reservation.payment.completed') {
                    const data = payload.data || {};
                    const reservationId = data.reservation_id || 'unknown';
                    const eventKey = `${et}:${reservationId}`;
                    if (!shouldHandleRealtimeEvent(eventKey)) return;

                    loadAdminStats();
                    return;
                }
            } catch (error) {
                console.error('Failed to handle admin realtime event', error);
            }
        });
        es.addEventListener('error', () => setAdminConnection('Realtime: reconnecting...'));
    } catch (error) {
        console.error('Failed to connect admin realtime stream', error);
        setAdminConnection('Realtime: unavailable');
    }
}

document.addEventListener('DOMContentLoaded', bindAdminDashboard);

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

const ADMIN_REPORTS = {
    days: 30,
    registrationsChart: null,
    revenueChart: null,
    _loaded: false,
};

function _chartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
        accent: style.getPropertyValue('--accent').trim() || '#3a6f63',
        muted: style.getPropertyValue('--muted').trim() || '#666055',
    };
}

async function loadReports() {
    const days = ADMIN_REPORTS.days;
    try {
        const [regData, revData, topData] = await Promise.all([
            fetchJson(`/api/admin/reports/registrations?days=${days}`),
            fetchJson(`/api/admin/reports/revenue?days=${days}`),
            fetchJson(`/api/admin/reports/top-games?days=${days}`),
        ]);
        _renderRegistrationsChart(regData);
        _renderRevenueChart(revData);
        _renderTopGames(topData);
    } catch (err) {
        console.error('Failed to load reports:', err);
    }
}

function _renderRegistrationsChart(data) {
    const ctx = document.getElementById('chart-registrations');
    if (!ctx) return;
    const c = _chartColors();
    if (ADMIN_REPORTS.registrationsChart) ADMIN_REPORTS.registrationsChart.destroy();
    ADMIN_REPORTS.registrationsChart = new Chart(ctx, {
        data: {
            labels: data.map((d) => d.date),
            datasets: [
                {
                    type: 'bar',
                    label: 'New registrations',
                    data: data.map((d) => d.new_users),
                    backgroundColor: (c.accent || '#e8632a') + 'cc',
                    yAxisID: 'yNew',
                    order: 2,
                },
                {
                    type: 'line',
                    label: 'Cumulative users',
                    data: data.map((d) => d.cumulative),
                    borderColor: c.muted || '#6b7280',
                    backgroundColor: 'transparent',
                    pointRadius: 2,
                    tension: 0.3,
                    yAxisID: 'yCumulative',
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            scales: {
                yNew: { type: 'linear', position: 'left', beginAtZero: true, ticks: { precision: 0 } },
                yCumulative: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } },
            },
            plugins: { legend: { position: 'bottom' } },
        },
    });
}

function _renderRevenueChart(data) {
    const ctx = document.getElementById('chart-revenue');
    if (!ctx) return;
    const c = _chartColors();
    if (ADMIN_REPORTS.revenueChart) ADMIN_REPORTS.revenueChart.destroy();
    ADMIN_REPORTS.revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map((d) => d.date),
            datasets: [{
                label: 'Revenue (NOK)',
                data: data.map((d) => +(d.total_cents / 100).toFixed(2)),
                backgroundColor: (c.accent || '#e8632a') + 'cc',
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { callback: (v) => `${v} kr` } } },
        },
    });
}

function _renderTopGames(data) {
    function buildList(listId, items, renderItem) {
        const el = document.getElementById(listId);
        if (!el) return;
        if (!items || items.length === 0) {
            el.innerHTML = '<li class="reports-rank-list__empty">No data for this period.</li>';
            return;
        }
        el.innerHTML = items.map((item) => `<li class="reports-rank-list__item">${renderItem(item)}</li>`).join('');
    }
    buildList('top-games-by-rating', data.by_rating, (g) =>
        `<span class="reports-rank-badge">${g.avg_rating.toFixed(1)} &#9733;</span> ${g.title} <small>(${g.rating_count} rating${g.rating_count !== 1 ? 's' : ''})</small>`
    );
    buildList('top-games-by-bookings', data.by_bookings, (g) =>
        `<span class="reports-rank-badge">${g.booking_count}</span> ${g.title} <small>booking${g.booking_count !== 1 ? 's' : ''}</small>`
    );
}

function bindReports() {
    const panel = document.getElementById('admin-reports-panel');
    if (!panel) return;

    panel.addEventListener('toggle', () => {
        if (panel.open && !ADMIN_REPORTS._loaded) {
            ADMIN_REPORTS._loaded = true;
            loadReports();
        }
    });

    document.getElementById('reports-span-selector')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.reports-span-btn');
        if (!btn) return;
        document.querySelectorAll('.reports-span-btn').forEach((b) => b.classList.remove('reports-span-btn--active'));
        btn.classList.add('reports-span-btn--active');
        ADMIN_REPORTS.days = parseInt(btn.dataset.days, 10);
        loadReports();
    });

    document.getElementById('btn-download-csv')?.addEventListener('click', () => {
        window.location.href = `/api/admin/reports/revenue/csv?days=${ADMIN_REPORTS.days}`;
    });
}

document.addEventListener('DOMContentLoaded', bindReports);
