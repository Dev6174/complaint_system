// Global State
let currentUser = null;
let currentView = 'auth';

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
    // Pre-fetch CSRF token so login/signup work immediately
    await apiFetch('/api/auth/csrf');

    // Check if user is logged in
    const userMe = await apiFetch('/api/auth/me');
    if (userMe && !userMe.error) {
        currentUser = userMe;
        localStorage.setItem('user', JSON.stringify(currentUser));
        switchView('citizen');
    } else {
        localStorage.removeItem('user');
        switchView('auth');
    }
    updateNav();
    
    // Wire up AI categorization suggestion when citizen is typing title/description
    const reportTitle = document.getElementById('report-title');
    const reportDesc = document.getElementById('report-description');
    
    if (reportTitle && reportDesc) {
        let suggestTimeout;
        const triggerSuggestion = () => {
            clearTimeout(suggestTimeout);
            suggestTimeout = setTimeout(async () => {
                const title = reportTitle.value.trim();
                const desc = reportDesc.value.trim();
                if (title.length >= 5 && desc.length >= 10) {
                    const formData = new FormData();
                    formData.append('title', title);
                    formData.append('description', desc);
                    
                    const res = await apiFetch('/api/issues/suggest-classification', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (res && !res.error) {
                        const box = document.getElementById('ai-suggestion-box');
                        const content = document.getElementById('ai-suggestion-content');
                        content.innerHTML = `
                            Category: <strong>${res.category}</strong> (Confidence: ${Math.round(res.confidence * 100)}%)<br>
                            Priority Suggestion: <strong>${res.priority}</strong><br>
                            Reasoning: <span class="small-text">${res.reasoning}</span><br>
                            <button type="button" class="btn btn-secondary btn-icon" style="margin-top: 8px; padding: 4px 8px; font-size: 0.75rem;" onclick="applyAISuggestions('${res.category}', '${res.priority}')">
                                Apply Suggestions
                            </button>
                        `;
                        box.classList.remove('hidden');
                    }
                }
            }, 1000);
        };
        
        reportTitle.addEventListener('input', triggerSuggestion);
        reportDesc.addEventListener('input', triggerSuggestion);
    }
});

// Switch visible tabs
function switchAuthTab(tab) {
    const loginForm = document.getElementById('form-login');
    const signupForm = document.getElementById('form-signup');
    const tabLogin = document.getElementById('btn-tab-login');
    const tabSignup = document.getElementById('btn-tab-signup');
    
    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        tabLogin.classList.add('active');
        tabSignup.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        tabLogin.classList.remove('active');
        tabSignup.classList.add('active');
    }
}

// Router Switch Views
function switchView(viewName) {
    if (!currentUser && viewName !== 'auth') {
        viewName = 'auth';
    }
    
    currentView = viewName;
    
    // Toggle Section visibility
    document.querySelectorAll('.view-section').forEach(sec => {
        sec.classList.add('hidden');
    });
    
    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
        targetSection.classList.remove('hidden');
        targetSection.classList.add('active');
    }
    
    // Specific View Initializations
    if (viewName === 'citizen') {
        initCitizenPickerMap();
        fetchCitizenDashboard();
    } else if (viewName === 'issues') {
        fetchIssuesList();
    } else if (viewName === 'staff') {
        fetchStaffIssues();
    } else if (viewName === 'dashboard') {
        fetchDashboardData();
    } else if (viewName === 'leaderboard') {
        fetchLeaderboard();
    } else if (viewName === 'audit') {
        fetchAuditTrail();
    }
    
    // Highlight Active Link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    const activeLink = document.getElementById(`nav-link-${viewName}`);
    if (activeLink) activeLink.classList.add('active');
}

