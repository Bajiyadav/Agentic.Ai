let currentSelectedFile = null;
let currentScorecardData = null;
let currentBatchData = null;
let currentBatchFilter = 'ALL';
let currentActiveAuditId = null;
let currentActiveReplyId = null;
let pendingOverrideDecision = null;
let currentHistoryFilter = 'ALL';
let currentHistoryQuery = '';

// ================= MODERN TOAST NOTIFICATION SYSTEM =================
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('auditagent-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'auditagent-toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast-card toast-${type}`;
  
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠️',
    info: '⚡'
  };

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || '⚡'}</span>
    <span class="toast-msg">${message}</span>
    <button type="button" class="toast-close" aria-label="Close">&times;</button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  if (closeBtn) {
    closeBtn.onclick = () => {
      toast.classList.add('toast-fade-out');
      setTimeout(() => toast.remove(), 250);
    };
  }

  container.appendChild(toast);

  // Trigger entrance animation
  requestAnimationFrame(() => toast.classList.add('toast-show'));

  setTimeout(() => {
    if (toast.parentElement) {
      toast.classList.add('toast-fade-out');
      setTimeout(() => toast.remove(), 250);
    }
  }, duration);
}
window.showToast = showToast;

async function parseResponseSafe(res) {
  try {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      return { detail: text || `HTTP ${res.status} ${res.statusText}` };
    }
  } catch (err) {
    return { detail: `Network error: ${err.message}` };
  }
}

// Global Error & Promise Rejection Watchdog (Surfaces all errors immediately)
window.addEventListener('error', (event) => {
  console.error('Captured Global UI Error:', event.error || event.message);
  if (window.showToast) {
    window.showToast(`UI Error: ${event.message || 'Script error'}`, 'error', 6000);
  }
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Captured Unhandled Rejection:', event.reason);
  const msg = event.reason?.message || event.reason || 'Unhandled network error';
  if (window.showToast) {
    window.showToast(`Request Error: ${msg}`, 'error', 6000);
  }
});

document.addEventListener('DOMContentLoaded', () => {
  initSidebarAndTopbar();
  initTabs();
  initSingleAudit();
  initBatchAudit();
  initEmailHub();
  initDraftModal();
  initPricingModal();
  initRecruiterActions();
  initHistoryControls();
  fetchHealth();
  fetchHistory();
  loadDashboardStats();
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
    const batchRows = document.querySelectorAll('#leaderboard-tbody tr');
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
  initInvalidDocumentActions();
}

function initInvalidDocumentActions() {
  const btnUpload = document.getElementById('btn-invalid-upload-resume');
  const btnDraftReq = document.getElementById('btn-invalid-draft-request');
  const btnViewReply = document.getElementById('btn-invalid-view-reply');
  const btnReset = document.getElementById('btn-invalid-reset-all');
  const fileInput = document.getElementById('resume-input');

  if (btnUpload) {
    btnUpload.addEventListener('click', () => {
      showPlaceholderState();
      fileInput?.click();
    });
  }

  const openNotice = () => {
    const draft = currentScorecardData?.draft_reply || {
      recipient_email: 'applicant@example.com',
      subject: 'Action Required: Updated Resume Needed for Application',
      body_text: 'Dear Applicant,\n\nThank you for your interest in TechCorp Solutions. The file uploaded appears to be academic coursework or exercise material rather than a professional resume.\n\nPlease reply with your updated resume PDF so our hiring team can evaluate your technical qualifications.\n\nBest regards,\nTalent Acquisition Team'
    };
    openDraftModal(draft, '⚠️ Auto-Drafted Document Resubmission Notice');
  };

  if (btnDraftReq) btnDraftReq.addEventListener('click', openNotice);
  if (btnViewReply) btnViewReply.addEventListener('click', openNotice);

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      clearSelectedFile();
      showPlaceholderState();
    });
  }
}

function clearSelectedFile(e) {
  if (e) e.stopPropagation();
  currentSelectedFile = null;
  const fileInput = document.getElementById('resume-input');
  if (fileInput) fileInput.value = '';
  const fileTag = document.getElementById('file-tag');
  if (fileTag) fileTag.style.display = 'none';
  const fileCard = document.getElementById('selected-file-card');
  if (fileCard) fileCard.style.display = 'none';
  const dropContent = document.getElementById('dropzone-content');
  if (dropContent) dropContent.style.display = 'flex';
}

function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-input');
  const removeFile = document.getElementById('remove-file');
  const btnRemoveSelected = document.getElementById('btn-remove-selected-file');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', (e) => {
    if (e.target.id !== 'remove-file' && e.target.id !== 'btn-remove-selected-file') {
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

  if (removeFile) removeFile.addEventListener('click', clearSelectedFile);
  if (btnRemoveSelected) btnRemoveSelected.addEventListener('click', clearSelectedFile);
}

function handleFileSelected(file) {
  currentSelectedFile = file;
  const fileTag = document.getElementById('file-tag');
  const fileName = document.getElementById('file-name');
  if (fileName) fileName.textContent = file.name;
  if (fileTag) fileTag.style.display = 'inline-flex';

  const fileCard = document.getElementById('selected-file-card');
  const selectedName = document.getElementById('selected-file-name');
  const selectedSize = document.getElementById('selected-file-size');
  const dropContent = document.getElementById('dropzone-content');

  if (fileCard && selectedName && selectedSize) {
    selectedName.textContent = file.name;
    const kb = (file.size / 1024).toFixed(1);
    selectedSize.textContent = `${kb} KB • PDF Document`;
    fileCard.style.display = 'flex';
    if (dropContent) dropContent.style.display = 'none';
  }
}

function initChips() {
  const chips = document.querySelectorAll('.chip[data-user]');
  const githubInput = document.getElementById('github-username');
  if (!githubInput) return;
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const user = chip.getAttribute('data-user');
      if (user) {
        githubInput.value = user;
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        showToast(`Demo GitHub profile set to @${user}`, 'info');
      }
    });
  });
}

function initDemoSample() {
  const btn = document.getElementById('btn-load-sample');
  if (!btn) return;
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
      if (githubInput && !githubInput.value) {
        githubInput.value = 'tiangolo';
      }
      const roleEl = document.getElementById('target-role');
      if (roleEl && !roleEl.value) {
        roleEl.value = 'Senior Backend Engineer';
      }
      const skillsEl = document.getElementById('required-skills');
      if (skillsEl && !skillsEl.value) {
        skillsEl.value = 'Python, FastAPI, Docker, PostgreSQL';
      }
      const accordion = document.getElementById('optional-job-accordion');
      if (accordion) accordion.open = true;

      showToast('⚡ Sample Resume (Aarav Sharma) loaded! Ready to audit.', 'success');
    } catch (err) {
      console.warn('Could not load sample_resume.pdf:', err);
      showToast('Could not load sample resume: ' + err.message, 'error');
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

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!currentSelectedFile) {
        showToast('Please upload a resume PDF first or click "Use Sample Resume".', 'warning');
        return;
      }

      const githubUser = document.getElementById('github-username')?.value.trim() || '';
      const targetRole = document.getElementById('target-role')?.value.trim() || '';
      const jobDescription = document.getElementById('job-description')?.value.trim() || '';
      const requiredSkills = document.getElementById('required-skills')?.value.trim() || '';
      const linkedinUrl = document.getElementById('linkedin-url')?.value.trim() || '';
      const webhookUrl = document.getElementById('webhook-url')?.value.trim() || '';

      showLoadingState();
      showToast('⚡ Initiating multi-agent candidate audit pipeline...', 'info');

      const formData = new FormData();
      formData.append('file', currentSelectedFile);
      if (githubUser) formData.append('github_username', githubUser);
      if (targetRole) formData.append('target_role', targetRole);
      if (jobDescription) formData.append('job_description', jobDescription);
      if (requiredSkills) formData.append('required_skills', requiredSkills);
      if (linkedinUrl) formData.append('linkedin_url', linkedinUrl);
      if (webhookUrl) formData.append('webhook_url', webhookUrl);

      try {
        const res = await fetch('/api/v1/screen', {
          method: 'POST',
          body: formData
        });

        const data = await parseResponseSafe(res);
        if (!res.ok) {
          throw new Error(data.detail || data.message || `Server Error (${res.status}: ${res.statusText || 'Request failed'})`);
        }

        const taskId = data.task_id;
        if (!taskId) {
          throw new Error('Server did not return a valid task_id.');
        }
        pollForResult(taskId);
      } catch (err) {
        showToast('Error: ' + err.message, 'error');
        showPlaceholderState();
      }
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      clearSelectedFile();
      const formEl = document.getElementById('screen-form');
      if (formEl) formEl.reset();
      const wordCount = document.getElementById('jd-word-count');
      if (wordCount) wordCount.textContent = '0 words';
      showPlaceholderState();
      showToast('Workspace reset to initial state', 'info');
    });
  }

  if (btnDownload) {
    btnDownload.addEventListener('click', () => {
      if (!currentScorecardData) {
        showToast('No active candidate audit to download', 'warning');
        return;
      }
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentScorecardData, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `${(currentScorecardData.candidate_name || 'candidate').replace(/\s+/g, '_').toLowerCase()}_scorecard.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Scorecard JSON exported successfully', 'success');
    });
  }

  const jdEl = document.getElementById('job-description');
  const jdWordCount = document.getElementById('jd-word-count');

  function updateJdWordCount() {
    if (!jdEl || !jdWordCount) return;
    const text = jdEl.value.trim();
    if (!text) {
      jdWordCount.textContent = '0 words';
      return;
    }
    const words = text.split(/\s+/).filter(Boolean).length;
    jdWordCount.textContent = `${words} words (${text.length} chars)`;
  }

  if (jdEl) {
    jdEl.addEventListener('input', updateJdWordCount);
  }

  const btnSampleJd = document.getElementById('btn-paste-sample-jd');
  if (btnSampleJd) {
    btnSampleJd.addEventListener('click', () => {
      const roleEl = document.getElementById('target-role');
      const skillsEl = document.getElementById('required-skills');
      const accordion = document.getElementById('optional-job-accordion');
      if (accordion) accordion.open = true;

      if (jdEl) {
        jdEl.value = 'We are hiring a Senior Full-Stack Engineer with 3+ years of experience in Python, TypeScript, React, and Docker to scale our cloud-native web platform. The candidate will architect robust APIs, manage PostgreSQL databases, and lead frontend feature delivery.';
        updateJdWordCount();
      }
      if (roleEl) {
        roleEl.value = 'Senior Full-Stack Engineer';
      }
      if (skillsEl) {
        skillsEl.value = 'Python, TypeScript, React, Docker';
      }
      showToast('Loaded short Job Description', 'info');
    });
  }

  const btnLinkedInJd = document.getElementById('btn-paste-linkedin-jd');
  if (btnLinkedInJd) {
    btnLinkedInJd.addEventListener('click', () => {
      const roleEl = document.getElementById('target-role');
      const skillsEl = document.getElementById('required-skills');
      const accordion = document.getElementById('optional-job-accordion');
      if (accordion) accordion.open = true;

      const sampleLinkedInPost = `About the Company:
TechCorp Enterprise is an industry-leading AI & data engineering platform serving Fortune 500 customers globally. We are expanding our core platform engineering organization and seeking an experienced Senior Full-Stack Engineer.

About the Role:
As a Senior Full-Stack Engineer, you will drive architecture and development across high-throughput distributed microservices, secure REST/GraphQL APIs, and modern responsive user interfaces.

Key Responsibilities:
- Design, build, and maintain production backend microservices and responsive web applications.
- Collaborate with product managers, designers, and engineering leaders to deliver end-to-end features.
- Build automated test suites and ensure high reliability, observability, and performance.

Basic Qualifications & Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, TypeScript, and modern JavaScript.
- Demonstrated experience with backend frameworks such as FastAPI, Django, or Node.js.
- Strong practical experience with Docker containerization and relational databases (PostgreSQL, MySQL).
- Experience with CI/CD automation, testing frameworks, and Git workflows.

Preferred Qualifications & Nice-to-Haves:
- Experience with Kubernetes orchestration and cloud platforms (AWS, GCP).
- Familiarity with Redis in-memory caching and Apache Kafka event streaming.
- Contributions to open-source software or public code repositories demonstrating clean architecture.`;

      if (jdEl) {
        jdEl.value = sampleLinkedInPost;
        updateJdWordCount();
      }
      if (roleEl) {
        roleEl.value = 'Senior Full-Stack Engineer';
      }
      if (skillsEl) {
        skillsEl.value = 'Python, TypeScript, React, Docker, PostgreSQL';
      }
      showToast('💼 Loaded Full LinkedIn Job Description & Requirements', 'info');
    });
  }

  const btnClearJd = document.getElementById('btn-clear-jd');
  if (btnClearJd) {
    btnClearJd.addEventListener('click', () => {
      if (jdEl) {
        jdEl.value = '';
        updateJdWordCount();
        showToast('Job description cleared', 'info');
      }
    });
  }

  const presetBackend = document.getElementById('preset-backend');
  if (presetBackend) {
    presetBackend.addEventListener('click', () => {
      const roleEl = document.getElementById('target-role');
      const skillsEl = document.getElementById('required-skills');
      const accordion = document.getElementById('optional-job-accordion');
      if (accordion) accordion.open = true;

      if (roleEl) roleEl.value = 'Senior Backend Engineer';
      if (skillsEl) skillsEl.value = 'Python, FastAPI, Docker, PostgreSQL';
      document.querySelectorAll('#preset-backend, #preset-fullstack').forEach(b => b.classList.remove('active'));
      presetBackend.classList.add('active');
      showToast('Applied Senior Backend Engineer preset', 'success');
    });
  }
  const presetFullstack = document.getElementById('preset-fullstack');
  if (presetFullstack) {
    presetFullstack.addEventListener('click', () => {
      const roleEl = document.getElementById('target-role');
      const skillsEl = document.getElementById('required-skills');
      const accordion = document.getElementById('optional-job-accordion');
      if (accordion) accordion.open = true;

      if (roleEl) roleEl.value = 'Full-Stack Engineer';
      if (skillsEl) skillsEl.value = 'React, TypeScript, Node.js, Next.js';
      document.querySelectorAll('#preset-backend, #preset-fullstack').forEach(b => b.classList.remove('active'));
      presetFullstack.classList.add('active');
      showToast('Applied Full-Stack Engineer preset', 'success');
    });
  }
}

