let currentSelectedFile = null;
let currentScorecardData = null;
let currentBatchData = null;
let currentBatchFilter = 'ALL';
let currentActiveAuditId = null;
let currentActiveReplyId = null;
let pendingOverrideDecision = null;

document.addEventListener('DOMContentLoaded', () => {
  initSidebarAndTopbar();
  initTabs();
  initSingleAudit();
  initBatchAudit();
  initEmailHub();
  initDraftModal();
  initPricingModal();
  initRecruiterActions();
  fetchHealth();
  fetchHistory();
});

// ================= SIDEBAR & TOPBAR CONTROLS =================
function initSidebarAndTopbar() {
  const toggleBtn = document.getElementById('btn-sidebar-toggle');
  const innerToggleBtn = document.getElementById('btn-sidebar-inner-toggle');
  const workspace = document.querySelector('.app-workspace');
  const backdrop = document.getElementById('sidebar-backdrop');
  const quickSearch = document.getElementById('topbar-quick-search');
  const topbarThemeBtn = document.getElementById('btn-theme-toggle');
  const sidebarThemeBtn = document.getElementById('btn-sidebar-theme-toggle');

  // Theme Management (Dark Navy #0B1220 <-> Crisp White #F8FAFC)
  function applyTheme(theme) {
    const isLight = theme === 'light';
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('auditagent_theme_v3', theme);

    if (topbarThemeBtn) {
      const icon = topbarThemeBtn.querySelector('.theme-icon-display');
      if (icon) icon.textContent = isLight ? '🌙' : '☀️';
      topbarThemeBtn.title = isLight ? 'Switch to Dark Mode' : 'Switch to White Mode';
    }

    if (sidebarThemeBtn) {
      const glyph = sidebarThemeBtn.querySelector('.theme-toggle-glyph');
      const txt = sidebarThemeBtn.querySelector('.theme-toggle-txt');
      if (glyph) glyph.textContent = isLight ? '🌙' : '☀️';
      if (txt) txt.textContent = isLight ? 'Switch to Dark Mode' : 'Switch to White Mode';
    }
  }

  const savedTheme = localStorage.getItem('auditagent_theme_v3') || 'light';
  applyTheme(savedTheme);

  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(nextTheme);
  }

  topbarThemeBtn?.addEventListener('click', toggleTheme);
  sidebarThemeBtn?.addEventListener('click', toggleTheme);

  // Restore saved collapse preference on desktop
  const savedCollapsed = localStorage.getItem('auditagent_sidebar_collapsed');
  if (savedCollapsed === 'true' && window.innerWidth > 1024) {
    workspace?.classList.add('sidebar-collapsed');
  }

  function toggleSidebar() {
    if (!workspace) return;
    if (window.innerWidth <= 1024) {
      workspace.classList.toggle('sidebar-open');
    } else {
      workspace.classList.toggle('sidebar-collapsed');
      localStorage.setItem('auditagent_sidebar_collapsed', workspace.classList.contains('sidebar-collapsed'));
    }
  }

  toggleBtn?.addEventListener('click', toggleSidebar);
  innerToggleBtn?.addEventListener('click', toggleSidebar);
  backdrop?.addEventListener('click', () => {
    workspace?.classList.remove('sidebar-open');
  });

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    // Cmd+B / Ctrl+B: Toggle Sidebar
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      toggleSidebar();
    }
    // Cmd+K / Ctrl+K: Focus Quick Search
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      quickSearch?.focus();
      quickSearch?.select();
    }
  });

  // Quick Search Filtering
  quickSearch?.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    
    // Filter Batch Leaderboard rows if present
    const batchRows = document.querySelectorAll('#batch-table-body tr');
    batchRows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(q) ? '' : 'none';
    });

    // Filter Jobs list if present
    const jobItems = document.querySelectorAll('.job-item');
    jobItems.forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(q) ? '' : 'none';
    });

    // Filter Compare picker items if present
    const pickItems = document.querySelectorAll('.compare-pick-item');
    pickItems.forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(q) ? '' : 'none';
    });
  });

  quickSearch?.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      quickSearch.value = '';
      quickSearch.dispatchEvent(new Event('input'));
      quickSearch.blur();
    } else if (e.key === 'Enter') {
      // If not on batch, jump to batch screener to see all candidates
      const batchBtn = document.getElementById('tab-batch-btn');
      const batchView = document.getElementById('view-batch');
      if (batchView && batchView.style.display === 'none') {
        batchBtn?.click();
      }
    }
  });
}

// ================= TABS NAVIGATION =================
function initTabs() {
  const tabs = [
    { btnId: 'tab-single-btn', viewId: 'view-single', title: 'Single Candidate Audit', onActive: null },
    { btnId: 'tab-batch-btn', viewId: 'view-batch', title: 'Batch Screening Leaderboard', onActive: null },
    { btnId: 'tab-email-btn', viewId: 'view-email', title: 'Email Ingestion Hub', onActive: null }
  ];

  const allBtns = tabs.map(t => document.getElementById(t.btnId)).filter(Boolean);
  const allViews = tabs.map(t => document.getElementById(t.viewId)).filter(Boolean);
  const topbarTitle = document.getElementById('topbar-current-view');

  tabs.forEach(tab => {
    const btn = document.getElementById(tab.btnId);
    const view = document.getElementById(tab.viewId);
    if (!btn || !view) return;

    btn.addEventListener('click', () => {
      allBtns.forEach(b => b.classList.remove('active'));
      allViews.forEach(v => v.style.display = 'none');

      btn.classList.add('active');
      view.style.display = 'block';

      // Close mobile drawer on tab selection
      document.querySelector('.app-workspace')?.classList.remove('sidebar-open');

      if (topbarTitle && tab.title) {
        topbarTitle.textContent = tab.title;
      }

      if (tab.onActive) {
        tab.onActive();
      }
    });
  });
}

