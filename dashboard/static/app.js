// ChameleonNet Operations Dashboard Frontend Logic

let chartInstance = null;
let ws = null;

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('techniqueChart');
    if (!ctx) return;

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [
                'T1082: Sys Info',
                'T1033: User Discovery',
                'T1087: Account Recon',
                'T1552: Unsecured Creds',
                'T1548: Priv Escalation',
                'T1083: File Discovery',
                'T1190: Web Exploit Probes'
            ],
            datasets: [{
                label: 'Interactions Observed',
                data: [3, 2, 2, 2, 1, 4, 1],
                backgroundColor: '#D2600F',
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0, font: { size: 11, family: '-apple-system' } }
                },
                y: {
                    ticks: { font: { size: 11, family: '-apple-system' } }
                }
            }
        }
    });
}

// Connect WebSocket with resilient fallback
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        document.getElementById('connection-status').innerText = 'Live WebSocket Active';
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleIncomingMessage(data);
        } catch (e) {
            console.error('Error parsing WebSocket message', e);
        }
    };

    ws.onclose = () => {
        document.getElementById('connection-status').innerText = 'Reconnecting...';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.warn('WebSocket encountered error, fallback active', err);
    };
}

function handleIncomingMessage(data) {
    if (data.type === 'INITIAL_SNAPSHOT') {
        updateStats(data.stats);
        renderSessions(data.sessions);
        renderEvents(data.events);
        if (data.pipeline_state) {
            updatePipelineVisualizer(data.pipeline_state);
        }
    } else if (data.type === 'NEW_EVENT') {
        prependEvent(data.event);
        updateSession(data.session);
        updateStats(data.stats);
        if (data.pipeline_state) {
            updatePipelineVisualizer(data.pipeline_state);
        }
    }
}

function updatePipelineVisualizer(state) {
    // Reset stages
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`stage-${i}`)?.classList.remove('active');
    }

    const stage = state.stage;
    const cycleStatus = document.getElementById('pipeline-cycle-status');

    if (stage === 'INTERACTION_CAPTURED') {
        document.getElementById('stage-1')?.classList.add('active');
        cycleStatus.innerText = `Active Input: ${state.input.substring(0, 30)}`;
    } else if (stage === 'TELEMETRY_ANALYZED') {
        document.getElementById('stage-2')?.classList.add('active');
        cycleStatus.innerText = `Analyzing Skill & MITRE Techniques...`;
    } else if (stage === 'HONEYPOT_ADAPTS') {
        document.getElementById('stage-3')?.classList.add('active');
        cycleStatus.innerText = `Adapting Fidelity & Staging Decoys...`;
    } else if (stage === 'LLM_GENERATES_RESPONSE' || stage === 'CYCLE_COMPLETE') {
        document.getElementById('stage-4')?.classList.add('active');
        cycleStatus.innerText = `LLM Synthesizing Response | Loop Complete`;
    }
}

function updateStats(stats) {
    if (!stats) return;
    document.getElementById('val-active-sessions').innerText = stats.active_sessions || 0;
    document.getElementById('val-total-events').innerText = stats.total_events || 0;
    document.getElementById('val-avg-dwell').innerText = `${Math.round(stats.avg_dwell_seconds || 0)}s`;

    // Update Chart if technique distribution available
    if (chartInstance && stats.technique_distribution) {
        const labels = Object.keys(stats.technique_distribution);
        const values = Object.values(stats.technique_distribution);
        if (labels.length > 0) {
            chartInstance.data.labels = labels.map(l => l.split(':')[0]);
            chartInstance.data.datasets[0].data = values;
            chartInstance.update();
        }
    }
}

