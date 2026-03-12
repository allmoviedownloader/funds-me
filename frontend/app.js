// Supabase Configuration
const SUPABASE_URL = 'https://ukeeqgbsvjsazoqqpmxu.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZWVxZ2JzdmpzYXpvcXFwbXh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwODIyNjYsImV4cCI6MjA4ODY1ODI2Nn0.tNPM0LQ2JSkHpBh-Gj-_8Q8StIsxSDXXdjca1b6cbbc';

const getSupabase = () => {
    if (window.supabase) return window.supabase;
    if (typeof supabase !== 'undefined') return supabase;
    return null;
};

const client = getSupabase();
if (!client) {
    console.error("Supabase library not found!");
}
const supabaseClient = client ? client.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;

// DOM Elements
const fundsGrid = document.getElementById('fundsGrid');
const emptyState = document.getElementById('emptyState');
const filterContainer = document.getElementById('filterContainer');
const searchInput = document.getElementById('searchInput');
const lastUpdatedText = document.getElementById('lastUpdatedText');

// Modal Elements
const modalOverlay = document.getElementById('modalOverlay');
const modalSheet = document.getElementById('modalSheet');
const modalClose = document.getElementById('modalClose');
const modalContent = document.getElementById('modalContent');

let allFunds = [];
let filteredFunds = []; // Global store for filtered results
let activeFilter = 'All';
let searchQuery = '';
let searchTimeout = null;
const BATCH_SIZE = 20;
let currentIndex = 0;
let renderTimeout = null;

// Initialize
async function init() {
    console.log("Initializing Dashboard...");
    setupEventListeners();
    setupInfiniteScroll();
    
    try {
        await fetchFunds();
    } catch (e) {
        console.warn("Initial fetch failed. Using fallback.", e);
        if (allFunds.length === 0) {
            allFunds = dummyDataForPreview();
            performFiltering();
        }
    }
}

// Fetch data from Supabase
async function fetchFunds() {
    try {
        const { data, error } = await supabaseClient
            .from('funds')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            if(error.code === '42P01') {
                allFunds = dummyDataForPreview();
            } else {
                throw error;
            }
        } else {
            allFunds = (data || []).map(f => ({
                ...f,
                _searchText: `${f.company_name} ${f.investor} ${f.amount_offered} ${f.eligibility} ${f.category} ${f.funding_stage}`.toLowerCase()
            }));

            if (allFunds.length === 0) allFunds = dummyDataForPreview();
            
            // Update "Last Updated" text
            if (allFunds.length > 0) {
                const newest = allFunds.reduce((a, b) => new Date(a.created_at) > new Date(b.created_at) ? a : b);
                const updateTime = new Date(newest.created_at);
                lastUpdatedText.innerText = `Last updated: ${updateTime.toLocaleDateString('en-US', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}`;
            }
        }
    } catch (err) {
        console.error('Error fetching funds:', err);
        allFunds = dummyDataForPreview();
    } finally {
        performFiltering();
    }
}

// ... normalizeQuery remains same ...

// 1. Filtering Logic (Run once on data change or search/filter change)
function performFiltering() {
    renderSkeletons();
    
    let filtered = allFunds;
    
    // Category Filter
    if (activeFilter === 'Government Funds') {
        filtered = allFunds.filter(f => (f.category || '').includes('Government'));
    } else if (activeFilter === 'Big Companies') {
        const bigCorps = ['Google', 'Microsoft', 'Amazon', 'Meta', 'Tata', 'Reliance', 'Adobe', 'Apple', 'Y Combinator', 'Sequoia', 'Tiger Global', 'Goldman Sachs', 'Visa', 'Stripe', 'IBM', 'Oracle'];
        filtered = allFunds.filter(f => 
            bigCorps.some(name => 
                (f.company_name && f.company_name.toLowerCase().includes(name.toLowerCase())) || 
                (f.investor && f.investor.toLowerCase().includes(name.toLowerCase()))
            )
        );
    } else if (activeFilter === 'Idea Stage') {
        filtered = allFunds.filter(f => 
            (f.funding_stage && f.funding_stage.toLowerCase().includes('idea')) ||
            (f.category && f.category.toLowerCase().includes('idea'))
        );
    } else if (activeFilter === 'Urgent') {
        const now = new Date();
        const twoDaysFromNow = new Date(now.getTime() + (48 * 60 * 60 * 1000));
        filtered = allFunds.filter(f => {
            if (!f.deadline) return false;
            const dDate = new Date(f.deadline);
            return dDate > now && dDate <= twoDaysFromNow;
        });
    }
    
    // Search Filter
    if (searchQuery) {
        const qRaw = searchQuery.toLowerCase();
        const queries = normalizeQuery(qRaw);
        filtered = filtered.filter(f => {
            return queries.some(q => f._searchText.includes(q));
        });
    }

    filteredFunds = filtered;
    currentIndex = 0;
    
    // Clear any pending render to prevent slowness/collisions
    if (renderTimeout) clearTimeout(renderTimeout);
    
    // If we have data, show skeletons briefly OR show data immediately if cached
    const needsWait = allFunds.length === 0; // Only wait on initial load
    
    renderTimeout = setTimeout(() => {
        fundsGrid.innerHTML = '';
        renderBatch();
        renderTimeout = null;
    }, needsWait ? 400 : 50); 
}

