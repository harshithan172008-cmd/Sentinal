/* Local-only integration with run_frontend.py. The server forces sample mode. */
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const api = { state: null };
  const request = async (path, method = 'GET', body) => {
    const response = await fetch(path, {
      method,
      headers: method === 'POST' ? { 'Content-Type': 'application/json' } : {},
      body: method === 'POST' ? JSON.stringify(body || {}) : undefined,
      cache: 'no-store'
    });
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || 'Local backend request failed');
    return data;
  };
  const h = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const text = (selector, value) => { const node = $(selector); if (node) node.textContent = value; };
  const money = (value, currency = 'INR') => {
    const n = Number(value || 0);
    try { return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n); }
    catch { return `₹${Math.round(n).toLocaleString('en-IN')}`; }
  };
  const dateLabel = value => {
    if (!value) return 'Date unclear';
    const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  };
  const dedupedInbox = () => [...new Map((api.state?.inbox || []).map(item => [item.id, item])).values()];
  const notify = message => window.toast ? window.toast(message) : console.info(message);

  function setConnection(connected, message) {
    const banner = $('.global-demo-banner');
    const bannerText = banner?.querySelector('span:nth-of-type(2)');
    if (bannerText) bannerText.textContent = message;
    const pill = $('.demo-pill');
    if (pill) {
      const dot = pill.querySelector('span');
      pill.textContent = connected ? ' LOCAL BACKEND · DEMO' : ' BACKEND OFFLINE · SAMPLE VIEW';
      if (dot) pill.prepend(dot);
      pill.classList.toggle('backend-connected', connected);
    }
    document.documentElement.dataset.backend = connected ? 'connected' : 'offline';
  }

  function renderSubscriptions() {
    const subs = api.state?.subscriptions || [];
    const list = $('#subscriptionList');
    if (!list) return;
    list.replaceChildren();
    if (!subs.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-sample';
      empty.textContent = 'No subscriptions loaded yet. Choose “Scan inbox” to scan the bundled sample messages through the Python backend.';
      list.append(empty);
    }
    for (const sub of subs) {
      const row = document.createElement('article');
      row.className = 'subscription-row';
      const merchant = document.createElement('div');
      merchant.className = 'merchant-icon merchant-google';
      merchant.textContent = (sub.merchant || '?').slice(0, 1).toUpperCase();
      const name = document.createElement('div');
      name.className = 'service-name';
      name.innerHTML = `<b>${h(sub.merchant)}</b><small>${h(sub.status || 'subscription')} · Local backend record</small>`;
      const amount = document.createElement('div');
      amount.className = sub.old_amount != null ? 'price-change' : 'price-cell';
      amount.innerHTML = `${sub.old_amount != null ? '<span class="change-badge">PRICE CHANGE</span>' : ''}<b>${h(money(sub.amount, sub.currency))}${sub.old_amount != null ? ` <s>${h(money(sub.old_amount, sub.currency))}</s>` : ''}</b>${sub.old_amount == null ? '<small>per month / bill</small>' : ''}`;
      const renewal = document.createElement('div');
      renewal.className = 'renewal-date';
      renewal.innerHTML = `<b>${h(dateLabel(sub.renewal_date))}</b><small>${h(sub.status || '')}</small>`;
      row.append(merchant, name, amount, renewal);
      list.append(row);
    }
    const total = subs.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const summary = $('.subscription-summary');
    if (summary) summary.textContent = `${subs.length} BACKEND RECORD${subs.length === 1 ? '' : 'S'} · ${money(total)} TOTAL · LOCAL SAMPLE DATA`;
    const active = subs.filter(item => item.status === 'active' || item.status === 'trial');
    const monthly = active.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const pending = (api.state?.proposals || []).filter(item => item.status === 'pending').length;
    const now = new Date();
    const soon = subs.filter(item => {
      if (!item.renewal_date) return false;
      const dt = new Date(`${String(item.renewal_date).slice(0, 10)}T00:00:00`);
      const days = (dt - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000;
      return days >= 0 && days <= 7;
    }).length;
    const counts = $$('.metric-card .count-up');
    const vals = [monthly, soon, pending];
    counts.forEach((node, i) => { if (vals[i] != null) { node.dataset.target = String(vals[i]); node.dataset.done = '1'; node.textContent = Math.round(vals[i]).toLocaleString('en-IN'); } });
    const firstFoot = $('.metric-card .metric-foot');
    if (firstFoot) firstFoot.textContent = `${subs.length} subscription records loaded from Python`;
    const inboxCount = $('#inboxCount');
    if (inboxCount) inboxCount.textContent = String(dedupedInbox().length).padStart(2, '0');
    const queueCount = $('#queueCount');
    if (queueCount) queueCount.textContent = String(pending).padStart(2, '0');
  }

  function renderQueue() {
    const root = $('#queueList');
    if (!root) return;
    root.replaceChildren();
    const proposals = api.state?.proposals || [];
    const pending = proposals.filter(item => item.status === 'pending');
    const decided = proposals.filter(item => item.status === 'approved');
    const items = [...pending, ...decided];
    text('#queueEyebrowCount', `${pending.length} WAITING`);
    const sortButton = $('#queueSort'); if (sortButton) sortButton.hidden = true;
    text('#queueSummaryNum', String(pending.length).padStart(2, '0'));
    text('#queueCount', String(pending.length).padStart(2, '0'));
    $('#queueEmpty').hidden = pending.length !== 0;
    root.style.display = items.length ? 'flex' : 'none';
    text('.queue-policy b', 'Backend proposals.');
    const policyCopy = $('.queue-policy span:nth-of-type(2)');
    if (policyCopy) policyCopy.textContent = 'Approvals use the existing Python policy and approval modules. Demo connectors are forced on; no real calendar event or email draft is created.';
    for (const item of items) {
      const card = document.createElement('article');
      card.className = `proposal-card${item.status === 'approved' ? ' decided' : ''}`;
      card.dataset.id = item.id;
      const kindName = item.kind === 'draft' ? 'DRAFT PROPOSAL' : item.kind === 'tracker' ? 'TRACKER RECORD' : 'CALENDAR REMINDER';
      const details = item.details || {};
      const facts = item.kind === 'reminder'
        ? `PROPOSED DATE <b>${h(dateLabel(details.start))}</b>`
        : item.kind === 'draft'
          ? 'DRAFT ONLY · NOT SENT'
          : `AMOUNT <b>${h(money(details.amount, 'INR'))}</b>`;
      const editFields = item.kind === 'draft' ? `<div class="integration-draft-fields"><label>Draft recipient<input data-draft="to" type="email" maxlength="254" value="${h(details.to || '')}" placeholder="Add recipient before approval" ${item.status === 'approved' ? 'disabled' : ''}></label><label>Subject<input data-draft="subject" maxlength="200" value="${h(details.subject || '')}" ${item.status === 'approved' ? 'disabled' : ''}></label><label>Draft body<textarea data-draft="body" maxlength="5000" ${item.status === 'approved' ? 'disabled' : ''}>${h(details.body || '')}</textarea></label></div>` : '';
      card.innerHTML = `<div class="proposal-rail rail-coral"></div><div class="proposal-content"><div class="proposal-top"><span class="proposal-type">${h(kindName)} · PYTHON BACKEND</span><span class="proposal-when">${h(item.status.toUpperCase())}</span></div><div class="proposal-heading"><div class="merchant-icon merchant-netflix">${h((item.title || 'S').slice(0, 1).toUpperCase())}</div><div><h2>${h(item.title)}</h2><p>${h(item.kind === 'draft' ? 'Review the unsent draft details before approving.' : item.kind === 'tracker' ? 'Add this item to the local tracker.' : 'Review this proposed reminder before approving.')}</p></div></div><div class="proposal-detail"><div class="proposal-facts"><span>${facts}</span></div>${item.source_snippet ? `<div class="proposal-quote"><span>${h(item.source_snippet)}</span><small>REDACTED SOURCE PROOF · LOCAL BACKEND</small></div>` : ''}${editFields}</div><div class="proposal-actions">${item.status === 'pending' ? `<button class="button button-approve proposal-action" data-action="approve">${item.kind === 'draft' ? 'Approve draft' : 'Approve proposal'} <span>✓</span></button><button class="button button-reject proposal-action" data-action="reject">Reject</button>` : '<span class="approval-explainer">Approved in local demo backend</span>'}${item.status === 'approved' ? '<button class="undo-hint" data-action="undo">Undo</button>' : ''}</div></div>`;
      root.append(card);
    }
  }

  function renderInbox() {
    const inbox = dedupedInbox();
    const list = $('#inboxList');
    if (!list) return;
    list.replaceChildren();
    text('.inbox-risk-banner b', 'Untrusted content stays in its lane.');
    const heading = $('.inbox-risk-banner span:nth-of-type(2)');
    if (heading) heading.textContent = 'The Python gateway sanitizes and redacts sample messages before this browser receives their display text.';
    if (!inbox.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-sample';
      empty.textContent = 'No messages loaded. Scan the bundled sample inbox to see backend results.';
      list.append(empty);
      text('#detailSender', 'Local Python backend');
      text('#detailDate', 'No message selected');
      text('#detailSubject', 'Run a sample scan to load messages');
      const body = $('#detailMessage');
      if (body) body.textContent = 'No message body is sent to the browser until the local backend has scanned and redacted a sample.';
      return;
    }
    inbox.forEach((item, index) => {
      const button = document.createElement('button');
      button.className = `email-item${index === 0 ? ' selected' : ''}${item.flags?.length ? ' flagged' : ''}`;
      button.dataset.emailId = item.id;
      button.innerHTML = `<span class="email-unread"></span><span class="email-brand ${item.flags?.length ? 'flagged-brand' : 'normal-brand'}">${item.flags?.length ? '!' : 'S'}</span><span class="email-copy"><b>Local sample <span class="email-risk ${item.flags?.length ? 'blocked' : 'normal'}">${item.flags?.length ? 'REVIEW FLAG' : 'BACKEND RESULT'}</span></b><strong>${h(item.subject)}</strong><small>${h(dateLabel(item.date))} · Redacted display</small></span><span class="email-amount">—</span>`;
      list.append(button);
    });
    showInbox(inbox[0].id);
  }

  function showInbox(id) {
    const item = dedupedInbox().find(row => row.id === id);
    if (!item) return;
    $$('.email-item', $('#inboxList')).forEach(button => button.classList.toggle('selected', button.dataset.emailId === id));
    text('#detailSender', 'Local sanitized source');
    text('#detailDate', `${item.source || 'sample'} · ${dateLabel(item.date)}`);
    text('#detailSubject', item.subject);
    const body = $('#detailMessage');
    if (body) { body.textContent = String(item.masked_body || '').replace(/<\/?untrusted_data>/g, ''); body.style.whiteSpace = 'pre-wrap'; }
    text('#extractMerchant', 'See renewal timeline');
    text('#extractPrice', 'From backend result');
    text('#extractPrevious', 'Not inferred');
    text('#extractDate', dateLabel((api.state?.subscriptions || []).find(sub => sub.source_email_id === id)?.renewal_date));
    const label = $('.source-label');
    if (label) label.textContent = 'SOURCE PROOF · REDACTED IN LOCAL PYTHON';
  }

  function renderTimeline() {
    const subs = api.state?.subscriptions || [];
    const stats = $$('.timeline-stats > div');
    const monthly = subs.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const hikes = subs.filter(item => (item.flags || []).includes('price_hike')).length;
    const trials = subs.filter(item => item.status === 'trial').length;
    if (stats[0]) { const b = stats[0].querySelector('b'); if (b) b.textContent = money(monthly); const small = stats[0].querySelector('small'); if (small) small.textContent = `${subs.length} local backend records`; }
    if (stats[1]) { const b = stats[1].querySelector('b'); if (b) b.textContent = String(hikes); const small = stats[1].querySelector('small'); if (small) small.textContent = 'From deterministic price comparison'; }
    if (stats[2]) { const b = stats[2].querySelector('b'); if (b) b.textContent = String(trials); const small = stats[2].querySelector('small'); if (small) small.textContent = 'From sample scan results'; }
    const calendar = $('#calendarGrid');
    if (calendar) {
      $$('.calendar-event', calendar).forEach(node => node.remove());
      for (const sub of subs) {
        if (!sub.renewal_date) continue;
        const d = new Date(`${String(sub.renewal_date).slice(0, 10)}T00:00:00`);
        if (d.getFullYear() !== 2026 || d.getMonth() !== 11) continue;
        const cell = $(`.calendar-day[data-day="${d.getDate()}"]`, calendar);
        if (!cell) continue;
        const event = document.createElement('span');
        event.className = `calendar-event ${(sub.flags || []).includes('price_hike') ? 'change' : ''}`;
        event.textContent = `${sub.merchant} · ${money(sub.amount, sub.currency)}`;
        cell.append(event);
      }
    }
    const upcoming = $('.upcoming-panel');
    if (upcoming) {
      $$('.upcoming-date', upcoming).forEach(node => node.remove());
      const list = [...subs].filter(item => item.renewal_date).sort((a, b) => String(a.renewal_date).localeCompare(String(b.renewal_date))).slice(0, 6);
      const heading = $('h2', upcoming);
      list.forEach(item => {
        const date = new Date(`${String(item.renewal_date).slice(0, 10)}T00:00:00`);
        const row = document.createElement('div');
        row.className = `upcoming-date${(item.flags || []).includes('price_hike') ? ' price-date' : ''}`;
        row.innerHTML = `<span class="upcoming-day">${h(String(date.getDate()).padStart(2, '0'))}</span><span><b>${h(item.merchant)}</b><small>${h(dateLabel(item.renewal_date))} · ${h(money(item.amount, item.currency))}</small></span><span class="upcoming-status">${h((item.flags || []).includes('price_hike') ? 'CHANGE' : item.status.toUpperCase())}</span>`;
        heading?.after(row);
      });
      if (!list.length) { const empty = document.createElement('p'); empty.className = 'empty-sample'; empty.textContent = 'Scan sample messages to build this timeline.'; heading?.after(empty); }
    }
  }

  function renderPrivacy() {
    const inbox = dedupedInbox();
    const original = $('#originalCopy');
    const masked = $('#maskedCopy');
    if (original) original.textContent = 'The original message remains inside the local Python process. It is not returned to this browser.';
    if (masked) masked.textContent = inbox[0]?.masked_body ? inbox[0].masked_body.replace(/<\/?untrusted_data>/g, '') : 'Run a sample scan to see the redacted text returned by ControlHub.';
    text('#redactionModeLabel', 'MASKED OUTPUT · LOCAL BACKEND');
    const toggle = $('#redactionToggle');
    if (toggle) { toggle.classList.add('active'); toggle.setAttribute('aria-checked', 'true'); }
    if (original) original.hidden = true;
    if (masked) masked.hidden = false;
    const disclaimer = $('.redaction-foot span');
    if (disclaimer) disclaimer.textContent = 'ONLY THE REDACTED DISPLAY TEXT IS SENT TO THIS LOCAL FRONTEND.';
  }

  function renderAudit() {
    const entries = api.state?.audit || [];
    const root = $('#auditRows');
    if (!root) return;
    root.replaceChildren();
    entries.forEach(entry => {
      const row = document.createElement('div');
      row.className = `audit-row${entry.decision === 'block' ? ' blocked' : entry.decision === 'ask' ? ' approval' : ''}`;
      const hash = String(entry.hash || '');
      row.innerHTML = `<span class="audit-event"><i></i>${h(entry.action)} · ${h(entry.detail || '')}</span><span>${h(entry.actor)} / ${h(entry.tool)}</span><span class="audit-decision">${h(String(entry.decision || '').toUpperCase())}</span><span class="hash-cell">${h(hash ? `${hash.slice(0, 6)}…${hash.slice(-4)}` : '—')}</span>`;
      root.append(row);
    });
    const integrity = api.state?.audit_integrity || { valid: true };
    text('#integrityStatus', integrity.valid ? 'Verified' : 'Broken');
    text('#integritySub', `${entries.length} backend entries · ${integrity.valid ? 'chain intact' : `first break at #${integrity.broken_at}`}`);
    text('#blockedCount', String(entries.filter(entry => entry.decision === 'block').length).padStart(2, '0'));
    text('#verifiedTime', new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const foot = $('.audit-table-foot span');
    if (foot) foot.textContent = 'SHA-256 HASH CHAIN · LOCAL PYTHON BACKEND';
    const warning = $('.audit-warning');
    if (warning) {
      const content = warning.firstChild;
      if (content) content.textContent = 'This view reads the actual local Python audit chain. Verification uses the backend hash checker; sample-only tamper/wipe controls are disabled. ';
    }
    ['#tamperButton', '#resetAudit', '#wipeDemoData'].forEach(selector => { const button = $(selector); if (button) button.hidden = true; });
  }

  function renderState() {
    if (!api.state?.backend_connected) return;
    setConnection(true, 'Connected to the local Python backend in safe sample mode. Bundled fixtures only; no live Gmail, Calendar, or model access.');
    const headerText = $('.demo-pill');
    if (headerText) headerText.title = 'Local Python backend connected; sample connectors only.';
    renderSubscriptions();
    renderQueue();
    renderInbox();
    renderTimeline();
    renderPrivacy();
    renderAudit();
    const killPanel = $('#killPanel');
    if (killPanel) {
      killPanel.classList.toggle('paused', api.state.killed);
      text('#killTitle', api.state.killed ? 'Sentinel is paused' : 'Sentinel is watching');
      text('#killSub', api.state.killed ? 'Local demo tools are blocked' : 'Local Python backend · sample mode');
      const toggle = $('#killToggle');
      if (toggle) toggle.setAttribute('aria-label', api.state.killed ? 'Resume local demo' : 'Pause local demo');
      text('#killAction', api.state.killed ? 'Resume local demo' : 'Pause local backend');
    }
    const scan = api.state.last_scan_at;
    if (scan) text('#lastScanTime', new Date(scan).toLocaleString());
    const summary = $('.overview-footer');
    if (summary) summary.querySelector('span:last-child')?.replaceChildren(document.createTextNode('LOCAL PYTHON BACKEND · SAMPLE FIXTURES'));
  }

  async function refresh() {
    const response = await request('/api/state');
    api.state = response;
    window.SentinelBackendState = api.state;
    renderState();
  }

  async function doScan(button) {
    if (api.state?.killed) { notify('Sentinel is paused by the local backend kill switch.'); return; }
    const original = button.innerHTML;
    button.disabled = true;
    button.classList.add('is-loading');
    button.innerHTML = '<span>Scanning local sample messages…</span>';
    try {
      const response = await request('/api/scan', 'POST', {});
      api.state = response.state;
      window.SentinelBackendState = api.state;
      renderState();
      notify(`Local scan complete: ${api.state.subscriptions.length} subscriptions · ${api.state.proposals.filter(item => item.status === 'pending').length} waiting for review.`);
    } catch (error) { notify(error.message); }
    finally { button.disabled = false; button.classList.remove('is-loading'); button.innerHTML = original; }
  }

  async function doProposalAction(button, card) {
    const id = card.dataset.id;
    const action = button.dataset.action;
    if (!id || !action) return;
    const edits = {};
    $$('[data-draft]', card).forEach(field => { edits[field.dataset.draft] = field.value; });
    button.disabled = true;
    try {
      const response = await request(`/api/approvals/${encodeURIComponent(id)}/${action}`, 'POST', { edits });
      api.state = response.state;
      window.SentinelBackendState = api.state;
      renderState();
      notify(action === 'approve' ? 'Approval recorded by the local Python backend (sample mode).' : action === 'reject' ? 'Proposal dismissed in the local backend.' : 'Approval undone in the local backend.');
    } catch (error) { notify(error.message); button.disabled = false; }
  }

  function confirmKillSwitch() {
    const proceed = async () => {
      try {
        const response = await request(api.state?.killed ? '/api/resume' : '/api/kill', 'POST', {});
        api.state = response.state;
        window.SentinelBackendState = api.state;
        renderState();
        notify(api.state.killed ? 'Local backend kill switch is active.' : 'Local demo backend resumed.');
      } catch (error) { notify(error.message); }
    };
    if (api.state?.killed) { proceed(); return; }
    if (typeof window.askConfirm === 'function') window.askConfirm('Pause Sentinel?', 'This blocks the local demo backend. It does not affect Gmail or Calendar because live connectors are disabled.', 'Pause local backend', proceed);
    else if (window.confirm('Pause the local Sentinel demo backend?')) proceed();
  }

  function exportCsv() {
    const subs = api.state?.subscriptions || [];
    const rows = [['Merchant', 'Amount', 'Currency', 'Status', 'Renewal date'], ...subs.map(item => [item.merchant, item.amount, item.currency, item.status, item.renewal_date || ''])];
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const link = document.createElement('a'); link.href = url; link.download = 'sentinel-local-backend.csv'; link.click(); URL.revokeObjectURL(url);
    notify('Downloaded subscription rows from the local backend.');
  }

  document.addEventListener('click', async event => {
    const loginButton = event.target.closest('#loginButton');
    if (loginButton) {
      event.preventDefault(); event.stopImmediatePropagation();
      const continueAsDemo = () => {
        loginButton.textContent = 'Demo User';
        loginButton.classList.add('is-signed-in');
        loginButton.setAttribute('aria-label', 'Signed in as the local demo user; sample data only');
        notify('Demo session active. No Google account was connected.');
      };
      if (typeof window.askConfirm === 'function') {
        window.askConfirm('Sign in to Sentinel', 'This local frontend uses the sample-only Python backend. Continue as the demo user; this does not authenticate with Google or access live Gmail or Calendar. The repository’s Google OAuth helper is a separate desktop setup.', 'Continue in demo mode', continueAsDemo);
      } else {
        notify('This frontend is sample-only; Google sign-in is not connected.');
      }
      return;
    }
    if (!api.state?.backend_connected) return;
    const scan = event.target.closest('#scanButton, #inboxScanButton');
    if (scan) { event.preventDefault(); event.stopImmediatePropagation(); doScan(scan); return; }
    const proposalButton = event.target.closest('#queueList .proposal-card [data-action]');
    if (proposalButton) { event.preventDefault(); event.stopImmediatePropagation(); doProposalAction(proposalButton, proposalButton.closest('.proposal-card')); return; }
    const emailButton = event.target.closest('#inboxList .email-item[data-email-id]');
    if (emailButton) { event.preventDefault(); event.stopImmediatePropagation(); showInbox(emailButton.dataset.emailId); return; }
    if (event.target.closest('#queueEmail')) { event.preventDefault(); event.stopImmediatePropagation(); window.setSentinelView?.('queue'); notify('Review the proposals created by the local backend scan.'); return; }
    if (event.target.closest('#redactionToggle')) { event.preventDefault(); event.stopImmediatePropagation(); const toggle = $('#redactionToggle'); toggle.classList.add('active'); toggle.setAttribute('aria-checked', 'true'); if ($('#originalCopy')) $('#originalCopy').hidden = true; if ($('#maskedCopy')) $('#maskedCopy').hidden = false; notify('Only the redacted backend view is sent to this browser.'); return; }
    if (event.target.closest('#redactionSimulate')) { event.preventDefault(); event.stopImmediatePropagation(); notify('The backend has already redacted this sample before returning it.'); return; }
    if (event.target.closest('#killToggle, #killAction')) { event.preventDefault(); event.stopImmediatePropagation(); confirmKillSwitch(); return; }
    if (event.target.closest('#exportCsv')) { event.preventDefault(); event.stopImmediatePropagation(); exportCsv(); return; }
    if (event.target.closest('#attackButton')) {
      event.preventDefault(); event.stopImmediatePropagation();
      try { const response = await request('/api/simulate-block', 'POST', {}); api.state = response.state; window.SentinelBackendState = api.state; renderState(); notify(response.blocked ? 'ControlHub blocked the test action; nothing was sent.' : 'The backend did not block the test action.'); }
      catch (error) { notify(error.message); }
      return;
    }
    if (event.target.closest('#verifyAudit')) {
      event.preventDefault(); event.stopImmediatePropagation();
      try { const response = await request('/api/audit/verify', 'POST', {}); api.state = response.state; window.SentinelBackendState = api.state; renderState(); notify(response.valid ? 'Local SHA-256 audit chain is intact.' : `Audit chain mismatch at entry ${response.broken_at}.`); }
      catch (error) { notify(error.message); }
      return;
    }
    const dayCell = event.target.closest('#calendarGrid .calendar-day[data-day]');
    if (dayCell) {
      event.preventDefault(); event.stopImmediatePropagation();
      const day = String(dayCell.dataset.day).padStart(2, '0');
      const hits = (api.state?.subscriptions || []).filter(item => item.renewal_date && item.renewal_date.slice(8, 10) === day && item.renewal_date.slice(0, 7) === '2026-12');
      notify(hits.length ? hits.map(item => `${item.merchant} · ${money(item.amount, item.currency)}`).join(' / ') : `No backend renewals on December ${Number(day)}.`);
    }
  }, true);

  document.addEventListener('keydown', event => {
    if (api.state?.backend_connected && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); event.stopImmediatePropagation();
      const button = $('#scanButton'); if (button) doScan(button);
    }
  }, true);

  setConnection(false, 'Backend offline. Run “py run_frontend.py” from the Sentinel repo to connect this dashboard to its local Python backend. The visible sample dashboard still works.');
  refresh().catch(error => {
    console.warn('[Sentinel] local backend unavailable:', error.message);
  });
})();