// Render dynamic navbar depending on user role
function updateNav() {
    const navLinks = document.getElementById('nav-links');
    const userStatus = document.getElementById('user-status-area');
    
    if (!currentUser) {
        navLinks.innerHTML = '';
        userStatus.innerHTML = '';
        return;
    }
    
    // Links base setup
    let linksHtml = `
        <a class="nav-link" id="nav-link-citizen" onclick="switchView('citizen')">Citizen Panel</a>
        <a class="nav-link" id="nav-link-issues" onclick="switchView('issues')">Explore Issues</a>
        <a class="nav-link" id="nav-link-leaderboard" onclick="switchView('leaderboard')">Leaderboard</a>
        <a class="nav-link" id="nav-link-dashboard" onclick="switchView('dashboard')">Impact Dashboard</a>
    `;
    
    if (currentUser.role === 'Staff' || currentUser.role === 'Admin') {
        linksHtml += `<a class="nav-link" id="nav-link-staff" onclick="switchView('staff')">Staff Resolution</a>`;
    }
    
    if (currentUser.role === 'Admin') {
        linksHtml += `<a class="nav-link" id="nav-link-audit" onclick="switchView('audit')">Audit Logs</a>`;
    }
    
    navLinks.innerHTML = linksHtml;
    
    // User status block
    userStatus.innerHTML = `
        <div style="text-align: right; display: flex; flex-direction: column; gap: 2px;">
            <strong>${currentUser.name}</strong>
            <span class="user-badge">${currentUser.role}</span>
        </div>
        <button class="btn btn-secondary btn-icon" onclick="handleLogout()" style="padding: 0.5rem 0.75rem;">
            <span class="material-icons-round">logout</span>
        </button>
    `;
}

// Authentication Handlers
async function handleLogin(e) {
    e.preventDefault();
    // Always get a fresh CSRF token before login
    await apiFetch('/api/auth/csrf');

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    const data = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    if (data.error) {
        showAlert(data.error, 'error');
    } else {
        currentUser = data.user;
        localStorage.setItem('user', JSON.stringify(currentUser));
        showAlert('Logged in successfully!');
        switchView('citizen');
        updateNav();
    }
}

async function handleSignup(e) {
    e.preventDefault();
    // Always get a fresh CSRF token before signup
    await apiFetch('/api/auth/csrf');

    const name = document.getElementById('signup-name').value;
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const role = document.getElementById('signup-role').value;
    
    const data = await apiFetch('/api/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role })
    });
    
    if (data.error) {
        showAlert(data.error, 'error');
    } else {
        showAlert('Registration successful! Please log in.');
        switchAuthTab('login');
    }
}

async function handleLogout() {
    await apiFetch('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    localStorage.removeItem('user');
    // Get fresh CSRF token for next login
    await apiFetch('/api/auth/csrf');
    switchView('auth');
    updateNav();
    showAlert('Logged out successfully.');
}

// Citizen Panel Actions
function applyAISuggestions(category, priority) {
    document.getElementById('report-category').value = category;
    document.getElementById('report-priority').value = priority;
    showAlert('Suggestions applied!');
}

async function getUserLocation() {
    if (!navigator.geolocation) {
        showAlert('Geolocation is not supported by your browser.', 'error');
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            updateCitizenPickerLocation(lat, lng);
            showAlert('GPS location captured!');
        },
        (err) => {
            showAlert('Unable to retrieve location. Please click on the map manually.', 'error');
        }
    );
}

