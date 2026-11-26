/* Animated, frontend-only Sentinel landing page. All figures and UI previews are synthetic. */
(() => {
  const viewTitles = window.__sentinelViewTitles;
  const titleMap = { home: 'Home', overview: 'Dashboard', inbox: 'Inbox review', queue: 'Approval queue', timeline: 'Renewal timeline', privacy: 'What the AI saw', audit: 'Audit log' };

  const nav = document.querySelector('.side-nav');
  const homeButton = document.createElement('button');
  homeButton.className = 'nav-item landing-nav active';
  homeButton.dataset.view = 'home';
  homeButton.innerHTML = '<span class="nav-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-8 9 8v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg></span><span>Home</span><span class="nav-shortcut">00</span>';
  nav.prepend(homeButton);
  const brand = document.querySelector('.brand');
  if (brand) { brand.href = '#home'; brand.dataset.viewLink = 'home'; }
  const logoMark = document.querySelector('.brand-emblem svg');
  if (logoMark) logoMark.innerHTML = '<path d="M18 2 32 8v10c0 9-5.8 15.3-14 20C9.8 33.3 4 27 4 18V8z"/><path class="brand-check" d="m10.5 20 5.2 5.2L26 14.8"/>';

  const overviewButton = document.querySelector('.nav-item[data-view="overview"]');
  if (overviewButton) overviewButton.querySelector('span:nth-child(2)').textContent = 'Dashboard';

  const home = document.createElement('section');
  home.className = 'view landing-view active';
  home.id = 'view-home';
  home.dataset.title = titleMap.home;
  home.innerHTML = `
    <section class="landing-hero" aria-labelledby="landingTitle">
      <div class="landing-orbit orbit-one" aria-hidden="true"></div><div class="landing-orbit orbit-two" aria-hidden="true"></div>
      <div class="landing-copy">
        <div class="landing-kicker"><span class="landing-kicker-dot"></span> YOUR QUIET, LOCAL-FIRST WATCHTOWER</div>
        <h1 id="landingTitle">Money leaks<br><span>quietly.</span><br>Sentinel catches<br><span class="landing-word-wrap"><span id="landingWord">forgotten trials.</span></span></h1>
        <p class="landing-lead">Spot price jumps, trials, and upcoming bills—with the source proof in view and your approval in control.</p>
        <div class="landing-actions"><button class="button button-dark landing-primary" data-view-link="overview">Explore the watchtower <span>↗</span></button><button class="button button-outline landing-secondary" data-view-link="privacy">See privacy, visibly <span>→</span></button></div>
        <div class="landing-reassurance"><span><i></i> Synthetic sample data</span><span><i></i> No accounts connected</span><span><i></i> Nothing sent</span></div>
      </div>
      <div class="landing-stage landing-reveal">
        <div class="landing-stage-head"><span><i></i> THIS WEEK / DEMO SNAPSHOT</span><b>SAMPLE / LOCAL</b></div>
        <div class="landing-total">₹2,847<small>sample recurring spend / month</small></div>
        <div class="landing-bars" aria-hidden="true"><i style="--bar:32%"></i><i style="--bar:50%"></i><i style="--bar:43%"></i><i style="--bar:68%"></i><i style="--bar:56%"></i><i style="--bar:79%"></i><i style="--bar:63%"></i><i style="--bar:94%"></i><i style="--bar:74%"></i><i style="--bar:100%"></i></div>
        <div class="landing-preview-title"><span>ONE CHANGE TO REVIEW</span><span class="landing-risk">+30%</span></div>
        <article class="landing-price-card"><div class="landing-merchant">N</div><div class="landing-price-copy"><b>Netflix Premium</b><small>Source: synthetic billing notice</small></div><div class="landing-price-amount"><s>₹499</s><b>₹649</b></div></article>
        <div class="landing-proof"><span>“Your plan will change to ₹649/month starting December 1.”</span><small>EXACT SOURCE LINE · SAMPLE ONLY</small></div>
        <div class="landing-stage-foot"><span><i></i> NOTHING MOVES WITHOUT YOU</span><button data-view-link="queue">Review proposals ↗</button></div>
        <div class="landing-orbit-badge"><span>CONTROLHUB</span><b>ASK</b><small>approval first</small></div>
      </div>
      <a href="#landingFlow" class="landing-scroll" aria-label="Scroll to see how Sentinel works"><span></span> SCROLL TO SEE THE FLOW</a>
    </section>
    <div class="landing-ticker" aria-label="Sentinel demo capabilities"><div class="landing-ticker-track"><span>PRICE HIKES, FLAGGED</span><b>◆</b><span>TRIALS, REMEMBERED</span><b>◆</b><span>PRIVATE DETAILS, MASKED</span><b>◆</b><span>EVERY ACTION, YOUR CALL</span><b>◆</b><span>PRICE HIKES, FLAGGED</span><b>◆</b><span>TRIALS, REMEMBERED</span><b>◆</b><span>PRIVATE DETAILS, MASKED</span><b>◆</b><span>EVERY ACTION, YOUR CALL</span><b>◆</b></div></div>
    <section class="landing-flow landing-reveal" id="landingFlow"><div class="landing-section-head"><div><span class="landing-eyebrow">HOW SENTINEL WORKS / DEMO FLOW</span><h2>Proof first.<br><span>Actions last.</span></h2></div><p>Every surface below uses synthetic records. The interface demonstrates Sentinel’s guardrails without connecting to an inbox, calendar, bank, or model.</p></div>
      <div class="landing-steps"><button class="landing-step" data-view-link="inbox"><span class="landing-step-num">01</span><span class="landing-step-icon step-icon-coral"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4z"/><path d="m4 7 8 6 8-6M4 15h5l2 2h3l2-2h4"/></svg></span><b>Read the evidence</b><p>Review a sample billing message with the exact line that supports the proposal.</p><span class="landing-step-link">Open inbox review <i>↗</i></span></button><button class="landing-step featured-step" data-view-link="privacy"><span class="landing-step-num">02</span><span class="landing-step-icon step-icon-cream"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg></span><b>Mask what’s private</b><p>See synthetic personal details switch to placeholders before the AI view.</p><span class="landing-step-link">See the privacy view <i>↗</i></span></button><button class="landing-step" data-view-link="queue"><span class="landing-step-num">03</span><span class="landing-step-icon step-icon-green"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 20 6v6c0 5-3.3 8-8 10-4.7-2-8-5-8-10V6z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg></span><b>You decide what moves</b><p>Approve, reject, or undo sample proposals. No external action is available.</p><span class="landing-step-link">Open approval queue <i>↗</i></span></button></div>
    </section>
    <section class="landing-lastcall landing-reveal"><div><span class="landing-eyebrow">A SMALL, CALM PROMISE</span><h2>Your subscriptions,<br><span>under your control.</span></h2></div><div class="landing-boundaries"><span><b>0</b> connected bank accounts</span><span><b>0</b> messages sent by this demo</span><span><b>100%</b> synthetic sample records</span><button data-view-link="audit">Inspect policy &amp; audit ↗</button></div></section>`;

  const main = document.querySelector('.page-content');
  const banner = document.querySelector('.global-demo-banner');
  main.insertBefore(home, banner.nextSibling);

  if (viewTitles) viewTitles.home = titleMap.home;
  homeButton.addEventListener('click', () => window.setSentinelView('home'));

  const requested = location.hash.replace('#', '');
  window.setSentinelView(titleMap[requested] ? requested : 'home');

  const phrases = ['forgotten trials.', 'price hikes.', 'buried bills.', 'sneaky renewals.'];
  const word = document.querySelector('#landingWord');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reducedMotion) window.setInterval(() => {
    word.classList.add('word-out');
    window.setTimeout(() => {
      const next = (phrases.indexOf(word.textContent) + 1) % phrases.length;
      word.textContent = phrases[next];
      word.classList.remove('word-out');
      word.classList.add('word-in');
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => word.classList.remove('word-in')));
    }, 300);
  }, 2800);

  if (!reducedMotion && 'IntersectionObserver' in window) {
    const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('revealed'); reveal.unobserve(entry.target); }
    }), { threshold: .14 });
    document.querySelectorAll('.landing-reveal').forEach(node => reveal.observe(node));
  } else {
    document.querySelectorAll('.landing-reveal').forEach(node => node.classList.add('revealed'));
  }
})();
