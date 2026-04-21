async function fetchJson(path, opts = {}) {
    opts.credentials = opts.credentials || 'same-origin';

    const method = (opts.method || 'GET').toUpperCase();
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

    if (res.status === 204) return {};

    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        try {
            return await res.text();
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
    lastUpdated: null,
};

const ADMIN_LOCATION_STATE = {
    floors: [],
    zones: [],
    tables: [],
    selectedFloor: null,
    availability: [],
};

function getSelectedSnapshotDate() {
    const snapshotDate = document.getElementById('admin-snapshot-date');
    if (snapshotDate && snapshotDate.value) {
        return snapshotDate.value;
    }

    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function buildAvailabilityQuery(dateValue) {
    const start = new Date(`${dateValue}T00:00:00`);
    const end = new Date(`${dateValue}T23:59:59`);
    return `?start_ts=${encodeURIComponent(start.toISOString())}&end_ts=${encodeURIComponent(end.toISOString())}&party_size=1`;
}

function findFloorByNumber(floors, floorNumber) {
    return floors.find((floor) => String(floor.number) === String(floorNumber)) || null;
}

function findZone(zones, floorNumber, zoneName) {
    return zones.find((zone) => String(zone.floor) === String(floorNumber) && String(zone.name) === String(zoneName)) || null;
}

function findTableByAvailabilityItem(tables, item) {
    const byId = tables.find((table) => String(table.id) === String(item.id));
    if (byId) return byId;

    return tables.find((table) => String(table.floor) === String(item.floor)
        && String(table.zone || '') === String(item.zone || '')
        && String(table.number) === String(item.table_nr));
}

function showEditDialog({ title, fields, submitLabel = 'Save changes' }) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(15, 23, 42, 0.45)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '9999';

        const modal = document.createElement('form');
        modal.style.background = '#ffffff';
        modal.style.borderRadius = '10px';
        modal.style.padding = '16px';
        modal.style.width = 'min(460px, 92vw)';
        modal.style.display = 'grid';
        modal.style.gap = '10px';

        const heading = document.createElement('h4');
        heading.textContent = title;
        heading.style.margin = '0 0 4px 0';
        modal.appendChild(heading);

        const controls = {};
        fields.forEach((field) => {
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = field.label;
            modal.appendChild(label);

            let control;
            if (field.type === 'select') {
                control = document.createElement('select');
                (field.options || []).forEach((option) => {
                    const opt = document.createElement('option');
                    opt.value = String(option.value);
                    opt.textContent = option.label;
                    control.appendChild(opt);
                });
                control.value = String(field.value ?? '');
            } else {
                control = document.createElement('input');
                control.type = field.type || 'text';
                control.value = String(field.value ?? '');
                if (field.min !== undefined) control.min = String(field.min);
            }

            control.className = 'form-input';
            if (field.required) control.required = true;
            control.name = field.name;
            controls[field.name] = control;
            modal.appendChild(control);
        });

        const actionRow = document.createElement('div');
        actionRow.className = 'action-row';

        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'button button-subtle';
        cancel.textContent = 'Cancel';
        cancel.addEventListener('click', () => {
            document.body.removeChild(overlay);
            resolve(null);
        });

        const submit = document.createElement('button');
        submit.type = 'submit';
        submit.className = 'button';
        submit.textContent = submitLabel;

        actionRow.appendChild(cancel);
        actionRow.appendChild(submit);
        modal.appendChild(actionRow);

        modal.addEventListener('submit', (event) => {
            event.preventDefault();
            const result = {};
            fields.forEach((field) => {
                result[field.name] = controls[field.name].value;
            });
            document.body.removeChild(overlay);
            resolve(result);
        });

        overlay.appendChild(modal);
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                document.body.removeChild(overlay);
                resolve(null);
            }
        });

        document.body.appendChild(overlay);
    });
}