async function submitIssue(e) {
    e.preventDefault();
    const title = document.getElementById('report-title').value;
    const description = document.getElementById('report-description').value;
    const category = document.getElementById('report-category').value;
    const priority = document.getElementById('report-priority').value;
    const lat = document.getElementById('report-lat').value;
    const lng = document.getElementById('report-lng').value;
    const fileInput = document.getElementById('report-file');
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('category', category);
    formData.append('priority', priority);
    formData.append('latitude', lat);
    formData.append('longitude', lng);
    
    if (fileInput.files[0]) {
        formData.append('file', fileInput.files[0]);
    }
    
    const res = await apiFetch('/api/issues', {
        method: 'POST',
        body: formData
    });
    
    if (res.error) {
        showAlert(res.error, 'error');
    } else {
        showAlert('Issue reported successfully! Earned +10 Points.');
        
        // Reset form
        document.getElementById('form-report').reset();
        document.getElementById('ai-suggestion-box').classList.add('hidden');
        
        // Refresh citizen view
        fetchCitizenDashboard();
        
        // Recapture local profile (refresh points/badges)
        const updatedMe = await apiFetch('/api/auth/me');
        if (updatedMe && !updatedMe.error) {
            currentUser = updatedMe;
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateNav();
        }
    }
}

// Fetch Citizen dashboard lists and stats
async function fetchCitizenDashboard() {
    if (!currentUser) return;
    
    // User profile panel updates
    document.getElementById('citizen-points').textContent = currentUser.points;
    
    const badgesContainer = document.getElementById('citizen-badges');
    badgesContainer.innerHTML = '';
    
    // Deserialize badges
    const badges = currentUser.badges || [];
    if (badges.length === 0) {
        badgesContainer.innerHTML = '<span class="small-text">No badges unlocked yet. Keep reporting!</span>';
    } else {
        badges.forEach(badge => {
            badgesContainer.innerHTML += `
                <div class="badge-item">
                    <span class="material-icons-round">emoji_events</span>
                    ${badge}
                </div>
            `;
        });
    }
    
    // Fetch issues awaiting validation
    const res = await apiFetch('/api/issues?limit=10');
    const verifyList = document.getElementById('verify-list');
    verifyList.innerHTML = '';
    
    if (res && res.issues) {
        // Filter out issues reporter is themselves or already verified
        const toVerify = res.issues.filter(issue => 
            issue.reporter_id !== currentUser.id && 
            issue.status === 'Open'
        );
        
        if (toVerify.length === 0) {
            verifyList.innerHTML = '<p class="small-text">No pending issues to verify right now.</p>';
        } else {
            toVerify.forEach(issue => {
                verifyList.innerHTML += `
                    <div class="mini-card">
                        <div class="mini-card-info">
                            <h4>#${issue.id}: ${issue.title}</h4>
                            <p class="small-text">${issue.category} &bull; ${issue.priority}</p>
                        </div>
                        <button class="btn btn-secondary btn-icon" onclick="verifyIssueDirect(${issue.id})">
                            <span class="material-icons-round">check_circle</span> Verify
                        </button>
                    </div>
                `;
            });
        }
    }
}

async function verifyIssueDirect(issueId) {
    const res = await apiFetch('/api/verifications', {
        method: 'POST',
        body: JSON.stringify({ issue_id: issueId })
    });
    
    if (res.error) {
        showAlert(res.error, 'error');
    } else {
        showAlert('Verification submitted! +2 Points awarded.');
        fetchCitizenDashboard();
        
        // Refresh points
        const me = await apiFetch('/api/auth/me');
        if (me && !me.error) {
            currentUser = me;
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateNav();
        }
    }
}

