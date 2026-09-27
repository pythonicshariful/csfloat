// CSFloat DB Price Row Injector v2
// Injects market listing prices directly into each DB row by float matching

console.log('[CSFloat Injector] Loaded v2 - Row Price Injector');

// ─── CONFIG ──────────────────────────────────────────────────
const MIN_PRICE_HIGHLIGHT = 300; // highlight rows above this price ($)
const API_LIMIT = 100;           // fetch top N cheapest listings per page

// ─── STATE ───────────────────────────────────────────────────
let listingsCache = {};  // defIndex -> [{float, price, listingId}]
let injecting = false;

// ─── STYLES ──────────────────────────────────────────────────
function injectStyles() {
    if (document.getElementById('csf-injector-style')) return;
    const style = document.createElement('style');
    style.id = 'csf-injector-style';
    style.textContent = `
        .csf-price-cell {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 700;
            font-size: 13px;
            padding: 3px 10px;
            border-radius: 20px;
            white-space: nowrap;
            cursor: pointer;
        }
        .csf-price-cell.ultra {
            background: rgba(251,191,36,0.18);
            color: #fbbf24;
            border: 1px solid rgba(251,191,36,0.4);
        }
        .csf-price-cell.high {
            background: rgba(239,68,68,0.15);
            color: #f87171;
            border: 1px solid rgba(239,68,68,0.35);
        }
        .csf-price-cell.mid {
            background: rgba(59,130,246,0.15);
            color: #60a5fa;
            border: 1px solid rgba(59,130,246,0.3);
        }
        .csf-price-cell.low {
            background: rgba(34,197,94,0.15);
            color: #22c55e;
            border: 1px solid rgba(34,197,94,0.3);
        }
        .csf-price-cell.unlisted {
            background: rgba(100,100,100,0.1);
            color: #6b7280;
            border: 1px solid rgba(100,100,100,0.2);
            font-weight: 400;
            font-size: 11px;
        }
        .csf-price-cell.loading {
            background: rgba(100,100,100,0.08);
            color: #9ca3af;
            border: 1px dashed rgba(100,100,100,0.3);
            font-weight: 400;
            font-size: 11px;
            animation: csf-pulse 1.2s ease-in-out infinite;
        }
        @keyframes csf-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .csf-status-bar {
            position: fixed;
            bottom: 16px;
            right: 16px;
            background: #1f2937;
            color: #9ca3af;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-family: monospace;
            border: 1px solid #374151;
            z-index: 999999;
            transition: opacity 0.3s;
            pointer-events: none;
        }
    `;
    document.head.appendChild(style);
}

// ─── STATUS BAR ──────────────────────────────────────────────
let statusTimer = null;
function showStatus(msg, duration = 3000) {
    let bar = document.getElementById('csf-status-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'csf-status-bar';
        bar.className = 'csf-status-bar';
        document.body.appendChild(bar);
    }
    bar.textContent = msg;
    bar.style.opacity = '1';
    clearTimeout(statusTimer);
    if (duration > 0) {
        statusTimer = setTimeout(() => { bar.style.opacity = '0'; }, duration);
    }
}

// ─── FETCH LISTINGS ──────────────────────────────────────────
async function fetchListings(defIndex) {
    if (listingsCache[defIndex]) return listingsCache[defIndex];

    showStatus(`⟳ Fetching all prices from CSFloat...`, 0);

    // ── Primary: CSFloat official API — paginate to get max coverage ──
    try {
        const PAGE_SIZE = 100;
        const MAX_PAGES = 5;   // fetch up to 500 listings
        let allListings = [];

        for (let page = 0; page < MAX_PAGES; page++) {
            showStatus(`⟳ Loading prices... (page ${page + 1}/${MAX_PAGES})`, 0);
            const res = await fetch(
                `https://csfloat.com/api/v1/listings?def_index=${defIndex}&sort_by=lowest_float&limit=${PAGE_SIZE}&page=${page}`,
                { credentials: 'include' }
            );
            if (!res.ok) break;

            const data = await res.json();
            const items = data.data || [];
            if (!items.length) break;  // no more pages

            const mapped = items.map(l => ({
                float:     l.item?.float_value,
                price:     (l.price || 0) / 100,
                listingId: l.id
            })).filter(l => l.float !== undefined && l.float !== null);

            allListings = allListings.concat(mapped);

            // Stop early if we got fewer items than page size (last page)
            if (items.length < PAGE_SIZE) break;

            await new Promise(r => setTimeout(r, 300)); // small delay between pages
        }

        if (allListings.length > 0) {
            listingsCache[defIndex] = allListings;
            showStatus(`✓ Loaded ${allListings.length} listings from CSFloat`, 4000);
            return allListings;
        }
    } catch (e) {
        console.warn('[CSFloat Injector] CSFloat API failed, trying local bot...', e);
    }

    // ── Fallback: Local bot scraped data ─────────────────────────────
    try {
        const res  = await fetch(`http://127.0.0.1:5000/api/results`);
        const data = await res.json();
        const listings = (data.items || []).map(l => ({
            float:     parseFloat(l.float),
            price:     l.price,
            listingId: l.source_url
        })).filter(l => !isNaN(l.float));

        listingsCache[defIndex] = listings;
        showStatus(`✓ Loaded ${listings.length} bot-scraped prices`, 3000);
        return listings;
    } catch (e) {
        console.error('[CSFloat Injector] Both sources failed:', e);
        showStatus('✘ Could not load prices', 4000);
        return [];
    }
}

