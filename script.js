/* ═══════════════════════════════════
   LSF Website v3 — Hormozi Edition
═══════════════════════════════════ */

const I = {
  arr: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  star: '★',
  check: '✓',
};

/* ── Navigation ── */
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const target = document.getElementById('page-' + page);
  if (target) { target.classList.add('active'); }
  const navBtn = document.querySelector(`.nav-link[data-page="${page}"]`);
  if (navBtn) navBtn.classList.add('active');
  document.getElementById('mobile-nav')?.classList.remove('open');
  window.scrollTo({ top: 0, behavior: 'instant' });
  setTimeout(initReveal, 50);
  setTimeout(initCounters, 100);
}

/* ── Scroll Reveal ── */
function initReveal() {
  const els = document.querySelectorAll('.reveal:not(.visible)');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.15 });
  els.forEach(el => obs.observe(el));
}

/* ── Counter animation ── */
function animateCounter(el) {
  const end = parseInt(el.dataset.end, 10);
  const suffix = el.dataset.suffix || '';
  const prefix = el.dataset.prefix || '';
  const steps = 50, dur = 2000, inc = end / steps;
  let cur = 0;
  const t = setInterval(() => {
    cur = Math.min(cur + inc, end);
    el.textContent = prefix + Math.floor(cur).toLocaleString() + suffix;
    if (cur >= end) clearInterval(t);
  }, dur / steps);
}

function initCounters() {
  const counters = document.querySelectorAll('.counter:not([data-ran])');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && !e.target.dataset.ran) {
        e.target.dataset.ran = '1';
        animateCounter(e.target);
      }
    });
  }, { threshold: 0.3 });
  counters.forEach(c => obs.observe(c));
}

/* ── Rep Finder ── */
const reps = {
  dfw:     { ini:'BH', name:'Ben Herrick',            title:'President — DFW & North Texas',       phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'20+' },
  houston: { ini:'HT', name:'Houston Territory Team',  title:'Houston Metro Specialist',            phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'12+' },
  central: { ini:'CT', name:'Central Texas Team',      title:'Austin / Central Texas Manager',       phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'10+' },
  south:   { ini:'ST', name:'South Texas Territory',   title:'San Antonio / South Texas Director',   phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'15+' },
};

function findRep() {
  const sel = document.getElementById('rep-region').value;
  const box = document.getElementById('rep-result');
  if (!sel || !reps[sel]) { box.classList.remove('show'); return; }
  const r = reps[sel];
  box.innerHTML = `
    <div class="rep-avatar">${r.ini}</div>
    <div class="rep-info">
      <h3>${r.name}</h3>
      <div class="rep-title">${r.title} · ${r.yrs} Yrs K–12 Experience</div>
      <div class="rep-contacts">
        <a href="tel:${r.phone.replace(/\D/g,'')}">📞 ${r.phone}</a>
        <a href="mailto:${r.email}">✉ ${r.email}</a>
      </div>
    </div>
    <button class="rep-book-btn" onclick="navigateTo('contact')">Book 15-Min Call</button>
  `;
  box.classList.add('show');
}

/* ── Contact Form ── */
function handleContactSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('form-submit-btn');
  btn.textContent = 'Submitting…';
  btn.disabled = true;
  setTimeout(() => {
    document.getElementById('contact-form').style.display = 'none';
    document.getElementById('form-success').classList.add('show');
  }, 1500);
}
function resetForm() {
  document.getElementById('contact-form').style.display = 'block';
  document.getElementById('contact-form').reset();
  document.getElementById('form-success').classList.remove('show');
  const btn = document.getElementById('form-submit-btn');
  btn.innerHTML = 'Get My Free Project Audit ' + I.arr;
  btn.disabled = false;
}

/* ── Mobile menu ── */
function toggleMobileMenu() {
  const nav = document.getElementById('mobile-nav');
  const btn = document.getElementById('mobile-menu-btn');
  const open = nav.classList.toggle('open');
  btn.textContent = open ? '✕' : '☰';
}

/* ═══════════════════════════════════
   PAGE RENDERS
═══════════════════════════════════ */