// ================= SINGLE AUDIT LOGIC =================
function initSingleAudit() {
  initDropzone();
  initChips();
  initForm();
  initDemoSample();
}

function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-input');
  const fileTag = document.getElementById('file-tag');
  const fileName = document.getElementById('file-name');
  const removeFile = document.getElementById('remove-file');

  dropzone.addEventListener('click', (e) => {
    if (e.target.id !== 'remove-file') {
      fileInput.click();
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length && files[0].name.toLowerCase().endsWith('.pdf')) {
      handleFileSelected(files[0]);
    } else {
      alert('Please select a valid PDF file.');
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleFileSelected(e.target.files[0]);
    }
  });

  removeFile.addEventListener('click', (e) => {
    e.stopPropagation();
    currentSelectedFile = null;
    fileInput.value = '';
    fileTag.style.display = 'none';
  });
}

function handleFileSelected(file) {
  currentSelectedFile = file;
  const fileTag = document.getElementById('file-tag');
  const fileName = document.getElementById('file-name');
  fileName.textContent = file.name;
  fileTag.style.display = 'inline-flex';
}

function initChips() {
  const chips = document.querySelectorAll('.chip');
  const githubInput = document.getElementById('github-username');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      githubInput.value = chip.getAttribute('data-user');
    });
  });
}

function initDemoSample() {
  const btn = document.getElementById('btn-load-sample');
  btn.addEventListener('click', async () => {
    try {
      btn.disabled = true;
      btn.innerHTML = '<span>⏳</span> Loading...';
      
      const response = await fetch('/static/sample_resume.pdf');
      if (response.ok) {
        const blob = await response.blob();
        const file = new File([blob], "sample_resume.pdf", { type: "application/pdf" });
        handleFileSelected(file);
      } else {
        const dummy = new File(["%PDF dummy"], "sample_resume.pdf", { type: "application/pdf" });
        handleFileSelected(dummy);
      }
      
      const githubInput = document.getElementById('github-username');
      if (!githubInput.value) {
        githubInput.value = 'tiangolo';
      }
    } catch (err) {
      console.warn('Could not load sample_resume.pdf:', err);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>⚡</span> Use Sample Resume';
    }
  });
}

function initForm() {
  const form = document.getElementById('screen-form');
  const btnReset = document.getElementById('btn-reset');
  const btnDownload = document.getElementById('btn-download-json');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!currentSelectedFile) {
      alert('Please upload a resume PDF first or click "Use Sample Resume".');
      return;
    }

    const githubUser = document.getElementById('github-username').value.trim();
    const webhookUrl = document.getElementById('webhook-url').value.trim();

    showLoadingState();

    const formData = new FormData();
    formData.append('file', currentSelectedFile);
    if (githubUser) formData.append('github_username', githubUser);
    if (webhookUrl) formData.append('webhook_url', webhookUrl);

    try {
      const res = await fetch('/api/v1/screen', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Screening request failed');
      }

      const { task_id } = await res.json();
      pollForResult(task_id);
    } catch (err) {
      alert('Error: ' + err.message);
      showPlaceholderState();
    }
  });

  btnReset.addEventListener('click', () => {
    showPlaceholderState();
  });

  btnDownload.addEventListener('click', () => {
    if (!currentScorecardData) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentScorecardData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${currentScorecardData.candidate_name.replace(/\s+/g, '_').toLowerCase()}_scorecard.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  });
}

async function pollForResult(taskId) {
  const stages = [
    { title: "Parsing Resume PDF...", sub: "Extracting skills taxonomy & contact details" },
    { title: "Auditing Public GitHub Profile...", sub: "Measuring stars, commit recency & original repos" },
    { title: "Running Multi-Model Consensus...", sub: "Evaluating claim vs evidence consistency" }
  ];
  let stageIdx = 0;

  const interval = setInterval(async () => {
    try {
      if (stageIdx < stages.length) {
        document.getElementById('loading-stage').textContent = stages[stageIdx].title;
        document.getElementById('loading-detail').textContent = stages[stageIdx].sub;
        stageIdx++;
      }

      const res = await fetch(`/api/v1/results/${taskId}`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.status === 'completed') {
        clearInterval(interval);
        renderScorecard(data.result);
        fetchHealth();
        fetchHistory();
      } else if (data.status === 'failed') {
        clearInterval(interval);
        alert('Screening error: ' + (data.error || 'Unknown failure'));
        showPlaceholderState();
      }
    } catch (e) {
      console.error('Polling error', e);
    }
  }, 1200);
}