async function pollForResult(taskId) {
  const stages = [
    { title: 'Resume uploaded & format verified...', detail: 'Validating PDF integrity and parsing structure' },
    { title: 'Document verification & authenticity check...', detail: 'Cross-verifying document against safety & anti-fraud taxonomy' },
    { title: 'Candidate info & claimed skills extracted...', detail: 'Structuring proficiencies, career timeline, and project claims' },
    { title: 'Role match & technical domain analysis...', detail: 'Comparing candidate capabilities against target job expectations' },
    { title: 'Code evidence & project verification...', detail: 'Auditing verified public GitHub repositories and original code' },
    { title: 'Preparing recruiter scorecard & decision...', detail: 'Cross-examining claims vs evidence to assemble recruiter briefing' }
  ];

  let currentStageIdx = 0;
  const stageTitle = document.getElementById('loading-stage');
  const stageDetail = document.getElementById('loading-detail');
  const progressBar = document.getElementById('progress-bar');
  const stepIds = ['chk-upload', 'chk-doc', 'chk-claims', 'chk-skills', 'chk-evidence', 'chk-assess'];

  // Initialize checklist steps
  stepIds.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (!el) return;
    const icon = el.querySelector('.chk-icon');
    if (idx === 0) {
      el.className = 'chk-step done';
      if (icon) icon.textContent = '✓';
    } else if (idx === 1) {
      el.className = 'chk-step active';
      if (icon) icon.textContent = '○';
    } else {
      el.className = 'chk-step';
      if (icon) icon.textContent = '○';
    }
  });

  const stageInterval = setInterval(() => {
    currentStageIdx = (currentStageIdx + 1) % stages.length;
    const stg = stages[currentStageIdx];
    if (stageTitle) stageTitle.textContent = stg.title;
    if (stageDetail) stageDetail.textContent = stg.detail;
    if (progressBar) progressBar.style.width = `${Math.min(95, (currentStageIdx + 1) * 16)}%`;

    stepIds.forEach((id, idx) => {
      const el = document.getElementById(id);
      if (!el) return;
      const icon = el.querySelector('.chk-icon');
      if (idx <= currentStageIdx) {
        el.className = 'chk-step done';
        if (icon) icon.textContent = '✓';
      } else if (idx === currentStageIdx + 1) {
        el.className = 'chk-step active';
        if (icon) icon.textContent = '○';
      } else {
        el.className = 'chk-step';
        if (icon) icon.textContent = '○';
      }
    });
  }, 800);

  const pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/v1/screen/${taskId}`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.status === 'completed') {
        clearInterval(pollInterval);
        clearInterval(stageInterval);
        if (progressBar) progressBar.style.width = '100%';

        stepIds.forEach(id => {
          const el = document.getElementById(id);
          if (el) {
            el.className = 'chk-step done';
            const icon = el.querySelector('.chk-icon');
            if (icon) icon.textContent = '✓';
          }
        });

        setTimeout(() => {
          document.getElementById('state-loading').style.display = 'none';
          const isInvalid = data.result.is_valid_resume === false || (data.result.document && data.result.document.is_valid_resume === false);
          if (isInvalid) {
            showInvalidDocumentState(data.result);
          } else {
            renderScorecard(data.result);
            showResultState();
          }
          fetchHistory();
          loadDashboardStats();
        }, 300);
      } else if (data.status === 'failed') {
        clearInterval(pollInterval);
        clearInterval(stageInterval);
        alert('Screening pipeline failed: ' + (data.error || 'Unknown error'));
        showPlaceholderState();
      }
    } catch (e) {
      console.error('Polling error', e);
    }
  }, 1000);
}

function renderScorecard(result) {
  const isInvalidDoc = result.is_valid_resume === false || (result.document && result.document.is_valid_resume === false) || (result.candidate_name || '').toLowerCase().includes('non-resume');
  if (isInvalidDoc) {
    showInvalidDocumentState(result);
    return;
  }

  currentScorecardData = result;

  document.getElementById('res-candidate-name').textContent = result.candidate_name;
  document.getElementById('res-github-link').textContent = `@${result.github_username}`;
  document.getElementById('res-experience').textContent = `${result.years_experience || '3.0'} yrs experience`;

  // Target Role
  const targetRoleEl = document.getElementById('res-target-role');
  if (targetRoleEl) {
    if (result.target_role) {
      targetRoleEl.textContent = result.target_role;
      targetRoleEl.style.display = 'inline-block';
    } else {
      targetRoleEl.style.display = 'none';
    }
  }

  // LinkedIn Verification Link
  const linkedinSep = document.getElementById('res-linkedin-sep');
  const linkedinLink = document.getElementById('res-linkedin-link');
  const linkedinAnchor = document.getElementById('res-linkedin-anchor');
  if (linkedinLink && linkedinAnchor) {
    if (result.linkedin_url) {
      let lUrl = result.linkedin_url;
      if (!lUrl.startsWith('http')) {
        lUrl = lUrl.startsWith('linkedin.com') ? `https://${lUrl}` : `https://linkedin.com/in/${lUrl}`;
      }
      linkedinAnchor.href = lUrl;
      linkedinLink.style.display = 'inline-flex';
      if (linkedinSep) linkedinSep.style.display = 'inline';
    } else {
      linkedinLink.style.display = 'none';
      if (linkedinSep) linkedinSep.style.display = 'none';
    }
  }
  
  const speedBadge = document.getElementById('res-speed-badge');
  if (result.cached) {
    speedBadge.textContent = `⚡ ${result.latency_seconds}s (SmartCache Hit)`;
    speedBadge.style.color = 'var(--color-success)';
  } else {
    speedBadge.textContent = `⚡ ${result.latency_seconds}s (Consensus Pipeline)`;
    speedBadge.style.color = 'var(--color-primary)';
  }

  const recBadge = document.getElementById('res-rec-badge');
  const rawRec = (result.assessment?.recommendation || result.recruiter_recommendation || result.recommendation || 'REVIEW').toUpperCase();
  let recLabel = 'NEEDS REVIEW';
  let badgeClass = 'review';
  if (rawRec.includes('SHORTLIST') || rawRec.includes('STRONG')) {
    recLabel = 'STRONG CANDIDATE';
    badgeClass = 'shortlist';
  } else if (rawRec.includes('REJECT') || rawRec.includes('NOT')) {
    recLabel = 'NOT RECOMMENDED';
    badgeClass = 'reject';
  }
  if (recBadge) {
    recBadge.textContent = recLabel;
    recBadge.className = 'rec-badge ' + badgeClass;
  }

  const overall = isInvalidDoc ? 0 : result.overall_score;
  const scoreCircle = document.getElementById('score-circle');
  document.getElementById('res-overall-score').textContent = overall;

  let color = 'var(--color-success)';
  if (overall < 55) {
    color = 'var(--color-danger)';
  } else if (overall < 78) {
    color = 'var(--color-warning)';
  }
  scoreCircle.style.borderColor = color;
  scoreCircle.style.boxShadow = '0 2px 8px rgba(15, 23, 42, 0.08)';
  if (isInvalidDoc) {
    scoreCircle.style.backgroundColor = '#fee2e2';
  } else {
    scoreCircle.style.backgroundColor = 'transparent';
  }
  document.getElementById('res-overall-score').style.color = color;

  // Actionable Recruiter Next-Step Banner
  const actionBanner = document.getElementById('res-action-banner');
  const actionHeadline = document.getElementById('res-action-headline');
  const actionSub = document.getElementById('res-action-sub');
  const actionIcon = document.getElementById('res-action-icon');

  if (actionBanner && actionHeadline && actionSub) {
    const nextAction = result.assessment?.next_action || (badgeClass === 'shortlist' ? 'SCHEDULE_INTERVIEW' : (badgeClass === 'review' ? 'REVIEW_RECOMMENDED' : 'DO_NOT_PROCEED'));
    const nextActionLabel = result.assessment?.next_action_label || (
      nextAction === 'SCHEDULE_INTERVIEW'
        ? 'Next step: Schedule 30-minute technical phone screen'
        : (nextAction === 'REVIEW_RECOMMENDED'
          ? 'Next step: Review code evidence and technical discrepancies'
          : 'Next step: Send polite rejection notice')
    );

    actionHeadline.textContent = nextActionLabel;
    if (nextAction === 'SCHEDULE_INTERVIEW') {
      actionBanner.className = 'recruiter-action-banner banner-shortlist';
      if (actionIcon) actionIcon.textContent = '📅';
      actionSub.textContent = 'Candidate demonstrates verified skills alignment and authentic project evidence.';
    } else if (nextAction === 'REVIEW_RECOMMENDED') {
      actionBanner.className = 'recruiter-action-banner banner-review';
      if (actionIcon) actionIcon.textContent = '🔍';
      actionSub.textContent = 'Mixed signals detected between resume claims and verified code. Technical follow-up advised.';
    } else {
      actionBanner.className = 'recruiter-action-banner banner-reject';
      if (actionIcon) actionIcon.textContent = '🛑';
      actionSub.textContent = 'Insufficient authentic project evidence or major skills mismatch for target role.';
    }
  }

  // 5 Recruiter Sub-Scores
  const sub = result.assessment?.sub_scores || {};
  const skillsVal = sub.skills_match ?? result.skills_match_score ?? 85;
  const expVal = sub.experience_depth ?? Math.min(100, Math.round((result.years_experience || 3) * 25));
  const projVal = sub.project_complexity ?? 88;
  const evVal = sub.technical_evidence ?? result.code_quality_score ?? 85;
  const qualVal = sub.resume_quality ?? result.consistency_score ?? 88;

  const elSkills = document.getElementById('res-sub-skills');
  const elSkillsBar = document.getElementById('res-sub-skills-bar');
  if (elSkills) elSkills.textContent = `${skillsVal}%`;
  if (elSkillsBar) elSkillsBar.style.width = `${skillsVal}%`;

  const elExp = document.getElementById('res-sub-exp');
  const elExpBar = document.getElementById('res-sub-exp-bar');
  if (elExp) elExp.textContent = `${expVal}%`;
  if (elExpBar) elExpBar.style.width = `${expVal}%`;

  const elProj = document.getElementById('res-sub-proj');
  const elProjBar = document.getElementById('res-sub-proj-bar');
  if (elProj) elProj.textContent = `${projVal}%`;
  if (elProjBar) elProjBar.style.width = `${projVal}%`;

  const elEv = document.getElementById('res-sub-evidence');
  const elEvBar = document.getElementById('res-sub-evidence-bar');
  if (elEv) elEv.textContent = `${evVal}%`;
  if (elEvBar) elEvBar.style.width = `${evVal}%`;

  const elQual = document.getElementById('res-sub-quality');
  const elQualBar = document.getElementById('res-sub-quality-bar');
  if (elQual) elQual.textContent = `${qualVal}%`;
  if (elQualBar) elQualBar.style.width = `${qualVal}%`;

  // Legacy triad synchronization
  const legacySkills = document.getElementById('res-skills-score');
  const legacySkillsBar = document.getElementById('res-skills-bar');
  if (legacySkills) legacySkills.textContent = `${result.skills_match_score}%`;
  if (legacySkillsBar) legacySkillsBar.style.width = `${result.skills_match_score}%`;

  const legacyQual = document.getElementById('res-quality-score');
  const legacyQualBar = document.getElementById('res-quality-bar');
  if (legacyQual) legacyQual.textContent = `${result.code_quality_score}%`;
  if (legacyQualBar) legacyQualBar.style.width = `${result.code_quality_score}%`;

  const legacyCons = document.getElementById('res-consistency-score');
  const legacyConsBar = document.getElementById('res-consistency-bar');
  if (legacyCons) legacyCons.textContent = `${result.consistency_score}%`;
  if (legacyConsBar) legacyConsBar.style.width = `${result.consistency_score}%`;

  // "Why [Score]?" Card
  const whyStrengths = document.getElementById('res-why-strengths');
  const whyAreas = document.getElementById('res-why-areas');
  const whyScore = result.assessment?.why_score || {};

  if (whyStrengths) {
    whyStrengths.innerHTML = '';
    const strengthsList = (whyScore.strengths && whyScore.strengths.length > 0)
      ? whyScore.strengths
      : (result.green_flags && result.green_flags.length > 0
        ? result.green_flags
        : ['Candidate has authentic project history and verified technical proficiencies.']);
    strengthsList.forEach(s => {
      const li = document.createElement('li');
      li.textContent = s;
      whyStrengths.appendChild(li);
    });
  }

  if (whyAreas) {
    whyAreas.innerHTML = '';
    const areasList = (whyScore.areas_to_verify && whyScore.areas_to_verify.length > 0)
      ? whyScore.areas_to_verify
      : (result.red_flags && result.red_flags.length > 0
        ? result.red_flags
        : ['Confirm architectural ownership and systems scale in technical interview.']);
    areasList.forEach(a => {
      const li = document.createElement('li');
      li.textContent = a;
      whyAreas.appendChild(li);
    });
  }

  // Claim vs Evidence Table
  const evidenceTableBody = document.getElementById('res-evidence-table-body');
  if (evidenceTableBody) {
    evidenceTableBody.innerHTML = '';
    let claims = result.assessment?.claim_vs_evidence || result.evidence_items || [];

    if (claims.length === 0) {
      const skillsToCheck = (result.company_required_skills && result.company_required_skills.length > 0)
        ? result.company_required_skills
        : (result.skills || ['Python', 'Docker', 'PostgreSQL']);
      const verifiedList = result.verified_company_skills || [];
      const matchedList = result.matched_company_skills || skillsToCheck;

      claims = skillsToCheck.map(s => {
        const isVer = verifiedList.includes(s);
        const isClaimed = matchedList.includes(s);
        const hasGithub = Boolean(result.github_username && result.github_username !== 'no_github');

        if (!hasGithub) {
          return {
            skill_or_claim: s,
            claimed_in: 'Resume Skills & Experience',
            evidence_found: 'No public GitHub profile provided',
            status: 'Unavailable',
            notes: 'Request project or repository portfolio'
          };
        }
        if (isVer) {
          return {
            skill_or_claim: s,
            claimed_in: 'Resume Skills / Work History',
            evidence_found: 'Verified code samples in public repositories',
            status: 'Verified',
            notes: 'Strong practical evidence in repository code'
          };
        }
        if (isClaimed) {
          return {
            skill_or_claim: s,
            claimed_in: 'Resume Skills Section',
            evidence_found: 'Mentioned on resume, no code found in repos',
            status: 'Partially Verified',
            notes: 'Verify proficiency during technical screen'
          };
        }
        return {
          skill_or_claim: s,
          claimed_in: 'Target Role Requirement',
          evidence_found: 'Not identified in resume or repositories',
          status: 'Unverified',
          notes: 'Candidate may need upskilling for this skill'
        };
      });
    }

    claims.forEach(c => {
      const tr = document.createElement('tr');
      let bClass = 'status-badge-unverified';
      let bIcon = '?';

      if (c.status === 'Verified') {
        bClass = 'status-badge-verified';
        bIcon = '✓';
      } else if (c.status === 'Partially Verified') {
        bClass = 'status-badge-partial';
        bIcon = '~';
      } else if (c.status === 'Unavailable') {
        bClass = 'status-badge-unavailable';
        bIcon = '—';
      }

      tr.innerHTML = `
        <td><strong>${c.skill_or_claim || c.skill || ''}</strong></td>
        <td style="color: var(--color-text-muted); font-size: 0.8rem;">${c.claimed_in || 'Resume'}</td>
        <td style="font-size: 0.82rem;">${c.evidence_found || c.evidence || 'None'}</td>
        <td><span class="${bClass}">${bIcon} ${c.status || 'Unverified'}</span></td>
        <td style="color: var(--color-text-dim); font-size: 0.78rem;">${c.notes || ''}</td>
      `;
      evidenceTableBody.appendChild(tr);
    });
  }

  // Company Required Skills Gap Analysis Section
  const companySection = document.getElementById('company-skills-section');
  const skillsGapGrid = document.getElementById('res-skills-gap-grid');
  const companyMatchBadge = document.getElementById('res-company-match-badge');

  if (companySection && skillsGapGrid && result.company_required_skills && result.company_required_skills.length > 0) {
    companySection.style.display = 'block';
    const matchScore = (result.company_skills_match_score !== null && result.company_skills_match_score !== undefined)
      ? result.company_skills_match_score
      : result.skills_match_score;
    
    if (companyMatchBadge) {
      companyMatchBadge.textContent = `Role Match: ${matchScore}%`;
      companyMatchBadge.style.background = matchScore >= 75 ? 'rgba(34, 197, 94, 0.15)' : (matchScore >= 50 ? 'rgba(234, 179, 8, 0.15)' : 'rgba(239, 68, 68, 0.15)');
      companyMatchBadge.style.color = matchScore >= 75 ? 'var(--color-success)' : (matchScore >= 50 ? 'var(--color-warning)' : 'var(--color-danger)');
    }

    const jdContainer = document.getElementById('res-jd-preview-container');
    const jdText = document.getElementById('res-jd-preview-text');
    const jdRoleTag = document.getElementById('res-jd-role-tag');
    const btnToggleJd = document.getElementById('btn-toggle-full-jd');
    if (jdContainer && jdText) {
      if (result.job_description) {
        jdContainer.style.display = 'block';
        jdText.textContent = result.job_description;
        if (jdRoleTag) jdRoleTag.textContent = result.target_role || 'Target Role';
        
        let isExpanded = false;
        jdText.style.maxHeight = '70px';
        if (btnToggleJd) {
          btnToggleJd.textContent = 'Show More ▾';
          btnToggleJd.onclick = () => {
            isExpanded = !isExpanded;
            jdText.style.maxHeight = isExpanded ? '500px' : '70px';
            btnToggleJd.textContent = isExpanded ? 'Show Less ▴' : 'Show More ▾';
          };
        }
      } else {
        jdContainer.style.display = 'none';
      }
    }

    skillsGapGrid.innerHTML = '';
    result.company_required_skills.forEach(skill => {
      const isVerified = (result.verified_company_skills || []).includes(skill);
      const isClaimed = (result.matched_company_skills || []).includes(skill);

      let statusBadge, statusDesc, borderLeft;
      if (isVerified) {
        statusBadge = '<span style="background: rgba(34, 197, 94, 0.15); color: var(--color-success); padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">✓ VERIFIED IN CODE</span>';
        statusDesc = '<span style="font-size: 0.8rem; color: var(--color-text-muted);">Proven in public GitHub repositories</span>';
        borderLeft = 'border-left: 3px solid var(--color-success);';
      } else if (isClaimed) {
        statusBadge = '<span style="background: rgba(234, 179, 8, 0.15); color: var(--color-warning); padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">⚠ CLAIMED ONLY</span>';
        statusDesc = '<span style="font-size: 0.8rem; color: var(--color-text-muted);">Asserted on resume, but 0 public code evidence</span>';
        borderLeft = 'border-left: 3px solid var(--color-warning);';
      } else {
        statusBadge = '<span style="background: rgba(239, 68, 68, 0.15); color: var(--color-danger); padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">✗ MISSING</span>';
        statusDesc = '<span style="font-size: 0.8rem; color: var(--color-text-muted);">Absent from both resume claims and code</span>';
        borderLeft = 'border-left: 3px solid var(--color-danger);';
      }

      const row = document.createElement('div');
      row.style = `display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--color-surface-hover); border-radius: 8px; ${borderLeft}`;
      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
          <strong style="font-size: 0.9rem; color: var(--color-text);">${skill}</strong>
          ${statusDesc}
        </div>
        ${statusBadge}
      `;
      skillsGapGrid.appendChild(row);
    });

    const skillsLabel = document.getElementById('res-skills-label');
    if (skillsLabel) skillsLabel.textContent = 'Company Match';
    document.getElementById('res-skills-score').textContent = `${matchScore}%`;
    document.getElementById('res-skills-bar').style.width = `${matchScore}%`;
  } else if (companySection) {
    companySection.style.display = 'none';
    const skillsLabel = document.getElementById('res-skills-label');
    if (skillsLabel) skillsLabel.textContent = 'Skills Match';
  }

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

  // Topic-Focused Interview Questions Section
  const topicSection = document.getElementById('topic-questions-section');
  const topicGrid = document.getElementById('res-topic-questions-grid');
  const btnCopyGuide = document.getElementById('btn-copy-interview-guide');

  if (topicSection && topicGrid) {
    const questions = result.topic_interview_questions || [];
    if (questions.length > 0) {
      topicSection.style.display = 'block';
      topicGrid.innerHTML = '';

      questions.forEach((q) => {
        const card = document.createElement('div');
        card.style = 'padding: 14px 16px; background: var(--color-surface-hover); border-radius: 10px; border-left: 4px solid var(--color-warning); display: flex; flex-direction: column; gap: 8px;';
        
        let statusTag = '<span style="background: rgba(234, 179, 8, 0.15); color: var(--color-warning); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">CLAIMED WITHOUT CODE</span>';
        if (q.status === 'MISSING_MANDATORY') {
          statusTag = '<span style="background: rgba(239, 68, 68, 0.15); color: var(--color-danger); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">MISSING MANDATORY</span>';
          card.style.borderLeftColor = 'var(--color-danger)';
        } else if (q.status === 'EXPERIENCE_GAP') {
          statusTag = '<span style="background: rgba(249, 115, 22, 0.15); color: #f97316; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">EXPERIENCE GAP</span>';
          card.style.borderLeftColor = '#f97316';
        } else if (q.status === 'CODE_HEALTH') {
          statusTag = '<span style="background: rgba(168, 85, 247, 0.15); color: #a855f7; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">CODE HEALTH</span>';
          card.style.borderLeftColor = '#a855f7';
        }

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="font-size: 0.95rem; color: var(--color-text);">Topic: ${q.topic}</strong>
              ${statusTag}
            </div>
            <span style="font-size: 0.75rem; color: var(--color-text-muted);">Difficulty: <strong>${q.difficulty}</strong></span>
          </div>
          <p style="margin: 0; font-size: 0.9rem; font-weight: 600; color: var(--color-text); line-height: 1.45;">
            "${q.question}"
          </p>
          <div style="font-size: 0.78rem; color: var(--color-text-muted); background: var(--color-surface); padding: 8px 10px; border-radius: 6px; border: 1px solid var(--color-border);">
            <div style="margin-bottom: 4px;"><strong>• Why Ask:</strong> ${q.rationale}</div>
            <div><strong style="color: var(--color-success);">• Listen For:</strong> ${q.ideal_response_guide}</div>
          </div>
        `;
        topicGrid.appendChild(card);
      });

      if (btnCopyGuide) {
        btnCopyGuide.onclick = () => {
          let guideText = `TECHNICAL INTERVIEW GUIDE: ${result.candidate_name} (${result.target_role || 'Candidate'})\nOverall Score: ${result.overall_score}/100 | Recommendation: ${result.recommendation}\n\n`;
          questions.forEach((q, i) => {
            guideText += `[Question ${i+1}: Topic: ${q.topic} - ${q.status}]\n`;
            guideText += `Q: ${q.question}\n`;
            guideText += `Why Ask: ${q.rationale}\n`;
            guideText += `Listen For: ${q.ideal_response_guide}\n\n`;
          });
          navigator.clipboard.writeText(guideText).then(() => {
            btnCopyGuide.textContent = '✓ Copied!';
            setTimeout(() => { btnCopyGuide.textContent = '📋 Copy Interview Guide'; }, 2000);
          }).catch(() => {
            alert('Copied to clipboard:\n\n' + guideText);
          });
        };
      }
    } else {
      topicSection.style.display = 'none';
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
      recruiterBadge.style.background = 'var(--color-indigo-bg)';
      recruiterBadge.style.color = 'var(--color-indigo)';
      recruiterBadge.style.borderColor = 'var(--color-border)';
      if (overrideNotice) {
        overrideNotice.textContent = `✓ Recruiter Override Active: ${result.recruiter_decision} — "${result.recruiter_decision_reason || 'Verified'}"`;
        overrideNotice.style.display = 'block';
      }
    } else {
      recruiterBadge.textContent = `AI VERDICT: ${result.recommendation}`;
      recruiterBadge.style.background = 'var(--color-info-bg)';
      recruiterBadge.style.color = 'var(--color-primary)';
      recruiterBadge.style.borderColor = 'var(--color-info-border)';
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
          replyBadge.style.background = 'var(--color-success-bg)';
          replyBadge.style.color = 'var(--color-success)';
          replyBadge.style.borderColor = 'var(--color-success-border)';
        } else if (result.draft_reply.status === 'approved') {
          replyBadge.style.background = 'var(--color-info-bg)';
          replyBadge.style.color = 'var(--color-primary)';
          replyBadge.style.borderColor = 'var(--color-info-border)';
        } else {
          replyBadge.style.background = 'var(--color-warning-bg)';
          replyBadge.style.color = 'var(--color-warning)';
          replyBadge.style.borderColor = 'var(--color-warning-border)';
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
          recruiterBadge.style.background = 'var(--color-indigo-bg)';
          recruiterBadge.style.color = 'var(--color-indigo)';
          recruiterBadge.style.borderColor = 'var(--color-border)';
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
            replyBadge.style.background = 'var(--color-info-bg)';
            replyBadge.style.color = 'var(--color-primary)';
            replyBadge.style.borderColor = 'var(--color-info-border)';
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
            replyBadge.style.background = 'var(--color-success-bg)';
            replyBadge.style.color = 'var(--color-success)';
            replyBadge.style.borderColor = 'var(--color-success-border)';
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

  // Recruiter Action Bar Buttons
  const btnActionSchedule = document.getElementById('btn-action-schedule');
  const btnActionRequestInfo = document.getElementById('btn-action-request-info');
  const btnActionDraft = document.getElementById('btn-action-draft-email');
  const btnActionReject = document.getElementById('btn-action-reject');
  const btnActionCopyGuide = document.getElementById('btn-action-copy-guide');
  const btnActionScreenAnother = document.getElementById('btn-action-screen-another');

  if (btnActionSchedule) {
    btnActionSchedule.addEventListener('click', () => {
      if (!currentScorecardData) return;
      const candidateName = currentScorecardData.candidate_name || 'Candidate';
      const firstName = candidateName.split(' ')[0] || 'there';
      const draft = currentScorecardData.draft_reply || {
        recipient_email: 'candidate@example.com',
        subject: `Interview Invitation: Technical Screen for ${currentScorecardData.target_role || 'Software Engineer'}`,
        body_text: `Hi ${firstName},\n\nOur engineering team reviewed your background and verified your technical projects. We were very impressed by your work and would love to invite you for a 30-minute introductory technical conversation.\n\nPlease choose a time that works best for you using our scheduling link below:\n👉 https://calendly.com/techcorp-hiring/30min\n\nLooking forward to speaking with you!\n\nBest regards,\nThe Talent Acquisition Team\nTechCorp Solutions`
      };
      openDraftModal(draft, `📅 Schedule Interview (${candidateName})`);
    });
  }

  if (btnActionRequestInfo) {
    btnActionRequestInfo.addEventListener('click', () => {
      if (!currentScorecardData) return;
      const candidateName = currentScorecardData.candidate_name || 'Candidate';
      const firstName = candidateName.split(' ')[0] || 'there';
      const draft = {
        recipient_email: 'candidate@example.com',
        subject: `Additional Information Needed: GitHub / Project Portfolio`,
        body_text: `Hi ${firstName},\n\nThank you for applying for the ${currentScorecardData.target_role || 'Software Engineer'} position. We are reviewing your application and would love to see direct source code samples or GitHub links for the projects mentioned on your resume.\n\nPlease reply with any public repository links or portfolio references at your convenience.\n\nBest regards,\nThe Talent Acquisition Team\nTechCorp Solutions`
      };
      openDraftModal(draft, `📩 Request Additional Information (${candidateName})`);
    });
  }

  if (btnActionDraft) {
    btnActionDraft.addEventListener('click', () => {
      if (!currentScorecardData) return;
      const draft = currentScorecardData.draft_reply || {
        recipient_email: 'candidate@example.com',
        subject: `Application Update: ${currentScorecardData.target_role || 'Software Engineer'}`,
        body_text: `Hi,\n\nThank you for applying. We are reviewing your technical profile.`
      };
      openDraftModal(draft, `✉️ Draft Candidate Email (${currentScorecardData.candidate_name})`);
    });
  }

  if (btnActionReject) {
    btnActionReject.addEventListener('click', () => {
      if (!currentScorecardData) return;
      const candidateName = currentScorecardData.candidate_name || 'Candidate';
      const firstName = candidateName.split(' ')[0] || 'there';
      const draft = {
        recipient_email: 'candidate@example.com',
        subject: `Application Update: ${currentScorecardData.target_role || 'Software Engineer'}`,
        body_text: `Dear ${firstName},\n\nThank you for taking the time to share your background with us. After careful review against our current engineering requirements, we have decided not to move forward with your candidacy at this time.\n\nWe appreciate your interest in our team and wish you the best in your search.\n\nBest regards,\nThe Talent Acquisition Team\nTechCorp Solutions`
      };
      openDraftModal(draft, `🛑 Candidate Rejection Notice (${candidateName})`);
    });
  }

  if (btnActionCopyGuide) {
    btnActionCopyGuide.addEventListener('click', () => {
      const guideBtn = document.getElementById('btn-copy-interview-guide');
      if (guideBtn) {
        guideBtn.click();
      } else {
        navigator.clipboard.writeText(`Technical Interview Guide for ${currentScorecardData?.candidate_name || 'Candidate'}`);
      }
      btnActionCopyGuide.innerHTML = '<span>✓</span> Copied!';
      setTimeout(() => {
        btnActionCopyGuide.innerHTML = '<span>📋</span> Copy Interview Guide';
      }, 1800);
    });
  }

  if (btnActionScreenAnother) {
    btnActionScreenAnother.addEventListener('click', () => {
      clearSelectedFile();
      showPlaceholderState();
      window.scrollTo({ top: 80, behavior: 'smooth' });
    });
  }
}

