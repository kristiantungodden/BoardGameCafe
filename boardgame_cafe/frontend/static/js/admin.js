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

const ADMIN_LOCATION_STATE = {
    floors: [],
    zones: [],
    tables: [],
    selectedFloor: null,
    availability: [],
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
        ADMIN_SUMMARY.publishedAnnouncements = data.published_announcements || 0;
        ADMIN_SUMMARY.lastUpdated = new Date();

        updateAdminSummaryUI();
        setAdminConnection('Admin stats loaded');
    } catch (error) {
        console.error(error);
        setAdminConnection('Error loading admin stats');
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
                await loadAdminStats();
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
                await loadAdminStats();
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
        await loadAdminStats();
    } catch (error) {
        console.error(error);
        setAnnouncementMessage('Could not save announcement.', true);
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

function setFormMessage(elementId, message, isError = false) {
    const node = document.getElementById(elementId);
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? 'var(--danger, #b42318)' : '';
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
            loadLocationOverview();
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
    loadPricing();
    loadCatalogue();
    loadLocationOverview();
    loadAnnouncements();
}

document.addEventListener('DOMContentLoaded', bindAdminDashboard);