function prependEvent(evt) {
    const feed = document.getElementById('event-feed');
    // Remove placeholder if present
    if (feed.children.length === 1 && feed.children[0].innerText.includes('Waiting for attacker')) {
        feed.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = 'event-item';

    const serviceBadge = evt.service === 'ssh' ? 'badge-ssh' : 'badge-web';
    const fidelityBadge = evt.fidelity_mode === 'high' ? 'badge-high' : 'badge-med';
    const dateStr = new Date(evt.timestamp * 1000).toLocaleTimeString();

    let tagsHtml = '';
    if (evt.technique_tags && evt.technique_tags.length > 0) {
        tagsHtml = '<div class="tech-tags">' + 
            evt.technique_tags.map(t => `<span class="tech-tag">${t}</span>`).join('') + 
            '</div>';
    }

    item.innerHTML = `
        <div class="event-meta">
            <div>
                <span class="badge ${serviceBadge}">${evt.service.toUpperCase()}</span>
                <span style="font-weight: 600; margin-left: 0.3rem;">${evt.source_ip}</span>
                <span style="margin-left: 0.4rem; color: var(--text-muted);">(${evt.session_id})</span>
            </div>
            <div>
                <span class="badge ${fidelityBadge}">${evt.fidelity_mode}</span>
                <span style="margin-left: 0.3rem;">${dateStr}</span>
            </div>
        </div>
        <div class="event-cmd">${escapeHtml(evt.raw_input)}</div>
        ${evt.response_summary ? `<div class="event-resp">${escapeHtml(evt.response_summary)}</div>` : ''}
        ${tagsHtml}
    `;

    feed.insertBefore(item, feed.firstChild);

    // Keep feed trimmed to 50 items
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}

function renderEvents(events) {
    if (!events || events.length === 0) return;
    const feed = document.getElementById('event-feed');
    feed.innerHTML = '';
    events.forEach(evt => prependEvent(evt));
}

function updateSession(sess) {
    // Re-render or update session card
    fetch('/api/sessions').then(r => r.json()).then(renderSessions);
}

function renderSessions(sessions) {
    const list = document.getElementById('sessions-list');
    if (!list) return;
    if (!sessions || sessions.length === 0) {
        list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No active adversary sessions recorded yet.</div>';
        return;
    }

    list.innerHTML = sessions.slice(0, 5).map(s => `
        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); padding: 0.75rem; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                <span style="font-weight: 700; font-size: 0.85rem;">${s.session_id}</span>
                <span class="badge ${s.current_fidelity === 'high' ? 'badge-high' : 'badge-med'}">${s.current_fidelity}</span>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); display: flex; gap: 0.8rem; margin-bottom: 0.4rem;">
                <span>IP: <strong>${s.source_ip}</strong></span>
                <span>Dwell: <strong>${Math.round(s.dwell_seconds)}s</strong></span>
                <span>Commands: <strong>${s.command_count}</strong></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem;">
                <span>Attacker Skill: <strong style="color: var(--accent-orange);">${s.skill_score} / 10</strong></span>
                <span>Profile: <em>${s.current_profile}</em></span>
            </div>
            ${s.decoys_revealed && s.decoys_revealed.length > 0 ? 
                `<div style="margin-top: 0.4rem; font-size: 0.72rem; color: var(--accent-orange); font-weight: 600;">
                    Discovered Decoys: ${s.decoys_revealed.join(', ')}
                 </div>` : ''}
        </div>
    `).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// User Actions
async function triggerSimulation(scenario) {
    try {
        const res = await fetch(`/api/simulate?scenario=${scenario}`, { method: 'POST' });
        const data = await res.json();
        console.log('Simulation triggered:', data);
    } catch (e) {
        console.error('Failed to trigger simulation', e);
    }
}

async function runBenchmark() {
    const btn = document.getElementById('btn-run-benchmark');
    if (btn) btn.innerText = 'Running Benchmark...';
    try {
        const res = await fetch('/api/benchmark/run', { method: 'POST' });
        const data = await res.json();
        
        document.getElementById('cmp-static-dwell').innerText = `${data.static_honeypot.dwell_time_seconds}s`;
        document.getElementById('cmp-cham-dwell').innerText = `${data.chameleon_net.dwell_time_seconds}s`;
        
        document.getElementById('cmp-static-cmds').innerText = `${data.static_honeypot.commands_completed} / 12 (Aborted)`;
        document.getElementById('cmp-cham-cmds').innerText = `${data.chameleon_net.commands_completed} / 12 (Completed)`;
        
        document.getElementById('cmp-static-decoys').innerText = `${data.static_honeypot.decoys_deployed} artifacts`;
        document.getElementById('cmp-cham-decoys').innerText = `${data.chameleon_net.unique_artifacts_captured} synthetic artifacts`;
        
        document.getElementById('cmp-dwell-mult').innerText = data.multiplier.dwell_increase;
        document.getElementById('cmp-intel-mult').innerText = data.multiplier.intelligence_gain;
    } catch (e) {
        console.error('Failed to run benchmark', e);
    } finally {
        if (btn) btn.innerText = '⚡ Compare vs Static';
    }
}

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    connectWebSocket();
    // Load initial stats
    fetch('/api/stats').then(r => r.json()).then(updateStats);
    fetch('/api/sessions').then(r => r.json()).then(renderSessions);
    fetch('/api/events').then(r => r.json()).then(renderEvents);
});