// ─── MATCH FLOAT ─────────────────────────────────────────────
function findListingByFloat(listings, targetFloat) {
    if (!targetFloat || !listings.length) return null;
    const tf = parseFloat(targetFloat);
    // Find the listing whose float is closest to the row float
    let best = null;
    let bestDiff = Infinity;
    for (const l of listings) {
        const diff = Math.abs(l.float - tf);
        if (diff < bestDiff) {
            bestDiff = diff;
            best = l;
        }
    }
    // Only match if very close (within 6 significant decimal places)
    return bestDiff < 0.000001 ? best : null;
}

// ─── PRICE BADGE HTML ─────────────────────────────────────────
function priceBadge(price, listingId) {
    const cls = price >= 10000 ? 'ultra'
              : price >= 3000  ? 'high'
              : price >= 1000  ? 'mid'
              : 'low';
    // listingId is the UUID from CSFloat API
    const url = listingId ? `https://csfloat.com/item/${listingId}` : '#';
    return `<a href="${url}" target="_blank" class="csf-price-cell ${cls}" title="Click to view listing on CSFloat">
        💰 $${price.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}
    </a>`;
}

// ─── INJECT INTO ROWS ────────────────────────────────────────
async function injectPricesIntoRows() {
    if (injecting) return;
    if (!window.location.pathname.includes('/db')) return;

    const urlParams = new URLSearchParams(window.location.search);
    const defIndex  = urlParams.get('def_index') || urlParams.get('defIndex');
    if (!defIndex) {
        showStatus('ℹ Open a DB page with ?def_index= to see prices', 4000);
        return;
    }

    injecting = true;

    // Place loading badges first
    const rows = document.querySelectorAll('mat-table mat-row, table tbody tr, .item-row');
    if (!rows.length) {
        injecting = false;
        return;
    }

    // Add loading placeholders
    rows.forEach(row => {
        if (row.querySelector('.csf-price-cell')) return; // already injected
        const lastCell = row.querySelector('mat-cell:last-child, td:last-child');
        if (lastCell) {
            const placeholder = document.createElement('span');
            placeholder.className = 'csf-price-cell loading';
            placeholder.textContent = '⟳ loading...';
            lastCell.appendChild(placeholder);
        }
    });

    const listings = await fetchListings(defIndex);

    // Now inject real prices
    rows.forEach(row => {
        // Find float value in this row's cells
        const floatCell = row.querySelector('mat-cell.cdk-column-float, td.cdk-column-float');
        const rowText   = floatCell ? floatCell.innerText : (row.innerText || '');
        // CS2 floats: 0.XXXXXXXX (8-15 decimal digits)
        const floatMatch = rowText.match(/0\.\d{8,}/);
        if (!floatMatch) {
            const ph = row.querySelector('.csf-price-cell.loading');
            if (ph) ph.remove();
            return;
        }

        const rowFloat = floatMatch[0];
        const listing  = findListingByFloat(listings, rowFloat);

        // Remove old placeholder
        const old = row.querySelector('.csf-price-cell');
        if (old) old.remove();

        // Find last cell to inject into
        const lastCell = row.querySelector('mat-cell:last-child, td:last-child');
        if (!lastCell) return;

        const wrapper = document.createElement('span');
        if (listing) {
            wrapper.innerHTML = priceBadge(listing.price, listing.listingId);
        } else {
            wrapper.innerHTML = `<span class="csf-price-cell unlisted">Not listed</span>`;
        }
        lastCell.appendChild(wrapper);
    });

    const matched = listings.length;
    // Mark all rows as done so MutationObserver won't re-run on them
    rows.forEach(row => row.setAttribute('data-csf-done', '1'));
    showStatus(`✓ Prices injected! ${matched} listings loaded for defIndex=${defIndex}`, 5000);
    injecting = false;
}

// ─── INIT ────────────────────────────────────────────────────
injectStyles();
setTimeout(injectPricesIntoRows, 2500);

// Watch for URL changes and table DOM mutations (Angular SPA)
let lastUrl = location.href;
const observer = new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
        lastUrl = url;
        listingsCache = {}; // clear cache on navigation
        setTimeout(injectPricesIntoRows, 2000);
        return;
    }
    // Also re-run when table rows appear/change
    const hasNewRows = document.querySelectorAll('mat-row:not([data-csf-done]), tr:not([data-csf-done])').length > 0;
    if (hasNewRows && !injecting) {
        clearTimeout(window._csfDebounce);
        window._csfDebounce = setTimeout(injectPricesIntoRows, 1200);
    }
});
observer.observe(document.body, { subtree: true, childList: true });