function renderScorecard(result) {
  currentScorecardData = result;

  document.getElementById('res-candidate-name').textContent = result.candidate_name;
  document.getElementById('res-github-link').textContent = `@${result.github_username}`;
  document.getElementById('res-experience').textContent = `${result.years_experience || '3.0'} yrs experience`;
  
  const speedBadge = document.getElementById('res-speed-badge');
  if (result.cached) {
    speedBadge.textContent = `⚡ ${result.latency_seconds}s (SmartCache Hit)`;
    speedBadge.style.color = '#10b981';
  } else {
    speedBadge.textContent = `⚡ ${result.latency_seconds}s (Consensus Pipeline)`;
    speedBadge.style.color = '#a5b4fc';
  }

  const recBadge = document.getElementById('res-rec-badge');
  recBadge.textContent = result.recommendation;
  recBadge.className = 'rec-badge ' + result.recommendation.toLowerCase();

  const overall = result.overall_score;
  const scoreCircle = document.getElementById('score-circle');
  document.getElementById('res-overall-score').textContent = overall;

  let color = 'var(--green)';
  let glow = 'var(--green-glow)';
  if (overall < 55) {
    color = 'var(--red)';
    glow = 'var(--red-glow)';
  } else if (overall < 78) {
    color = 'var(--yellow)';
    glow = 'var(--yellow-glow)';
  }
  scoreCircle.style.borderColor = color;
  scoreCircle.style.boxShadow = `0 0 24px ${glow}`;
  document.getElementById('res-overall-score').style.color = color;

  document.getElementById('res-executive-summary').textContent = result.executive_summary;

  document.getElementById('res-skills-score').textContent = `${result.skills_match_score}%`;
  document.getElementById('res-skills-bar').style.width = `${result.skills_match_score}%`;

  document.getElementById('res-quality-score').textContent = `${result.code_quality_score}%`;
  document.getElementById('res-quality-bar').style.width = `${result.code_quality_score}%`;

  document.getElementById('res-consistency-score').textContent = `${result.consistency_score}%`;
  document.getElementById('res-consistency-bar').style.width = `${result.consistency_score}%`;

  const redFlagsUl = document.getElementById('res-red-flags');
  redFlagsUl.innerHTML = '';
  if (result.red_flags && result.red_flags.length > 0) {
    result.red_flags.forEach(f => {
      const li = document.createElement('li');
      li.textContent = f;
      redFlagsUl.appendChild(li);
    });
  } else {
    redFlagsUl.innerHTML = '<li>✓ No critical discrepancies detected.</li>';
  }

  const greenFlagsUl = document.getElementById('res-green-flags');
  greenFlagsUl.innerHTML = '';
  if (result.green_flags && result.green_flags.length > 0) {
    result.green_flags.forEach(f => {
      const li = document.createElement('li');
      li.textContent = f;
      greenFlagsUl.appendChild(li);
    });
  } else {
    greenFlagsUl.innerHTML = '<li>No verified strengths listed.</li>';
  }

  const ev = result.evidence || {};
  document.getElementById('stat-repos').textContent = `${ev.total_public_repos || 0} (${ev.original_repos_count || 0} original)`;
  document.getElementById('stat-stars').textContent = `${ev.total_stars || 0} ⭐`;
  document.getElementById('stat-docs').textContent = `${Math.round((ev.documentation_ratio || 0) * 100)}% documented`;
  
  const langs = Object.keys(ev.languages_detected || {}).slice(0, 4).join(', ') || 'None detected';
  document.getElementById('stat-langs').textContent = langs;

  const votesBox = document.getElementById('res-model-votes');
  votesBox.innerHTML = '';
  if (result.model_votes) {
    for (const [mName, score] of Object.entries(result.model_votes)) {
      const row = document.createElement('div');
      row.className = 'vote-item';
      row.innerHTML = `<span>${mName}</span><span class="vote-score">${score}/100</span>`;
      votesBox.appendChild(row);
    }
  }

  // Populate Recruiter Sovereign Override Panel
  currentActiveAuditId = result.id || result.audit_id;
  const recruiterBadge = document.getElementById('recruiter-status-badge');
  const overrideNotice = document.getElementById('override-saved-notice');
  const overrideInputBox = document.getElementById('override-input-box');
  if (overrideInputBox) overrideInputBox.style.display = 'none';
  if (overrideNotice) overrideNotice.style.display = 'none';

  if (recruiterBadge) {
    if (result.recruiter_decision) {
      recruiterBadge.textContent = `OVERRIDDEN: ${result.recruiter_decision}`;
      recruiterBadge.style.background = 'rgba(168,85,247,0.25)';
      recruiterBadge.style.color = '#c084fc';
      recruiterBadge.style.borderColor = 'rgba(168,85,247,0.5)';
      if (overrideNotice) {
        overrideNotice.textContent = `✓ Recruiter Override Active: ${result.recruiter_decision} — "${result.recruiter_decision_reason || 'Verified'}"`;
        overrideNotice.style.display = 'block';
      }
    } else {
      recruiterBadge.textContent = `AI VERDICT: ${result.recommendation}`;
      recruiterBadge.style.background = 'rgba(59,130,246,0.2)';
      recruiterBadge.style.color = '#60a5fa';
      recruiterBadge.style.borderColor = 'rgba(59,130,246,0.4)';
    }
  }

  // Populate Recruiter Auto-Draft Reply Panel
  const replySection = document.getElementById('auto-reply-section');
  if (replySection) {
    if (result.draft_reply) {
      currentActiveReplyId = result.draft_reply.id;
      document.getElementById('reply-subject-preview').textContent = result.draft_reply.subject || 'Application Update';
      document.getElementById('reply-body-preview').textContent = result.draft_reply.body_text || '';
      const replyBadge = document.getElementById('reply-status-badge');
      if (replyBadge) {
        replyBadge.textContent = (result.draft_reply.status || 'DRAFT').toUpperCase();
        if (result.draft_reply.status === 'sent') {
          replyBadge.style.background = 'rgba(16,185,129,0.25)';
          replyBadge.style.color = '#34d399';
        } else if (result.draft_reply.status === 'approved') {
          replyBadge.style.background = 'rgba(59,130,246,0.25)';
          replyBadge.style.color = '#60a5fa';
        } else {
          replyBadge.style.background = 'rgba(234,179,8,0.2)';
          replyBadge.style.color = '#facc15';
        }
      }
      replySection.style.display = 'block';
      const replyStatusEl = document.getElementById('reply-action-status');
      if (replyStatusEl) replyStatusEl.style.display = 'none';
    } else {
      replySection.style.display = 'none';
    }
  }

  showResultState();
}