// Issues Database list loader
async function fetchIssuesList(page = 1) {
    const search = document.getElementById('filter-search').value;
    const category = document.getElementById('filter-category').value;
    const status = document.getElementById('filter-status').value;
    
    let url = `/api/issues?page=${page}&limit=10`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    
    const res = await apiFetch(url);
    const body = document.getElementById('issue-table-body');
    const pag = document.getElementById('issues-pagination');
    body.innerHTML = '';
    pag.innerHTML = '';
    
    if (res && res.issues) {
        if (res.issues.length === 0) {
            body.innerHTML = `<tr><td colspan="8" style="text-align: center;">No issues found.</td></tr>`;
            return;
        }
        
        res.issues.forEach(issue => {
            body.innerHTML += `
                <tr>
                    <td>#${issue.id}</td>
                    <td><strong>${issue.title}</strong></td>
                    <td>${issue.category}</td>
                    <td><span class="priority-tag ${issue.priority.toLowerCase()}">${issue.priority}</span></td>
                    <td><span class="status-tag ${issue.status.toLowerCase().replace(' ', '-')}">${issue.status}</span></td>
                    <td>${issue.verification_count}</td>
                    <td>${issue.assigned_department || 'None'}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="showIssueDetails(${issue.id})" style="padding: 4px 8px; font-size: 0.8rem;">Details</button>
                    </td>
                </tr>
            `;
        });
        
        // Pagination
        const totalPages = Math.ceil(res.total / res.limit);
        if (totalPages > 1) {
            for (let i = 1; i <= totalPages; i++) {
                pag.innerHTML += `
                    <button class="btn btn-secondary ${i === page ? 'active' : ''}" onclick="fetchIssuesList(${i})" style="padding: 4px 10px; margin: 0 2px;">${i}</button>
                `;
            }
        }
    }
}

// Details Modal
async function showIssueDetails(issueId) {
    const issue = await apiFetch(`/api/issues/${issueId}`);
    if (!issue || issue.error) {
        showAlert('Unable to load issue details.', 'error');
        return;
    }
    
    const history = await apiFetch(`/api/issues/${issueId}/history`);
    
    const modal = document.getElementById('issue-modal');
    const body = document.getElementById('modal-body-content');
    modal.classList.remove('hidden');
    
    // Status History timeline HTML
    let historyHtml = '<p class="small-text">No activity history recorded.</p>';
    if (history && history.length > 0) {
        historyHtml = '<ul class="timeline" style="list-style: none; padding-left: 0; margin-top: 10px;">';
        history.forEach(item => {
            const time = new Date(item.timestamp).toLocaleString();
            historyHtml += `
                <li style="margin-bottom: 12px; border-left: 2px solid var(--info); padding-left: 12px; position: relative;">
                    <strong>${item.action.replace('_', ' ')}</strong> &bull; <span class="small-text">${time}</span><br>
                    <span class="small-text" style="color: var(--text-muted);">${JSON.stringify(item.details)}</span>
                </li>
            `;
        });
        historyHtml += '</ul>';
    }

    // Feedback rating block (only if resolved and current user is reporter)
    let feedbackHtml = '';
    if (issue.status === 'Resolved' && issue.reporter_id === currentUser.id) {
        const fbCheck = await apiFetch(`/api/feedback/issue/${issueId}`);
        if (fbCheck && fbCheck.error) {
            feedbackHtml = `
                <div class="feedback-sub-box glass-panel" style="margin-top: 20px; padding: 1.25rem;">
                    <h4>Submit Resolution Feedback</h4>
                    <form onsubmit="submitFeedbackForm(event, ${issueId})">
                        <div class="input-group-vertical">
                            <label>Rating (1 to 5 Stars)</label>
                            <select id="fb-rating" required>
                                <option value="5">5 Stars — Excellent</option>
                                <option value="4">4 Stars — Good</option>
                                <option value="3">3 Stars — Satisfactory</option>
                                <option value="2">2 Stars — Poor</option>
                                <option value="1">1 Star — Very Dissatisfied</option>
                            </select>
                        </div>
                        <div class="input-group-vertical">
                            <label>Comments</label>
                            <textarea id="fb-comment" rows="2" placeholder="Leave your comments..."></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary" style="margin-top: 8px;">Submit Feedback</button>
                    </form>
                </div>
            `;
        } else if (fbCheck) {
            feedbackHtml = `
                <div style="margin-top: 20px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-radius: 8px;">
                    <strong>Your Feedback Submitted</strong> &bull; Rating: ${fbCheck.rating}/5<br>
                    <span class="small-text">${fbCheck.comment || ''}</span>
                </div>
            `;
        }
    }

    const mediaHtml = issue.attachment_filename 
        ? `<div style="margin: 15px 0;">
             <h4 style="margin-bottom: 6px;">Attachment</h4>
             ${issue.attachment_filename.endsWith('.mp4') 
                ? `<video src="/uploads/${issue.attachment_filename}" controls style="max-width: 100%; border-radius: 10px;"></video>` 
                : `<img src="/uploads/${issue.attachment_filename}" style="max-width: 100%; border-radius: 10px; border: 1px solid var(--panel-border);">`}
           </div>`
        : '';
        
    body.innerHTML = `
        <h2 style="font-family: var(--font-heading); font-size: 1.6rem; margin-bottom: 8px;">#${issue.id}: ${issue.title}</h2>
        <div style="display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap;">
            <span class="priority-tag ${issue.priority.toLowerCase()}">${issue.priority} Priority</span>
            <span class="status-tag ${issue.status.toLowerCase().replace(' ', '-')}">${issue.status}</span>
            <span class="user-badge">${issue.category}</span>
        </div>
        <p style="margin-bottom: 15px; line-height: 1.5;">${issue.description}</p>
        ${mediaHtml}
        <div style="margin: 15px 0; font-size: 0.9rem; color: var(--text-muted);">
            Location: Lat <strong>${issue.latitude}</strong>, Lng <strong>${issue.longitude}</strong><br>
            Reporter: <strong>${issue.reporter_name || 'Anonymous'}</strong> &bull; Created: ${new Date(issue.created_at).toLocaleString()}<br>
            Assigned Department: <strong>${issue.assigned_department || 'Unassigned'}</strong>
        </div>
        ${issue.resolution_notes ? `
            <div style="padding: 12px; background: rgba(19, 81, 168, 0.08); border-left: 4px solid var(--primary); border-radius: 4px; margin: 15px 0;">
                <strong>Resolution Notes (by Staff)</strong>: ${issue.resolution_notes}<br>
                <span class="small-text">Resolved on: ${new Date(issue.resolved_at).toLocaleString()}</span>
            </div>
        ` : ''}
        ${feedbackHtml}
        <div style="margin-top: 25px; border-top: 1px solid var(--panel-border); padding-top: 15px;">
            <h3>Audit Status Timeline</h3>
            ${historyHtml}
        </div>
    `;
}

