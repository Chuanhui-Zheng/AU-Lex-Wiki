/* AU-WorkLaw-Atlas: shared JS utilities */

// Keyboard shortcut: / focuses search
document.addEventListener('keydown', (e) => {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT'
      && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault();
    const searchInput = document.querySelector('.header-search input');
    if (searchInput) searchInput.focus();
  }
});

// Highlight the current section in the TOC sidebar
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  document.querySelectorAll('.toc-sidebar a').forEach(a => {
    if (a.getAttribute('href') === path) {
      a.style.fontWeight = '700';
      a.style.color = 'var(--accent)';
      a.scrollIntoView({block: 'nearest'});
    }
  });

  // Persist only the visual preference, never credentials.
  const savedTheme = localStorage.getItem('aulex.theme') || 'light';
  document.documentElement.dataset.theme = savedTheme;
  document.getElementById('themeToggle')?.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('aulex.theme', next);
  });

  const toast = document.getElementById('siteToast');
  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.setTimeout(() => toast.classList.remove('is-visible'), 2200);
  };

  document.getElementById('shareButton')?.addEventListener('click', async () => {
    const shareData = {title: document.title, text: 'AU-WorkLaw-Atlas', url: window.location.href};
    try {
      if (navigator.share) await navigator.share(shareData);
      else {
        await navigator.clipboard.writeText(window.location.href);
        showToast('Link copied to clipboard');
      }
    } catch (_) { /* user cancelled or clipboard is unavailable */ }
  });

  const dock = document.getElementById('askDock');
  const orb = document.getElementById('askOrb');
  const dockPanel = document.getElementById('askDockPanel');
  const dockInput = document.getElementById('askDockInput');
  const dockForm = document.getElementById('askDockForm');
  const dockSubmit = document.getElementById('askDockSubmit');
  const dockResult = document.getElementById('askDockResult');
  const modeLabel = document.getElementById('askModeLabel');
  let askMode = 'offline';
  let dragState = null;
  let dragged = false;
  const settingsStorage = 'aulex.llm_settings';
  const maskedKey = '••••••••••••';

  function settingsPayload() {
    try { return JSON.parse(sessionStorage.getItem(settingsStorage) || '{}'); }
    catch (_) { return {}; }
  }

  function setDockOpen(open) {
    if (!dock || !dockPanel) return;
    dock.classList.toggle('is-open', open);
    dockPanel.setAttribute('aria-hidden', String(!open));
    orb?.setAttribute('aria-expanded', String(open));
    if (open) {
      dockInput?.focus();
    }
  }

  function openDock() {
    if (typeof window.openLibraryAsk === 'function') {
      window.openLibraryAsk();
      return;
    }
    setDockOpen(true);
    dockInput?.focus();
  }

  document.getElementById('askToggle')?.addEventListener('click', (event) => {
    event.preventDefault();
    openDock();
  });
  orb?.addEventListener('click', () => {
    if (dragged) { dragged = false; return; }
    if (typeof window.openLibraryAsk === 'function') {
      window.openLibraryAsk();
      return;
    }
    setDockOpen(!dock.classList.contains('is-open'));
  });
  document.getElementById('askDockClose')?.addEventListener('click', () => setDockOpen(false));

  // The collapsed assistant can be moved vertically without blocking page content.
  orb?.addEventListener('pointerdown', event => {
    dragState = {startY: event.clientY, startTop: dock.getBoundingClientRect().top, moved: false};
    orb.setPointerCapture?.(event.pointerId);
  });
  orb?.addEventListener('pointermove', event => {
    if (!dragState) return;
    const delta = event.clientY - dragState.startY;
    if (Math.abs(delta) > 4) dragState.moved = true;
    const size = 58;
    const top = Math.max(size / 2 + 10, Math.min(window.innerHeight - size / 2 - 10, dragState.startTop + delta + size / 2));
    dock.style.top = `${top}px`;
    dock.style.bottom = 'auto';
  });
  const stopDragging = () => {
    if (dragState?.moved) dragged = true;
    dragState = null;
  };
  orb?.addEventListener('pointerup', stopDragging);
  orb?.addEventListener('pointercancel', stopDragging);

  document.querySelectorAll('.mode-option').forEach(button => {
    button.addEventListener('click', () => {
      askMode = button.dataset.mode;
      document.querySelectorAll('.mode-option').forEach(item => item.classList.toggle('is-active', item === button));
      modeLabel.textContent = askMode === 'offline' ? 'Offline evidence mode' : 'Online model mode';
      dockInput.placeholder = askMode === 'offline'
        ? 'Search the local indexed provisions…'
        : 'Ask the model about the indexed provisions…';
    });
  });

  function renderDockResult(data) {
    dockResult.replaceChildren();
    const answer = document.createElement('p');
    answer.className = 'dock-answer';
    answer.textContent = data.answer || data.error || 'No answer returned.';
    dockResult.appendChild(answer);
    if (data.sources?.length) {
      const sources = document.createElement('div');
      sources.className = 'dock-sources';
      const label = document.createElement('strong');
      label.textContent = 'Relevant provisions';
      sources.appendChild(label);
      data.sources.slice(0, 3).forEach(source => {
        const link = document.createElement('a');
        link.href = source.decision_id
          ? `/decision/${encodeURIComponent(source.decision_id)}`
          : source.agreement_id
            ? `/agreement/${encodeURIComponent(source.agreement_id)}`
            : (source.id ? `/section/${source.id}` : (source.source_url || '#'));
        const authority = source.authority_level === 'official_guidance'
          ? 'official guidance'
          : (source.document_type || 'primary law').replaceAll('_', ' ');
        link.textContent = `${source.marker} · ${source.act_name} s ${source.section_no} · ${authority}`;
        sources.appendChild(link);
      });
      dockResult.appendChild(sources);
    }
  }

  const settingsModal = document.getElementById('askSettingsModal');
  const settingsProvider = document.getElementById('askProviderInput');
  const settingsKey = document.getElementById('askApiKeyInput');
  const settingsModel = document.getElementById('askModelInput');
  const settingsBaseUrl = document.getElementById('askBaseUrlInput');
  const settingsBaseField = document.getElementById('askBaseUrlField');
  const settingsStatus = document.getElementById('askSettingsStatus');

  function updateSettingsFields() {
    const provider = settingsProvider.value;
    const knownUrls = ['https://api.openai.com/v1', 'https://openrouter.ai/api/v1', 'https://generativelanguage.googleapis.com/v1beta'];
    settingsBaseField.hidden = !['openai_compatible', 'openrouter'].includes(provider);
    if (provider === 'anthropic' && (!settingsModel.value || settingsModel.value === 'gpt-4o-mini' || settingsModel.value === 'openai/gpt-4o-mini')) settingsModel.value = 'claude-opus-4-5';
    if (provider === 'openai_compatible' && (!settingsModel.value || settingsModel.value === 'claude-opus-4-5' || settingsModel.value === 'openai/gpt-4o-mini')) settingsModel.value = 'gpt-4o-mini';
    if (provider === 'openrouter' && (!settingsModel.value || settingsModel.value === 'claude-opus-4-5' || settingsModel.value === 'gpt-4o-mini')) settingsModel.value = 'openai/gpt-4o-mini';
    if (provider === 'gemini' && (!settingsModel.value || settingsModel.value === 'gpt-4o-mini' || settingsModel.value === 'openai/gpt-4o-mini')) settingsModel.value = 'gemini-2.5-flash';
    if (provider === 'openrouter' && (!settingsBaseUrl.value || knownUrls.includes(settingsBaseUrl.value))) settingsBaseUrl.value = 'https://openrouter.ai/api/v1';
    if (provider === 'openai_compatible' && (!settingsBaseUrl.value || knownUrls.includes(settingsBaseUrl.value))) settingsBaseUrl.value = 'https://api.openai.com/v1';
    settingsKey.placeholder = provider === 'gemini' ? 'AIza…' : provider === 'anthropic' ? 'sk-ant-…' : provider === 'openrouter' ? 'sk-or-v1-…' : 'sk-…';
  }

  function openSettings() {
    const settings = settingsPayload();
    settingsProvider.value = settings.provider || 'openrouter';
    settingsModel.value = settings.model || 'openai/gpt-4o-mini';
    settingsBaseUrl.value = settings.base_url || 'https://openrouter.ai/api/v1';
    settingsKey.value = settings.api_key ? maskedKey : '';
    settingsKey.readOnly = Boolean(settings.api_key);
    updateSettingsFields();
    settingsStatus.textContent = settings.api_key ? 'Key saved for this session. It is not stored in the database.' : 'No browser key set. You can also configure a server-side key.';
    settingsStatus.classList.toggle('is-active', Boolean(settings.api_key));
    settingsModal.hidden = false;
    settingsKey.focus();
  }
  window.openAskSettings = openSettings;

  function closeSettings() { if (settingsModal) settingsModal.hidden = true; }
  document.getElementById('askSettingsToggle')?.addEventListener('click', openSettings);
  document.querySelectorAll('[data-settings-close]').forEach(button => button.addEventListener('click', closeSettings));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeSettings(); });
  settingsProvider?.addEventListener('change', updateSettingsFields);
  settingsKey?.addEventListener('focus', () => {
    if (settingsKey.readOnly) { settingsKey.value = ''; settingsKey.readOnly = false; }
  });
  document.getElementById('askSaveSettings')?.addEventListener('click', () => {
    const existing = settingsPayload();
    const entered = settingsKey.value.trim();
    sessionStorage.setItem(settingsStorage, JSON.stringify({
      api_key: entered && entered !== maskedKey ? entered : (existing.api_key || ''),
      provider: settingsProvider.value,
      model: settingsModel.value.trim(),
      base_url: settingsBaseUrl.value.trim(),
    }));
    settingsKey.value = maskedKey;
    settingsKey.readOnly = true;
    settingsStatus.textContent = 'Key saved for this session. It is not stored in the database.';
    settingsStatus.classList.add('is-active');
  });
  document.getElementById('askClearSettings')?.addEventListener('click', () => {
    sessionStorage.removeItem(settingsStorage);
    settingsKey.value = '';
    settingsKey.readOnly = false;
    settingsStatus.textContent = 'No browser key set. You can also configure a server-side key.';
    settingsStatus.classList.remove('is-active');
  });

  window.aulexSubmitQuestion = async (query, mode = 'offline', actId = null) => {
    const settings = settingsPayload();
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          query,
          mode,
          act_id: actId || undefined,
          api_key: settings.api_key || undefined,
          provider: settings.provider || undefined,
          model: settings.model || undefined,
          base_url: settings.base_url || undefined,
        }),
      });
    return response.json();
  };

  dockForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = dockInput.value.trim();
    if (!query) return;
    dockSubmit.disabled = true;
    dockSubmit.textContent = '…';
    try {
      const data = await window.aulexSubmitQuestion(query, askMode);
      if (typeof window.handleLibraryAsk === 'function') window.handleLibraryAsk(data, query);
      else renderDockResult(data);
    } catch (error) {
      renderDockResult({answer: 'The Ask service could not be reached.'});
    } finally {
      dockSubmit.disabled = false;
      dockSubmit.textContent = 'Ask';
    }
  });
});