function renderHome() {
  const marqueeItems = ['250+ Texas ISDs Served','1,000+ Projects Delivered','100% On-Time Record','BuyBoard Approved','TIPS / TAPS Approved','18 Years in Texas','White-Glove Installation','Local Staging in DFW & Houston','100+ Manufacturer Partners','Zero-Surprise Pricing'];
  const marqueeHTML = marqueeItems.map(i => `<span class="marquee-item"><span class="marquee-dot"></span>${i}</span>`).join('');

  return `
  <!-- HERO -->
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-badge reveal">🛡️ Texas K–12 FF&E Specialists · Serving ISDs Since 2008</div>
      <h1 class="sf reveal reveal-d1">We Furnish Your Schools.<br><span class="gold-text">You Get the Credit.</span></h1>
      <p class="hero-sub reveal reveal-d2">We handle every desk, every chair, every deadline — so when your superintendent walks the hallway on Day 1 and everything is perfect, <strong style="color:white;">that's your win.</strong></p>
      
      <div class="hero-proof reveal reveal-d2">
        <div class="hero-proof-item"><strong>250+</strong> ISDs Served</div>
        <div class="hero-proof-sep"></div>
        <div class="hero-proof-item"><strong>1,000+</strong> Projects</div>
        <div class="hero-proof-sep"></div>
        <div class="hero-proof-item"><strong>100%</strong> On-Time</div>
      </div>

      <div class="hero-btns reveal reveal-d3">
        <button class="btn-cta" onclick="navigateTo('contact')">Get Your Free Project Audit ${I.arr}</button>
        <button class="btn-ghost" onclick="navigateTo('projects')">See the Proof</button>
      </div>
      <div class="hero-risk reveal reveal-d4">
        <span>✓ No risk.</span> Free audit. No obligation. We'll show you exactly what your project would cost.
      </div>
    </div>
  </section>

  <!-- MARQUEE -->
  <div class="marquee-wrap">
    <div class="marquee-track">${marqueeHTML}${marqueeHTML}</div>
  </div>

  <!-- STATS -->
  <section class="stats-bar">
    <div class="stats-grid">
      <div class="stat-cell"><div class="stat-number sf"><span class="counter" data-end="18" data-suffix="+">0</span></div><div class="stat-label">Years in Texas</div></div>
      <div class="stat-cell"><div class="stat-number sf"><span class="counter" data-end="250" data-suffix="+">0</span></div><div class="stat-label">ISDs Served</div></div>
      <div class="stat-cell"><div class="stat-number sf"><span class="counter" data-end="1000" data-suffix="+">0</span></div><div class="stat-label">Projects Completed</div></div>
      <div class="stat-cell"><div class="stat-number sf"><span class="counter" data-end="100" data-suffix="%">0</span></div><div class="stat-label">On-Time Rate</div></div>
    </div>
  </section>

  <!-- PROBLEM / AGITATION -->
  <section class="section section-dark">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">The real problem</div>
        <h2 class="sf">You Don't Have a Furniture Problem.<br>You Have a <span style="color:var(--danger)">Coordination</span> Problem.</h2>
        <p>Right now, you're managing 4–12 different vendors, a freight company that won't return calls, and an installer who shows up when he feels like it. That's not a furniture project. That's a second full-time job you didn't sign up for.</p>
      </div>
      <div class="problem-grid">
        <div class="problem-card reveal"><div class="p-num">01</div><h3>The RFP Trap</h3><p>You spend <span class="strike">120+ hours</span> on procurement paperwork when you could be <strong>using our co-op contracts</strong> and skip the bid entirely — legally and compliantly.</p></div>
        <div class="problem-card reveal reveal-d1"><div class="p-num">02</div><h3>The Finger-Pointing Loop</h3><p>Manufacturer blames freight. Freight blames installer. Installer blames you. Nobody owns the outcome — so <strong>you absorb the failure</strong>. Every time.</p></div>
        <div class="problem-card reveal reveal-d2"><div class="p-num">03</div><h3>The Day-1 Panic</h3><p>25 classrooms. 3 still have furniture in boxes. Teachers improvise with folding chairs. Board members walk in. <strong>That's your reputation on the line.</strong></p></div>
      </div>
    </div>
  </section>

  <!-- OFFER STACK -->
  <section class="section section-dark" style="padding-top:0;">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">What you actually get</div>
        <h2 class="sf">Here's What We Take Off Your Plate<br><em style="color:var(--gold);">(And What It's Worth)</em></h2>
      </div>
      <div class="offer-grid">
        <div class="offer-card reveal"><div class="o-tag">Included</div><h3>Full 3D Space Planning & Renderings</h3><p>Photo-realistic visuals of every room — before you spend a dollar. Boards approve these in one meeting, not three.</p>
          <ul class="offer-bullets"><li>Custom 3D renderings within 72 hours</li><li>Unlimited revisions until you're satisfied</li><li>Board-ready presentation packages</li></ul></div>
        <div class="offer-card reveal reveal-d1"><div class="o-tag">Included</div><h3>Co-Op Procurement Management</h3><p>We process everything through BuyBoard, TIPS, or Choice Partners — your purchasing team touches nothing except the final PO approval.</p>
          <ul class="offer-bullets"><li>Complete bid exemption via active contracts</li><li>Line-item transparency on every quote</li><li>Full audit-ready documentation</li></ul></div>
        <div class="offer-card reveal reveal-d2"><div class="o-tag">Included</div><h3>White-Glove Installation</h3><p>Our W-2 crews unbox, assemble, place to spec, and haul every shred of packaging. You walk in, flip the lights, and it's done.</p>
          <ul class="offer-bullets"><li>W-2 employees, not day-labor subcontractors</li><li>Dedicated on-site project manager</li><li>Same-day damage resolution from local stock</li></ul></div>
        <div class="offer-card reveal reveal-d3"><div class="o-tag">Included</div><h3>Post-Install Warranty & Support</h3><p>If a chair breaks in Year 2, you call one number. We handle the manufacturer claim, the replacement, and the install. You do nothing.</p>
          <ul class="offer-bullets"><li>Single point of contact for all warranty</li><li>We manage every manufacturer claim</li><li>Free labor on all warranty replacements</li></ul></div>
      </div>
    </div>
  </section>

  <!-- PROCESS -->
  <section class="section section-dark" style="padding-top:0;">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">How it works</div>
        <h2 class="sf">3 Steps. Zero Surprises.</h2>
        <p>From first call to first bell. Here's exactly what happens.</p>
      </div>
      <div class="process-steps">
        <div class="process-step reveal"><div class="step-num">1</div><h3>Free Project Audit</h3><p>We visit your site, audit your spaces, understand your timeline and budget, and deliver a complete project scope — at zero cost. You decide if we're the right fit.</p></div>
        <div class="process-step reveal reveal-d1"><div class="step-num">2</div><h3>Design, Specify & Lock Pricing</h3><p>3D renderings. Co-op-aligned specifications. A fixed price that doesn't move. You get board-ready documents and a guaranteed budget number.</p></div>
        <div class="process-step reveal reveal-d2"><div class="step-num">3</div><h3>We Install. You Turn the Key.</h3><p>We stage locally, install during your window, and leave every room teacher-ready. You walk the building and take the credit. That's it.</p></div>
      </div>
    </div>
  </section>

  <!-- GUARANTEE -->
  <section class="section section-dark" style="padding-top:0;">
    <div class="guarantee-box reveal">
      <div class="eyebrow eyebrow-center" style="margin-bottom:20px;">Our guarantee</div>
      <h2 class="sf">Teacher-Ready Rooms on Day 1 —<br><span class="gold-text">Or We Pay for It.</span></h2>
      <p>If any room isn't fully assembled, placed to spec, and ready for students when we said it would be, <strong style="color:white">we cover the cost of making it right — including any interim solutions your teachers need.</strong> No exceptions. No fine print.</p>
      <button class="btn-cta" onclick="navigateTo('contact')">Get Your Free Project Audit — Zero Risk ${I.arr}</button>
    </div>
  </section>

  <!-- TESTIMONIALS -->
  <section class="section section-dark">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">Don't take our word for it</div>
        <h2 class="sf">What Texas Districts Say After Working With Us</h2>
      </div>
      <div class="testimonials-grid">
        <div class="test-card reveal"><div class="test-stars">★★★★★</div><blockquote>"Lone Star managed our entire district refresh without a single delay. When supply chain issues threatened our timeline, they pulled from local inventory and never missed a beat. Not one classroom was late."</blockquote><div class="test-footer"><div><div class="test-name">Director of Operations</div><div class="test-dist">Godley ISD</div></div><span class="test-tag">District Refresh</span></div></div>
        <div class="test-card reveal reveal-d1"><div class="test-stars">★★★★★</div><blockquote>"Using their BuyBoard contract saved our team weeks of paperwork. The install crew left every room spotless. We won't use anyone else — they've earned our repeat business for every future bond project."</blockquote><div class="test-footer"><div><div class="test-name">Purchasing Coordinator</div><div class="test-dist">Lumberton ISD</div></div><span class="test-tag">Campus FF&E</span></div></div>
        <div class="test-card reveal reveal-d2"><div class="test-stars">★★★★★</div><blockquote>"The 3D renderings got us board approval in one meeting — not three. The STEM labs look exactly like the pictures. Students and teachers genuinely love the new spaces. Best vendor experience we've had."</blockquote><div class="test-footer"><div><div class="test-name">Assistant Superintendent</div><div class="test-dist">Angleton ISD</div></div><span class="test-tag">CTE Labs</span></div></div>
      </div>
    </div>
  </section>

  <!-- REP FINDER -->
  <section class="rep-section">
    <div class="section-inner" style="max-width:860px;margin:0 auto;">
      <div class="section-header reveal" style="margin-bottom:40px;">
        <div class="eyebrow eyebrow-center">Talk to a real human, fast</div>
        <h2 class="sf" style="font-size:clamp(24px,3.8vw,40px);">Find Your Dedicated Territory Manager</h2>
        <p>Not a call center. Not a chatbot. A real person who knows your region.</p>
      </div>
      <div class="rep-finder-box reveal">
        <div class="rep-finder-row">
          <div class="rep-finder-select-wrap">
            <label>Your Texas Region</label>
            <select id="rep-region" onchange="document.getElementById('rep-result').classList.remove('show')">
              <option value="" disabled selected>Select your metro / region…</option>
              <option value="dfw">Dallas / Fort Worth (ESC 10 & 11)</option>
              <option value="houston">Houston Metro (ESC 4)</option>
              <option value="central">Austin / Central Texas (ESC 13)</option>
              <option value="south">San Antonio / South Texas (ESC 20)</option>
            </select>
          </div>
          <button class="rep-find-btn" onclick="findRep()">🔍 Find My Rep</button>
        </div>
        <div class="rep-result" id="rep-result"></div>
      </div>
    </div>
  </section>

  <!-- FINAL CTA -->
  <section class="final-cta">
    <div class="section-inner reveal">
      <div class="eyebrow eyebrow-center" style="margin-bottom:20px;">Ready?</div>
      <h2 class="sf">Stop Coordinating Vendors.<br><span class="gold-text">Start Taking Credit.</span></h2>
      <p>Get a free, no-obligation project audit. We'll show you exactly how we'd execute your project — with pricing, timeline, and 3D renderings. Keep everything even if you don't hire us.</p>
      <button class="btn-cta" onclick="navigateTo('contact')" style="margin:0 auto;">Get My Free Project Audit ${I.arr}</button>
      <div class="hero-risk" style="justify-content:center;margin-top:16px;"><span>✓ Free.</span>&nbsp;No obligation. Keep the audit even if you go with someone else.</div>
    </div>
  </section>
  `;
}