function closeIssueModal() {
    document.getElementById('issue-modal').classList.add('hidden');
}

async function submitFeedbackForm(e, issueId) {
    e.preventDefault();
    const rating = document.getElementById('fb-rating').value;
    const comment = document.getElementById('fb-comment').value;
    
    const res = await apiFetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({ issue_id: issueId, rating, comment })
    });
    
    if (res.error) {
        showAlert(res.error, 'error');
    } else {
        showAlert('Feedback submitted successfully! +5 Points.');
        closeIssueModal();
        fetchIssuesList();
        const me = await apiFetch('/api/auth/me');
        if (me && !me.error) {
            currentUser = me;
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateNav();
        }
    }
}

// Staff Board Actions
async function fetchStaffIssues() {
    const res = await apiFetch('/api/issues?limit=100');
    const staffList = document.getElementById('staff-issue-list');
    staffList.innerHTML = '';
    
    if (res && res.issues) {
        const activeIssues = res.issues.filter(issue => issue.status !== 'Closed');
        if (activeIssues.length === 0) {
            staffList.innerHTML = '<p class="small-text">No active department issues.</p>';
            return;
        }
        activeIssues.forEach(issue => {
            staffList.innerHTML += `
                <div class="mini-card" onclick="selectStaffIssue(${issue.id})">
                    <div class="mini-card-info">
                        <h4>#${issue.id}: ${issue.title}</h4>
                        <p class="small-text">Priority: <strong>${issue.priority}</strong> &bull; Dept: <strong>${issue.assigned_department || 'Unassigned'}</strong></p>
                    </div>
                    <span class="status-tag ${issue.status.toLowerCase().replace(' ', '-')}">${issue.status}</span>
                </div>
            `;
        });
    }
}

