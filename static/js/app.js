// app.js - Interactive redistricting logic

let districts = Array(5).fill(null).map(() => Array(5).fill(-1));
let currentDistrict = 0;
let isValid = false;

const DISTRICT_COLORS = ['#4A90E2', '#50C878', '#FFD700', '#FF6B6B', '#9B59B6'];

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        timeZone: 'America/Chicago',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

// Initialize grids
function initializeGrids() {
    const voteGridEl = document.getElementById('voteGrid');
    const districtGridEl = document.getElementById('districtGrid');
    
    // Create vote distribution grid
    for (let i = 0; i < 5; i++) {
        for (let j = 0; j < 5; j++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.classList.add(voteGrid[i][j] === 1 ? 'hearts' : 'clubs');
            cell.innerHTML = voteGrid[i][j] === 1 ? '♥' : '♣';
            voteGridEl.appendChild(cell);
        }
    }
    
    // Create district grid (interactive)
    for (let i = 0; i < 5; i++) {
        for (let j = 0; j < 5; j++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.row = i;
            cell.dataset.col = j;
            cell.innerHTML = voteGrid[i][j] === 1 ? '♥' : '♣';
            
            cell.addEventListener('click', () => handleCellClick(i, j, cell));
            
            districtGridEl.appendChild(cell);
        }
    }
}

// Handle cell click to assign district
function handleCellClick(row, col, cellEl) {
    districts[row][col] = currentDistrict;
    cellEl.className = 'cell';
    cellEl.classList.add(`district-${currentDistrict}`);
    cellEl.innerHTML = voteGrid[row][col] === 1 ? '♥' : '♣';
    
    // Clear validation when map changes
    isValid = false;
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('validationMessage').innerHTML = '';
    document.getElementById('results').style.display = 'none';
}

// District button selection
document.querySelectorAll('.district-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.district-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentDistrict = parseInt(btn.dataset.district);
    });
});

// Clear all districts
document.getElementById('clearBtn').addEventListener('click', () => {
    districts = Array(5).fill(null).map(() => Array(5).fill(-1));
    document.querySelectorAll('#districtGrid .cell').forEach(cell => {
        cell.className = 'cell';
        const row = parseInt(cell.dataset.row);
        const col = parseInt(cell.dataset.col);
        cell.innerHTML = voteGrid[row][col] === 1 ? '♥' : '♣';
    });
    isValid = false;
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('validationMessage').innerHTML = '';
    document.getElementById('results').style.display = 'none';
});

// Validate plan
document.getElementById('validateBtn').addEventListener('click', async () => {
    const msgEl = document.getElementById('validationMessage');
    const resultsEl = document.getElementById('results');
    
    try {
        const response = await fetch('/api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ districts })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            isValid = true;
            msgEl.className = 'message success';
            msgEl.innerHTML = '✅ Valid district plan! You can now submit.';
            document.getElementById('submitBtn').disabled = false;
            
            // Show results
            displayResults(data);
            resultsEl.style.display = 'block';
        } else {
            isValid = false;
            msgEl.className = 'message error';
            msgEl.innerHTML = '<strong>Invalid Plan:</strong><br>' + data.errors.join('<br>');
            document.getElementById('submitBtn').disabled = true;
            resultsEl.style.display = 'none';
        }
    } catch (error) {
        console.error('Validation error:', error);
        msgEl.className = 'message error';
        msgEl.innerHTML = '❌ Error validating plan. Please try again.';
    }
});

// Display results
function displayResults(data) {
    const overallEl = document.getElementById('overallResults');
    const districtEl = document.getElementById('districtResults');
    
    overallEl.innerHTML = `
        <span style="color: #e74c3c;">♥ Hearts: ${data.hearts_won}</span>
        <span style="margin: 0 20px;">-</span>
        <span style="color: #2c3e50;">♣ Clubs: ${data.clubs_won}</span>
    `;
    
    districtEl.innerHTML = '';
    for (let i = 0; i < 5; i++) {
        const winner = data.winners[i];
        const div = document.createElement('div');
        div.className = 'district-result';
        div.style.background = DISTRICT_COLORS[i];
        div.style.color = 'white';
        div.innerHTML = `
            <span>District ${i + 1}</span>
            <span>${winner === 'Hearts' ? '♥ Hearts Win' : '♣ Clubs Win'}</span>
        `;
        districtEl.appendChild(div);
    }
}

// Submit plan
document.getElementById('submitBtn').addEventListener('click', async () => {
    if (!isValid) {
        alert('Please validate your plan first!');
        return;
    }
    
    const planType = document.querySelector('input[name="planType"]:checked').value;
    const userName = document.getElementById('userName').value.trim() || 'Anonymous';
    
    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                districts,
                type: planType,
                name: userName
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Plan submitted successfully!');
            loadUserPlans();
            
            // Clear the grid
            document.getElementById('clearBtn').click();
        } else {
            alert('❌ Error submitting plan: ' + (data.errors ? data.errors.join(', ') : 'Unknown error'));
        }
    } catch (error) {
        console.error('Submit error:', error);
        alert('❌ Error submitting plan. Please try again.');
    }
});