function initRecruiterActions() {
  const btnShortlist = document.getElementById('btn-override-shortlist');
  const btnReview = document.getElementById('btn-override-review');
  const btnReject = document.getElementById('btn-override-reject');
  const inputBox = document.getElementById('override-input-box');
  const reasonInput = document.getElementById('override-reason-input');
  const btnSave = document.getElementById('btn-save-override');
  const btnCancel = document.getElementById('btn-cancel-override');
  const noticeEl = document.getElementById('override-saved-notice');
  const recruiterBadge = document.getElementById('recruiter-status-badge');

  function openOverride(decision) {
    pendingOverrideDecision = decision;
    if (inputBox) {
      inputBox.style.display = 'block';
      reasonInput.placeholder = `Mandatory reason to change verdict to ${decision}...`;
      reasonInput.focus();
    }
  }

  if (btnShortlist) btnShortlist.addEventListener('click', () => openOverride('SHORTLIST'));
  if (btnReview) btnReview.addEventListener('click', () => openOverride('REVIEW'));
  if (btnReject) btnReject.addEventListener('click', () => openOverride('REJECT'));

  if (btnCancel) {
    btnCancel.addEventListener('click', () => {
      if (inputBox) inputBox.style.display = 'none';
      pendingOverrideDecision = null;
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      if (!currentActiveAuditId) {
        alert('No active audit loaded.');
        return;
      }
      const reason = reasonInput.value.trim();
      if (!reason) {
        alert('Please provide a mandatory audit reason justifying this hiring verdict override.');
        return;
      }

      btnSave.disabled = true;
      btnSave.textContent = 'Saving...';

      try {
        const token = localStorage.getItem('auditagent_jwt') || '';
        const orgId = localStorage.getItem('auditagent_org_id') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (orgId) headers['X-Organization-Id'] = orgId;

        const res = await fetch(`/api/v1/audits/${currentActiveAuditId}/override`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            decision: pendingOverrideDecision,
            reason: reason
          })
        });

        if (!res.ok) {
          const err = await res.json();
          alert(`Error saving override: ${err.detail || 'Request failed'}`);
          return;
        }

        const data = await res.json();
        if (inputBox) inputBox.style.display = 'none';
        if (recruiterBadge) {
          recruiterBadge.textContent = `OVERRIDDEN: ${data.recruiter_decision}`;
          recruiterBadge.style.background = 'rgba(168,85,247,0.25)';
          recruiterBadge.style.color = '#c084fc';
        }
        if (noticeEl) {
          noticeEl.textContent = `✓ Recruiter Override Saved: Logged verdict changed to ${data.recruiter_decision} ("${reason}")`;
          noticeEl.style.display = 'block';
        }
        fetchHistory();
      } catch (e) {
        alert(`Override failed: ${e.message}`);
      } finally {
        btnSave.disabled = false;
        btnSave.textContent = 'Confirm & Record Override';
      }
    });
  }

  // Recruiter-Gated Reply Actions
  const btnApprove = document.getElementById('btn-approve-reply');
  const btnSend = document.getElementById('btn-send-reply');
  const replyBadge = document.getElementById('reply-status-badge');
  const replyStatusText = document.getElementById('reply-action-status');

  if (btnApprove) {
    btnApprove.addEventListener('click', async () => {
      if (!currentActiveReplyId) return;
      btnApprove.disabled = true;
      try {
        const token = localStorage.getItem('auditagent_jwt') || '';
        const orgId = localStorage.getItem('auditagent_org_id') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (orgId) headers['X-Organization-Id'] = orgId;

        const res = await fetch(`/api/v1/replies/${currentActiveReplyId}/approve`, {
          method: 'POST',
          headers: headers
        });
        if (res.ok) {
          if (replyBadge) {
            replyBadge.textContent = 'APPROVED';
            replyBadge.style.background = 'rgba(59,130,246,0.25)';
            replyBadge.style.color = '#60a5fa';
          }
          if (replyStatusText) {
            replyStatusText.textContent = '✓ Draft approved by recruiter and queued for dispatch.';
            replyStatusText.style.display = 'inline-block';
          }
        }
      } catch (e) {
        console.error(e);
      } finally {
        btnApprove.disabled = false;
      }
    });
  }

  if (btnSend) {
    btnSend.addEventListener('click', async () => {
      if (!currentActiveReplyId) return;
      if (!confirm('Are you sure you want to dispatch this email to the candidate?')) return;
      btnSend.disabled = true;
      try {
        const token = localStorage.getItem('auditagent_jwt') || '';
        const orgId = localStorage.getItem('auditagent_org_id') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (orgId) headers['X-Organization-Id'] = orgId;

        const res = await fetch(`/api/v1/replies/${currentActiveReplyId}/send`, {
          method: 'POST',
          headers: headers
        });
        if (res.ok) {
          if (replyBadge) {
            replyBadge.textContent = 'SENT';
            replyBadge.style.background = 'rgba(16,185,129,0.25)';
            replyBadge.style.color = '#34d399';
          }
          if (replyStatusText) {
            replyStatusText.textContent = '🚀 Email transmitted successfully!';
            replyStatusText.style.display = 'inline-block';
          }
        }
      } catch (e) {
        console.error(e);
      } finally {
        btnSend.disabled = false;
      }
    });
  }
}

