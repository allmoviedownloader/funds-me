// Supabase Configuration
const SUPABASE_URL = 'https://ukeeqgbsvjsazoqqpmxu.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrZWVxZ2JzdmpzYXpvcXFwbXh1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwODIyNjYsImV4cCI6MjA4ODY1ODI2Nn0.tNPM0LQ2JSkHpBh-Gj-_8Q8StIsxSDXXdjca1b6cbbc';

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// DOM Elements
const fundsGrid = document.getElementById('fundsGrid');
const loader = document.getElementById('loader');
const emptyState = document.getElementById('emptyState');
const filterContainer = document.getElementById('filterContainer');
const searchInput = document.getElementById('searchInput');

// Modal Elements
const modalOverlay = document.getElementById('modalOverlay');
const modalSheet = document.getElementById('modalSheet');
const modalClose = document.getElementById('modalClose');
const modalContent = document.getElementById('modalContent');

let allFunds = [];
let activeFilter = 'All';
let searchQuery = '';

// Initialize
async function init() {
    await fetchFunds();
    setupEventListeners();
}

// Fetch data from Supabase
async function fetchFunds() {
    try {
        loader.style.display = 'flex';
        // Get today's date in YYYY-MM-DD
        const today = new Date().toISOString().split('T')[0];
        
        // Fetch funds where deadline is >= today (or no deadline specified)
        const { data, error } = await supabase
            .from('funds')
            .select('*')
            // Frontend failsafe: don't show expired funds
            // The backend cron will also delete these from DB
            .gte('deadline', today)
            .order('created_at', { ascending: false });

        if (error) {
            // If table doesn't exist yet, just use empty array to prevent breaking UI
            if(error.code === '42P01') {
                console.warn("Table 'funds' does not exist yet. Please create it in Supabase.");
                allFunds = dummyDataForPreview(); // Load dummy data if table is missing so user can see UI
            } else {
                throw error;
            }
        } else {
            allFunds = data || [];
            
            // Fallback for visual testing if DB is empty
            if (allFunds.length === 0) {
                 allFunds = dummyDataForPreview();
            }
        }
        
    } catch (err) {
        console.error('Error fetching funds:', err);
        allFunds = dummyDataForPreview(); // Fallback for UI preview
    } finally {
        loader.style.display = 'none';
        renderFunds();
    }
}

// Render Cards
function renderFunds() {
    fundsGrid.innerHTML = '';
    
    // Filter by Category
    let filtered = allFunds;
    if (activeFilter !== 'All') {
        filtered = filtered.filter(f => f.category === activeFilter);
    }
    
    // Filter by Search Search
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter(f => 
            (f.company_name && f.company_name.toLowerCase().includes(q)) ||
            (f.investor && f.investor.toLowerCase().includes(q)) ||
            (f.funding_stage && f.funding_stage.toLowerCase().includes(q))
        );
    }
    
    if (filtered.length === 0) {
        emptyState.style.display = 'block';
    } else {
        emptyState.style.display = 'none';
        
        filtered.forEach((fund, index) => {
            const card = document.createElement('div');
            card.className = 'fund-card card-enter';
            // Stagger animation delay
            card.style.animationDelay = `${index * 0.05}s`;
            
            // Determine nice tag style based on stage
            let stageClass = 'tag-stage';
            if (fund.funding_stage && fund.funding_stage.toLowerCase().includes('idea')) stageClass = 'tag-idea';
            
            // Format deadline date nicely
            const dDate = fund.deadline ? new Date(fund.deadline) : null;
            const formattedDeadline = dDate ? 
                dDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year:'numeric' }) : 
                'Open / Ongoing';
            
            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3 class="card-title">${fund.company_name || fund.investor}</h3>
                        <div class="card-investor">${fund.investor || fund.category}</div>
                    </div>
                    <span class="tag ${stageClass}">${fund.funding_stage || fund.category}</span>
                </div>
                <div class="card-amount">${fund.amount_offered || 'As per requirement'}</div>
                <div class="card-details">${fund.eligibility || 'No specific eligibility mentioned. Open to view details.'}</div>
                <div class="card-footer">
                    <div class="deadline">
                        <svg class="deadline-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        <span>${formattedDeadline}</span>
                    </div>
                    <a href="${fund.apply_link || '#'}" target="_blank" class="apply-btn" onclick="event.stopPropagation()">
                        Apply 
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="M12 5l7 7-7 7"></path></svg>
                    </a>
                </div>
            `;
            
            // Click card to open modal
            card.addEventListener('click', () => openModal(fund, formattedDeadline));
            
            fundsGrid.appendChild(card);
        });
    }
}

// Modal Logic
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
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeModal() {
    modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

// Event Listeners
function setupEventListeners() {
    // Filters
    filterContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('filter-pill')) {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            e.target.classList.add('active');
            activeFilter = e.target.getAttribute('data-filter');
            renderFunds();
        }
    });
    
    // Search
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.trim();
        renderFunds();
    });
    
    // Modal Close
    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });
    
    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
            closeModal();
        }
    });
}

// Dummy Data for Preview if table is empty
function dummyDataForPreview() {
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    
    return [
        {
            id: 1,
            company_name: "Startup India Seed Fund",
            funding_stage: "Seed",
            amount_offered: "Up to ₹50 Lakhs",
            investor: "Government of India",
            eligibility: "DPIIT-recognized startups incorporated less than 2 years ago.",
            category: "Government Funds",
            apply_link: "https://seedfund.startupindia.gov.in/",
            deadline: nextMonth.toISOString().split('T')[0]
        },
        {
            id: 2,
            company_name: "Y Combinator W25",
            funding_stage: "Idea Stage",
            amount_offered: "$500,000",
            investor: "Y Combinator",
            eligibility: "Global startups looking for seed capital and intense 3-month mentoring.",
            category: "Private Seed Funds",
            apply_link: "https://www.ycombinator.com/apply",
            deadline: nextMonth.toISOString().split('T')[0]
        },
        {
            id: 3,
            company_name: "100X.VC Class 13",
            funding_stage: "Pre-Seed",
            amount_offered: "₹1.25 Crore",
            investor: "100X.VC",
            eligibility: "Founders with a scalable tech business idea. iSAFE notes used.",
            category: "Private Seed Funds",
            apply_link: "https://www.100x.vc/",
            deadline: nextMonth.toISOString().split('T')[0]
        }
    ];
}

// Boot
init();
