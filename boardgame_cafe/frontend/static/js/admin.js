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
        });
    }

    const stewardForm = document.getElementById('create-steward-form');
    stewardForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        createSteward(stewardForm);
    });

    loadAdminStats();
    loadUsers();
}

document.addEventListener('DOMContentLoaded', bindAdminDashboard);