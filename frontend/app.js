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
    console.log("Initializing Dashboard...");
    setupEventListeners(); // Setup listeners first so UI is responsive
    try {
        // Race fetch against a 5s timeout
        const fetchPromise = fetchFunds();
        const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error("Fetch Timeout")), 5000)
        );
        await Promise.race([fetchPromise, timeoutPromise]);
    } catch (e) {
        console.warn("Initial fetch timed out or failed. Using fallback.", e);
        if (allFunds.length === 0) {
            allFunds = dummyDataForPreview();
            renderFunds();
        }
        loader.style.display = 'none';
    }
}

// Fetch data from Supabase
async function fetchFunds() {
    try {
        loader.style.display = 'flex';
        const today = new Date().toISOString().split('T')[0];
        
        const { data, error } = await supabaseClient
            .from('funds')
            .select('*')
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
                 console.info("Database is empty. Loading dummy data for preview.");
                 allFunds = dummyDataForPreview();
            }
        }
        
    } catch (err) {
        console.error('Error fetching funds:', err);
        // Show a helpful hint on the page if it's a 404/PGRST205
        if (err.message && err.message.includes('PGRST205')) {
             alert("Database table 'funds' is missing. Please follow the setup instructions in the chat.");
        }
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
    if (activeFilter === 'Government Funds') {
        filtered = allFunds.filter(f => (f.category || '').includes('Government'));
    } else if (activeFilter === 'Big Companies') {
        const bigCorps = ['Google', 'Microsoft', 'Amazon', 'Meta', 'Tata', 'Reliance', 'Adobe', 'Apple', 'Y Combinator', 'Sequoia', 'Tiger Global', 'Goldman Sachs'];
        filtered = allFunds.filter(f => 
            bigCorps.some(name => 
                (f.company_name && f.company_name.toLowerCase().includes(name.toLowerCase())) || 
                (f.investor && f.investor.toLowerCase().includes(name.toLowerCase()))
            )
        );
    }
    
    // Filter by Search
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
            
            // Format dates nicely
            const rDate = fund.release_date ? new Date(fund.release_date) : new Date(fund.created_at);
            const dDate = fund.deadline ? new Date(fund.deadline) : null;
            
            const formattedRelease = rDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
            const formattedDeadline = dDate ? 
                dDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year:'numeric' }) : 
                'Ongoing';
            
            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3 class="card-title">${fund.company_name || 'New Opportunity'}</h3>
                        <div class="card-investor">By ${fund.investor || fund.category}</div>
                    </div>
                    <span class="tag ${stageClass}">${fund.funding_stage || fund.category}</span>
                </div>
                <div class="card-amount">${fund.amount_offered || 'Grant'}</div>
                <div class="card-challenge">${fund.challenge_info ? `<strong>Problem Statement:</strong> ${fund.challenge_info}` : ''}</div>
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
                    <a href="${fund.apply_link || '#'}" target="_blank" class="apply-btn" onclick="event.stopPropagation()">
                        Apply
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

// WhatsApp Registration
function registerWhatsApp() {
    const phoneInput = document.getElementById('whatsappPhone');
    const interestInput = document.getElementById('whatsappInterest');
    const phone = phoneInput.value.trim();
    const interest = interestInput.value;
    
    if (!phone || phone.length < 10) {
        alert("Please enter a valid phone number!");
        return;
    }

    // Count matching funds for instant gratification
    const count = allFunds.filter(f => f.category === interest || interest === 'All').length;
    
    const msg = `Successfully joined WhatsApp Alerts! ✅\n\nFound ${count} matching funds for "${interest}".\nRedirecting you to WhatsApp to confirm...`;
    alert(msg);
    
    // Redirect to WhatsApp with a pre-filled message
    const waMsg = encodeURIComponent(`Hi! I want to receive alerts for ${interest} startup funds on my number ${phone}.`);
    window.open(`https://wa.me/918260797177?text=${waMsg}`, '_blank');
    
    phoneInput.value = '';
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
    const lastWeek = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    lastWeek.setDate(lastWeek.getDate() - 7);
    
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
            release_date: lastWeek.toISOString().split('T')[0],
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
            release_date: lastWeek.toISOString().split('T')[0],
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
            release_date: lastWeek.toISOString().split('T')[0],
            deadline: nextMonth.toISOString().split('T')[0]
        }
    ];
}

// Boot
init();
