/**
 * PharmaLit MVP — SPA App Logic
 * Hash-based routing: #landing | #app | #health
 * No build step — vanilla ES modules served by FastAPI
 */

// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  route: 'landing',
  query: '',
  daysBack: 180,
  maxPapers: 20,
  fetchFresh: true,
  loading: false,
  results: null,
  chatHistory: [],       // { role: 'user'|'system', type, content, time }
  activeTab: 0,
  ragStats: { chunk_count: 0, paper_count: 0 },
  healthStatus: null,
};

// ─── DOM root ─────────────────────────────────────────────────────────────────
const $app = document.getElementById('app');

// ─── Router ───────────────────────────────────────────────────────────────────
function navigate(route) {
  state.route = route;
  window.location.hash = route;
  render();
}

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.replace('#', '') || 'landing';
  state.route = hash;
  render();
});

// ─── Main render ──────────────────────────────────────────────────────────────
function render() {
  $app.innerHTML = renderHeader() + renderPage();
  attachHandlers();
  if (state.route === 'app') {
    loadRagStats();
    scrollChatToBottom();
  }
  if (state.route === 'health') {
    loadHealth();
  }
}

// ─── Header ───────────────────────────────────────────────────────────────────
function renderHeader() {
  const navItem = (label, route, id) => {
    const active = state.route === route ? 'active' : '';
    return `<button class="nav-btn ${active}" id="${id}" onclick="navigate('${route}')">${label}</button>`;
  };
  const dotClass = state.healthStatus
    ? (state.healthStatus.status === 'ok' ? 'ok' : state.healthStatus.status === 'degraded' ? 'degraded' : 'error')
    : '';
  return `
  <header id="header">
    <div class="logo">
      <div class="logo-icon">🧬</div>
      <span>Pharma<span class="accent">Lit</span></span>
    </div>
    <nav>
      ${navItem('Landing', 'landing', 'nav-landing')}
      ${navItem('Analysis', 'app', 'nav-app')}
      ${navItem('API Health', 'health', 'nav-health')}
    </nav>
    <div style="display:flex;align-items:center;gap:8px;font-size:0.78rem;color:var(--text-dim)">
      <span class="health-dot ${dotClass}"></span>
      <span>${state.healthStatus ? state.healthStatus.status.toUpperCase() : 'checking...'}</span>
    </div>
  </header>`;
}

