/**
 * AuditAgent.ai — Standalone Candidate Assessment Portal
 * Handles Camera/Mic Pre-flight, Live AI Proctoring, Anti-Cheat Enforcement,
 * Sandbox Code Execution, and 3-Strike Auto-Termination.
 */

(function() {
  // State
  const state = {
    assessmentId: null,
    token: null,
    candidateName: '',
    jobTitle: '',
    durationMinutes: 30,
    timeRemainingSeconds: 1800,
    timerInterval: null,
    heartbeatInterval: null,
    currentQuestionIndex: 0,
    questions: [],
    candidateAnswers: {}, // { [question_id]: code }
    currentLanguage: 'python',
    strikeCount: 0,
    maxStrikes: 3,
    integrityScore: 100,
    stream: null,
    audioContext: null,
    analyserNode: null,
    micDataArray: null,
    isTerminated: false,
    offscreenCanvas: document.createElement('canvas')
  };

  // DOM Elements
  const screens = {
    auth: document.getElementById('screen-auth'),
    preflight: document.getElementById('screen-preflight'),
    assessment: document.getElementById('screen-assessment'),
    results: document.getElementById('screen-results'),
    terminated: document.getElementById('screen-terminated')
  };

  const otpInputs = document.querySelectorAll('.otp-input-field');
  const otpErrorMsg = document.getElementById('otp-error-msg');
  const btnVerifyOtp = document.getElementById('btn-verify-otp');
  const btnStartTest = document.getElementById('btn-start-test');
  const preflightVideo = document.getElementById('preflight-video');
  const liveProctorVideo = document.getElementById('live-proctor-video');
  const audioMeterFill = document.getElementById('audio-meter-fill');
  const hudAudioDot = document.getElementById('hud-audio-dot');
  const hudStatusText = document.getElementById('hud-status-text');

  const questionTabsBar = document.getElementById('question-tabs-bar');
  const questionDetailsWrap = document.getElementById('question-details-wrap');
  const editorPanel = document.getElementById('editor-panel');
  const mcqPanel = document.getElementById('mcq-panel');
  const mcqOptionsContainer = document.getElementById('mcq-options-container');

  const codeEditor = document.getElementById('code-editor');
  const editorLangSelect = document.getElementById('editor-lang-select');
  const btnResetCode = document.getElementById('btn-reset-code');
  const btnRunCode = document.getElementById('btn-run-code');
  const btnSubmitAssessment = document.getElementById('btn-submit-assessment');
  const sandboxOutputBody = document.getElementById('sandbox-output-body');
  const sandboxExecutionTime = document.getElementById('sandbox-execution-time');

  const btnPrevQuestion = document.getElementById('btn-prev-question');
  const btnNextQuestion = document.getElementById('btn-next-question');
  const btnFooterSubmit = document.getElementById('btn-footer-submit');
  const progressIndicatorText = document.getElementById('progress-indicator-text');
  const progressDotsBar = document.getElementById('progress-dots-bar');

  const timerDisplay = document.getElementById('time-remaining');
  const strikeCountText = document.getElementById('strike-count-text');
  const violationToast = document.getElementById('violation-toast');
  const violationToastMsg = document.getElementById('violation-toast-msg');

  // Initialization
  window.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    state.assessmentId = urlParams.get('id');
    state.token = urlParams.get('token');

    setupOtpInputs();
    setupCodeEditorShortcuts();
    setupNavigationButtons();
    setupAntiCheatListeners();

    if (!state.assessmentId) {
      otpErrorMsg.textContent = "Missing Assessment ID in URL parameters.";
      return;
    }

    // If magic link token is present in URL, auto-verify!
    if (state.token) {
      await verifyOtpOrToken(state.token);
    }
  });

  function showScreen(screenKey) {
    Object.values(screens).forEach(s => s && s.classList.remove('active'));
    if (screens[screenKey]) {
      screens[screenKey].classList.add('active');
    }
  }

  // --- OTP & Token Authentication ---
  function setupOtpInputs() {
    otpInputs.forEach((input, index) => {
      input.addEventListener('input', (e) => {
        if (e.target.value.length === 1 && index < otpInputs.length - 1) {
          otpInputs[index + 1].focus();
        }
      });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !e.target.value && index > 0) {
          otpInputs[index - 1].focus();
        }
      });
    });

    btnVerifyOtp.addEventListener('click', async () => {
      const code = Array.from(otpInputs).map(inp => inp.value).join('');
      if (code.length !== 6) {
        otpErrorMsg.textContent = "Please enter all 6 digits.";
        return;
      }
      await verifyOtpOrToken(code);
    });
  }

  async function verifyOtpOrToken(credential) {
    try {
      otpErrorMsg.textContent = "";
      btnVerifyOtp.disabled = true;
      btnVerifyOtp.textContent = "Verifying...";

      const res = await fetch(`/api/v1/assessments/${state.assessmentId}/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp_or_token: credential })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Authentication failed.");
      }

      const data = await res.json();
      state.candidateName = data.candidate_name;
      state.durationMinutes = data.duration_minutes || 30;
      state.timeRemainingSeconds = state.durationMinutes * 60;
      state.token = data.token || state.token;

      // Transition to Preflight Check
      showScreen('preflight');
      await initializeMediaDevices();

    } catch (err) {
      otpErrorMsg.textContent = err.message;
      btnVerifyOtp.disabled = false;
      btnVerifyOtp.textContent = "Verify & Continue";
    }
  }

  // --- Hardware & Media Stream Pre-flight ---
  async function initializeMediaDevices() {
    try {
      state.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
        audio: true
      });

      preflightVideo.srcObject = state.stream;
      liveProctorVideo.srcObject = state.stream;

      // Audio Meter Setup
      state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const sourceNode = state.audioContext.createMediaStreamSource(state.stream);
      state.analyserNode = state.audioContext.createAnalyser();
      state.analyserNode.fftSize = 256;
      sourceNode.connect(state.analyserNode);
      state.micDataArray = new Uint8Array(state.analyserNode.frequencyBinCount);

      monitorAudioLevels();

    } catch (err) {
      alert("Camera and Microphone access are mandatory for proctored technical assessments. Please enable permissions in your browser: " + err.message);
    }
  }

  function monitorAudioLevels() {
    if (!state.analyserNode) return;

    function checkLevel() {
      if (state.isTerminated) return;
      state.analyserNode.getByteFrequencyData(state.micDataArray);
      let sum = 0;
      for (let i = 0; i < state.micDataArray.length; i++) {
        sum += state.micDataArray[i];
      }
      const avg = sum / state.micDataArray.length;
      const pct = Math.min(100, Math.round((avg / 128) * 100));

      if (audioMeterFill) {
        audioMeterFill.style.width = pct + '%';
      }

      if (hudAudioDot) {
        if (pct > 40) {
          hudAudioDot.classList.add('speaking');
        } else {
          hudAudioDot.classList.remove('speaking');
        }
      }

      requestAnimationFrame(checkLevel);
    }
    requestAnimationFrame(checkLevel);
  }

  // --- Start Assessment Room ---
  btnStartTest.addEventListener('click', async () => {
    // Request Fullscreen
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } catch (err) {
      console.warn("Fullscreen request not granted:", err);
    }

    const preflightRole = document.getElementById('preflight-role-select')?.value || '';
    if (preflightRole) state.roleTrack = preflightRole;

    // Load Questions & Workspace
    await loadCandidateWorkspace(state.roleTrack);
    showScreen('assessment');
    startCountdownTimer();
    startProctoringHeartbeat();
  });

  // Track Selector change listener in test room
  const roleTrackSelect = document.getElementById('role-track-select');
  if (roleTrackSelect) {
    roleTrackSelect.addEventListener('change', async (e) => {
      const selectedRole = e.target.value;
      state.candidateAnswers = {};
      await loadCandidateWorkspace(selectedRole);
    });
  }

  async function loadCandidateWorkspace(roleTrack) {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const targetRole = roleTrack || state.roleTrack || urlParams.get('role') || document.getElementById('preflight-role-select')?.value || '';
      state.roleTrack = targetRole;

      let url = `/api/v1/assessments/${state.assessmentId}/candidate-view?token=${encodeURIComponent(state.token || '')}`;
      if (targetRole) {
        url += `&role=${encodeURIComponent(targetRole)}`;
      }

      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed loading assessment questions.");
      const data = await res.json();

      state.questions = data.questions || [];
      state.jobTitle = data.job_title;
      state.strikeCount = data.strike_count || 0;
      state.maxStrikes = data.max_strikes || 3;
      state.integrityScore = data.integrity_score || 100;

      updateStrikeHUD();

      const headerJob = document.getElementById('header-job-title');
      if (headerJob) headerJob.textContent = `${state.jobTitle} — ${state.candidateName}`;

      if (roleTrackSelect && data.role_track) {
        roleTrackSelect.value = data.role_track;
      }

      renderQuestionTabs();
      loadQuestion(0);

    } catch (err) {
      alert("Error loading assessment: " + err.message);
    }
  }

  // --- Render Questions & Editor ---
  const MCQ_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

  function renderQuestionTabs() {
    questionTabsBar.innerHTML = '';
    if (progressDotsBar) progressDotsBar.innerHTML = '';

    state.questions.forEach((q, idx) => {
      // Top Question Tab Button
      const btn = document.createElement('button');
      btn.className = `q-tab-btn ${idx === 0 ? 'active' : ''}`;
      const isMcq = q.type === 'mcq' || q.section === 'mcq';
      const isSql = q.type === 'sql' || q.section === 'sql';
      const typeLabel = isMcq ? 'MCQ' : (isSql ? 'SQL' : 'DSA');
      btn.textContent = `Q${idx + 1}: ${typeLabel}`;
      btn.title = `${q.section_title || ''} - ${q.title}`;
      btn.addEventListener('click', () => loadQuestion(idx));
      questionTabsBar.appendChild(btn);

      // Bottom Direct Question Pill Button
      if (progressDotsBar) {
        const qBtn = document.createElement('button');
        qBtn.type = 'button';
        qBtn.className = `btn-q-direct ${idx === 0 ? 'active' : ''}`;
        qBtn.setAttribute('data-idx', idx);
        qBtn.title = `Jump directly to Q${idx + 1}: ${q.title}`;
        qBtn.innerHTML = `<span>Q${idx + 1}</span><span class="q-check-mark" style="display: none; font-size: 0.75rem; color: #4ade80;">✓</span>`;
        qBtn.addEventListener('click', () => loadQuestion(idx));
        progressDotsBar.appendChild(qBtn);
      }
    });

    updateProgressDots();
  }

  function updateProgressDots() {
    if (progressDotsBar) {
      const qBtns = progressDotsBar.querySelectorAll('.btn-q-direct');
      qBtns.forEach((btn, idx) => {
        const q = state.questions[idx];
        const hasAnswer = q && state.candidateAnswers[q.id] !== undefined && String(state.candidateAnswers[q.id]).trim().length > 0;
        btn.classList.toggle('active', idx === state.currentQuestionIndex);
        btn.classList.toggle('answered', Boolean(hasAnswer));
        const check = btn.querySelector('.q-check-mark');
        if (check) check.style.display = hasAnswer ? 'inline' : 'none';
      });
    }

    if (progressIndicatorText && state.questions.length > 0) {
      progressIndicatorText.textContent = `Question ${state.currentQuestionIndex + 1} of ${state.questions.length}`;
    }
  }

  function loadQuestion(index) {
    if (!state.questions || state.questions.length === 0) return;
    if (index < 0 || index >= state.questions.length) return;
    state.currentQuestionIndex = index;

    // Update active state across tabs
    const tabs = questionTabsBar.querySelectorAll('.q-tab-btn');
    tabs.forEach((t, i) => t.classList.toggle('active', i === index));

    const q = state.questions[index];
    const isMcq = q.type === 'mcq' || q.section === 'mcq' || (q.options && q.options.length > 0);
    const isSql = q.type === 'sql' || q.section === 'sql';

    // Detect question type traits
    const isDebugging = q.type === 'debugging' || (q.title && q.title.toLowerCase().includes('debugging'));
    const isSecurity = q.type === 'security' || (q.title && q.title.toLowerCase().includes('security'));

    // Update Section Banner Header
    const sectionTitleDisplay = document.getElementById('section-title-display');
    const sectionBadgeIcon = document.getElementById('section-badge-icon');
    const sectionBadgePill = document.getElementById('section-badge-pill');

    if (sectionTitleDisplay) {
      if (isMcq) {
        sectionTitleDisplay.textContent = q.section_title || "Section 1: Multiple Choice Questions (MCQs)";
        if (sectionBadgeIcon) sectionBadgeIcon.textContent = "🔷";
        if (sectionBadgePill) {
          sectionBadgePill.textContent = "MCQ • Concepts";
          sectionBadgePill.style.background = "rgba(168,85,247,0.15)";
          sectionBadgePill.style.color = "#c084fc";
        }
      } else if (isSql) {
        sectionTitleDisplay.textContent = q.section_title || "Section 2: SQL Analytics & Challenges";
        if (sectionBadgeIcon) sectionBadgeIcon.textContent = "🗄️";
        if (sectionBadgePill) {
          sectionBadgePill.textContent = "SQL • Database";
          sectionBadgePill.style.background = "rgba(16,185,129,0.15)";
          sectionBadgePill.style.color = "#34d399";
        }
      } else if (isDebugging) {
        sectionTitleDisplay.textContent = q.section_title || "Section 2: Code Debugging & Bug Fixing";
        if (sectionBadgeIcon) sectionBadgeIcon.textContent = "🐛";
        if (sectionBadgePill) {
          sectionBadgePill.textContent = "Bug Fix • Debugging";
          sectionBadgePill.style.background = "rgba(245,158,11,0.15)";
          sectionBadgePill.style.color = "#fbbf24";
        }
      } else if (isSecurity) {
        sectionTitleDisplay.textContent = q.section_title || "Section 2: Security & Defense Challenges";
        if (sectionBadgeIcon) sectionBadgeIcon.textContent = "🛡️";
        if (sectionBadgePill) {
          sectionBadgePill.textContent = "Security • Defense";
          sectionBadgePill.style.background = "rgba(244,63,94,0.15)";
          sectionBadgePill.style.color = "#fb7185";
        }
      } else {
        sectionTitleDisplay.textContent = q.section_title || "Section 2: Coding & DSA Challenges";
        if (sectionBadgeIcon) sectionBadgeIcon.textContent = "💻";
        if (sectionBadgePill) {
          sectionBadgePill.textContent = "Coding • DSA";
          sectionBadgePill.style.background = "rgba(6,182,212,0.15)";
          sectionBadgePill.style.color = "#22d3ee";
        }
      }
    }

    // Render Question Details in Left Panel
    let tcHtml = '';
    if (q.test_cases && q.test_cases.length > 0) {
      tcHtml = `
        <div style="margin-top: 16px;">
          <h4 style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px;">Automated Test Cases</h4>
          ${q.test_cases.map((tc, i) => `
            <div style="background: #0f172a; padding: 10px 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; margin-bottom: 6px; border: 1px solid #1e293b;">
              <div style="color: #94a3b8; font-size: 0.75rem; margin-bottom: 4px;">${tc.description || `Test Case ${i + 1}`}</div>
              ${tc.setup_sql ? `<div style="color: #64748b; font-size: 0.72rem; margin-bottom: 3px;">[Schema seeded in-memory SQLite]</div>` : ''}
              ${tc.input_data ? `<div><span style="color: #38bdf8;">Input:</span> ${JSON.stringify(tc.input_data)}</div>` : ''}
              <div><span style="color: #4ade80;">Expected:</span> ${JSON.stringify(tc.expected_output)}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    let badgeStyle = 'background: rgba(6,182,212,0.15); color: #22d3ee;';
    let typeLabel = 'Coding & DSA';

    if (isMcq) {
      badgeStyle = 'background: rgba(168,85,247,0.15); color: #c084fc;';
      typeLabel = 'Multiple Choice (MCQ)';
    } else if (isSql) {
      badgeStyle = 'background: rgba(16,185,129,0.15); color: #34d399;';
      typeLabel = 'SQL Query Challenge';
    } else if (isDebugging) {
      badgeStyle = 'background: rgba(245,158,11,0.15); color: #fbbf24;';
      typeLabel = 'Bug Fix & Debugging';
    } else if (isSecurity) {
      badgeStyle = 'background: rgba(244,63,94,0.15); color: #fb7185;';
      typeLabel = 'Security & Threat Defense';
    }

    questionDetailsWrap.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <span style="${badgeStyle} padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">${typeLabel}</span>
        <span style="color: #64748b; font-size: 0.8rem;">Est. Time: ${q.time_limit_minutes || 5}m</span>
      </div>
      <h3 style="font-size: 1.15rem; margin-bottom: 12px; color: #f8fafc;">${q.title}</h3>
      <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap;">${q.prompt}</p>
      ${q.code_snippet ? `
        <div style="margin-top: 14px;">
          <h4 style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px;">Reference Snippet:</h4>
          <pre style="background: #000; padding: 12px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; overflow-x: auto; color: #fbbf24;">${q.code_snippet}</pre>
        </div>
      ` : ''}
      ${tcHtml}
    `;

    // Toggle between Code Editor and MCQ Panel
    if (isMcq) {
      if (editorPanel) editorPanel.style.display = 'none';
      if (mcqPanel) mcqPanel.style.display = 'flex';
      renderMcqOptions(q);
    } else {
      if (mcqPanel) mcqPanel.style.display = 'none';
      if (editorPanel) editorPanel.style.display = 'flex';

      // Set language according to challenge type
      if (isSql) {
        state.currentLanguage = 'sql';
        if (editorLangSelect) editorLangSelect.value = 'sql';
      } else if (state.currentLanguage === 'sql') {
        state.currentLanguage = 'python';
        if (editorLangSelect) editorLangSelect.value = 'python';
      }

      // Load code into editor (existing candidate answer, or starter code)
      if (state.candidateAnswers[q.id] !== undefined) {
        codeEditor.value = state.candidateAnswers[q.id];
      } else {
        const starters = q.starter_code || {};
        if (isSql) {
          codeEditor.value = starters['sql'] || '-- Write your SQL query below\nSELECT * FROM employees;\n';
        } else {
          codeEditor.value = starters[state.currentLanguage] || starters['python'] || starters['javascript'] || '# Write your solution below:\ndef solution():\n    pass\n';
        }
        state.candidateAnswers[q.id] = codeEditor.value;
      }
    }

    // Update Bottom Navigation Buttons
    if (btnPrevQuestion) {
      btnPrevQuestion.disabled = (index === 0);
    }

    const isLast = (index === state.questions.length - 1);
    if (btnNextQuestion) {
      btnNextQuestion.style.display = isLast ? 'none' : 'inline-flex';
    }
    if (btnFooterSubmit) {
      btnFooterSubmit.style.display = 'inline-flex';
      if (isLast) {
        btnFooterSubmit.className = 'btn-portal-primary';
        btnFooterSubmit.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        btnFooterSubmit.style.boxShadow = '0 0 16px rgba(16, 185, 129, 0.4)';
        btnFooterSubmit.innerHTML = '✓ Submit Assessment';
      } else {
        btnFooterSubmit.className = 'btn-nav';
        btnFooterSubmit.style.background = 'rgba(16, 185, 129, 0.15)';
        btnFooterSubmit.style.border = '1px solid rgba(16, 185, 129, 0.4)';
        btnFooterSubmit.style.color = '#4ade80';
        btnFooterSubmit.style.boxShadow = 'none';
        btnFooterSubmit.innerHTML = '✓ Submit';
      }
    }

    updateProgressDots();
  }

  // --- MCQ Option Selection ---
  function renderMcqOptions(q) {
    if (!mcqOptionsContainer) return;
    mcqOptionsContainer.innerHTML = '';

    const options = q.options || [];
    const currentAnswer = state.candidateAnswers[q.id];

    options.forEach((optText, idx) => {
      const isSelected = (currentAnswer !== undefined && (String(currentAnswer) === String(idx) || currentAnswer === optText));
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `mcq-option-card ${isSelected ? 'selected' : ''}`;
      card.setAttribute('data-idx', idx);
      card.setAttribute('role', 'radio');
      card.setAttribute('aria-checked', isSelected ? 'true' : 'false');
      card.title = `Select Option ${MCQ_LETTERS[idx] || idx + 1}`;

      const letter = MCQ_LETTERS[idx] || `${idx + 1}`;
      card.innerHTML = `
        <div class="mcq-letter-badge">${letter}</div>
        <div class="mcq-option-text">${optText}</div>
        <div class="mcq-radio-circle"></div>
      `;

      card.addEventListener('click', () => {
        selectMcqOption(q, idx, optText);
      });

      mcqOptionsContainer.appendChild(card);
    });
  }

  function selectMcqOption(q, idx, optText) {
    state.candidateAnswers[q.id] = String(idx);

    if (mcqOptionsContainer) {
      const cards = mcqOptionsContainer.querySelectorAll('.mcq-option-card');
      cards.forEach((c, i) => {
        c.classList.toggle('selected', i === idx);
      });
    }

    updateProgressDots();
  }

  // --- Navigation Controls (Previous, Next, Submit) ---
  function setupNavigationButtons() {
    if (btnPrevQuestion) {
      btnPrevQuestion.addEventListener('click', () => {
        if (state.currentQuestionIndex > 0) {
          loadQuestion(state.currentQuestionIndex - 1);
        }
      });
    }

    if (btnNextQuestion) {
      btnNextQuestion.addEventListener('click', () => {
        if (state.currentQuestionIndex < state.questions.length - 1) {
          loadQuestion(state.currentQuestionIndex + 1);
        }
      });
    }

    if (btnFooterSubmit) {
      btnFooterSubmit.addEventListener('click', submitAssessment);
    }

    // Keyboard Shortcuts for MCQ selection and quick navigation
    window.addEventListener('keydown', (e) => {
      // Don't trigger shortcuts when candidate is actively typing in textarea or input
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (activeTag === 'textarea' || activeTag === 'input') return;

      const q = state.questions[state.currentQuestionIndex];
      if (!q) return;

      // Quick MCQ option selection: keys 1-4 or A-D
      if ((q.type === 'mcq' || (q.options && q.options.length > 0)) && q.options) {
        const key = e.key.toUpperCase();
        let targetIdx = -1;
        if (['1', '2', '3', '4', '5'].includes(key)) {
          targetIdx = parseInt(key, 10) - 1;
        } else if (['A', 'B', 'C', 'D', 'E'].includes(key)) {
          targetIdx = key.charCodeAt(0) - 65;
        }

        if (targetIdx >= 0 && targetIdx < q.options.length) {
          e.preventDefault();
          selectMcqOption(q, targetIdx, q.options[targetIdx]);
          return;
        }
      }

      // Quick navigation with ArrowLeft / ArrowRight
      if (e.key === 'ArrowRight' || (e.altKey && e.key === 'n')) {
        if (state.currentQuestionIndex < state.questions.length - 1) {
          e.preventDefault();
          loadQuestion(state.currentQuestionIndex + 1);
        }
      } else if (e.key === 'ArrowLeft' || (e.altKey && e.key === 'p')) {
        if (state.currentQuestionIndex > 0) {
          e.preventDefault();
          loadQuestion(state.currentQuestionIndex - 1);
        }
      }
    });
  }

  // --- Code Editor Shortcuts & Tab Support ---
  function setupCodeEditorShortcuts() {
    codeEditor.addEventListener('keydown', (e) => {
      // Tab key indent
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = codeEditor.selectionStart;
        const end = codeEditor.selectionEnd;
        codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
        codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
      }
      // Ctrl+Enter or Cmd+Enter to run tests
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runSandboxCode();
      }
    });

    codeEditor.addEventListener('input', () => {
      const q = state.questions[state.currentQuestionIndex];
      if (q) {
        state.candidateAnswers[q.id] = codeEditor.value;
        updateProgressDots();
      }
    });

    editorLangSelect.addEventListener('change', (e) => {
      state.currentLanguage = e.target.value;
      const q = state.questions[state.currentQuestionIndex];
      if (q && q.starter_code && q.starter_code[state.currentLanguage]) {
        codeEditor.value = q.starter_code[state.currentLanguage];
        state.candidateAnswers[q.id] = codeEditor.value;
        updateProgressDots();
      }
    });

    btnResetCode.addEventListener('click', () => {
      const q = state.questions[state.currentQuestionIndex];
      if (q && q.starter_code) {
        codeEditor.value = q.starter_code[state.currentLanguage] || q.starter_code['python'] || '';
        state.candidateAnswers[q.id] = codeEditor.value;
        updateProgressDots();
      }
    });

    btnRunCode.addEventListener('click', runSandboxCode);
    btnSubmitAssessment.addEventListener('click', submitAssessment);
  }

  // --- Run Sandbox Code ---
  async function runSandboxCode() {
    const q = state.questions[state.currentQuestionIndex];
    if (!q) return;

    btnRunCode.disabled = true;
    btnRunCode.textContent = "Executing...";
    sandboxExecutionTime.textContent = "Running...";
    sandboxOutputBody.innerHTML = `<span style="color: #38bdf8;">Executing solution in ${state.currentLanguage} sandbox...</span>`;

    try {
      const res = await fetch(`/api/v1/assessments/${state.assessmentId}/sandbox/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: q.id,
          language: state.currentLanguage,
          code: codeEditor.value,
          token: state.token
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Execution failed");
      }

      const result = await res.json();
      sandboxExecutionTime.textContent = `${result.execution_time_ms} ms`;

      let outputHtml = '';
      if (result.total_tests > 0) {
        const badgeColor = result.all_passed ? '#10b981' : '#ef4444';
        outputHtml += `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <strong style="color: ${badgeColor}; font-size: 0.9rem;">
              ${result.all_passed ? '✓ ALL TESTS PASSED' : `✕ SOME TESTS FAILED (${result.tests_passed}/${result.total_tests})`}
            </strong>
          </div>
        `;

        result.test_results.forEach(tr => {
          outputHtml += `
            <div style="padding: 6px 10px; margin-bottom: 4px; border-radius: 4px; background: ${tr.passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; border-left: 3px solid ${tr.passed ? '#10b981' : '#ef4444'};">
              <span style="font-weight: 600; color: ${tr.passed ? '#4ade80' : '#f87171'};">Test ${tr.test_index}: ${tr.passed ? 'Passed' : 'Failed'}</span>
              ${tr.description ? `<span style="color: #94a3b8; font-size: 0.78rem;"> — ${tr.description}</span>` : ''}
              ${!tr.passed && tr.error ? `<div style="color: #fca5a5; margin-top: 2px;">Error: ${tr.error}</div>` : ''}
              ${!tr.passed && tr.actual !== undefined ? `<div style="color: #cbd5e1; font-size: 0.78rem;">Expected: ${JSON.stringify(tr.expected)} | Received: ${JSON.stringify(tr.actual)}</div>` : ''}
            </div>
          `;
        });
      }

      if (result.stdout) {
        outputHtml += `<div style="margin-top: 8px; color: #94a3b8; font-size: 0.75rem;">Standard Output:</div><pre style="color: #cbd5e1; white-space: pre-wrap;">${result.stdout}</pre>`;
      }
      if (result.stderr) {
        outputHtml += `<div style="margin-top: 8px; color: #f87171; font-size: 0.75rem;">Standard Error:</div><pre style="color: #fca5a5; white-space: pre-wrap;">${result.stderr}</pre>`;
      }
      if (result.error_message) {
        outputHtml += `<div style="color: #ef4444; margin-top: 8px;">${result.error_message}</div>`;
      }

      sandboxOutputBody.innerHTML = outputHtml || '<span style="color: #10b981;">Execution completed with no console output.</span>';

    } catch (err) {
      sandboxOutputBody.innerHTML = `<span style="color: #ef4444;">Error: ${err.message}</span>`;
      sandboxExecutionTime.textContent = "Error";
    } finally {
      btnRunCode.disabled = false;
      btnRunCode.textContent = "▶ Run Tests (Ctrl+Enter)";
    }
  }

  // --- Strict Anti-Cheat Listeners (Copy/Paste, Tab Switch, Fullscreen) ---
  function setupAntiCheatListeners() {
    // 1. Copy/Paste/Cut Interceptors
    ['copy', 'paste', 'cut'].forEach(evt => {
      document.addEventListener(evt, (e) => {
        e.preventDefault();
        reportProctorViolation('copy_paste_attempt', `Attempted unauthorized ${evt} action.`);
        showViolationToast(`⚠️ Copy/Paste is strictly disabled. Strike recorded.`);
      });
    });

    // 2. Disable Context Menu
    document.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    });

    // 3. Tab Switching / Window Blur
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && screens.assessment.classList.contains('active')) {
        reportProctorViolation('tab_blur', 'Candidate navigated away from assessment tab.');
        showViolationToast(`⚠️ Window unfocused. You must remain on the assessment screen.`);
      }
    });

    window.addEventListener('blur', () => {
      if (screens.assessment.classList.contains('active')) {
        reportProctorViolation('tab_blur', 'Candidate switched focus away from assessment browser window.');
        showViolationToast(`⚠️ Window focus lost. Strike recorded.`);
      }
    });

    // 4. Fullscreen Exit
    document.addEventListener('fullscreenchange', () => {
      if (!document.fullscreenElement && screens.assessment.classList.contains('active') && !state.isTerminated) {
        reportProctorViolation('fullscreen_exit', 'Candidate exited fullscreen mode.');
        showViolationToast(`⚠️ Exited fullscreen. Fullscreen is mandatory.`);
      }
    });
  }

  async function reportProctorViolation(eventType, details) {
    if (state.isTerminated) return;
    try {
      const snapB64 = captureWebcamFrame();
      const res = await fetch(`/api/v1/assessments/${state.assessmentId}/proctor/violation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          details: details,
          snapshot_base64: snapB64,
          token: state.token
        })
      });

      if (res.ok) {
        const data = await res.json();
        handleProctorCheckResult(data);
      }
    } catch (err) {
      console.error("Failed to report proctor violation:", err);
    }
  }

  // --- Proctoring Heartbeat Loop (Video & Audio Telemetry) ---
  function startProctoringHeartbeat() {
    if (state.heartbeatInterval) clearInterval(state.heartbeatInterval);

    state.heartbeatInterval = setInterval(async () => {
      if (state.isTerminated) return;
      try {
        const snapB64 = captureWebcamFrame();
        const audioRms = calculateAudioRms();

        const res = await fetch(`/api/v1/assessments/${state.assessmentId}/proctor/heartbeat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            snapshot_base64: snapB64,
            audio_level_rms: audioRms,
            token: state.token
          })
        });

        if (res.ok) {
          const data = await res.json();
          handleProctorCheckResult(data);
        }
      } catch (err) {
        console.warn("Heartbeat tick failed:", err);
      }
    }, 5000); // Check every 5 seconds
  }

  function captureWebcamFrame() {
    if (!liveProctorVideo || !liveProctorVideo.videoWidth) return null;
    const canvas = state.offscreenCanvas;
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(liveProctorVideo, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.6);
  }

  function calculateAudioRms() {
    if (!state.analyserNode || !state.micDataArray) return 0.0;
    state.analyserNode.getByteFrequencyData(state.micDataArray);
    let sumSquares = 0;
    for (let i = 0; i < state.micDataArray.length; i++) {
      const norm = (state.micDataArray[i] / 128.0) - 1.0;
      sumSquares += norm * norm;
    }
    return Math.min(1.0, Math.sqrt(sumSquares / state.micDataArray.length));
  }

  function handleProctorCheckResult(res) {
    state.strikeCount = res.strike_count;
    state.maxStrikes = res.max_strikes;
    state.integrityScore = res.integrity_score;

    updateStrikeHUD();

    if (res.strike_added) {
      showViolationToast(`⚠️ Strike ${state.strikeCount}/${state.maxStrikes}: ${res.message}`);
    }

    if (res.is_disqualified || res.status === 'auto_terminated') {
      triggerAutoTermination(res.details || res.message);
    }
  }

  function updateStrikeHUD() {
    strikeCountText.textContent = `${state.strikeCount} / ${state.maxStrikes}`;
    const dots = [
      document.getElementById('dot-strike-1'),
      document.getElementById('dot-strike-2'),
      document.getElementById('dot-strike-3')
    ];
    dots.forEach((dot, idx) => {
      if (dot) {
        dot.classList.toggle('active', idx < state.strikeCount);
      }
    });
  }

  function showViolationToast(msg) {
    violationToastMsg.textContent = msg;
    violationToast.style.display = 'flex';
    setTimeout(() => {
      violationToast.style.display = 'none';
    }, 4500);
  }

  function triggerAutoTermination(reason) {
    state.isTerminated = true;
    if (state.timerInterval) clearInterval(state.timerInterval);
    if (state.heartbeatInterval) clearInterval(state.heartbeatInterval);

    if (document.exitFullscreen && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }

    document.getElementById('terminated-details-text').textContent = reason || "The assessment was terminated due to exceeding maximum allowed violation strikes.";
    screens.terminated.style.display = 'flex';
  }

  // --- Countdown Timer ---
  function startCountdownTimer() {
    if (state.timerInterval) clearInterval(state.timerInterval);

    state.timerInterval = setInterval(() => {
      if (state.isTerminated) return;
      state.timeRemainingSeconds--;
      if (state.timeRemainingSeconds <= 0) {
        clearInterval(state.timerInterval);
        submitAssessment();
        return;
      }

      const m = Math.floor(state.timeRemainingSeconds / 60);
      const s = state.timeRemainingSeconds % 60;
      timerDisplay.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;

      if (state.timeRemainingSeconds < 300) {
        document.getElementById('timer-display').classList.add('urgent');
      }
    }, 1000);
  }

  // --- Submit Assessment ---
  async function submitAssessment() {
    if (!confirm("Are you sure you want to submit your assessment? This cannot be undone.")) return;

    if (btnSubmitAssessment) {
      btnSubmitAssessment.disabled = true;
      btnSubmitAssessment.textContent = "Submitting...";
    }
    if (btnFooterSubmit) {
      btnFooterSubmit.disabled = true;
      btnFooterSubmit.textContent = "Submitting...";
    }

    try {
      const res = await fetch(`/api/v1/assessments/${state.assessmentId}/candidate-submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answers: state.candidateAnswers,
          token: state.token
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Submission failed");
      }

      const result = await res.json();

      // Stop camera/audio stream
      if (state.stream) {
        state.stream.getTracks().forEach(t => t.stop());
      }
      if (state.timerInterval) clearInterval(state.timerInterval);
      if (state.heartbeatInterval) clearInterval(state.heartbeatInterval);

      if (document.exitFullscreen && document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }

      // Populate Scorecard
      document.getElementById('final-tech-score').textContent = `${result.score}/100`;
      document.getElementById('final-integrity-score').textContent = `${result.integrity_score}%`;
      document.getElementById('final-feedback-box').innerHTML = `
        <strong>AI Evaluation Summary:</strong>
        <p style="margin-top: 6px;">${result.feedback}</p>
        <div style="margin-top: 10px; color: #4ade80;"><strong>Key Strengths:</strong> ${result.strengths.join(', ')}</div>
        <div style="margin-top: 6px; color: #f87171;"><strong>Areas for Growth:</strong> ${result.weaknesses.join(', ')}</div>
      `;

      showScreen('results');

    } catch (err) {
      alert("Submission error: " + err.message);
      if (btnSubmitAssessment) {
        btnSubmitAssessment.disabled = false;
        btnSubmitAssessment.textContent = "Submit Assessment";
      }
      if (btnFooterSubmit) {
        btnFooterSubmit.disabled = false;
        btnFooterSubmit.textContent = "✓ Submit Assessment";
      }
    }
  }

})();