async function selectStaffIssue(issueId) {
    const issue = await apiFetch(`/api/issues/${issueId}`);
    const deptsRes = await apiFetch('/api/departments');
    const panel = document.getElementById('staff-resolution-panel');
    if (!issue || issue.error) {
        panel.innerHTML = '<p class="error">Failed to load issue details.</p>';
        return;
    }
    let deptOptions = '<option value="">-- Choose Department --</option>';
    if (deptsRes && deptsRes.departments) {
        deptsRes.departments.forEach(d => {
            deptOptions += `<option value="${d}" ${issue.assigned_department === d ? 'selected' : ''}>${d}</option>`;
        });
    }
    panel.innerHTML = `
        <h3>Active Issue #${issue.id}</h3>
        <p style="margin: 10px 0;"><strong>${issue.title}</strong></p>
        <p class="small-text" style="margin-bottom: 12px;">${issue.description}</p>
        <form onsubmit="handleManualAssignment(event, ${issue.id})">
            <div class="input-group-vertical">
                <label for="dept-assign-select">Route / Assign Department</label>
                <div class="form-row inline-btns">
                    <select id="dept-assign-select" required>${deptOptions}</select>
                    <button type="submit" class="btn btn-secondary">Assign</button>
                </div>
            </div>
        </form>
        <form onsubmit="handleResolveIssue(event, ${issue.id})" style="margin-top: 20px; border-top: 1px solid var(--panel-border); padding-top: 15px;">
            <h3>Post Resolution</h3>
            <div class="input-group-vertical">
                <label for="staff-res-notes">Resolution Notes</label>
                <textarea id="staff-res-notes" rows="3" placeholder="Provide details of the resolution action taken..." required minlength="5"></textarea>
            </div>
            <button type="submit" class="btn btn-primary" style="margin-top: 8px;">Mark as Resolved</button>
        </form>
    `;
}

async function handleManualAssignment(e, issueId) {
    e.preventDefault();
    const dept = document.getElementById('dept-assign-select').value;
    const res = await apiFetch(`/api/departments/assign?issue_id=${issueId}&department=${encodeURIComponent(dept)}`, {
        method: 'POST'
    });
    if (res.error) {
        showAlert(res.error, 'error');
    } else {
        showAlert('Department routed successfully.');
        fetchStaffIssues();
        selectStaffIssue(issueId);
    }
}