// ─── Page dispatch ────────────────────────────────────────────────────────────
function renderPage() {
  switch (state.route) {
    case 'app':    return renderApp();
    case 'health': return renderHealth();
    default:       return renderLanding();
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// LANDING PAGE
// ══════════════════════════════════════════════════════════════════════════════
function renderLanding() {
  return `
  <div id="page-landing">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-badge">🧬 Pharmaceutical R&amp;D Intelligence</div>
      <h1>Autonomous R&amp;D Intelligence —<br/>not a smarter search bar.</h1>
      <p class="subtitle">
        One query turns into a ranked, tool-verified target scoreboard,
        multi-source evidence, and a cited hypothesis brief. Local-first. IP-safe.
      </p>
      <button class="hero-cta" id="hero-cta-btn">
        Start Analysis <span>→</span>
      </button>
    </section>

    <!-- Stats strip -->
    <div class="stat-strip">
      <div class="stat-item">
        <span class="stat-value">5+</span>
        <span class="stat-label">Data Sources</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">1–10</span>
        <span class="stat-label">Transparent Score</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">~3 min</span>
        <span class="stat-label">Per Query</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">0 keys</span>
        <span class="stat-label">For OT &amp; UniProt</span>
      </div>
    </div>

    <!-- Perks -->
    <section class="section">
      <div class="section-label">Why PharmaLit</div>
      <h2 class="section-title">Built for pharma R&amp;D teams, not chatbots</h2>
      <p class="section-sub">Every output is citable, every score is explainable, every run is fully audited.</p>
      <div class="perks-grid">
        ${renderPerkCard('🎯', 'Pharma-native output', 'Ranked, citable target briefs — not a list of papers. Each target gets a structured evidence card with mechanism, trials, and contradicting evidence.')}
        ${renderPerkCard('🔒', 'Local-first / IP safe', 'ChromaDB runs on your machine. Your queries and documents never leave your environment. No cloud AI risk.')}
        ${renderPerkCard('🔄', 'Multi-source fusion', 'PubMed + preprints (bioRxiv/medRxiv) + ClinicalTrials.gov + RAG in one query. Preprints tagged [NOT PEER REVIEWED].')}
        ${renderPerkCard('📊', 'Transparent scoring (1–10)', 'Every target score is computed by tool — not guessed by AI. Open Targets tractability + UniProt validation. Full breakdown per point.')}
        ${renderPerkCard('🔍', 'Full audit trail', 'Agent Trace tab shows every tool call, every API response, every step. Reproducible and explainable.')}
        ${renderPerkCard('💰', 'Low cost', 'Public APIs for OT, UniProt, Europe PMC, ClinicalTrials — no key required. Just your Gemini API key for the LLM.')}
      </div>
    </section>

    <!-- Scoring explainer -->
    <section class="scoring-section">
      <div style="max-width:1100px;margin:0 auto;padding:0 2rem">
        <div style="text-align:center;margin-bottom:3rem">
          <div class="section-label">How Scores Work</div>
          <h2 class="section-title">Composite score 1–10 — not guessed by AI</h2>
          <p style="max-width:560px;margin:0 auto;color:var(--text-muted)">
            Each candidate gene gets a score built from two deterministic sources.
            Every point is itemised. The AI brief summarises literature; the scoreboard is the source of truth.
          </p>
        </div>
        <div class="scoring-inner">
          <div class="score-demo">
            <!-- Ring gauge demo (PCSK9 example, score 7) -->
            <div class="ring-demo-wrap">
              ${renderRingSVG(7, 80, 'var(--score-amber)')}
              <div class="ring-demo-label">
                <span class="score-number" style="color:var(--score-amber)">7</span>
                <span class="score-sub">/10</span>
              </div>
            </div>
            <div style="font-size:1.1rem;font-weight:700">PCSK9</div>
            <div style="font-size:0.8rem;color:var(--text-muted)">Example target — NASH cholesterol</div>
            <div class="breakdown-demo">
              <div class="breakdown-row">
                <span class="label">SM Tractability (Bucket 2)</span>
                <span class="source">Open Targets</span>
                <span class="pts">+5</span>
              </div>
              <div class="breakdown-row">
                <span class="label">High Quality Molecules</span>
                <span class="source">Open Targets</span>
                <span class="pts">+2</span>
              </div>
              <div class="breakdown-row">
                <span class="label">UniProt Entry (P04114)</span>
                <span class="source">UniProt</span>
                <span class="pts">+2</span>
              </div>
              <div class="breakdown-row">
                <span class="label">Functional Annotation</span>
                <span class="source">UniProt</span>
                <span class="pts">+1</span>
              </div>
              <div class="breakdown-total">
                <span style="color:var(--text-muted)">Total (capped at 10)</span>
                <span class="total-pts">7/10</span>
              </div>
            </div>
          </div>
          <div>
            <h3 style="margin-bottom:1.2rem;color:var(--text)">Scoring components</h3>
            <div style="display:flex;flex-direction:column;gap:1rem">
              ${renderScoringComponent('Open Targets — Druggability', 'var(--accent)', [
                'Small molecule bucket ≤2 (clinical drugs exist) → +5',
                'Small molecule bucket ≤4 (pre-clinical) → +4',
                'Weak SM precedent (bucket >4) → +2',
                'High Quality Molecules bonus → +2',
                'Antibody druggable (any bucket) → +3',
              ])}
              ${renderScoringComponent('UniProt — Protein validation', 'var(--accent-2)', [
                'Human protein entry found → +2',
                'Functional annotation present → +1',
                'Ensembl ID fallback (via MyGene.info) for hard-to-resolve symbols',
              ])}
            </div>
            <div style="margin-top:1.5rem;padding:1rem;background:var(--glass);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:0.82rem;color:var(--text-muted)">
              🎯 <strong style="color:var(--text)">Ring gauge colours:</strong>
              <span style="color:var(--score-green)">■ Green (8–10)</span> ·
              <span style="color:var(--score-amber)">■ Amber (5–7)</span> ·
              <span style="color:var(--score-red)">■ Red (1–4)</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Bottom CTA -->
    <section class="landing-cta-bottom">
      <h2 style="margin-bottom:0.75rem">Ready to run your first query?</h2>
      <p style="margin-bottom:2rem;color:var(--text-muted)">No SaaS login. No cloud upload. Just your query and your data.</p>
      <button class="hero-cta" id="cta-bottom-btn">
        Open Analysis App <span>→</span>
      </button>
    </section>
  </div>`;
}

function renderPerkCard(icon, title, desc) {
  return `
  <div class="perk-card">
    <span class="perk-icon">${icon}</span>
    <div class="perk-title">${title}</div>
    <p class="perk-desc">${desc}</p>
  </div>`;
}

function renderScoringComponent(title, color, items) {
  return `
  <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:1rem">
    <div style="font-weight:700;color:${color};margin-bottom:0.5rem;font-size:0.9rem">${title}</div>
    <ul style="color:var(--text-muted);font-size:0.82rem;padding-left:1.2em;display:flex;flex-direction:column;gap:4px">
      ${items.map(i => `<li>${i}</li>`).join('')}
    </ul>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════════
// ANALYSIS APP PAGE
// ══════════════════════════════════════════════════════════════════════════════
function renderApp() {
  const results = state.results;
  const tabLabels = [
    { label: '📊 Target Brief', count: results?.target_scores?.length },
    { label: '📚 Papers',       count: results?.papers?.length },
    { label: '🧪 Preprints',    count: results?.preprints?.length },
    { label: '🏥 Trials',       count: results?.trials?.length },
    { label: '🔍 Agent Trace',  count: null },
  ];

  return `
  <div id="page-app">
    <div class="app-main">
      <!-- Chat area -->
      <div class="chat-area">
        <div class="chat-thread" id="chat-thread">
          ${state.chatHistory.length === 0
            ? `<div class="empty-state"><span class="empty-icon">🧬</span><p>Enter a disease or target area below to begin your analysis.</p></div>`
            : state.chatHistory.map(renderChatItem).join('')
          }
          ${state.loading ? `
            <div class="event-card">
              <span class="ev-icon"><span class="spinner"></span></span>
              <span>Pipeline running... this takes ~2–3 minutes</span>
            </div>` : ''}
        </div>

        <!-- Query bar -->
        <div class="query-bar">
          <div class="query-controls">
            <div class="control-group">
              <label class="control-label">Days back</label>
              <div style="display:flex;align-items:center;gap:8px">
                <input type="range" class="days-slider" id="days-slider"
                  min="1" max="1825" value="${state.daysBack}"
                  style="--slider-pct:${((state.daysBack - 1) / 1824 * 100).toFixed(1)}%"
                />
                <span class="days-value" id="days-value">${state.daysBack}d</span>
              </div>
            </div>
            <div class="control-group">
              <label class="control-label">Max papers</label>
              <input type="number" class="papers-input" id="papers-input"
                min="1" max="50" value="${state.maxPapers}" />
            </div>
            <div class="control-group">
              <label class="control-label">Fetch fresh</label>
              <label class="fetch-toggle" id="fetch-toggle">
                <div class="toggle-track ${state.fetchFresh ? 'on' : ''}" id="toggle-track">
                  <div class="toggle-thumb"></div>
                </div>
                <span class="toggle-label">${state.fetchFresh ? 'On' : 'Off'}</span>
              </label>
            </div>
          </div>
          <div class="query-row">
            <input type="text" id="query-input" placeholder="e.g. NASH FXR agonist, KRAS mutant NSCLC..."
              value="${state.query}" />
            <button id="send-btn" ${state.loading ? 'disabled' : ''}>
              ${state.loading
                ? '<span class="spinner"></span>'
                : '<span>Analyze</span><span class="send-arrow">↑</span>'}
            </button>
          </div>
        </div>
      </div>

      <!-- Stats sidebar -->
      <div class="stats-sidebar">
        <div>
          <div class="sidebar-section-title">Knowledge Base</div>
          <div class="stat-pill">
            <span class="sp-value">${state.ragStats.paper_count}</span>
            <span class="sp-label">Papers ingested</span>
          </div>
          <div class="stat-pill" style="margin-top:6px">
            <span class="sp-value">${state.ragStats.chunk_count}</span>
            <span class="sp-label">Text chunks</span>
          </div>
          ${state.ragStats.chunk_count > 0
            ? `<button class="clear-kb-btn" id="clear-kb-btn" style="margin-top:8px">🗑 Clear KB</button>`
            : ''}
        </div>
        ${results ? `
        <div>
          <div class="sidebar-section-title">Last Run</div>
          <div class="stat-pill">
            <span class="sp-value">${results.target_scores?.length || 0}</span>
            <span class="sp-label">Targets scored</span>
          </div>
          <div class="stat-pill" style="margin-top:6px">
            <span class="sp-value">${(results.papers?.length || 0) + (results.preprints?.length || 0)}</span>
            <span class="sp-label">Sources fetched</span>
          </div>
        </div>` : ''}
      </div>
    </div>

    <!-- Tabs (only show when results exist) -->
    ${results ? `
    <div class="tabs-container">
      <div class="tabs-header">
        ${tabLabels.map((t, i) => `
          <button class="tab-btn ${state.activeTab === i ? 'active' : ''}" id="tab-btn-${i}">
            ${t.label}
            ${t.count != null ? `<span class="tab-count">${t.count}</span>` : ''}
          </button>`).join('')}
      </div>
      <div class="tab-panel ${state.activeTab === 0 ? 'active' : ''}" id="tab-panel-0">
        ${renderBriefTab(results)}
      </div>
      <div class="tab-panel ${state.activeTab === 1 ? 'active' : ''}" id="tab-panel-1">
        ${renderPapersTab(results.papers || [])}
      </div>
      <div class="tab-panel ${state.activeTab === 2 ? 'active' : ''}" id="tab-panel-2">
        ${renderPreprintsTab(results.preprints || [])}
      </div>
      <div class="tab-panel ${state.activeTab === 3 ? 'active' : ''}" id="tab-panel-3">
        ${renderTrialsTab(results.trials || [])}
      </div>
      <div class="tab-panel ${state.activeTab === 4 ? 'active' : ''}" id="tab-panel-4">
        ${renderTraceTab(results)}
      </div>
    </div>` : ''}
  </div>`;
}

function renderChatItem(item) {
  if (item.role === 'user') {
    return `
    <div class="msg user">
      <div class="msg-avatar">U</div>
      <div>
        <div class="msg-bubble">${escapeHtml(item.content)}</div>
        <div class="msg-time">${item.time}</div>
      </div>
    </div>`;
  }
  if (item.type === 'step') {
    const statusClass = item.status === 'ok' ? 'ok' : item.status === 'warn' ? 'warn' : 'error';
    return `
    <div class="event-card ${statusClass}">
      <span class="ev-icon">${item.icon || '•'}</span>
      <span>${escapeHtml(item.label)}${item.detail ? `<br/><span style="font-size:0.72rem;color:var(--text-dim)">${escapeHtml(item.detail)}</span>` : ''}</span>
    </div>`;
  }
  if (item.type === 'result') {
    return `
    <div class="msg system">
      <div class="msg-avatar">🧬</div>
      <div>
        <div class="msg-bubble">${item.content}</div>
        <div class="msg-time">${item.time}</div>
      </div>
    </div>`;
  }
  return '';
}

// ── Tab: Target Brief ─────────────────────────────────────────────────────────
function renderBriefTab(results) {
  const scores = results.target_scores || [];
  const brief  = results.brief || '';

  let html = '';

  // Scoreboard FIRST
  if (scores.length > 0) {
    html += `<div class="score-cards-grid">${scores.map(renderScoreCard).join('')}</div>`;
  } else {
    html += `<div class="empty-state"><span class="empty-icon">📊</span><p>No target scores available. Run analysis with a specific gene or disease target.</p></div>`;
  }

  // Narrative below (collapsible)
  if (brief) {
    html += `
    <div class="brief-section">
      <button class="brief-collapsible-btn" id="brief-toggle-btn">
        📝 Full Hypothesis Brief
        <span id="brief-toggle-arrow">▼</span>
      </button>
      <div class="brief-body" id="brief-body">
        <div style="margin-bottom:0.75rem">
          <button class="brief-download" id="brief-download-btn">⬇️ Copy Markdown</button>
        </div>
        <div class="brief-content">${marked.parse(brief)}</div>
      </div>
    </div>`;
  }

  return html || `<div class="empty-state"><span class="empty-icon">📊</span><p>Run an analysis to see the Target Brief.</p></div>`;
}

function renderScoreCard(s) {
  const score = s.score || 1;
  const color = score >= 8 ? 'var(--score-green)' : score >= 5 ? 'var(--score-amber)' : 'var(--score-red)';
  const tractClass = (s.tractability || '').includes('Small') ? 'sm' : (s.tractability || '').includes('Antibody') ? 'ab' : 'unk';
  const breakdown = s.breakdown || [];
  const geneId = `score-card-${s.gene}`.replace(/[^a-z0-9-]/gi, '-');

  return `
  <div class="score-card" id="${geneId}">
    <div class="score-card-top">
      <div class="ring-wrap">
        ${renderRingSVG(score, 72, color)}
        <div class="ring-label">
          <span class="score-n" style="color:${color}">${score}</span>
          <span class="score-of">/10</span>
        </div>
      </div>
      <div class="score-card-info">
        <div class="gene-name">${escapeHtml(s.gene)}</div>
        <div class="tractability-badge ${tractClass}">${escapeHtml(s.tractability || 'Unknown')}</div>
        <div class="uniprot-id">${s.uniprot_id && s.uniprot_id !== 'Unknown' ? `UniProt: ${s.uniprot_id}` : ''}</div>
        ${s.ensembl_id ? `<div class="uniprot-id" style="margin-top:2px">Ensembl: ${s.ensembl_id}</div>` : ''}
      </div>
    </div>
    ${s.protein_function && s.protein_function !== 'Unknown'
      ? `<div class="protein-fn">${escapeHtml(s.protein_function)}</div>` : ''}
    ${breakdown.length > 0 ? `
    <div style="margin-top:0.75rem">
      <button class="breakdown-toggle" onclick="toggleBreakdown('${geneId}-bd')">
        Score breakdown <span id="${geneId}-bd-arrow">▼</span>
      </button>
      <div class="breakdown-body" id="${geneId}-bd">
        ${breakdown.map(b => `
        <div class="bd-row">
          <span class="bd-label">${escapeHtml(b.label)}</span>
          <span class="bd-source">${escapeHtml(b.source)}</span>
          <span class="bd-pts">+${b.points}</span>
        </div>`).join('')}
        <div class="bd-total">
          <span>Total score</span>
          <span>${score}/10</span>
        </div>
      </div>
    </div>` : ''}
  </div>`;
}

function toggleBreakdown(id) {
  const body = document.getElementById(id);
  const arrow = document.getElementById(id + '-arrow');
  if (!body) return;
  body.classList.toggle('open');
  if (arrow) arrow.textContent = body.classList.contains('open') ? '▲' : '▼';
}
window.toggleBreakdown = toggleBreakdown;

// ── Tab: Papers ───────────────────────────────────────────────────────────────
function renderPapersTab(papers) {
  if (!papers.length) return `<div class="empty-state"><span class="empty-icon">📚</span><p>No papers retrieved. Make sure fetch_fresh is ON and run analysis.</p></div>`;
  return `
  <div style="margin-bottom:0.75rem;color:var(--text-muted);font-size:0.82rem">${papers.length} papers from PubMed</div>
  <div class="paper-list">
    ${papers.map((p, i) => renderPaperCard(p, i, 'pubmed')).join('')}
  </div>`;
}

function renderPreprintsTab(preprints) {
  if (!preprints.length) return `<div class="empty-state"><span class="empty-icon">🧪</span><p>No preprints found. Try broader query or more days.</p></div>`;
  return `
  <div style="margin-bottom:0.75rem;color:var(--text-muted);font-size:0.82rem">
    ${preprints.length} preprints from bioRxiv / medRxiv
    <span style="background:rgba(245,158,11,0.12);color:var(--score-amber);font-size:0.7rem;padding:2px 6px;border-radius:4px;margin-left:6px">⚠️ Not peer reviewed</span>
  </div>
  <div class="paper-list">
    ${preprints.map((p, i) => renderPaperCard(p, i, 'preprint')).join('')}
  </div>`;
}

function renderPaperCard(p, i, type) {
  const cardId = `paper-${type}-${i}`;
  const pmid = p.pmid || '';
  const doi  = p.doi || '';
  const date = (p.date || '').slice(0, 10);
  const abstract = (p.abstract || '').slice(0, 600);
  const server = p.server || p.journal || (type === 'preprint' ? 'Preprint' : 'PubMed');

  return `
  <div class="paper-card" id="${cardId}">
    <div class="paper-summary" onclick="togglePaper('${cardId}')">
      <span class="paper-badge ${type}">${type === 'preprint' ? server : 'PubMed'}</span>
      <span class="paper-title">${escapeHtml(p.title || 'Unknown title')}</span>
      <span class="paper-chevron">▼</span>
    </div>
    <div class="paper-detail">
      <div class="paper-meta">
        ${p.journal ? `<span><strong>Journal:</strong> ${escapeHtml(p.journal)}</span>` : ''}
        ${date ? `<span><strong>Date:</strong> ${date}</span>` : ''}
        ${pmid && pmid !== 'N/A' ? `<span><strong>PMID:</strong> <a href="https://pubmed.ncbi.nlm.nih.gov/${pmid}/" target="_blank">${pmid}</a></span>` : ''}
        ${doi && doi !== 'N/A' ? `<span><strong>DOI:</strong> <a href="https://doi.org/${doi}" target="_blank">${doi}</a></span>` : ''}
        ${p.authors ? `<span><strong>Authors:</strong> ${escapeHtml((p.authors+'').slice(0, 120))}${(p.authors+'').length > 120 ? '…' : ''}</span>` : ''}
      </div>
      ${abstract ? `<div class="paper-abstract">${escapeHtml(abstract)}${(p.abstract||'').length > 600 ? '…' : ''}</div>` : ''}
    </div>
  </div>`;
}

function togglePaper(id) {
  const card = document.getElementById(id);
  if (card) card.classList.toggle('open');
}
window.togglePaper = togglePaper;

// ── Tab: Trials ───────────────────────────────────────────────────────────────
function renderTrialsTab(trials) {
  if (!trials.length) return `<div class="empty-state"><span class="empty-icon">🏥</span><p>No active clinical trials found for this condition.</p></div>`;
  return `
  <div style="margin-bottom:0.75rem;color:var(--text-muted);font-size:0.82rem">${trials.length} active/recruiting trials</div>
  ${trials.map(t => {
    const status = t.status || '';
    const statusClass = status.toUpperCase().includes('RECRUIT') ? 'recruiting' : status.toUpperCase().includes('ACTIVE') ? 'active' : 'other';
    const nctLink = t.url || (t.nct_id ? `https://clinicaltrials.gov/study/${t.nct_id}` : '');
    return `
    <div class="trial-card">
      <div class="trial-header">
        <span class="trial-status-badge ${statusClass}">${status || 'Unknown'}</span>
        <span class="trial-title">${escapeHtml(t.title || 'Unknown trial')}</span>
      </div>
      <div class="trial-meta">
        ${t.nct_id ? `<span><strong>NCT:</strong> <a href="${nctLink}" target="_blank">${t.nct_id}</a></span>` : ''}
        ${t.phase ? `<span><strong>Phase:</strong> ${escapeHtml(t.phase)}</span>` : ''}
        ${t.sponsor ? `<span><strong>Sponsor:</strong> ${escapeHtml(t.sponsor)}</span>` : ''}
        ${t.start_date ? `<span><strong>Start:</strong> ${t.start_date}</span>` : ''}
        ${t.interventions ? `<span><strong>Interventions:</strong> ${escapeHtml((t.interventions+'').slice(0, 150))}</span>` : ''}
      </div>
    </div>`;
  }).join('')}`;
}

// ── Tab: Agent Trace ──────────────────────────────────────────────────────────
function renderTraceTab(results) {
  const steps = results.steps || [];
  const trace = results.trace || '';
  let html = '';
  if (steps.length) {
    html += `<div class="trace-steps">${steps.map(s => `
      <div class="trace-step ${s.status || 'ok'}">
        <span class="ts-icon">${s.icon || '•'}</span>
        <span class="ts-label">${escapeHtml(s.label)}</span>
        ${s.detail ? `<span class="ts-detail">${escapeHtml(s.detail)}</span>` : ''}
      </div>`).join('')}</div>`;
  }
  if (trace && trace !== 'No tool calls traced.') {
    html += `<div style="margin-top:1rem;font-size:0.82rem;font-weight:600;color:var(--text-muted);margin-bottom:0.4rem">Raw tool call trace</div>
    <div class="trace-raw">${escapeHtml(trace)}</div>`;
  }
  if (!html) html = `<div class="empty-state"><span class="empty-icon">🔍</span><p>Run an analysis to see the agent trace.</p></div>`;
  return html;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function renderHealth() {
  const h = state.healthStatus;
  return `
  <div id="page-health">
    <div class="section-label">System</div>
    <h2 class="section-title" style="margin-bottom:1rem">API Health Status</h2>
    <button class="refresh-btn" id="refresh-health-btn">↺ Refresh</button>
    ${h ? `
    <div style="margin-bottom:1rem;font-size:0.85rem;color:var(--text-muted)">
      Overall: <span style="font-weight:700;color:${h.status === 'ok' ? 'var(--score-green)' : h.status === 'degraded' ? 'var(--score-amber)' : 'var(--score-red)'}">${h.status.toUpperCase()}</span>
    </div>
    ${(h.services || []).map(s => `
    <div class="health-card">
      <span class="h-icon">${s.status === 'ok' ? '✅' : '❌'}</span>
      <div class="h-info">
        <div class="h-name">${escapeHtml(s.name)}</div>
        <div class="h-detail">${escapeHtml(s.detail || '')}</div>
      </div>
      <span class="h-latency">${s.latency_ms}ms</span>
      <span class="health-badge ${s.status === 'ok' ? 'ok' : 'error'}">${s.status.toUpperCase()}</span>
    </div>`).join('')}` : `
    <div class="empty-state"><span class="spinner"></span><p>Checking APIs...</p></div>`}
  </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// RING SVG HELPER
// ═══════════════════════════════════════════════════════════════════════════════
function renderRingSVG(score, size, color) {
  const R = (size / 2) * 0.78;
  const cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * R;
  const pct = Math.max(0, Math.min(10, score)) / 10;
  const dashOffset = circ * (1 - pct);
  return `
  <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${cx}" cy="${cy}" r="${R}"
      stroke="rgba(255,255,255,0.06)" stroke-width="7" fill="none"/>
    <circle cx="${cx}" cy="${cy}" r="${R}"
      stroke="${color}" stroke-width="7" fill="none"
      stroke-linecap="round"
      stroke-dasharray="${circ}"
      stroke-dashoffset="${dashOffset}"
      transform="rotate(-90 ${cx} ${cy})"/>
  </svg>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// EVENT HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════
function attachHandlers() {
  // Landing CTAs
  bindClick('hero-cta-btn', () => navigate('app'));
  bindClick('cta-bottom-btn', () => navigate('app'));

  // App: slider
  bindInput('days-slider', (e) => {
    state.daysBack = parseInt(e.target.value);
    const pct = ((state.daysBack - 1) / 1824 * 100).toFixed(1);
    e.target.style.setProperty('--slider-pct', pct + '%');
    const label = document.getElementById('days-value');
    if (label) label.textContent = state.daysBack + 'd';
  });

  // App: papers input
  bindInput('papers-input', (e) => {
    state.maxPapers = Math.max(1, Math.min(50, parseInt(e.target.value) || 20));
  });

  // App: fetch toggle
  bindClick('fetch-toggle', () => {
    state.fetchFresh = !state.fetchFresh;
    const track = document.getElementById('toggle-track');
    if (track) {
      track.classList.toggle('on', state.fetchFresh);
      const thumb = track.querySelector('.toggle-thumb');
      const lbl = document.querySelector('.toggle-label');
      if (lbl) lbl.textContent = state.fetchFresh ? 'On' : 'Off';
    }
  });

  // App: query input sync
  bindInput('query-input', (e) => { state.query = e.target.value; });

  // App: send on Enter
  const qi = document.getElementById('query-input');
  if (qi) qi.addEventListener('keydown', (e) => { if (e.key === 'Enter') runAnalysis(); });

  // App: send button
  bindClick('send-btn', runAnalysis);

  // App: clear KB
  bindClick('clear-kb-btn', clearKB);

  // App: tabs
  for (let i = 0; i < 5; i++) {
    bindClick(`tab-btn-${i}`, () => {
      state.activeTab = i;
      document.querySelectorAll('.tab-btn').forEach((b, j) => b.classList.toggle('active', j === i));
      document.querySelectorAll('.tab-panel').forEach((p, j) => p.classList.toggle('active', j === i));
    });
  }

  // Brief: toggle
  bindClick('brief-toggle-btn', () => {
    const body = document.getElementById('brief-body');
    const arrow = document.getElementById('brief-toggle-arrow');
    if (body) {
      body.classList.toggle('open');
      if (arrow) arrow.textContent = body.classList.contains('open') ? '▲' : '▼';
    }
  });

  // Brief: copy markdown
  bindClick('brief-download-btn', () => {
    const brief = state.results?.brief || '';
    navigator.clipboard.writeText(brief).then(() => {
      const btn = document.getElementById('brief-download-btn');
      if (btn) { btn.textContent = '✓ Copied!'; setTimeout(() => { btn.textContent = '⬇️ Copy Markdown'; }, 2000); }
    });
  });

  // Health: refresh
  bindClick('refresh-health-btn', loadHealth);
}

function bindClick(id, fn) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('click', fn);
}
function bindInput(id, fn) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', fn);
}

// ═══════════════════════════════════════════════════════════════════════════════
// ANALYSIS — API CALL
// ═══════════════════════════════════════════════════════════════════════════════
async function runAnalysis() {
  const query = (document.getElementById('query-input')?.value || '').trim();
  if (!query) return;
  if (state.loading) return;

  state.query = query;
  state.loading = true;
  state.results = null;
  state.activeTab = 0;

  // Add user message to chat
  const now = new Date().toLocaleTimeString();
  state.chatHistory.push({ role: 'user', content: query, time: now });

  render();
  scrollChatToBottom();

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: state.query,
        days_back: state.daysBack,
        max_papers: state.maxPapers,
        fetch_fresh: state.fetchFresh,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    const data = await res.json();
    state.results = data;
    state.loading = false;

    // Add step events to chat
    (data.steps || []).forEach(s => {
      state.chatHistory.push({ role: 'system', type: 'step', ...s });
    });

    // Add summary result card
    const scoresSummary = (data.target_scores || [])
      .map(s => `<strong>${s.gene}</strong> ${s.score}/10`)
      .join(' · ') || 'No targets scored';
    state.chatHistory.push({
      role: 'system',
      type: 'result',
      content: `
        <div style="font-size:0.85rem">
          <div style="font-weight:700;margin-bottom:6px;color:var(--accent)">✓ Analysis complete</div>
          <div>🎯 ${scoresSummary}</div>
          <div style="margin-top:4px;color:var(--text-dim)">
            ${data.papers?.length || 0} papers · ${data.preprints?.length || 0} preprints · ${data.trials?.length || 0} trials
          </div>
          <div style="margin-top:4px;font-size:0.75rem;color:var(--text-dim)">See tabs below for details</div>
        </div>`,
      time: new Date().toLocaleTimeString(),
    });

    loadRagStats();

  } catch (err) {
    state.loading = false;
    state.chatHistory.push({
      role: 'system',
      type: 'step',
      icon: '❌',
      label: 'Analysis failed',
      detail: String(err),
      status: 'error',
    });
  }

  render();
  scrollChatToBottom();
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════
async function loadRagStats() {
  try {
    const res = await fetch('/api/rag/stats');
    if (res.ok) {
      state.ragStats = await res.json();
      // Update sidebar only if on app page
      const spPaper = document.querySelector('.stat-pill .sp-value');
      if (spPaper) spPaper.textContent = state.ragStats.paper_count;
    }
  } catch (_) {}
}

async function clearKB() {
  try {
    await fetch('/api/rag/clear', { method: 'DELETE' });
    state.ragStats = { chunk_count: 0, paper_count: 0 };
    render();
  } catch (e) {
    console.error('Clear KB failed:', e);
  }
}

async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      state.healthStatus = await res.json();
    }
  } catch (_) {
    state.healthStatus = { status: 'error', services: [] };
  }
  render();
}

function scrollChatToBottom() {
  requestAnimationFrame(() => {
    const thread = document.getElementById('chat-thread');
    if (thread) thread.scrollTop = thread.scrollHeight;
  });
}

function escapeHtml(str) {
  if (typeof str !== 'string') return str ?? '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ═══════════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════════
(async function init() {
  // Detect current route from hash
  const hash = window.location.hash.replace('#', '') || 'landing';
  state.route = hash;

  // Initial health check (non-blocking)
  loadHealth().catch(() => {});

  render();
})();