// Load user plans
async function loadUserPlans() {
    try {
        const response = await fetch('/api/plans/user');
        const data = await response.json();
        
        const listEl = document.getElementById('userPlansList');
        
        if (data.plans.length === 0) {
            listEl.innerHTML = '<p class="empty-message">No plans submitted yet</p>';
            return;
        }
        
        listEl.innerHTML = '';
        data.plans.forEach(plan => {
            const div = document.createElement('div');
            div.className = 'user-plan-item';
            
            const typeClass = plan.type === 'neutral' ? 'neutral' : 'hearts';
            const typeName = plan.type === 'neutral' ? 'Neutral' : 'Hearts Rep';
            
            div.innerHTML = `
                <div class="plan-header">
                    <div>
                        <strong>${plan.user_name}</strong>
                        <span class="plan-type ${typeClass}">${typeName}</span>
                    </div>
                    <button class="btn btn-danger" onclick="deletePlan(${plan.id})">Delete</button>
                </div>
                <small style="color: #999;">${formatDate(plan.created_at)} CST</small>
            `;
            
            listEl.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading user plans:', error);
    }
}

// Delete plan
async function deletePlan(planId) {
    if (!confirm('Are you sure you want to delete this plan?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/plans/${planId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Plan deleted successfully!');
            loadUserPlans();
        } else {
            alert('❌ Error deleting plan.');
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('❌ Error deleting plan. Please try again.');
    }
}

// Generate consensus maps
document.getElementById('generateConsensusBtn').addEventListener('click', async () => {
    const btn = document.getElementById('generateConsensusBtn');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    
    try {
        const response = await fetch('/api/consensus');
        const data = await response.json();
        
        const mapsEl = document.getElementById('consensusMaps');
        
        // Display All Plans
        if (data.all_plans) {
            document.getElementById('consensusAll').src = data.all_plans;
            document.querySelector('#consensusAll').parentElement.querySelector('h3').textContent = 
                `All Plans (n=${data.counts.total})`;
            displayCompactness('compactnessAll', data.compactness.all);
        }
        
        // Display Neutral Plans
        if (data.neutral_plans) {
            document.getElementById('consensusNeutral').src = data.neutral_plans;
            document.querySelector('#consensusNeutral').parentElement.querySelector('h3').textContent = 
                `Neutral Plans (n=${data.counts.neutral})`;
            document.querySelector('#consensusNeutral').parentElement.style.display = 'block';
            displayCompactness('compactnessNeutral', data.compactness.neutral);
        } else {
            document.querySelector('#consensusNeutral').parentElement.style.display = 'none';
        }
        
        // Display Hearts Plans
        if (data.hearts_plans) {
            document.getElementById('consensusHearts').src = data.hearts_plans;
            document.querySelector('#consensusHearts').parentElement.querySelector('h3').textContent = 
                `Hearts Plans (n=${data.counts.hearts})`;
            document.querySelector('#consensusHearts').parentElement.style.display = 'block';
            displayCompactness('compactnessHearts', data.compactness.hearts);
        } else {
            document.querySelector('#consensusHearts').parentElement.style.display = 'none';
        }
        
        mapsEl.style.display = 'grid';
        
    } catch (error) {
        console.error('Consensus error:', error);
        alert('❌ Error generating consensus maps. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Consensus Maps';
    }
});

// Display compactness metrics
function displayCompactness(elementId, metrics) {
    if (!metrics) return;
    
    const el = document.getElementById(elementId);
    let html = '<h4>Compactness Metrics</h4>';
    html += `<p><span class="metric-label">Cut Edges:</span> ${metrics.cut_edges}</p>`;
    html += `<p><span class="metric-label">Avg Polsby-Popper:</span> ${metrics.avg_polsby_popper}</p>`;
    html += '<p style="margin-top: 10px;"><strong>By District:</strong></p>';
    
    metrics.districts.forEach(d => {
        html += `<p style="margin-left: 10px;">District ${d.district + 1} (${d.color}): ${d.polsby_popper}</p>`;
    });
    
    el.innerHTML = html;
}

// Generate rankings
document.getElementById('generateRankingsBtn').addEventListener('click', async () => {
    const btn = document.getElementById('generateRankingsBtn');
    btn.disabled = true;
    btn.textContent = 'Loading...';
    
    try {
        const response = await fetch('/api/rankings');
        const data = await response.json();
        
        const tbody = document.getElementById('rankingsBody');
        tbody.innerHTML = '';
        
        data.rankings.forEach((plan, index) => {
            const rank = index + 1;
            const rankClass = rank === 1 ? 'rank-1' : rank === 2 ? 'rank-2' : rank === 3 ? 'rank-3' : 'rank-other';
            const typeClass = plan.type === 'neutral' ? 'neutral' : 'hearts';
            const typeName = plan.type === 'neutral' ? 'Neutral' : 'Hearts Rep';
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="rank-badge ${rankClass}">${rank}</span></td>
                <td>
                    ${plan.name}
                    ${plan.is_base ? '<span class="base-plan-indicator">(Base)</span>' : ''}
                </td>
                <td><span class="plan-type-badge ${typeClass}">${typeName}</span></td>
                <td>${plan.avg_pp}</td>
                <td>${plan.cut_edges}</td>
            `;
            tbody.appendChild(row);
        });
        
        document.getElementById('rankingsTable').style.display = 'block';
        
    } catch (error) {
        console.error('Rankings error:', error);
        alert('❌ Error loading rankings. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Show Rankings';
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeGrids();
    loadUserPlans();
});