async function ensureLocationRecords(floors, zones, availability) {
    let ensuredFloors = false;
    let ensuredZones = false;

    for (const floor of (availability || [])) {
        if (findFloorByNumber(floors, floor.floor)) continue;
        try {
            await fetchJson('/api/admin/floors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    number: Number(floor.floor),
                    name: `Floor ${floor.floor}`,
                }),
            });
            ensuredFloors = true;
        } catch (_error) {
            // ignore duplicates/races; a later refetch will reconcile state
        }
    }

    for (const floor of (availability || [])) {
        const zoneList = Array.isArray(floor.zones) ? floor.zones : [];
        for (const zone of zoneList) {
            const zoneName = String(zone.zone || '').trim();
            if (!zoneName) continue;
            if (findZone(zones, floor.floor, zoneName)) continue;

            try {
                await fetchJson('/api/admin/zones', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        floor: Number(floor.floor),
                        name: zoneName,
                    }),
                });
                ensuredZones = true;
            } catch (_error) {
                // ignore duplicates/races; a later refetch will reconcile state
            }
        }
    }

    if (!ensuredFloors && !ensuredZones) {
        return { floors, zones };
    }

    const [nextFloors, nextZones] = await Promise.all([
        fetchJson('/api/admin/floors'),
        fetchJson('/api/admin/zones'),
    ]);

    return { floors: nextFloors, zones: nextZones };
}

function setAdminConnection(text) {
    const node = document.getElementById('admin-connection-status');
    if (node) node.textContent = text;
}

function updateAdminSummaryUI() {
    const map = [
        ['metric-users', ADMIN_SUMMARY.users],
        ['metric-games', ADMIN_SUMMARY.games],
        ['metric-copies', ADMIN_SUMMARY.copies],
        ['metric-tables', ADMIN_SUMMARY.tables],
        ['metric-open-bookings', ADMIN_SUMMARY.openBookings],
        ['metric-open-incidents', ADMIN_SUMMARY.openIncidents],
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

function setFormMessage(elementId, message, isError = false) {
    const node = document.getElementById(elementId);
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? 'var(--danger, #b42318)' : '';
}

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
        meta.textContent = user.force_password_change
            ? 'Password change required on next login'
            : 'Password status: normal';
        item.appendChild(meta);

        if (!user.force_password_change) {
            const actions = document.createElement('div');
            actions.className = 'steward-item-actions';

            const resetBtn = document.createElement('button');
            resetBtn.className = 'button button-subtle';
            resetBtn.textContent = 'Force password reset';
            resetBtn.addEventListener('click', async () => {
                try {
                    await fetchJson(`/api/admin/users/${user.id}/force-password-reset`, { method: 'POST' });
                    await loadUsers();
                } catch (error) {
                    console.error(error);
                }
            });

            actions.appendChild(resetBtn);
            item.appendChild(actions);
        }

        list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);
}

async function loadUsers() {
    try {
        const users = await fetchJson('/api/admin/users');
        renderUsers(users);
    } catch (error) {
        console.error(error);
        const container = document.getElementById('admin-user-list');
        if (container) container.textContent = 'Error loading users';
    }
}