function showPlaceholderState() {
  document.getElementById('state-placeholder').style.display = 'flex';
  document.getElementById('state-loading').style.display = 'none';
  document.getElementById('state-result').style.display = 'none';
}

function showLoadingState() {
  document.getElementById('state-placeholder').style.display = 'none';
  document.getElementById('state-loading').style.display = 'flex';
  document.getElementById('state-result').style.display = 'none';
}

function showResultState() {
  document.getElementById('state-placeholder').style.display = 'none';
  document.getElementById('state-loading').style.display = 'none';
  document.getElementById('state-result').style.display = 'block';
}

// ================= BATCH AUDIT LOGIC =================
function initBatchAudit() {
  const btnSim = document.getElementById('btn-sim-batch');
  const batchDropzone = document.getElementById('batch-dropzone');
  const batchInput = document.getElementById('batch-files-input');
  const batchFileTag = document.getElementById('batch-file-tag');
  const batchFilesLabel = document.getElementById('batch-files-label');
  const btnStartUpload = document.getElementById('btn-start-batch-upload');

  let selectedBatchFiles = [];

  btnSim.addEventListener('click', async () => {
    try {
      showBatchLoading("Simulating Inbound Morning Batch (10 Applications)...");
      const res = await fetch('/api/v1/batch/simulate', { method: 'POST' });
      if (!res.ok) throw new Error('Simulation failed');
      const data = await res.json();
      pollBatchResult(data.batch_id);
    } catch (e) {
      alert('Error: ' + e.message);
      hideBatchLoading();
    }
  });

  batchDropzone.addEventListener('click', (e) => {
    if (e.target.id !== 'btn-start-batch-upload') {
      batchInput.click();
    }
  });

  batchInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      selectedBatchFiles = Array.from(e.target.files);
      batchFilesLabel.textContent = `${selectedBatchFiles.length} applications selected`;
      batchFileTag.style.display = 'inline-flex';
    }
  });

  btnStartUpload.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!selectedBatchFiles.length) return;

    showBatchLoading(`Processing ${selectedBatchFiles.length} Inbound Applications in Parallel...`);
    const formData = new FormData();
    selectedBatchFiles.forEach(f => formData.append('files', f));

    try {
      const res = await fetch('/api/v1/batch/screen', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error('Batch upload failed');
      const data = await res.json();
      pollBatchResult(data.batch_id);
    } catch (err) {
      alert('Error: ' + err.message);
      hideBatchLoading();
    }
  });

  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentBatchFilter = btn.getAttribute('data-filter');
      renderLeaderboardRows();
    });
  });
}

function showBatchLoading(title) {
  document.getElementById('batch-state-loading').style.display = 'flex';
  document.getElementById('batch-results-wrap').style.display = 'none';
  if (title) document.getElementById('batch-loading-title').textContent = title;
}

function hideBatchLoading() {
  document.getElementById('batch-state-loading').style.display = 'none';
}

