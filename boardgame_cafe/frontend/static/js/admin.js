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
}

document.addEventListener('DOMContentLoaded', bindAdminDashboard);