function renderLocationOverview(floors, zones, tables, availability) {
    const floorSelect = document.getElementById('admin-floor-select');
    const container = document.getElementById('admin-floorplan');

    if (!container) return;

    const safeFloors = Array.isArray(floors) ? floors : [];
    const safeZones = Array.isArray(zones) ? zones : [];
    const safeTables = Array.isArray(tables) ? tables : [];
    const safeAvailability = Array.isArray(availability) ? availability : [];

    const availabilityByFloor = new Map((safeAvailability || []).map((item) => [String(item.floor), item]));
    const floorNumberSet = new Set();
    safeFloors.forEach((floor) => floorNumberSet.add(String(floor.number)));
    safeAvailability.forEach((floor) => floorNumberSet.add(String(floor.floor)));
    const floorNumbers = Array.from(floorNumberSet).sort((a, b) => Number(a) - Number(b));

    if (floorNumbers.length === 0) {
        container.textContent = 'No floors found.';
        if (floorSelect) floorSelect.innerHTML = '';
        return;
    }

    if (floorSelect) {
        const current = floorSelect.value || String(ADMIN_LOCATION_STATE.selectedFloor || '');
        floorSelect.innerHTML = '';
        floorNumbers.forEach((floorNumber) => {
            const option = document.createElement('option');
            option.value = String(floorNumber);
            const floorRecord = findFloorByNumber(safeFloors, Number(floorNumber));
            option.textContent = floorRecord ? `Floor ${floorNumber}: ${floorRecord.name}` : `Floor ${floorNumber}`;
            floorSelect.appendChild(option);
        });
        const preferred = current && floorNumbers.includes(String(current))
            ? current
            : String(floorNumbers[0]);
        floorSelect.value = preferred;
        ADMIN_LOCATION_STATE.selectedFloor = Number(preferred);
    }

    const render = (floorNumber) => {
        const selectedFloor = String(floorNumber || floorNumbers[0]);
        const floorRecord = findFloorByNumber(safeFloors, Number(selectedFloor));
        const availabilityFloor = availabilityByFloor.get(selectedFloor);
        const zoneMap = new Map();

        if (availabilityFloor && Array.isArray(availabilityFloor.zones)) {
            availabilityFloor.zones.forEach((zone) => {
                const zoneName = String(zone.zone || '').trim() || 'Unzoned';
                zoneMap.set(zoneName, {
                    zone: zoneName,
                    tables: Array.isArray(zone.tables) ? zone.tables : [],
                });
            });
        }

        safeZones
            .filter((zone) => String(zone.floor) === selectedFloor)
            .forEach((zone) => {
                if (!zoneMap.has(zone.name)) {
                    zoneMap.set(zone.name, { zone: zone.name, tables: [] });
                }
            });

        const zoneSet = Array.from(zoneMap.values()).sort((a, b) => String(a.zone).localeCompare(String(b.zone)));

        container.innerHTML = '';

        const shell = document.createElement('div');
        shell.className = 'steward-item-list';

        const floorCard = document.createElement('article');
        floorCard.className = 'steward-item';

        const floorHead = document.createElement('div');
        floorHead.className = 'steward-item-head';

        const floorTitle = document.createElement('p');
        floorTitle.className = 'steward-item-title';
        floorTitle.textContent = floorRecord ? `Floor ${selectedFloor}: ${floorRecord.name}` : `Floor ${selectedFloor}`;
        floorHead.appendChild(floorTitle);

        const floorStatus = document.createElement('span');
        floorStatus.className = 'status-pill';
        floorStatus.textContent = floorRecord ? (floorRecord.active ? 'active' : 'inactive') : 'derived';
        floorHead.appendChild(floorStatus);
        floorCard.appendChild(floorHead);

        const floorMeta = document.createElement('p');
        floorMeta.className = 'steward-item-meta';
        floorMeta.textContent = floorRecord?.notes || (availabilityFloor ? 'Derived from table availability' : 'No tables on this floor yet');
        floorCard.appendChild(floorMeta);

        const floorActions = document.createElement('div');
        floorActions.className = 'steward-item-actions';

        const editFloorBtn = document.createElement('button');
        editFloorBtn.className = 'button button-subtle';
        editFloorBtn.textContent = 'Edit floor';
        editFloorBtn.disabled = !floorRecord;
        editFloorBtn.addEventListener('click', async () => {
            if (!floorRecord) return;
            const nextName = window.prompt('Floor name', floorRecord.name);
            if (!nextName || !nextName.trim()) return;
            try {
                await fetchJson(`/api/admin/floors/${floorRecord.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        number: floorRecord.number,
                        name: nextName.trim(),
                    }),
                });
                await loadLocationOverview();
            } catch (error) {
                console.error(error);
            }
        });

        const deleteFloorBtn = document.createElement('button');
        deleteFloorBtn.className = 'button button-subtle';
        deleteFloorBtn.textContent = 'Delete floor';
        deleteFloorBtn.disabled = !floorRecord;
        deleteFloorBtn.addEventListener('click', async () => {
            if (!floorRecord) return;
            try {
                await fetchJson(`/api/admin/floors/${floorRecord.id}?force=true`, { method: 'DELETE' });
                await loadLocationOverview();
                await loadAdminStats();
            } catch (error) {
                console.error(error);
                setFormMessage('create-floor-message', 'Could not delete floor.', true);
            }
        });

        floorActions.appendChild(editFloorBtn);
        floorActions.appendChild(deleteFloorBtn);
        floorCard.appendChild(floorActions);
        shell.appendChild(floorCard);

        zoneSet.forEach((zone) => {
            const zoneRecord = findZone(safeZones, Number(selectedFloor), zone.zone);
            const zoneCard = document.createElement('article');
            zoneCard.className = 'steward-item';
            zoneCard.style.marginTop = '0.75rem';

            const zoneHead = document.createElement('div');
            zoneHead.className = 'steward-item-head';

            const zoneTitle = document.createElement('p');
            zoneTitle.className = 'steward-item-title';
            zoneTitle.textContent = `Zone ${zone.zone}`;
            zoneHead.appendChild(zoneTitle);

            const zoneStatus = document.createElement('span');
            zoneStatus.className = 'status-pill';
            zoneStatus.textContent = zoneRecord ? (zoneRecord.active ? 'active' : 'inactive') : 'derived';
            zoneHead.appendChild(zoneStatus);
            zoneCard.appendChild(zoneHead);

            const zoneMeta = document.createElement('p');
            zoneMeta.className = 'steward-item-meta';
            zoneMeta.textContent = zoneRecord?.notes || `Floor ${selectedFloor}`;
            zoneCard.appendChild(zoneMeta);

            const zoneTables = Array.isArray(zone.tables) ? zone.tables : [];
            if (zoneTables.length === 0) {
                const emptyTables = document.createElement('p');
                emptyTables.className = 'quick-links';
                emptyTables.textContent = 'No tables in this zone yet.';
                zoneCard.appendChild(emptyTables);
            }

            const tableGrid = document.createElement('div');
            tableGrid.style.display = 'flex';
            tableGrid.style.flexWrap = 'wrap';
            tableGrid.style.gap = '8px';

            zoneTables.forEach((table) => {
                const tableRecord = findTableByAvailabilityItem(safeTables, table);
                const tableCard = document.createElement('div');
                tableCard.style.width = '88px';
                tableCard.style.border = '1px solid #d0d7de';
                tableCard.style.borderRadius = '8px';
                tableCard.style.padding = '8px';
                tableCard.style.display = 'flex';
                tableCard.style.flexDirection = 'column';
                tableCard.style.alignItems = 'center';
                tableCard.style.justifyContent = 'center';
                tableCard.style.background = table.available ? '#d4ffd4' : '#ffd6d6';

                const tableTitle = document.createElement('div');
                tableTitle.textContent = `T${table.table_nr}`;
                tableTitle.style.fontWeight = '600';
                tableCard.appendChild(tableTitle);

                const tableCap = document.createElement('div');
                tableCap.textContent = `${table.capacity}p`;
                tableCap.style.fontSize = '12px';
                tableCard.appendChild(tableCap);

                const tableActions = document.createElement('div');
                tableActions.style.display = 'flex';
                tableActions.style.gap = '4px';
                tableActions.style.marginTop = '6px';

                const editTableBtn = document.createElement('button');
                editTableBtn.className = 'button button-subtle';
                editTableBtn.textContent = 'Edit';
                editTableBtn.disabled = !tableRecord;
                editTableBtn.addEventListener('click', async () => {
                    if (!tableRecord) return;
                    const floorZones = safeZones
                        .filter((item) => item.floor === tableRecord.floor)
                        .map((item) => item.name)
                        .sort((a, b) => a.localeCompare(b));
                    const zoneOptions = Array.from(new Set([...floorZones, tableRecord.zone]))
                        .filter(Boolean)
                        .map((zoneName) => ({ value: zoneName, label: zoneName }));

                    const values = await showEditDialog({
                        title: 'Edit table',
                        fields: [
                            { name: 'number', label: 'Table number', type: 'number', min: 1, value: tableRecord.number, required: true },
                            { name: 'capacity', label: 'Capacity', type: 'number', min: 1, value: tableRecord.capacity, required: true },
                            { name: 'zone', label: 'Zone', type: zoneOptions.length ? 'select' : 'text', value: tableRecord.zone, options: zoneOptions, required: true },
                        ],
                        submitLabel: 'Save table',
                    });
                    if (!values) return;

                    const nextNumber = Number(values.number || 0);
                    const nextCapacity = Number(values.capacity || 0);
                    const nextZone = String(values.zone || '').trim();
                    if (!nextNumber || !nextCapacity || !nextZone) return;

                    try {
                        await fetchJson(`/api/admin/tables/${tableRecord.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                number: nextNumber,
                                capacity: nextCapacity,
                                floor: tableRecord.floor,
                                zone: nextZone,
                                width: tableRecord.width,
                                height: tableRecord.height,
                                rotation: tableRecord.rotation,
                                status: tableRecord.status,
                                features: tableRecord.features || {},
                            }),
                        });
                        await loadLocationOverview();
                    } catch (error) {
                        console.error(error);
                        setFormMessage('create-table-message', 'Could not update table.', true);
                    }
                });

                const deleteTableBtn = document.createElement('button');
                deleteTableBtn.className = 'button button-subtle';
                deleteTableBtn.textContent = 'Del';
                deleteTableBtn.disabled = !tableRecord;
                deleteTableBtn.addEventListener('click', async () => {
                    if (!tableRecord) return;
                    try {
                        await fetchJson(`/api/admin/tables/${tableRecord.id}?force=true`, { method: 'DELETE' });
                        await loadLocationOverview();
                        await loadAdminStats();
                    } catch (error) {
                        console.error(error);
                        setFormMessage('create-table-message', 'Could not delete table.', true);
                    }
                });

                tableActions.appendChild(editTableBtn);
                tableActions.appendChild(deleteTableBtn);
                tableCard.appendChild(tableActions);
                tableGrid.appendChild(tableCard);
            });

            zoneCard.appendChild(tableGrid);

            const zoneActions = document.createElement('div');
            zoneActions.className = 'steward-item-actions';

            const editZoneBtn = document.createElement('button');
            editZoneBtn.className = 'button button-subtle';
            editZoneBtn.textContent = 'Edit zone';
            editZoneBtn.disabled = !zoneRecord;
            editZoneBtn.addEventListener('click', async () => {
                if (!zoneRecord) return;
                const floorsForSelect = safeFloors
                    .slice()
                    .sort((a, b) => a.number - b.number)
                    .map((floor) => ({ value: floor.number, label: `Floor ${floor.number}: ${floor.name}` }));

                const values = await showEditDialog({
                    title: 'Edit zone',
                    fields: [
                        { name: 'name', label: 'Zone name', value: zoneRecord.name, required: true },
                        { name: 'floor', label: 'Floor', type: 'select', value: zoneRecord.floor, options: floorsForSelect, required: true },
                    ],
                    submitLabel: 'Save zone',
                });
                if (!values) return;

                const nextName = String(values.name || '').trim();
                const nextFloor = Number(values.floor || 0);
                if (!nextName || !nextFloor) return;

                try {
                    await fetchJson(`/api/admin/zones/${zoneRecord.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            floor: nextFloor,
                            name: nextName,
                            active: Boolean(zoneRecord.active),
                            notes: zoneRecord.notes || null,
                        }),
                    });
                    await loadLocationOverview();
                } catch (error) {
                    console.error(error);
                    setFormMessage('create-zone-message', 'Could not update zone.', true);
                }
            });

            const deleteZoneBtn = document.createElement('button');
            deleteZoneBtn.className = 'button button-subtle';
            deleteZoneBtn.textContent = 'Delete zone';
            deleteZoneBtn.disabled = !zoneRecord;
            deleteZoneBtn.addEventListener('click', async () => {
                if (!zoneRecord) return;
                try {
                    await fetchJson(`/api/admin/zones/${zoneRecord.id}?force=true`, { method: 'DELETE' });
                    await loadLocationOverview();
                    await loadAdminStats();
                } catch (error) {
                    console.error(error);
                    setFormMessage('create-zone-message', 'Could not delete zone.', true);
                }
            });

            zoneActions.appendChild(editZoneBtn);
            zoneActions.appendChild(deleteZoneBtn);
            zoneCard.appendChild(zoneActions);
            shell.appendChild(zoneCard);
        });

        if (zoneSet.length === 0) {
            const emptyZones = document.createElement('p');
            emptyZones.className = 'quick-links';
            emptyZones.textContent = 'No zones on this floor yet.';
            shell.appendChild(emptyZones);
        }

        container.appendChild(shell);
    };

    render(floorSelect ? floorSelect.value : floorNumbers[0]);

    if (floorSelect) {
        floorSelect.onchange = () => {
            ADMIN_LOCATION_STATE.selectedFloor = Number(floorSelect.value);
            render(floorSelect.value);
        };
    }
}

async function loadLocationOverview() {
    const container = document.getElementById('admin-floorplan');
    if (!container) return;

    try {
        const dateValue = getSelectedSnapshotDate();
        const [floorsResult, zonesResult, tablesResult, availabilityResult] = await Promise.allSettled([
            fetchJson('/api/admin/floors'),
            fetchJson('/api/admin/zones'),
            fetchJson('/api/admin/tables'),
            fetchJson('/api/tables/availability' + buildAvailabilityQuery(dateValue)),
        ]);

        let floors = floorsResult.status === 'fulfilled' ? floorsResult.value : [];
        let zones = zonesResult.status === 'fulfilled' ? zonesResult.value : [];
        const tables = tablesResult.status === 'fulfilled' ? tablesResult.value : [];
        const availability = availabilityResult.status === 'fulfilled' ? (availabilityResult.value.floors || []) : [];

        const synced = await ensureLocationRecords(floors, zones, availability);
        floors = synced.floors;
        zones = synced.zones;

        ADMIN_LOCATION_STATE.floors = floors;
        ADMIN_LOCATION_STATE.zones = zones;
        ADMIN_LOCATION_STATE.tables = tables;
        ADMIN_LOCATION_STATE.availability = availability;
        renderLocationOverview(floors, zones, tables, availability);
    } catch (error) {
        console.error(error);
        container.textContent = 'Error loading floor plan overview';
    }
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
        ADMIN_SUMMARY.lastUpdated = new Date();

        updateAdminSummaryUI();
        setAdminConnection('Admin stats loaded');
    } catch (error) {
        console.error(error);
        setAdminConnection('Error loading admin stats');
    }
}

async function createFloor(form) {
    try {
        await fetchJson('/api/admin/floors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                number: Number(form.elements.namedItem('number')?.value || 0),
                name: String(form.elements.namedItem('name')?.value || ''),
            }),
        });
        form.reset();
        setFormMessage('create-floor-message', 'Floor created.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setFormMessage('create-floor-message', 'Could not create floor.', true);
    }
}

async function createTable(form) {
    try {
        await fetchJson('/api/admin/tables', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                number: Number(form.elements.namedItem('number')?.value || 0),
                capacity: Number(form.elements.namedItem('capacity')?.value || 0),
                floor: Number(form.elements.namedItem('floor')?.value || 0),
                zone: String(form.elements.namedItem('zone')?.value || ''),
            }),
        });
        form.reset();
        setFormMessage('create-table-message', 'Table created.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setFormMessage('create-table-message', 'Could not create table.', true);
    }
}

async function createZone(form) {
    try {
        await fetchJson('/api/admin/zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                floor: Number(form.elements.namedItem('floor')?.value || 0),
                name: String(form.elements.namedItem('name')?.value || ''),
                notes: form.elements.namedItem('notes')?.value ? String(form.elements.namedItem('notes').value) : null,
            }),
        });
        form.reset();
        setFormMessage('create-zone-message', 'Zone created.');
        await loadLocationOverview();
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setFormMessage('create-zone-message', 'Could not create zone.', true);
    }
}

function bindAdminDashboard() {
    const refresh = document.getElementById('admin-refresh');
    refresh?.addEventListener('click', () => {
        loadAdminStats();
    });

    const snapshotDate = document.getElementById('admin-snapshot-date');
    if (snapshotDate) {
        snapshotDate.valueAsDate = new Date();
        snapshotDate.addEventListener('change', () => {
            loadAdminStats();
            loadLocationOverview();
        });
    }

    const stewardForm = document.getElementById('create-steward-form');
    stewardForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createSteward(stewardForm);
    });

    const floorForm = document.getElementById('create-floor-form');
    floorForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createFloor(floorForm);
    });

    const tableForm = document.getElementById('create-table-form');
    tableForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createTable(tableForm);
    });

    const zoneForm = document.getElementById('create-zone-form');
    zoneForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createZone(zoneForm);
    });

    loadAdminStats();
    loadUsers();
    loadLocationOverview();
}

document.addEventListener('DOMContentLoaded', bindAdminDashboard);