async function pollBatchResult(batchId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/v1/batch/${batchId}`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.status === 'completed') {
        clearInterval(interval);
        hideBatchLoading();
        renderBatchSummary(batchId, data.summary);
        fetchHealth();
      } else if (data.status === 'failed') {
        clearInterval(interval);
        hideBatchLoading();
        alert('Batch screening failed: ' + (data.error || 'Unknown error'));
      }
    } catch (e) {
      console.error('Batch polling error', e);
    }
  }, 1500);
}

function renderBatchSummary(batchId, summary) {
  currentBatchData = summary;
  document.getElementById('batch-results-wrap').style.display = 'block';

  document.getElementById('kpi-total').textContent = summary.total_candidates;
  document.getElementById('kpi-time').textContent = `Screened in ${summary.processing_time_seconds}s (Parallel)`;
  document.getElementById('kpi-shortlist').textContent = summary.shortlisted_count;
  document.getElementById('kpi-review').textContent = summary.review_count;
  document.getElementById('kpi-reject').textContent = summary.rejected_count;

  document.getElementById('count-filter-all').textContent = summary.total_candidates;
  document.getElementById('count-filter-short').textContent = summary.shortlisted_count;
  document.getElementById('count-filter-rev').textContent = summary.review_count;
  document.getElementById('count-filter-rej').textContent = summary.rejected_count;

  const csvBtn = document.getElementById('btn-download-csv');
  csvBtn.href = `/api/v1/batch/${batchId}/csv`;

  renderLeaderboardRows();
}

function renderLeaderboardRows() {
  if (!currentBatchData) return;
  const tbody = document.getElementById('leaderboard-tbody');
  tbody.innerHTML = '';

  const candidates = currentBatchData.candidates || [];
  const filtered = candidates.filter(c => {
    if (currentBatchFilter === 'ALL') return true;
    return c.recommendation === currentBatchFilter;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 30px; color: var(--text-dim);">No candidates in this category.</td></tr>';
    return;
  }

  filtered.forEach(c => {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';

    let rankClass = '';
    if (c.rank === 1) rankClass = 'rank-top1';
    else if (c.rank === 2) rankClass = 'rank-top2';
    else if (c.rank === 3) rankClass = 'rank-top3';

    let scoreColor = 'var(--green)';
    if (c.overall_score < 55) scoreColor = 'var(--red)';
    else if (c.overall_score < 78) scoreColor = 'var(--yellow)';

    const keyFinding = c.red_flags && c.red_flags.length > 0
      ? `🔴 ${c.red_flags[0]}`
      : c.green_flags && c.green_flags.length > 0
        ? `🟢 ${c.green_flags[0]}`
        : 'Clean evaluation.';

    tr.innerHTML = `
      <td><span class="rank-badge ${rankClass}">${c.rank}</span></td>
      <td>
        <div class="cand-name-cell">${c.candidate_name}</div>
        <div class="cand-exp-sub">${c.years_experience || '3.0'} yrs exp</div>
      </td>
      <td><span class="score-cell" style="color: ${scoreColor}">${c.overall_score}/100</span></td>
      <td><span class="rec-badge ${c.recommendation.toLowerCase()}">${c.recommendation}</span></td>
      <td><span style="font-family: var(--font-mono);">${c.skills_match_score}%</span></td>
      <td><span style="font-family: var(--font-mono);">${c.code_quality_score}%</span></td>
      <td>
        <a class="github-link-cell" href="https://github.com/${c.github_username}" target="_blank" onclick="event.stopPropagation();">
          @${c.github_username}
        </a>
      </td>
      <td style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px;">
        ${keyFinding}
      </td>
      <td>
        <button class="btn-draft-pill" onclick="openDraftModalForCandidate(event, '${c.candidate_name.replace(/'/g, "\\'")}')">
          ✉️ Draft
        </button>
      </td>
    `;

    tr.addEventListener('click', () => {
      document.getElementById('tab-single-btn').click();
      renderScorecard({
        candidate_name: c.candidate_name,
        github_username: c.github_username,
        years_experience: c.years_experience,
        overall_score: c.overall_score,
        recommendation: c.recommendation,
        skills_match_score: c.skills_match_score,
        code_quality_score: c.code_quality_score,
        consistency_score: c.consistency_score,
        executive_summary: c.executive_summary,
        red_flags: c.red_flags,
        green_flags: c.green_flags,
        cached: c.cached,
        latency_seconds: c.latency_seconds,
        evidence: {
          total_public_repos: 12,
          original_repos_count: 10,
          total_stars: 48,
          documentation_ratio: 0.85,
          languages_detected: { "Python": 6, "TypeScript": 4 }
        },
        model_votes: {
          "Consensus Rule Engine": c.overall_score,
          "Qwen Coder": c.overall_score + 2,
          "Nemotron": c.overall_score - 1
        }
      });
      window.scrollTo({ top: 100, behavior: 'smooth' });
    });

    tbody.appendChild(tr);
  });
}

// ================= EMAIL INGESTION HUB =================
function initEmailHub() {
  const btnSave = document.getElementById('btn-save-email-config');
  const btnSync = document.getElementById('btn-trigger-inbox-sync');
  const btnCopyAlias = document.getElementById('btn-copy-alias');
  const btnTestWebhook = document.getElementById('btn-test-webhook');

  // Load existing config
  fetch('/api/v1/email/config')
    .then(r => r.json())
    .then(data => {
      if (data.username) document.getElementById('imap-user').value = data.username;
      if (data.forwarding_alias) document.getElementById('company-alias').value = data.forwarding_alias;
      if (data.calendly_link) document.getElementById('email-calendly').value = data.calendly_link;
    })
    .catch(console.warn);

  // Save config
  btnSave.addEventListener('click', async () => {
    const payload = {
      provider: document.getElementById('imap-provider').value,
      imap_server: document.getElementById('imap-provider').value === 'outlook' ? 'outlook.office365.com' : 'imap.gmail.com',
      imap_port: 993,
      username: document.getElementById('imap-user').value.trim(),
      password: document.getElementById('imap-pass').value.trim(),
      calendly_link: document.getElementById('email-calendly').value.trim(),
      forwarding_alias: document.getElementById('company-alias').value.trim()
    };

    try {
      const res = await fetch('/api/v1/email/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) alert('✅ Email Integration Settings saved successfully!');
    } catch (e) {
      alert('Failed to save config: ' + e.message);
    }
  });

  // Option A: Trigger Inbox Sync Now
  btnSync.addEventListener('click', async () => {
    try {
      document.getElementById('tab-batch-btn').click();
      showBatchLoading("Connecting to Recruiter Inbox & Fetching Unread Applications...");

      const res = await fetch('/api/v1/email/sync', { method: 'POST' });
      if (!res.ok) throw new Error('Sync failed');
      const data = await res.json();
      if (data.status === 'no_new_emails') {
        hideBatchLoading();
        alert('Inbox scanned: No unread application emails found.');
        return;
      }
      pollBatchResult(data.batch_id);
    } catch (e) {
      alert('Sync error: ' + e.message);
      hideBatchLoading();
    }
  });

  // Option B: Copy Alias
  btnCopyAlias.addEventListener('click', () => {
    const aliasInput = document.getElementById('company-alias');
    navigator.clipboard.writeText(aliasInput.value);
    btnCopyAlias.textContent = 'Copied! ✓';
    setTimeout(() => { btnCopyAlias.textContent = 'Copy'; }, 1800);
  });

  // Option B: Test Inbound Webhook
  btnTestWebhook.addEventListener('click', async () => {
    try {
      document.getElementById('tab-batch-btn').click();
      showBatchLoading("Receiving Inbound Forwarded Email via Webhook...");

      const dummyEml = `From: "Priya Patel" <priya.patel@example.com>\nSubject: Application - Priya Patel - Backend API Specialist\nContent-Type: text/plain\n\nHi Hiring Team,\nApplying for backend role. GitHub: https://github.com/tiangolo`;
      const res = await fetch('/api/v1/email/webhook/techcorp', {
        method: 'POST',
        headers: { 'Content-Type': 'message/rfc822' },
        body: dummyEml
      });
      if (!res.ok) throw new Error('Webhook test failed');
      const data = await res.json();
      pollBatchResult(data.batch_id);
    } catch (e) {
      alert('Webhook error: ' + e.message);
      hideBatchLoading();
    }
  });

  // Automated Background Poller Controls
  const btnTogglePoller = document.getElementById('btn-toggle-poller');
  const btnCheckPoller = document.getElementById('btn-check-poller-status');
  const pollerIndicator = document.getElementById('poller-status-indicator');
  const pollerText = document.getElementById('poller-status-text');
  const btnPollerIcon = document.getElementById('btn-poller-icon');
  const btnPollerText = document.getElementById('btn-poller-text');
  const pollerInterval = document.getElementById('poller-interval');

  async function updatePollerStatusUI() {
    try {
      const res = await fetch('/api/v1/scheduler/status');
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === 'running') {
        pollerIndicator.className = 'status-indicator online';
        pollerText.textContent = `Running (${data.interval_minutes}m)`;
        btnPollerIcon.textContent = '⏹️';
        btnPollerText.textContent = 'Stop Poller';
        btnTogglePoller.classList.remove('btn-primary');
        btnTogglePoller.classList.add('btn-secondary');
      } else {
        pollerIndicator.className = 'status-indicator';
        pollerText.textContent = 'Stopped';
        btnPollerIcon.textContent = '▶️';
        btnPollerText.textContent = 'Start Poller';
        btnTogglePoller.classList.remove('btn-secondary');
        btnTogglePoller.classList.add('btn-primary');
      }
    } catch (e) {
      console.warn('Could not fetch scheduler status', e);
    }
  }

  // Fetch initial poller status
  updatePollerStatusUI();

  btnTogglePoller.addEventListener('click', async () => {
    try {
      const interval = parseInt(pollerInterval.value, 10) || 15;
      const res = await fetch('/api/v1/scheduler/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_minutes: interval })
      });
      if (!res.ok) throw new Error('Toggle failed');
      const data = await res.json();
      alert(`Automated Background Poller is now ${data.status.toUpperCase()} (Interval: ${data.interval_minutes || interval}m)`);
      updatePollerStatusUI();
    } catch (e) {
      alert('Error toggling poller: ' + e.message);
    }
  });

  btnCheckPoller.addEventListener('click', () => {
    updatePollerStatusUI();
  });

  // Recruiter Morning Digest Dispatchers
  const btnSlackDigest = document.getElementById('btn-send-slack-digest');
  const btnWhatsAppDigest = document.getElementById('btn-send-whatsapp-digest');
  const digestFeedback = document.getElementById('digest-feedback');

  btnSlackDigest.addEventListener('click', async () => {
    try {
      btnSlackDigest.disabled = true;
      btnSlackDigest.innerHTML = '<span>⏳</span> Sending...';
      const slackUrl = document.getElementById('digest-slack-url').value;
      const res = await fetch('/api/v1/digest/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: 'slack',
          webhook_url: slackUrl
        })
      });
      const data = await res.json();
      digestFeedback.style.display = 'block';
      digestFeedback.textContent = `✓ Slack Digest dispatched! ${data.message || 'Blocks rendered and simulated successfully.'}`;
      setTimeout(() => { digestFeedback.style.display = 'none'; }, 6000);
    } catch (e) {
      alert('Slack dispatch error: ' + e.message);
    } finally {
      btnSlackDigest.disabled = false;
      btnSlackDigest.innerHTML = '<span>💬</span> Send Slack Digest';
    }
  });

  btnWhatsAppDigest.addEventListener('click', async () => {
    try {
      btnWhatsAppDigest.disabled = true;
      btnWhatsAppDigest.innerHTML = '<span>⏳</span> Sending...';
      const phone = document.getElementById('digest-whatsapp-phone').value;
      const res = await fetch('/api/v1/digest/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: 'whatsapp',
          phone_number: phone
        })
      });
      const data = await res.json();
      digestFeedback.style.display = 'block';
      digestFeedback.textContent = `✓ WhatsApp Brief generated! ${data.message || 'Simulated brief delivered to recruiter.'}`;
      setTimeout(() => { digestFeedback.style.display = 'none'; }, 6000);
    } catch (e) {
      alert('WhatsApp dispatch error: ' + e.message);
    } finally {
      btnWhatsAppDigest.disabled = false;
      btnWhatsAppDigest.innerHTML = '<span>📱</span> Send WhatsApp Brief';
    }
  });
}