function renderSkeletons() {
    fundsGrid.innerHTML = '';
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < 6; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-card';
        skeleton.innerHTML = `
            <div class="skeleton-shimmer"></div>
            <div class="skeleton-content">
                <div class="skeleton-line skeleton-title"></div>
                <div class="skeleton-line skeleton-text"></div>
                <div class="skeleton-line skeleton-big"></div>
                <div class="skeleton-line skeleton-para"></div>
                <div class="skeleton-line skeleton-text" style="margin-top: 20px;"></div>
            </div>
        `;
        fragment.appendChild(skeleton);
    }
    fundsGrid.appendChild(fragment);
}

let isRendering = false;

// 2. Rendering Batch (Lazy loading)
function renderBatch() {
    if (isRendering || currentIndex >= filteredFunds.length) {
        if (filteredFunds.length === 0) emptyState.style.display = 'block';
        return;
    }
    isRendering = true;
    emptyState.style.display = 'none';
    
    const fragment = document.createDocumentFragment();
    const batch = filteredFunds.slice(currentIndex, currentIndex + BATCH_SIZE);
    
    batch.forEach((fund, index) => {
        const card = document.createElement('div');
        card.className = 'fund-card card-enter';
        
        const rDate = fund.release_date ? new Date(fund.release_date) : new Date(fund.created_at);
        const dDate = fund.deadline ? new Date(fund.deadline) : null;
        const formattedRelease = rDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
        const formattedDeadline = dDate ? dDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year:'numeric' }) : 'Ongoing';
        
        let stageClass = 'tag-stage';
        if (fund.funding_stage && fund.funding_stage.toLowerCase().includes('idea')) stageClass = 'tag-idea';

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <h3 class="card-title">${fund.company_name || 'New Opportunity'}</h3>
                    <div class="card-investor">By ${fund.investor || fund.category}</div>
                </div>
                <span class="tag ${stageClass}">${fund.funding_stage || fund.category}</span>
            </div>
            <div class="card-amount">${fund.amount_offered || 'Grant'}</div>
            <div class="card-challenge">${fund.challenge_info ? `<strong>Problem:</strong> ${fund.challenge_info}` : ''}</div>
            <div class="card-details">${fund.eligibility || 'Click to view details.'}</div>
            <div class="card-footer">
                <div class="deadline">
                    <div class="deadline-row">
                         <svg class="deadline-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                         <span><strong>Posted:</strong> ${formattedRelease}</span>
                    </div>
                    <div class="deadline-row">
                         <svg class="deadline-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                         <span><strong>Closes:</strong> ${formattedDeadline}</span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="more-info-btn">More Info</button>
                    <a href="${fund.apply_link || '#'}" target="_blank" class="apply-btn" onclick="event.stopPropagation()">Apply</a>
                </div>
            </div>
        `;
        
        card.addEventListener('click', () => openModal(fund, formattedDeadline));
        const infoBtn = card.querySelector('.more-info-btn');
        infoBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openModal(fund, formattedDeadline);
        });
        
        fragment.appendChild(card);
    });
    
    fundsGrid.appendChild(fragment);
    currentIndex += BATCH_SIZE;
    isRendering = false;
}

// 3. Setup Infinite Scroll (Throttled)
let scrollTimeout = null;
function setupInfiniteScroll() {
    window.addEventListener('scroll', () => {
        if (scrollTimeout) return;
        
        scrollTimeout = setTimeout(() => {
            if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
                renderBatch();
            }
            scrollTimeout = null;
        }, 100); // 100ms Throttle
    });
}

// Modal Logic ... same ...
function openModal(fund, formattedDeadline) {
    modalContent.innerHTML = `
        <div class="modal-header">
            <h2 class="modal-title">${fund.company_name || fund.investor}</h2>
            <div class="modal-investor">Backed by ${fund.investor || 'Multiple Investors'}</div>
            <div class="modal-amount">${fund.amount_offered || 'Grant Based'}</div>
        </div>
        <div class="modal-section">
            <h3>Funding Stage / Category</h3>
            <p><strong>${fund.funding_stage || 'Not specified'}</strong> &middot; ${fund.category || 'General'}</p>
        </div>
        <div class="modal-section">
            <h3>Problem Statement / Challenge</h3>
            <p>${fund.challenge_info || 'General innovation and growth support.'}</p>
        </div>
        <div class="modal-section">
            <h3>Eligibility Criteria</h3>
            <p>${fund.eligibility || 'Details missing. Please check the official link.'}</p>
        </div>
        <div class="modal-section" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3>Application Deadline</h3>
                <p style="color: var(--warning); font-weight: 600;">${formattedDeadline}</p>
            </div>
            ${fund.deadline ? `<div style="font-size: 0.8rem; color: var(--text-tertiary);">Entries expire automatically</div>` : ''}
        </div>
        <a href="${fund.apply_link || '#'}" target="_blank" class="modal-apply-btn">Proceed to Official Application</a>
    `;
    modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

// Event Listeners
function setupEventListeners() {
    filterContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('filter-pill')) {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            e.target.classList.add('active');
            activeFilter = e.target.getAttribute('data-filter');
            performFiltering();
        }
    });
    
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchQuery = val;
            performFiltering();
        }, 300); // 300ms Debounce
    });
    
    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });
}

function dummyDataForPreview() { return []; }

init();