async function handleResolveIssue(e, issueId) {
    e.preventDefault();
    const notes = document.getElementById('staff-res-notes').value;
    const res = await apiFetch(`/api/issues/${issueId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution_notes: notes })
    });
    if (res.error) {
        showAlert(res.error, 'error');
    } else {
        showAlert('Issue resolved successfully.');
        fetchStaffIssues();
        document.getElementById('staff-resolution-panel').innerHTML = `
            <p class="select-hint">Select an issue from the list to update its status or post resolution notes.</p>
        `;
    }
}

// Impact Dashboard
async function fetchDashboardData() {
    const res = await apiFetch('/api/analytics/dashboard');
    if (!res || res.error) {
        showAlert('Failed to load dashboard metrics.', 'error');
        return;
    }
    const metrics = document.getElementById('dashboard-metrics');
    const open = res.status_counts.Open || 0;
    const progress = res.status_counts['In Progress'] || 0;
    const resolved = res.status_counts.Resolved || 0;
    const closed = res.status_counts.Closed || 0;
    const total = open + progress + resolved + closed;
    metrics.innerHTML = `
        <div class="metric-card"><h4>Total Reports</h4><div class="num">${total}</div></div>
        <div class="metric-card"><h4>Open</h4><div class="num" style="color: var(--warning);">${open}</div></div>
        <div class="metric-card"><h4>In Progress</h4><div class="num" style="color: var(--info);">${progress}</div></div>
        <div class="metric-card"><h4>Resolved & Closed</h4><div class="num" style="color: var(--success);">${resolved + closed}</div></div>
    `;
    const insights = document.getElementById('at-risk-insights');
    let riskHtml = '<h4>At Risk Issues (Old & High Priority)</h4>';
    if (res.at_risk_issues.length === 0) {
        riskHtml += '<p class="small-text" style="color: var(--success);">All high priority issues are currently on track.</p>';
    } else {
        res.at_risk_issues.forEach(issue => {
            riskHtml += `
                <div style="padding: 6px; background: var(--danger-bg); border-left: 3px solid var(--danger); border-radius: 4px; margin-bottom: 6px; font-size: 0.8rem;">
                    <strong>#${issue.id}</strong>: ${issue.title} (${issue.category}) &bull; Pending ${Math.round((new Date() - new Date(issue.created_at)) / (3600*1000))} hrs!
                </div>
            `;
        });
    }
    let predHtml = '<h4 style="margin-top: 15px;">Historical Avg Resolution Time</h4>';
    const predictions = res.resolution_predictions;
    if (Object.keys(predictions).length === 0) {
        predHtml += '<p class="small-text">No prediction model data available yet.</p>';
    } else {
        for (const [key, hrs] of Object.entries(predictions)) {
            predHtml += `
                <div style="font-size: 0.8rem; margin-bottom: 4px; display: flex; justify-content: space-between;">
                    <span>${key.replace('_', ' - ')}</span>
                    <strong>${hrs.toFixed(1)} hours</strong>
                </div>
            `;
        }
    }
    insights.innerHTML = riskHtml + predHtml;
    initDashboardMap(res.map_issues || []);
}

async function downloadReport(type) {
    window.location.href = `/api/analytics/export?type=${type}`;
}

async function fetchLeaderboard() {
    const res = await apiFetch('/api/leaderboard');
    const container = document.getElementById('leaderboard-items');
    container.innerHTML = '';
    if (res && !res.error) {
        if (res.length === 0) {
            container.innerHTML = '<p class="small-text">Leaderboard is empty.</p>';
            return;
        }
        res.forEach((user, idx) => {
            const rank = idx + 1;
            let badgesHtml = '';
            user.badges.forEach(b => {
                badgesHtml += `<span class="material-icons-round" style="font-size: 1.1rem; color: var(--warning); margin-left: 2px;" title="${b}">emoji_events</span>`;
            });
            container.innerHTML += `
                <div class="leaderboard-item">
                    <div class="leaderboard-rank rank-${rank}">#${rank}</div>
                    <div class="leaderboard-info">
                        <h4>${user.name} ${badgesHtml}</h4>
                        <span class="user-badge">${user.role}</span>
                    </div>
                    <div class="leaderboard-points">${user.points} pts</div>
                </div>
            `;
        });
    }
}

async function fetchAuditTrail() {
    const res = await apiFetch('/api/audit');
    const body = document.getElementById('audit-table-body');
    body.innerHTML = '';
    if (res && !res.error) {
        if (res.length === 0) {
            body.innerHTML = `<tr><td colspan="5" style="text-align: center;">No audit logs recorded.</td></tr>`;
            return;
        }
        res.forEach(log => {
            const time = new Date(log.timestamp).toLocaleString();
            body.innerHTML += `
                <tr>
                    <td class="small-text">${time}</td>
                    <td><strong>${log.user_name}</strong> <span class="small-text">(ID: ${log.user_id || 'System'})</span></td>
                    <td><span style="font-family: monospace; font-size: 0.8rem; background: #eef3fa; padding: 2px 6px; border-radius: 4px;">${log.action}</span></td>
                    <td class="small-text" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title='${log.details}'>${log.details}</td>
                    <td class="small-text">${log.ip_address || 'None'}</td>
                </tr>
            `;
        });
    }
}