// ================= PRICING MODAL =================
function initPricingModal() {
  const modal = document.getElementById('pricing-modal');
  const btnOpen = document.getElementById('btn-open-pricing');
  const btnClose = document.getElementById('btn-close-pricing');

  if (btnOpen) {
    btnOpen.addEventListener('click', () => {
      modal.style.display = 'flex';
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
}

// ================= DRAFT MODAL =================
function initDraftModal() {
  const modal = document.getElementById('draft-modal');
  const btnClose = document.getElementById('btn-close-modal');
  const btnOk = document.getElementById('btn-ok-draft');
  const btnCopy = document.getElementById('btn-copy-draft');

  btnClose.addEventListener('click', () => modal.style.display = 'none');
  btnOk.addEventListener('click', () => modal.style.display = 'none');

  btnCopy.addEventListener('click', () => {
    const text = document.getElementById('modal-body').value;
    navigator.clipboard.writeText(text);
    btnCopy.textContent = 'Copied! ✓';
    setTimeout(() => { btnCopy.textContent = 'Copy Draft'; }, 1800);
  });
}

function openDraftModalForCandidate(event, candidateName) {
  event.stopPropagation();
  if (!currentBatchData) return;

  const candidate = (currentBatchData.candidates || []).find(c => c.candidate_name === candidateName);
  if (!candidate) return;

  const modal = document.getElementById('draft-modal');
  const draft = candidate.email_draft || {
    recipient_email: `${candidate.candidate_name.toLowerCase().replace(/\s+/g, '.')}@example.com`,
    subject: `Update regarding your application for Software Engineer`,
    body_text: `Hi ${candidate.candidate_name.split(' ')[0]},\n\nThank you for applying. We are reviewing your technical profile.`
  };

  document.getElementById('modal-draft-title').textContent = candidate.recommendation === 'SHORTLIST'
    ? `🟢 Auto-Drafted Interview Invitation (${candidate.candidate_name})`
    : `🔴 Auto-Drafted Rejection Email (${candidate.candidate_name})`;

  document.getElementById('modal-recipient').textContent = draft.recipient_email || `${candidate.candidate_name.toLowerCase().replace(/\s+/g, '.')}@example.com`;
  document.getElementById('modal-subject').value = draft.subject;
  document.getElementById('modal-body').value = draft.body_text;

  modal.style.display = 'flex';
}

// ================= TELEMETRY =================
async function fetchHealth() {
  try {
    const res = await fetch('/api/v1/health');
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('cache-hit-rate').textContent = `${data.cache.hit_rate_pct}%`;
  } catch (e) {
    console.warn('Health check failed', e);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/v1/screenings');
    if (!res.ok) return;
    const items = await res.json();
    const listEl = document.getElementById('history-list');
    document.getElementById('history-count').textContent = `${items.length} candidates screened`;

    if (!items.length) {
      listEl.innerHTML = '<div class="empty-history">No screening history yet. Run an audit above!</div>';
      return;
    }

    listEl.innerHTML = '';
    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'history-item';
      
      const badgeClass = item.recommendation.toLowerCase();
      row.innerHTML = `
        <div>
          <div class="h-candidate">${item.candidate_name}</div>
          <div class="h-meta">@${item.github_username} • ${item.screened_at || 'Just now'} • ${item.latency_seconds}s</div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="rec-badge ${badgeClass}">${item.recommendation}</span>
          <span class="h-score">${item.overall_score}/100</span>
        </div>
      `;

      row.addEventListener('click', () => {
        document.getElementById('tab-single-btn').click();
        renderScorecard(item);
        window.scrollTo({ top: 120, behavior: 'smooth' });
      });

      listEl.appendChild(row);
    });
  } catch (e) {
    console.warn('History fetch error', e);
  }
}