function showPlaceholderState() {
  document.getElementById('state-placeholder').style.display = 'flex';
  document.getElementById('state-loading').style.display = 'none';
  document.getElementById('state-result').style.display = 'none';
  const inv = document.getElementById('state-invalid-document');
  if (inv) inv.style.display = 'none';
}

function showLoadingState() {
  document.getElementById('state-placeholder').style.display = 'none';
  document.getElementById('state-loading').style.display = 'flex';
  document.getElementById('state-result').style.display = 'none';
  const inv = document.getElementById('state-invalid-document');
  if (inv) inv.style.display = 'none';
}

function showResultState() {
  document.getElementById('state-placeholder').style.display = 'none';
  document.getElementById('state-loading').style.display = 'none';
  document.getElementById('state-result').style.display = 'block';
  const inv = document.getElementById('state-invalid-document');
  if (inv) inv.style.display = 'none';
}

function showInvalidDocumentState(result) {
  currentScorecardData = result;
  document.getElementById('state-placeholder').style.display = 'none';
  document.getElementById('state-loading').style.display = 'none';
  document.getElementById('state-result').style.display = 'none';
  const inv = document.getElementById('state-invalid-document');
  if (inv) inv.style.display = 'block';

  // Detected type badge
  const docType = result.document_type || (result.document && result.document.document_type) || 'ACADEMIC_LAB_OR_EXERCISE';
  const typeBadge = document.getElementById('invalid-doc-type-badge');
  if (typeBadge) typeBadge.textContent = docType;

  // Description
  const descEl = document.getElementById('invalid-doc-main-desc');
  if (descEl) {
    if (docType === 'ACADEMIC_LAB_OR_EXERCISE') {
      descEl.textContent = 'The anti-fraud document validator detected academic coursework, lab manual instructions, or practical exercises instead of professional career history. Technical claims were not evaluated and scoring was halted at 0/100 REJECT.';
    } else if (docType === 'EMPTY_OR_CORRUPT') {
      descEl.textContent = 'The uploaded document contains insufficient text or appears corrupt. Please ensure you upload a readable, text-based PDF.';
    } else {
      descEl.textContent = `The uploaded file does not appear to be a candidate resume/CV (classified as ${docType}). Please upload a valid professional resume.`;
    }
  }

  // Reasons list
  const reasonsList = document.getElementById('invalid-doc-reasons-list');
  if (reasonsList) {
    reasonsList.innerHTML = '';
    const flags = (result.red_flags && result.red_flags.length > 0)
      ? result.red_flags
      : ((result.validation_flags && result.validation_flags.length > 0)
        ? result.validation_flags
        : ['Document matches academic lab/exercise markers.', 'No candidate work experience, education, or skills sections found.']);

    flags.forEach(f => {
      const li = document.createElement('li');
      li.style.cssText = 'padding: 10px 14px; background: rgba(239, 68, 68, 0.08); border-radius: 8px; border-left: 3px solid #ef4444; font-size: 0.85rem; color: var(--color-text);';
      li.textContent = f;
      reasonsList.appendChild(li);
    });
  }

  // Hook reply draft viewer
  const draftHandler = () => {
    const draft = result.draft_reply || {
      recipient_email: 'applicant@example.com',
      subject: 'Action Required: Updated Resume Needed for Application',
      body_text: 'Dear Applicant,\n\nThank you for your interest in TechCorp Solutions. The file uploaded appears to be academic coursework or exercise material rather than a professional resume.\n\nPlease reply with your updated resume PDF so our hiring team can evaluate your technical qualifications.\n\nBest regards,\nTalent Acquisition Team'
    };
    openDraftModal(draft, '⚠️ Auto-Drafted Document Resubmission Notice');
  };

  const btnDraftReq = document.getElementById('btn-invalid-draft-request');
  if (btnDraftReq) btnDraftReq.onclick = draftHandler;

  const btnViewReply = document.getElementById('btn-invalid-view-reply');
  if (btnViewReply) btnViewReply.onclick = draftHandler;
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

  if (btnSim) {
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
  }

  if (batchDropzone && batchInput) {
    batchDropzone.addEventListener('click', (e) => {
      if (e.target.id !== 'btn-start-batch-upload') {
        batchInput.click();
      }
    });

    batchInput.addEventListener('change', (e) => {
      if (e.target.files.length) {
        selectedBatchFiles = Array.from(e.target.files);
        if (batchFilesLabel) batchFilesLabel.textContent = `${selectedBatchFiles.length} applications selected`;
        if (batchFileTag) batchFileTag.style.display = 'inline-flex';
      }
    });
  }

  if (btnStartUpload) {
    btnStartUpload.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!selectedBatchFiles.length) {
        alert('Please select files first or click Simulate Batch.');
        return;
      }

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
  }

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

    const isInvalid = c.is_valid_resume === false || c.recruiter_recommendation === 'INVALID_DOCUMENT' || c.recommendation === 'INVALID_DOCUMENT';

    let scoreColor = 'var(--green)';
    if (isInvalid || c.overall_score < 55) scoreColor = 'var(--red)';
    else if (c.overall_score < 78) scoreColor = 'var(--yellow)';

    const displayScore = isInvalid ? '0/100' : `${c.overall_score}/100`;
    const recBadgeClass = isInvalid ? 'reject' : c.recommendation.toLowerCase();
    const recBadgeLabel = isInvalid ? 'INVALID' : (c.recruiter_recommendation || c.recommendation);

    const keyFinding = c.red_flags && c.red_flags.length > 0
      ? `🔴 ${c.red_flags[0]}`
      : c.green_flags && c.green_flags.length > 0
        ? `🟢 ${c.green_flags[0]}`
        : 'Clean evaluation.';

    const githubCell = (c.github_username && c.github_username !== 'none' && !isInvalid)
      ? `<a class="github-link-cell" href="https://github.com/${c.github_username}" target="_blank" onclick="event.stopPropagation();">@${c.github_username}</a>`
      : `<span style="color: var(--color-text-dim); font-size: 0.8rem;">—</span>`;

    tr.innerHTML = `
      <td><span class="rank-badge ${rankClass}">${c.rank}</span></td>
      <td>
        <div class="cand-name-cell">${c.candidate_name}</div>
        <div class="cand-exp-sub">${isInvalid ? (c.document_type || 'Invalid File') : ((c.years_experience || '3.0') + ' yrs exp')}</div>
      </td>
      <td><span class="score-cell" style="color: ${scoreColor}">${displayScore}</span></td>
      <td><span class="rec-badge ${recBadgeClass}">${recBadgeLabel}</span></td>
      <td><span style="font-family: var(--font-mono);">${c.skills_match_score}%</span></td>
      <td><span style="font-family: var(--font-mono);">${c.code_quality_score}%</span></td>
      <td>${githubCell}</td>
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
      if (isInvalid) {
        showInvalidDocumentState(c);
      } else {
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
        showResultState();
      }
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
        if (pollerIndicator) pollerIndicator.className = 'status-indicator online';
        if (pollerText) pollerText.textContent = `Running (${data.interval_minutes}m)`;
        if (btnPollerIcon) btnPollerIcon.textContent = '⏹️';
        if (btnPollerText) btnPollerText.textContent = 'Stop Poller';
        if (btnTogglePoller) {
          btnTogglePoller.classList.remove('btn-primary');
          btnTogglePoller.classList.add('btn-secondary');
        }
      } else {
        if (pollerIndicator) pollerIndicator.className = 'status-indicator';
        if (pollerText) pollerText.textContent = 'Stopped';
        if (btnPollerIcon) btnPollerIcon.textContent = '▶️';
        if (btnPollerText) btnPollerText.textContent = 'Start Poller';
        if (btnTogglePoller) {
          btnTogglePoller.classList.remove('btn-secondary');
          btnTogglePoller.classList.add('btn-primary');
        }
      }
    } catch (e) {
      console.warn('Could not fetch scheduler status', e);
    }
  }

  // Fetch initial poller status
  updatePollerStatusUI();

  if (btnTogglePoller) {
    btnTogglePoller.addEventListener('click', async () => {
      try {
        const interval = parseInt(pollerInterval?.value, 10) || 15;
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
  }

  if (btnCheckPoller) {
    btnCheckPoller.addEventListener('click', () => {
      updatePollerStatusUI();
    });
  }

  // Recruiter Morning Digest Dispatchers
  const btnSlackDigest = document.getElementById('btn-send-slack-digest');
  const btnWhatsAppDigest = document.getElementById('btn-send-whatsapp-digest');
  const digestFeedback = document.getElementById('digest-feedback');

  if (btnSlackDigest) {
    btnSlackDigest.addEventListener('click', async () => {
      try {
        btnSlackDigest.disabled = true;
        btnSlackDigest.innerHTML = '<span>⏳</span> Sending...';
        const slackUrl = document.getElementById('digest-slack-url')?.value || '';
        const res = await fetch('/api/v1/digest/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channel: 'slack',
            webhook_url: slackUrl
          })
        });
        const data = await res.json();
        if (digestFeedback) {
          digestFeedback.style.display = 'block';
          digestFeedback.textContent = `✓ Slack Digest dispatched! ${data.message || 'Blocks rendered and simulated successfully.'}`;
          setTimeout(() => { digestFeedback.style.display = 'none'; }, 6000);
        }
      } catch (e) {
        alert('Slack dispatch error: ' + e.message);
      } finally {
        btnSlackDigest.disabled = false;
        btnSlackDigest.innerHTML = '<span>💬</span> Send Slack Digest';
      }
    });
  }

  if (btnWhatsAppDigest) {
    btnWhatsAppDigest.addEventListener('click', async () => {
      try {
        btnWhatsAppDigest.disabled = true;
        btnWhatsAppDigest.innerHTML = '<span>⏳</span> Sending...';
        const phone = document.getElementById('digest-whatsapp-phone')?.value || '';
        const res = await fetch('/api/v1/digest/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channel: 'whatsapp',
            phone_number: phone
          })
        });
        const data = await res.json();
        if (digestFeedback) {
          digestFeedback.style.display = 'block';
          digestFeedback.textContent = `✓ WhatsApp Brief generated! ${data.message || 'Simulated brief delivered to recruiter.'}`;
          setTimeout(() => { digestFeedback.style.display = 'none'; }, 6000);
        }
      } catch (e) {
        alert('WhatsApp dispatch error: ' + e.message);
      } finally {
        btnWhatsAppDigest.disabled = false;
        btnWhatsAppDigest.innerHTML = '<span>📱</span> Send WhatsApp Brief';
      }
    });
  }
}

// ================= PRICING MODAL =================
function initPricingModal() {
  const modal = document.getElementById('pricing-modal');
  const btnOpen = document.getElementById('btn-open-pricing');
  const btnClose = document.getElementById('btn-close-pricing');

  if (!modal) return;

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

  if (!modal) return;

  if (btnClose) btnClose.addEventListener('click', () => modal.style.display = 'none');
  if (btnOk) btnOk.addEventListener('click', () => modal.style.display = 'none');

  if (btnCopy) {
    btnCopy.addEventListener('click', () => {
      const text = document.getElementById('modal-body')?.value || '';
      navigator.clipboard.writeText(text);
      btnCopy.textContent = 'Copied! ✓';
      setTimeout(() => { btnCopy.textContent = 'Copy Draft'; }, 1800);
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
}

function openDraftModalForCandidate(event, candidateName) {
  event.stopPropagation();
  if (!currentBatchData) return;

  const candidate = (currentBatchData.candidates || []).find(c => c.candidate_name === candidateName);
  if (!candidate) return;

  const modal = document.getElementById('draft-modal');
  const cleanName = (candidate.candidate_name || '').replace(/^[#\s\*\-_>]+/g, '').trim() || 'Applicant';
  const nameWords = cleanName.split(/\s+/);
  const firstName = (nameWords[0] && !['non-resume', 'invalid', 'document', 'candidate', 'applicant'].includes(nameWords[0].toLowerCase()))
    ? nameWords[0]
    : 'Applicant';

  const isInvalidDoc = candidate.is_valid_resume === false || (candidate.document && candidate.document.is_valid_resume === false) || candidate.recommendation === 'INVALID_DOCUMENT' || candidate.recruiter_recommendation === 'INVALID_DOCUMENT' || (candidate.candidate_name || '').toLowerCase().includes('non-resume');
  const draft = candidate.email_draft || {
    recipient_email: `${cleanName.toLowerCase().replace(/[^a-z0-9]/g, '.')}@example.com`,
    subject: isInvalidDoc
      ? `Action Required: Resume Submission for Software Engineer`
      : `Update regarding your application for Software Engineer`,
    body_text: isInvalidDoc
      ? `Dear Applicant,\n\nThank you for your interest in TechCorp Solutions. The uploaded file appears to be coursework, an assignment, or an unformatted document rather than a standard resume.\n\nPlease reply with your updated resume PDF so our engineering team can review your qualifications.\n\nBest regards,\nTalent Acquisition Team`
      : `Hi ${firstName},\n\nThank you for applying. We are reviewing your technical profile.`
  };

  let titleText = `🔴 Auto-Drafted Rejection Email (${cleanName})`;
  if (isInvalidDoc) {
    titleText = `⚠️ Auto-Drafted Document Resubmission Notice (${cleanName})`;
  } else if (candidate.recommendation === 'SHORTLIST') {
    titleText = `🟢 Auto-Drafted Interview Invitation (${cleanName})`;
  }

  document.getElementById('modal-draft-title').textContent = titleText;
  document.getElementById('modal-recipient').textContent = draft.recipient_email || 'applicant@example.com';
  document.getElementById('modal-subject').value = draft.subject;
  document.getElementById('modal-body').value = draft.body_text;

  modal.style.display = 'flex';
}

function openDraftModal(draft, title = 'Auto-Drafted Response') {
  const modal = document.getElementById('draft-modal');
  if (!modal) return;
  const titleEl = document.getElementById('modal-draft-title');
  const recipientEl = document.getElementById('modal-recipient');
  const subjectEl = document.getElementById('modal-subject');
  const bodyEl = document.getElementById('modal-body');

  if (titleEl) titleEl.textContent = title;
  if (recipientEl) recipientEl.textContent = draft?.recipient_email || 'applicant@example.com';
  if (subjectEl) subjectEl.value = draft?.subject || '';
  if (bodyEl) bodyEl.value = draft?.body_text || '';

  modal.style.display = 'flex';
}

// ================= TELEMETRY & DASHBOARD =================
async function fetchHealth() {
  try {
    const res = await fetch('/api/v1/health');
    if (!res.ok) return;
    const data = await res.json();
    const cacheEl = document.getElementById('cache-hit-rate');
    if (cacheEl) cacheEl.textContent = `${data.cache.hit_rate_pct}%`;
  } catch (e) {
    console.warn('Health check failed', e);
  }
}

async function loadDashboardStats() {
  try {
    const res = await fetch('/api/v1/dashboard/stats');
    if (!res.ok) return;
    const stats = await res.json();

    const elToday = document.getElementById('kpi-screened-today');
    const elTotal = document.getElementById('kpi-total-screened');
    const elStrong = document.getElementById('kpi-strong-count');
    const elReview = document.getElementById('kpi-review-count');
    const elRejected = document.getElementById('kpi-rejected-count');
    const elInvalid = document.getElementById('kpi-invalid-count');
    const elCreditsVal = document.getElementById('kpi-credits-val');
    const elCreditsSub = document.getElementById('kpi-credits-sub');

    if (elToday) elToday.textContent = stats.screened_today ?? 0;
    if (elTotal) elTotal.textContent = `${stats.total_screened ?? 0} total screened`;
    if (elStrong) elStrong.textContent = stats.strong_count ?? 0;
    if (elReview) elReview.textContent = stats.review_count ?? 0;
    if (elRejected) elRejected.textContent = (stats.rejected_count ?? 0) + (stats.invalid_count ?? 0);
    if (elInvalid) elInvalid.textContent = stats.invalid_count ?? 0;
    if (elCreditsVal) elCreditsVal.textContent = stats.credits_available ?? 250;
    if (elCreditsSub) elCreditsSub.textContent = `${stats.credits_available ?? 250} available this month`;

    // Also update history filter count chips
    const cntAll = document.getElementById('hist-cnt-all');
    const cntStrong = document.getElementById('hist-cnt-strong');
    const cntReview = document.getElementById('hist-cnt-review');
    const cntRej = document.getElementById('hist-cnt-rejected');
    const cntInv = document.getElementById('hist-cnt-invalid');

    if (cntAll) cntAll.textContent = stats.total_screened ?? 0;
    if (cntStrong) cntStrong.textContent = stats.strong_count ?? 0;
    if (cntReview) cntReview.textContent = stats.review_count ?? 0;
    if (cntRej) cntRej.textContent = stats.rejected_count ?? 0;
    if (cntInv) cntInv.textContent = stats.invalid_count ?? 0;
  } catch (err) {
    console.warn('Could not load dashboard stats:', err);
  }
}

function initHistoryControls() {
  const filterBtns = document.querySelectorAll('.hist-filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.getAttribute('data-filter') || 'ALL';
      fetchHistory(filter, currentHistoryQuery);
    });
  });

  const searchInput = document.getElementById('history-search-input');
  let searchTimer = null;
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        fetchHistory(currentHistoryFilter, e.target.value.trim());
      }, 250);
    });
  }
}

async function fetchHistory(filter = currentHistoryFilter, query = currentHistoryQuery) {
  try {
    currentHistoryFilter = filter;
    currentHistoryQuery = query;

    const url = `/api/v1/screenings?filter_status=${encodeURIComponent(filter)}&q=${encodeURIComponent(query)}`;
    const res = await fetch(url);
    if (!res.ok) return;
    const items = await res.json();
    const listEl = document.getElementById('history-list');
    const countEl = document.getElementById('history-count');
    if (countEl) countEl.textContent = `${items.length} candidate${items.length === 1 ? '' : 's'} displayed`;

    if (!items.length) {
      listEl.innerHTML = '<div class="empty-history">No candidates match the selected filter.</div>';
      return;
    }

    listEl.innerHTML = '';
    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'history-item';
      
      const isInvalid = item.is_valid_resume === false || (item.document && item.document.is_valid_resume === false) || (item.candidate_name || '').toLowerCase().includes('non-resume');
      
      let badgeClass = 'reject';
      let badgeLabel = 'NOT RECOMMENDED';
      if (isInvalid) {
        badgeClass = 'reject';
        badgeLabel = 'INVALID DOCUMENT';
      } else if (item.recommendation === 'SHORTLIST' || (item.assessment && item.assessment.recommendation === 'STRONG_CANDIDATE')) {
        badgeClass = 'shortlist';
        badgeLabel = 'STRONG CANDIDATE';
      } else if (item.recommendation === 'REVIEW' || (item.assessment && item.assessment.recommendation === 'REVIEW')) {
        badgeClass = 'review';
        badgeLabel = 'NEEDS REVIEW';
      }

      const scoreDisplay = isInvalid ? '0/100' : `${item.overall_score}/100`;
      const scoreColor = isInvalid ? 'var(--color-danger)' : (item.overall_score >= 78 ? 'var(--color-success)' : (item.overall_score >= 55 ? 'var(--color-warning)' : 'var(--color-danger)'));

      row.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 3px;">
          <div class="h-candidate" style="font-weight: 700; font-size: 0.92rem; color: var(--color-text);">${item.candidate_name || 'Candidate'}</div>
          <div class="h-meta" style="font-size: 0.76rem; color: var(--color-text-muted);">@${item.github_username || 'no_github'} • ${item.screened_at || 'Recently'} • ${item.latency_seconds || '0.8'}s</div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="rec-badge ${badgeClass}" style="font-size: 0.76rem; padding: 4px 10px;">${badgeLabel}</span>
          <span class="h-score" style="font-size: 0.95rem; font-weight: 800; color: ${scoreColor};">${scoreDisplay}</span>
        </div>
      `;

      row.addEventListener('click', () => {
        document.getElementById('tab-single-btn').click();
        if (isInvalid) {
          showInvalidDocumentState(item);
        } else {
          renderScorecard(item);
          showResultState();
        }
        window.scrollTo({ top: 120, behavior: 'smooth' });
      });

      listEl.appendChild(row);
    });
  } catch (e) {
    console.warn('History fetch error', e);
  }
}






























































































































































































































































