/* ── SOLUTIONS ── */
function renderSolutions() {
  const spaces = [
    { tag:'Most Requested', title:'Flexible Classrooms', body:'Lecture to collaborative pods in 60 seconds. Mobile nesting furniture, height-adjustable surfaces, and 1:1 device-ready power routing for modern pedagogy.', specs:['ADA desk ratio compliance','Caster grade for VCT vs. carpet','Integrated power management','Mobile whiteboard compatibility'], img:'https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&q=80&w=800' },
    { tag:'High Demand', title:'CTE & STEM Labs', body:'Purpose-built worksurfaces, robust storage, and pathway-specific configurations — coding, healthcare, culinary, welding, and beyond.', specs:['Utility knockout for trades','Chemical-resistant laminate','ADA compliance in active labs','Heavy-duty equipment casters'], img:'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&q=80&w=800' },
    { tag:'', title:'Library & Media Centers', body:'Quiet study zones to active maker spaces. Soft seating, acoustic dampening, and flexible layouts for multiple simultaneous learning modes.', specs:['Sightline management for staff','50k+ rub-count commercial fabric','Integrated power in lounge seating','Zoned acoustic absorption'], img:'https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&q=80&w=800' },
    { tag:'', title:'Cafeteria & Commons', body:'High-traffic durability meets clean design. Tables that stack, fold, and survive 180 days of K–12 abuse — without looking like they have.', specs:['Seat density optimization','Folding vs. fixed analysis','ADA table height mixing','Anti-graffiti finish options'], img:'https://images.unsplash.com/photo-1567521464027-f127ff144326?auto=format&fit=crop&q=80&w=800' },
  ];
  return `
  <section class="section section-dark">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">Every space. One partner.</div>
        <h1 class="sf" style="font-size:clamp(30px,4.5vw,52px);">Spaces Engineered for<br><span class="gold-text">15 Years of K–12 Abuse.</span></h1>
        <p>We don't sell catalogs. We design environments that reduce discipline issues, support 6 different learning configurations, and outlast your next bond cycle.</p>
      </div>
      <div class="sol-grid">
        ${spaces.map(s => `
          <div class="sol-card reveal">
            <div class="sol-card-img"><img src="${s.img}" alt="${s.title}"/>${s.tag ? `<span class="sol-img-tag">${s.tag}</span>` : ''}</div>
            <div class="sol-card-body">
              <h3>${s.title}</h3>
              <p>${s.body}</p>
              <div class="sol-specs"><div class="sol-specs-label">Planning Considerations</div><ul>${s.specs.map(sp => `<li>${sp}</li>`).join('')}</ul></div>
              <div class="sol-btns">
                <button class="sol-btn-primary" onclick="navigateTo('contact')">Get a Quote</button>
                <button class="sol-btn-secondary">Download Spec Sheet</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
      <div class="sol-mfr-box reveal" style="margin-top:3px;">
        <h3 class="sf">One PO. 100+ Manufacturers.</h3>
        <p>KI, Virco, Smith System, Fomcore, VS America, and dozens more — consolidated into a single co-op purchase order. No juggling vendor relationships. No surprises.</p>
        <button class="btn-cta" onclick="navigateTo('contact')">Request Our Full Line Card ${I.arr}</button>
      </div>
    </div>
  </section>
  `;
}

/* ── CASE STUDIES ── */
function renderProjects() {
  const studies = [
    { tag:'District Refresh', name:'Godley ISD — District-Wide Modernization', scope:'2 Campuses · 48 Classrooms · Commons & Libraries', timeline:'10 Weeks (Summer)', challenge:'Legacy fixed furniture locked teachers into lecture-only mode. Budget required surgical phasing — not every space could transform at once.', solution:'Room-by-room audit to prioritize highest-impact spaces first. Mobile nesting furniture that reconfigures in under 3 minutes. All old asset removal managed in-house with zero disruption to the calendar.', outcome:'100% delivered on time and on budget. Texas TAPR data showed consistent academic gains across all grades 2020–2024. The Assistant Superintendent directly credited the space redesign as a key driver of their instructional evolution.', img:'https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&q=80&w=900' },
    { tag:'CTE / STEM', name:'Angleton ISD — Career & Technical Center', scope:'12 Specialized Labs · Commons · Admin', timeline:'6 Weeks', challenge:'First CTE facility in the district — zero precedent for specs. Board needed visual proof before committing bond dollars.', solution:'Photo-realistic 3D renderings of all 12 lab configurations delivered within 72 hours. TIPS contract for bid-free procurement across 8 manufacturer lines simultaneously.', outcome:'Board approved on first presentation — zero revision requests. Zero change orders. All labs operational Day 1. Post-opening survey: 4.8/5 workspace quality rating from students and educators.', img:'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&q=80&w=900' },
  ];
  const installs = [['Moore Middle School','Celina ISD'],['Pleasant View Elementary','Godley ISD'],['Heartland ES & JH','Angleton ISD'],['Rockwall 9th-Grade Campus','Rockwall ISD'],['Sherman High School','Sherman ISD'],['Nolan Catholic HS','Diocese of FW'],['Aguirre JH Library','Channelview ISD'],['Sunnyvale Intermediate','Sunnyvale ISD'],['Peach Creek Elementary','Splendora ISD'],['Montgomery CTE','Montgomery ISD']];
  return `
  <section class="section section-dark">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">Receipts, not promises</div>
        <h1 class="sf" style="font-size:clamp(30px,4.5vw,52px);">We Don't Show You a Catalog.<br><span class="gold-text">We Show You Results.</span></h1>
        <p>Every project measured by the only three metrics that matter: on time, on budget, and measurable impact after move-in.</p>
      </div>
      ${studies.map(s => `
        <div class="case-card reveal">
          <div class="case-card-inner">
            <div class="case-img"><img src="${s.img}" alt="${s.name}"/><span class="case-img-tag">${s.tag}</span></div>
            <div class="case-body">
              <div class="case-meta"><span class="case-meta-item">🏢 ${s.scope}</span><span class="case-meta-item">📅 ${s.timeline}</span></div>
              <h2 class="sf">${s.name}</h2>
              <div style="display:flex;flex-direction:column;gap:16px;">
                <div><div class="case-section-label">The Challenge</div><p class="case-section-text">${s.challenge}</p></div>
                <div><div class="case-section-label">Our Solution</div><p class="case-section-text">${s.solution}</p></div>
                <div class="case-outcome"><div class="case-section-label">Measurable Outcome</div><p class="case-section-text">${s.outcome}</p></div>
              </div>
            </div>
          </div>
        </div>
      `).join('')}
      <div class="reveal" style="margin-top:52px;text-align:center;">
        <h3 class="sf" style="font-size:20px;color:white;margin-bottom:20px;">More Recent Texas Installations</h3>
        <div class="installs-grid">${installs.map(([n,d]) => `<div class="install-card"><div class="install-bar"></div><div class="install-name">${n}</div><div class="install-dist">${d}</div></div>`).join('')}</div>
      </div>
      <div style="text-align:center;margin-top:52px;" class="reveal">
        <button class="btn-cta" onclick="navigateTo('contact')">Get Your Free Project Audit ${I.arr}</button>
        <div class="hero-risk" style="justify-content:center;margin-top:14px;"><span>✓ Free.</span>&nbsp;No obligation. See exactly what your project would look like.</div>
      </div>
    </div>
  </section>
  `;
}

/* ── ABOUT ── */
function renderAbout() {
  return `
  <section class="about-hero">
    <div class="about-hero-inner">
      <div class="eyebrow eyebrow-center reveal" style="margin-bottom:18px;">Founded 2008 · Carrollton, Texas</div>
      <h1 class="sf reveal reveal-d1">Texas Roots.<br><em style="color:var(--gold-light);">Turnkey Accountability.</em></h1>
      <p class="reveal reveal-d2">We were built to solve one problem: Texas school districts were sick of coordinating three separate parties — dealers, freight companies, and installers — who blamed each other every time something went wrong. We brought it all under one roof. And we've never looked back.</p>
    </div>
  </section>
  <section class="section section-dark">
    <div class="section-inner">
      <div class="about-grid">
        <div class="reveal">
          <div class="eyebrow">Our operating principle</div>
          <h2 class="sf">We Win by Never Pointing Fingers.</h2>
          <p>In the FF&E world, something always goes wrong. A manufacturer runs late. Freight damages a piece. An installer no-shows. The question is: who owns the problem?</p>
          <p><strong style="color:white;">With Lone Star, the answer is always us.</strong> Because we employ our own W-2 crews and maintain local staging inventory, we resolve issues before your principal walks the floor.</p>
          <p>That's not marketing. It's how we've retained clients for 18 years in a market where trust is the only currency that matters.</p>
          <div class="about-pillars">
            <div class="about-pillar"><div class="about-pillar-icon">🛡️</div><div class="about-pillar-text"><h4>Co-Op Fluency</h4><p>Expert-level BuyBoard and TIPS compliance. Your purchasing department never faces audit risk on our projects.</p></div></div>
            <div class="about-pillar"><div class="about-pillar-icon">📍</div><div class="about-pillar-text"><h4>True Texas Footprint</h4><p>Staging hubs and crews across DFW and Houston. We handle summer installs that out-of-state dealers can't.</p></div></div>
            <div class="about-pillar"><div class="about-pillar-icon">🏆</div><div class="about-pillar-text"><h4>100+ Manufacturer Relationships</h4><p>Top-tier authorized dealer for KI, Virco, Fomcore, Smith System, and more. Our leverage = your budget savings.</p></div></div>
          </div>
        </div>
        <div class="about-img-grid reveal reveal-d2">
          <img src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=600" alt="Team"/>
          <img src="https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&q=80&w=600" alt="Planning"/>
          <img src="https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&q=80&w=600" alt="Install"/>
          <img src="https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&q=80&w=600" alt="Classroom"/>
        </div>
      </div>
    </div>
  </section>
  <section class="section section-dark" style="padding-top:0;">
    <div class="section-inner">
      <div class="section-header reveal">
        <div class="eyebrow eyebrow-center">By the numbers</div>
        <h2 class="sf">18 Years of Texas Execution.</h2>
      </div>
      <div class="numbers-grid">
        <div class="number-card reveal"><div class="number-big sf"><span class="counter" data-end="18" data-suffix="+">0</span></div><div class="number-label">Years in Texas</div><div class="number-sub">Founded 2008, Carrollton TX</div></div>
        <div class="number-card reveal reveal-d1"><div class="number-big sf"><span class="counter" data-end="250" data-suffix="+">0</span></div><div class="number-label">ISDs & Schools</div><div class="number-sub">DFW, Houston & statewide</div></div>
        <div class="number-card reveal reveal-d2"><div class="number-big sf"><span class="counter" data-end="1000" data-suffix="+">0</span></div><div class="number-label">Projects Completed</div><div class="number-sub">On time and on budget</div></div>
        <div class="number-card reveal reveal-d3"><div class="number-big sf"><span class="counter" data-end="4" data-suffix="">0</span></div><div class="number-label">Active Co-Op Contracts</div><div class="number-sub">BuyBoard, TIPS, Choice, TXMAS</div></div>
      </div>
    </div>
  </section>
  <section class="section section-dark" style="padding-top:0;">
    <div class="section-inner" style="max-width:960px;margin:0 auto;">
      <div class="section-header reveal"><div class="eyebrow eyebrow-center">The team</div><h2 class="sf">People, Not a Call Center.</h2><p>You'll work with the same faces from first call to final walkthrough.</p></div>
      <div class="team-grid">
        <div class="team-card reveal"><div class="team-avatar">BH</div><h3>Ben Herrick</h3><div class="team-role">President & Founder</div><div class="team-exp">20+ Yrs K–12 FF&E</div></div>
        <div class="team-card reveal reveal-d1"><div class="team-avatar">MF</div><h3>Melissa Fouché</h3><div class="team-role">VP of Sales</div><div class="team-exp">15+ Yrs K–12 Sales</div></div>
        <div class="team-card reveal reveal-d2"><div class="team-avatar">DT</div><h3>DFW Territory</h3><div class="team-role">North Texas Specialists</div><div class="team-exp">ESC 10 & 11 Coverage</div></div>
        <div class="team-card reveal reveal-d3"><div class="team-avatar">HT</div><h3>Houston Territory</h3><div class="team-role">Metro Specialists</div><div class="team-exp">ESC 4 Coverage</div></div>
      </div>
    </div>
  </section>
  `;
}

/* ── CONTACT ── */
function renderContact() {
  return `
  <section class="section section-dark">
    <div class="contact-grid">
      <div class="contact-left reveal">
        <div class="eyebrow">Let's do this</div>
        <h1 class="sf">Get Your Free<br><span class="gold-text">Project Audit.</span></h1>
        <p>No generic quote request. Fill this out and a dedicated territory manager will personally review your district's needs and respond within <strong style="color:white;">1 business day</strong> with a custom project scope, budget range, and timeline — whether you hire us or not.</p>
        <div style="margin-bottom:32px;">
          <div class="contact-detail"><div class="contact-detail-icon">📍</div><div><div class="contact-detail-label">DFW HQ & Showroom</div><div class="contact-detail-val">4301 Reeder Dr\nCarrollton, TX 75010</div></div></div>
          <div class="contact-detail"><div class="contact-detail-icon">📍</div><div><div class="contact-detail-label">Houston Showroom</div><div class="contact-detail-val">1907 Sabine St #134\nHouston, TX 77007</div></div></div>
          <div class="contact-detail"><div class="contact-detail-icon">📞</div><div><div class="contact-detail-label">Sales Line</div><div class="contact-detail-val">(972) 862-9900\nMon–Fri, 8am–5pm CST</div></div></div>
          <div class="contact-detail"><div class="contact-detail-icon">✉</div><div><div class="contact-detail-label">Email</div><div class="contact-detail-val">info@lonestarfurnishings.com</div></div></div>
        </div>
        <div class="contact-coops">
          <div class="contact-coops-label">Approved Co-Op Contracts</div>
          <div class="contact-coop-pills">
            <span class="coop-pill">BuyBoard</span><span class="coop-pill">TIPS / TAPS</span><span class="coop-pill">Choice Partners</span><span class="coop-pill">TXMAS</span>
          </div>
        </div>
      </div>
      <div class="form-box reveal reveal-d1">
        <div id="form-success" class="form-success">
          <div class="success-icon">✓</div>
          <h2 class="sf">Audit Request Received.</h2>
          <p>Your territory manager has been notified and will reach out within 1 business day with a tailored project scope for your district.</p>
          <button onclick="resetForm()">Submit another request</button>
        </div>
        <form id="contact-form" onsubmit="handleContactSubmit(event)">
          <h2>Free Project Audit Request</h2>
          <div class="form-row">
            <div class="form-group"><label>First Name *</label><input type="text" required/></div>
            <div class="form-group"><label>Last Name *</label><input type="text" required/></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>School District *</label><input type="text" required placeholder="e.g. Prosper ISD"/></div>
            <div class="form-group"><label>Your Title / Role</label><input type="text" placeholder="e.g. Director of Facilities"/></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Email *</label><input type="email" required/></div>
            <div class="form-group"><label>Phone</label><input type="tel"/></div>
          </div>
          <div class="form-divider">
            <h3>Project Details</h3>
            <div class="form-row">
              <div class="form-group"><label>Budget Range</label><select><option>Under $50K</option><option>$50K – $250K</option><option>$250K – $1M</option><option>$1M+</option><option>Need Guidance</option></select></div>
              <div class="form-group"><label>Timeline</label><select><option>ASAP (1–3 Months)</option><option>Next Summer Break</option><option>Bond Project (1+ Years)</option><option>Exploring</option></select></div>
            </div>
            <div class="form-group"><label>What spaces need furniture? *</label><textarea rows="4" required placeholder="e.g. 15 middle school classrooms, a new STEM lab, and cafeteria tables. Summer install window required."></textarea></div>
          </div>
          <button type="submit" class="form-submit" id="form-submit-btn">Get My Free Project Audit ${I.arr}</button>
          <p class="form-note">✓ Free. ✓ No obligation. ✓ Keep the audit even if you go with someone else.</p>
        </form>
      </div>
    </div>
  </section>
  `;
}

/* ── FOOTER ── */
function renderFooter() {
  return `<div class="footer-inner">
    <div class="footer-grid">
      <div>
        <div class="footer-brand"><div class="footer-brand-badge">LSF</div><span class="footer-brand-name">Lone Star Furnishings</span></div>
        <p class="footer-brand-desc">Texas's most accountable K–12 FF&E partner. When the first bell rings, every desk is in place.</p>
        <div class="footer-pills"><span class="footer-pill">BuyBoard</span><span class="footer-pill">TIPS</span><span class="footer-pill">Choice</span></div>
      </div>
      <div class="footer-col"><h4>Solutions</h4><ul class="footer-links"><li><button onclick="navigateTo('solutions')">Classrooms</button></li><li><button onclick="navigateTo('solutions')">Cafeteria & Commons</button></li><li><button onclick="navigateTo('solutions')">Libraries</button></li><li><button onclick="navigateTo('solutions')">STEM & CTE</button></li></ul></div>
      <div class="footer-col"><h4>Company</h4><ul class="footer-links"><li><button onclick="navigateTo('about')">About</button></li><li><button onclick="navigateTo('projects')">Case Studies</button></li><li><button onclick="navigateTo('contact')">Free Project Audit</button></li></ul></div>
      <div class="footer-col"><h4>Contact</h4><div class="footer-contact-items">
        <div class="footer-contact-item"><div><div class="footer-contact-label">DFW HQ</div><div class="footer-contact-val">4301 Reeder Dr\nCarrollton, TX 75010</div></div></div>
        <div class="footer-contact-item"><div><div class="footer-contact-label">Houston</div><div class="footer-contact-val">1907 Sabine St #134\nHouston, TX 77007</div></div></div>
        <div class="footer-contact-item"><div class="footer-contact-val">(972) 862-9900</div></div>
      </div></div>
    </div>
    <div class="footer-bottom"><span>© ${new Date().getFullYear()} Lone Star Furnishings. All rights reserved.</span><span>Privacy · Terms</span></div>
  </div>`;
}

/* ── INIT ── */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('mobile-menu-btn').textContent = '☰';
  document.getElementById('page-home').innerHTML = renderHome();
  document.getElementById('page-solutions').innerHTML = renderSolutions();
  document.getElementById('page-projects').innerHTML = renderProjects();
  document.getElementById('page-about').innerHTML = renderAbout();
  document.getElementById('page-contact').innerHTML = renderContact();
  document.getElementById('site-footer').innerHTML = renderFooter();
  document.querySelectorAll('.nav-link').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });
  navigateTo('home');
});
