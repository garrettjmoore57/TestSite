/* ═══════════════════════════════════
   LSF Website — script.js
═══════════════════════════════════ */

/* ── SVG Icon helper (Lucide-style) ── */
const icons = {
  arrowRight: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  shield: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>`,
  award: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></svg>`,
  mapPin: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
  phone: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.17 2 2 0 012 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14v2.92z"/></svg>`,
  mail: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,12 2,6"/></svg>`,
  check: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  quote: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/></svg>`,
  building: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><path d="M9 22V12h6v10M9 6h.01M15 6h.01M9 10h.01M15 10h.01"/></svg>`,
  users: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
  fileText: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
  search: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  calendar: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  star: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FBBF24" stroke="#FBBF24" stroke-width="1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  menu: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
  x: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
};

/* ── Navigation ── */
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const target = document.getElementById('page-' + page);
  if (target) target.classList.add('active');
  const navBtn = document.querySelector(`.nav-link[data-page="${page}"]`);
  if (navBtn) navBtn.classList.add('active');
  document.getElementById('mobile-nav')?.classList.remove('open');
  window.scrollTo({ top: 0, behavior: 'instant' });
}

/* ── Counter animation ── */
function animateCounter(el) {
  const end = parseInt(el.dataset.end, 10);
  const suffix = el.dataset.suffix || '';
  const steps = 55, dur = 1800, inc = end / steps;
  let cur = 0;
  const t = setInterval(() => {
    cur = Math.min(cur + inc, end);
    el.textContent = Math.floor(cur).toLocaleString() + suffix;
    if (cur >= end) clearInterval(t);
  }, dur / steps);
}

function initCounters() {
  const counters = document.querySelectorAll('.counter');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && !e.target.dataset.ran) {
        e.target.dataset.ran = '1';
        animateCounter(e.target);
      }
    });
  }, { threshold: 0.4 });
  counters.forEach(c => obs.observe(c));
}

/* ── Rep Finder ── */
const reps = {
  dfw:     { ini:'BH', name:'Ben Herrick',             title:'President — DFW & North Texas',       phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'20+' },
  houston: { ini:'SR', name:'Houston Territory Team',  title:'Houston Metro Specialist',             phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'12+' },
  central: { ini:'CT', name:'Central Texas Team',      title:'Austin / Central Texas Manager',       phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'10+' },
  south:   { ini:'ST', name:'South Texas Territory',   title:'San Antonio / South Texas Director',   phone:'(972) 862-9900', email:'info@lonestarfurnishings.com', yrs:'15+' },
};

function findRep() {
  const sel = document.getElementById('rep-region').value;
  const box = document.getElementById('rep-result');
  if (!sel || !reps[sel]) { box.style.display = 'none'; return; }
  const r = reps[sel];
  box.innerHTML = `
    <div class="rep-avatar">${r.ini}</div>
    <div class="rep-info">
      <h3>${r.name}</h3>
      <div class="rep-title">${r.title} · ${r.yrs} Yrs K–12</div>
      <div class="rep-contacts">
        <a href="tel:${r.phone.replace(/\D/g,'')}"> ${icons.phone} ${r.phone}</a>
        <a href="mailto:${r.email}"> ${icons.mail} ${r.email}</a>
      </div>
    </div>
    <button class="rep-book-btn" onclick="navigateTo('contact')">Book Intro Call</button>
  `;
  box.style.display = 'flex';
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
  }, 1600);
}

function resetForm() {
  document.getElementById('contact-form').style.display = 'block';
  document.getElementById('contact-form').reset();
  document.getElementById('form-success').classList.remove('show');
  const btn = document.getElementById('form-submit-btn');
  btn.innerHTML = 'Submit Project Request ' + icons.arrowRight;
  btn.disabled = false;
}

/* ── Mobile menu ── */
function toggleMobileMenu() {
  const nav = document.getElementById('mobile-nav');
  const btn = document.getElementById('mobile-menu-btn');
  const open = nav.classList.toggle('open');
  btn.innerHTML = open ? icons.x : icons.menu;
}

/* ── Page Renders ── */
function renderHome() {
  return `
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-badge fu0">${icons.shield} Texas K–12 FF&E Specialists · Est. 2008</div>
      <h1 class="sf fu1">When the First Bell Rings,<br><span class="gold-text">Every Desk Is in Place.</span></h1>
      <p class="hero-sub fu2">Texas's most accountable turnkey K–12 FF&E partner. Co-op approved contracts. White-glove installation. On time, on budget — put in writing.</p>
      <div class="hero-btns fu3">
        <button class="btn-primary" onclick="navigateTo('contact')">Request a Project Quote ${icons.arrowRight}</button>
        <button class="btn-outline-white" onclick="navigateTo('projects')">View District Case Studies</button>
      </div>
    </div>
  </section>

  <section class="stats-bar">
    <div class="stats-grid">
      <div class="stat-cell">
        <div class="stat-number sf"><span class="counter" data-end="18" data-suffix="+">18+</span></div>
        <div class="stat-label">Years in Texas</div>
      </div>
      <div class="stat-cell">
        <div class="stat-number sf"><span class="counter" data-end="250" data-suffix="+">250+</span></div>
        <div class="stat-label">ISDs Served</div>
      </div>
      <div class="stat-cell">
        <div class="stat-number sf"><span class="counter" data-end="1000" data-suffix="+">1,000+</span></div>
        <div class="stat-label">Projects Completed</div>
      </div>
      <div class="stat-cell">
        <div class="stat-number sf"><span class="counter" data-end="100" data-suffix="%">100%</span></div>
        <div class="stat-label">On-Time Delivery Rate</div>
      </div>
    </div>
  </section>

  <section class="coop-strip">
    <div class="coop-strip-inner">
      <span class="coop-strip-label">Procure without a bid — approved on:</span>
      <span class="coop-pill">BuyBoard</span>
      <span class="coop-pill">TIPS / TAPS</span>
      <span class="coop-pill">Choice Partners</span>
      <span class="coop-pill">TXMAS</span>
    </div>
  </section>

  <section class="section" style="background:white;">
    <div class="section-inner">
      <div class="section-header">
        <div class="eyebrow eyebrow-center" style="margin-bottom:12px;">Purpose-built for K–12 procurement</div>
        <h2>Every Stakeholder Has a Different Problem. We Solve for All of Them.</h2>
        <p>Purchasing needs compliance. Facilities needs execution. Leadership needs ROI. Here's how we address each role.</p>
      </div>
      <div class="buyer-grid">
        <div class="buyer-card">
          <div class="buyer-tag">${icons.fileText} Skip the RFP</div>
          <h3>Purchasing & Procurement</h3>
          <p>Active co-op contracts on BuyBoard, TIPS, and Choice Partners eliminate the bid process entirely. Transparent, line-item pricing with zero audit exposure.</p>
          <ul class="buyer-bullets">
            <li>${icons.check} Pre-negotiated co-op pricing</li>
            <li>${icons.check} Bid-exempt purchasing path</li>
            <li>${icons.check} Full compliance documentation</li>
          </ul>
          <button class="buyer-link" onclick="navigateTo('contact')">Get Contract Details ${icons.arrowRight}</button>
        </div>
        <div class="buyer-card">
          <div class="buyer-tag">${icons.building} We Own the Final Mile</div>
          <h3>Facilities & Operations</h3>
          <p>We don't drop pallets at your dock. Our W-2 installation crews stage, assemble, place, and remove all packaging before you walk the floor — every time.</p>
          <ul class="buyer-bullets">
            <li>${icons.check} White-glove install included</li>
            <li>${icons.check} Dedicated on-site project manager</li>
            <li>${icons.check} Same-day damage resolution</li>
          </ul>
          <button class="buyer-link" onclick="navigateTo('projects')">View Installation Process ${icons.arrowRight}</button>
        </div>
        <div class="buyer-card">
          <div class="buyer-tag">${icons.users} Bond Dollars, Maximized</div>
          <h3>Superintendent & Board</h3>
          <p>Photo-realistic 3D renderings that win board approval in one meeting. Phased timelines that fit construction schedules. Outcome data to show your community the ROI.</p>
          <ul class="buyer-bullets">
            <li>${icons.check} 3D renderings before any commitment</li>
            <li>${icons.check} Bond planning expertise</li>
            <li>${icons.check} Academic outcome documentation</li>
          </ul>
          <button class="buyer-link" onclick="navigateTo('projects')">See Learning Outcomes ${icons.arrowRight}</button>
        </div>
      </div>
    </div>
  </section>

  <section class="dark-section">
    <div class="dark-section-glow"></div>
    <div class="dark-grid">
      <div>
        <div class="eyebrow" style="color:#C4992A;margin-bottom:14px;">Our proven process</div>
        <h2 class="sf">"Turnkey" Is Only a Guarantee<br><em style="color:#DDB84C;">When It's in Writing.</em></h2>
        <p style="margin-bottom:0;">Most suppliers say turnkey. They mean "we sell furniture." We mean one team, one contract, complete accountability — from specification through opening day.</p>
        <div class="steps">
          <div class="step">
            <div class="step-num">01</div>
            <div class="step-body">
              <h4>Consult & Specify</h4>
              <p>Space audit, 3D visualization, co-op contract alignment, and a locked budget — before a single PO is cut.</p>
            </div>
          </div>
          <div class="step">
            <div class="step-num">02</div>
            <div class="step-body">
              <h4>Procure & Stage Locally</h4>
              <p>We own manufacturer timelines and stage all product in Texas. Zero missing pieces on install day.</p>
            </div>
          </div>
          <div class="step">
            <div class="step-num">03</div>
            <div class="step-body">
              <h4>White-Glove Install & Handoff</h4>
              <p>Our W-2 crews unbox, assemble, place to spec, and haul all packaging. You turn the key.</p>
            </div>
          </div>
        </div>
        <button class="btn-gold" style="margin-top:30px;" onclick="navigateTo('contact')">Schedule a Free Discovery Call ${icons.arrowRight}</button>
      </div>
      <div class="dark-img-wrap">
        <img src="https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&q=80&w=800" alt="Classroom installation"/>
        <div class="dark-quote-card">
          <div class="stars">${icons.star}${icons.star}${icons.star}${icons.star}${icons.star}</div>
          <p>"No longer are we bound by fixed furniture… the furniture is working for us, instead of us working for it."</p>
          <cite>— Assistant Superintendent, Godley ISD</cite>
        </div>
      </div>
    </div>
  </section>

  <section class="testimonials-section">
    <div class="section-inner">
      <div class="section-header">
        <div class="eyebrow eyebrow-center" style="margin-bottom:12px;">District voices</div>
        <h2>Trusted Across Texas.</h2>
      </div>
      <div class="testimonials-grid">
        <div class="testimonial-card">
          <div class="quote-icon">${icons.quote}</div>
          <blockquote>"Lone Star managed our entire district refresh without a single delay. When supply chain issues threatened our timeline, they pulled from local inventory and never missed a beat."</blockquote>
          <div class="testimonial-footer">
            <div>
              <div class="testimonial-name">Director of Operations</div>
              <div class="testimonial-dist">Godley ISD</div>
            </div>
            <span class="testimonial-tag">District Refresh</span>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="quote-icon">${icons.quote}</div>
          <blockquote>"Using their BuyBoard contract saved our team weeks of paperwork. The install crew left every room spotless. We won't use anyone else for future bond projects."</blockquote>
          <div class="testimonial-footer">
            <div>
              <div class="testimonial-name">Purchasing Coordinator</div>
              <div class="testimonial-dist">Lumberton ISD</div>
            </div>
            <span class="testimonial-tag">Campus FF&E</span>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="quote-icon">${icons.quote}</div>
          <blockquote>"The 3D renderings got us board approval in one meeting. The STEM labs look exactly like the pictures — students and teachers genuinely love them."</blockquote>
          <div class="testimonial-footer">
            <div>
              <div class="testimonial-name">Assistant Superintendent</div>
              <div class="testimonial-dist">Angleton ISD</div>
            </div>
            <span class="testimonial-tag">CTE Labs</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="rep-finder-section">
    <div class="rep-finder-header">
      <div class="eyebrow eyebrow-center" style="color:#C4992A;margin-bottom:12px;">Dedicated territory coverage</div>
      <h2>Find Your Texas Territory Manager</h2>
      <p>Every district has a dedicated rep. Find yours in seconds.</p>
    </div>
    <div class="rep-finder-box">
      <div class="rep-finder-row">
        <div class="rep-finder-select-wrap">
          <label>Your Texas Region</label>
          <div class="select-icon-wrap">
            ${icons.mapPin}
            <select id="rep-region" onchange="document.getElementById('rep-result').style.display='none'">
              <option value="" disabled selected>Select a metro / region…</option>
              <option value="dfw">Dallas / Fort Worth (ESC 10 & 11)</option>
              <option value="houston">Houston Metro (ESC 4)</option>
              <option value="central">Austin / Central Texas (ESC 13)</option>
              <option value="south">San Antonio / South Texas (ESC 20)</option>
            </select>
          </div>
        </div>
        <button class="rep-find-btn" onclick="findRep()">${icons.search} Find My Rep</button>
      </div>
      <div class="rep-result" id="rep-result" style="display:none;"></div>
    </div>
  </section>

  <section class="cta-strip">
    <div class="cta-strip-inner">
      <h2 class="sf">Ready to Put Turnkey to the Test?</h2>
      <p>Tell us your timeline, spaces, and budget. We'll show you exactly how we'd deliver — backed by proof from districts that have been through it.</p>
      <button class="btn-navy" onclick="navigateTo('contact')">Start Your Project Scoping Call ${icons.arrowRight}</button>
    </div>
  </section>
  `;
}

function renderSolutions() {
  const spaces = [
    { tag:'Most Requested', title:'Flexible Classrooms', body:'From lecture to collaborative pods in under 60 seconds. Mobile nesting furniture, height-adjustable surfaces, and 1:1 device-ready power management built for modern pedagogy.', specs:['ADA-compliant desk ratio requirements','Caster grade for VCT vs. carpet','Power routing for device programs','Mobile whiteboard integration'], img:'https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&q=80&w=800' },
    { tag:'High Demand', title:'CTE & STEM Labs', body:'Purpose-built worksurfaces, robust storage, and industry-specific configurations for every career pathway — coding, healthcare, culinary, welding, and beyond.', specs:['Utility knockout for trades programs','Chemical-resistant laminate surfaces','ADA compliance in active lab settings','Heavy-duty casters for equipment movement'], img:'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&q=80&w=800' },
    { tag:'', title:'Library & Media Centers', body:'From quiet study zones to active maker spaces. Soft seating, acoustic-dampening configurations, and flexible layouts that serve multiple simultaneous learning modes.', specs:['Sightline management for library staff','Commercial-grade fabric (50k+ rub count)','Integrated power nodes in lounge seating','Zoned acoustic absorption options'], img:'https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&q=80&w=800' },
    { tag:'', title:'Cafeteria & Commons', body:'High-traffic durability meets modern design. Tables and benches that stack cleanly and survive 180+ days of daily K–12 use — without looking like they have.', specs:['Seat count optimization per sq ft','Folding vs. fixed configurations','ADA-compliant table height mixing','Anti-graffiti finish options'], img:'https://images.unsplash.com/photo-1567521464027-f127ff144326?auto=format&fit=crop&q=80&w=800' },
  ];

  return `
  <div class="section">
    <div class="section-inner">
      <div class="solutions-header">
        <div class="eyebrow eyebrow-center" style="margin-bottom:12px;">100+ manufacturer partners</div>
        <h1 class="sf">Spaces Engineered for Learning.</h1>
        <p>We don't sell catalogs. We design environments that reduce discipline issues, support diverse learning styles, and withstand 15 years of K–12 wear.</p>
      </div>
      <div class="sol-grid">
        ${spaces.map(s => `
          <div class="sol-card">
            <div class="sol-card-img">
              <img src="${s.img}" alt="${s.title}"/>
              ${s.tag ? `<span class="sol-img-tag">${s.tag}</span>` : ''}
            </div>
            <div class="sol-card-body">
              <h3>${s.title}</h3>
              <p>${s.body}</p>
              <div class="sol-specs">
                <div class="sol-specs-label">Planning Considerations</div>
                <ul>${s.specs.map(sp => `<li>${sp}</li>`).join('')}</ul>
              </div>
              <div class="sol-btns">
                <button class="sol-btn-primary" onclick="navigateTo('contact')">Quote This Space</button>
                <button class="sol-btn-secondary">Download Spec Sheet</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
      <div class="sol-mfr-box">
        <h3>One PO. 100+ Manufacturers.</h3>
        <p>As an authorized dealer for KI, Virco, Smith System, Fomcore, VS America, and dozens more — we consolidate everything into a single co-op purchase order. No juggling vendor relationships.</p>
        <button class="btn-white-ghost" onclick="navigateTo('contact')">Request Our Full Line Card</button>
      </div>
    </div>
  </div>
  `;
}

function renderProjects() {
  const studies = [
    {
      tag:'District Refresh', name:'Godley ISD — District-Wide Modernization',
      scope:'2 Campuses · 48 Classrooms · Commons & Libraries', timeline:'10 Weeks (Summer Break)',
      challenge:'Legacy fixed furniture locked teachers into lecture-only configurations. A tight budget required strategic phasing — not every space could be transformed simultaneously.',
      solution:'Conducted a room-by-room audit to prioritize high-impact spaces. Specified mobile, nesting furniture allowing reconfiguration in under 3 minutes. Managed all removal and disposal of old assets with zero disruption to the school calendar.',
      outcome:'Delivered on time and on budget. Texas TAPR academic progress data showed consistent gains across all grades from 2020–2024. The Assistant Superintendent directly credited space redesign as a key driver of the district\'s instructional evolution.',
      img:'https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&q=80&w=900',
    },
    {
      tag:'CTE / STEM', name:'Angleton ISD — Career & Technical Center',
      scope:'12 Specialized Labs · Commons · Admin Suite', timeline:'6 Weeks',
      challenge:'First-of-its-kind CTE facility in the district with no precedent for furniture specifications. Board approval required visual confidence before any commitment of bond funds.',
      solution:'Delivered photo-realistic 3D renderings of all 12 lab configurations within 72 hours of initial consultation. Leveraged TIPS contract for bid-free procurement across 8 manufacturer lines simultaneously.',
      outcome:'Board approved on first presentation with zero revision requests. No change orders issued. All labs fully operational for Day 1. Post-opening survey rated workspace quality 4.8/5 by students and educators.',
      img:'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&q=80&w=900',
    },
  ];

  const installs = [
    ['Moore Middle School','Celina ISD'],['Pleasant View Elementary','Godley ISD'],
    ['Heartland ES & JH','Angleton ISD'],['Rockwall Ninth-Grade Campus','Rockwall ISD'],
    ['Sherman High School','Sherman ISD'],['Nolan Catholic High School','Diocese of FW'],
    ['Aguirre JH Library','Channelview ISD'],['Sunnyvale Intermediate','Sunnyvale ISD'],
    ['Peach Creek Elementary','Splendora ISD'],['Montgomery CTE Center','Montgomery ISD'],
  ];

  return `
  <div class="section">
    <div class="section-inner">
      <div class="case-header">
        <div class="eyebrow eyebrow-center" style="margin-bottom:12px;">Real Texas districts. Real outcomes.</div>
        <h1 class="sf">Case Studies</h1>
        <p>We measure success in on-time deliveries, on-budget completions, and the measurable data that comes after.</p>
      </div>
      <div class="case-studies">
        ${studies.map(s => `
          <div class="case-card">
            <div class="case-card-inner">
              <div class="case-img">
                <img src="${s.img}" alt="${s.name}"/>
                <span class="case-img-tag">${s.tag}</span>
              </div>
              <div class="case-body">
                <div class="case-meta">
                  <span class="case-meta-item">${icons.building} ${s.scope}</span>
                  <span class="case-meta-item">${icons.calendar} ${s.timeline}</span>
                </div>
                <h2>${s.name}</h2>
                <div class="case-sections">
                  <div>
                    <div class="case-section-label">The Challenge</div>
                    <p class="case-section-text">${s.challenge}</p>
                  </div>
                  <div>
                    <div class="case-section-label">Our Solution</div>
                    <p class="case-section-text">${s.solution}</p>
                  </div>
                  <div class="case-outcome">
                    <div class="case-section-label">Measurable Outcome</div>
                    <p class="case-section-text">${s.outcome}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
      <div class="recent-installs">
        <h3>More Recent Texas Installations</h3>
        <div class="installs-grid">
          ${installs.map(([name, dist]) => `
            <div class="install-card">
              <div class="install-bar"></div>
              <div class="install-name">${name}</div>
              <div class="install-dist">${dist}</div>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="case-cta">
        <button class="btn-navy" onclick="navigateTo('contact')">Plan Your Next Installation ${icons.arrowRight}</button>
      </div>
    </div>
  </div>
  `;
}

function renderAbout() {
  return `
  <section class="about-hero">
    <div class="about-hero-inner">
      <div class="eyebrow eyebrow-center" style="color:#C4992A;margin-bottom:16px;">Founded 2008 · Carrollton, Texas</div>
      <h1 class="sf">Texas Roots.<br><em style="color:#DDB84C;">Turnkey Accountability.</em></h1>
      <p>We were built to solve one problem: Texas school districts were exhausted managing three separate parties — dealers, freight companies, and installers — who pointed fingers at each other every time something went wrong. We brought it all under one roof.</p>
    </div>
  </section>

  <section class="section">
    <div class="section-inner">
      <div class="about-grid">
        <div>
          <div class="eyebrow" style="margin-bottom:13px;">Our operating philosophy</div>
          <h2>We Win by Never Pointing Fingers.</h2>
          <p>In the FF&E world, something always goes wrong. A manufacturer runs late. A freight carrier damages a piece. An installer is a no-show. The question is: who owns the problem?</p>
          <p>With Lone Star, the answer is always us. Because we employ our own W-2 installation crews and maintain local staging inventory across Texas, we can resolve field issues before your principal ever walks the floor.</p>
          <p>That's not a slogan — it's how we've retained clients for over 15 years in a relationship-driven market.</p>
          <div class="about-pillars">
            <div class="about-pillar">
              <div class="about-pillar-icon">${icons.shield}</div>
              <div class="about-pillar-text">
                <h4>Co-Op Fluency</h4>
                <p>We are experts in BuyBoard and TIPS compliance. Your purchasing team will never face an audit risk on one of our projects.</p>
              </div>
            </div>
            <div class="about-pillar">
              <div class="about-pillar-icon">${icons.mapPin}</div>
              <div class="about-pillar-text">
                <h4>True Texas Footprint</h4>
                <p>With staging hubs and crews across DFW and Houston, we handle aggressive summer installation timelines that out-of-state dealers simply cannot match.</p>
              </div>
            </div>
            <div class="about-pillar">
              <div class="about-pillar-icon">${icons.award}</div>
              <div class="about-pillar-text">
                <h4>Manufacturer-Level Relationships</h4>
                <p>As a top-tier authorized dealer for KI, Virco, Fomcore, Smith System, and 100+ others, we have procurement leverage that translates directly to your project budget.</p>
              </div>
            </div>
          </div>
        </div>
        <div class="about-img-grid">
          <img src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=600" alt="Team meeting"/>
          <img src="https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&q=80&w=600" alt="Planning session"/>
          <img src="https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&q=80&w=600" alt="Installation"/>
          <img src="https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&q=80&w=600" alt="Modern classroom"/>
        </div>
      </div>
    </div>
  </section>

  <section class="numbers-section">
    <div class="section-inner">
      <div style="text-align:center;max-width:560px;margin:0 auto 0;">
        <div class="eyebrow eyebrow-center" style="margin-bottom:11px;">By the numbers</div>
        <h2 class="sf">Eighteen Years of Texas FF&E Execution.</h2>
      </div>
      <div class="numbers-grid">
        <div class="number-card">
          <div class="number-big sf"><span class="counter" data-end="18" data-suffix="+">18+</span></div>
          <div class="number-label">Years Operating in Texas</div>
          <div class="number-sub">Founded 2008, Carrollton TX</div>
        </div>
        <div class="number-card">
          <div class="number-big sf"><span class="counter" data-end="250" data-suffix="+">250+</span></div>
          <div class="number-label">ISDs & Schools Served</div>
          <div class="number-sub">Across DFW, Houston & statewide</div>
        </div>
        <div class="number-card">
          <div class="number-big sf"><span class="counter" data-end="1000" data-suffix="+">1,000+</span></div>
          <div class="number-label">Projects Completed</div>
          <div class="number-sub">On time and on budget</div>
        </div>
        <div class="number-card">
          <div class="number-big sf"><span class="counter" data-end="4" data-suffix="">4</span></div>
          <div class="number-label">Active Co-Op Contracts</div>
          <div class="number-sub">BuyBoard, TIPS, Choice, TXMAS</div>
        </div>
      </div>
    </div>
  </section>

  <section class="team-section">
    <div class="team-section-inner">
      <div>
        <div class="eyebrow eyebrow-center" style="margin-bottom:12px;">The team behind the work</div>
        <h2>Leadership & Territory Managers</h2>
        <p>Texas school districts don't buy from companies — they buy from people. Here's who you'll work with.</p>
      </div>
      <div class="team-grid">
        <div class="team-card"><div class="team-avatar">BH</div><h3>Ben Herrick</h3><div class="team-role">President & Founder</div><div class="team-exp">20+ Yrs K–12 FF&E</div></div>
        <div class="team-card"><div class="team-avatar">MF</div><h3>Melissa Fouché</h3><div class="team-role">VP of Sales</div><div class="team-exp">15+ Yrs K–12 Sales</div></div>
        <div class="team-card"><div class="team-avatar">DT</div><h3>DFW Territory</h3><div class="team-role">North Texas Specialists</div><div class="team-exp">ESC 10 & 11 Coverage</div></div>
        <div class="team-card"><div class="team-avatar">HT</div><h3>Houston Territory</h3><div class="team-role">Houston Metro Specialists</div><div class="team-exp">ESC 4 Coverage</div></div>
      </div>
    </div>
  </section>

  <section class="philanthropy-section">
    <div class="philanthropy-inner">
      <div class="eyebrow eyebrow-center" style="color:#C4992A;margin-bottom:12px;">Community commitment</div>
      <h2>We Give Back to the Schools We Serve.</h2>
      <p>Beyond FF&E, Lone Star Furnishings is committed to the communities that make up our school districts — through charitable giving, furniture donations, and active participation in Texas education advocacy.</p>
      <button class="btn-gold" onclick="navigateTo('contact')">Partner With Our Team ${icons.arrowRight}</button>
    </div>
  </section>
  `;
}

function renderContact() {
  return `
  <div class="section">
    <div class="contact-grid">
      <div class="contact-left">
        <div class="eyebrow" style="margin-bottom:13px;">Let's build something</div>
        <h1 class="sf">Start Your Project.</h1>
        <p>Skip the generic contact queue. Fill out this scoping form and a dedicated territory manager will reach out within one business day with a tailored approach and pricing guidance for your district.</p>
        <div class="contact-details">
          <div class="contact-detail">
            <div class="contact-detail-icon">${icons.mapPin}</div>
            <div>
              <div class="contact-detail-label">DFW HQ & Showroom</div>
              <div class="contact-detail-val">4301 Reeder Dr\nCarrollton, TX 75010</div>
            </div>
          </div>
          <div class="contact-detail">
            <div class="contact-detail-icon">${icons.mapPin}</div>
            <div>
              <div class="contact-detail-label">Houston Showroom</div>
              <div class="contact-detail-val">1907 Sabine St #134\nHouston, TX 77007</div>
            </div>
          </div>
          <div class="contact-detail">
            <div class="contact-detail-icon">${icons.phone}</div>
            <div>
              <div class="contact-detail-label">Direct Sales Line</div>
              <div class="contact-detail-val">(972) 862-9900\nMon–Fri, 8am–5pm CST</div>
            </div>
          </div>
          <div class="contact-detail">
            <div class="contact-detail-icon">${icons.mail}</div>
            <div>
              <div class="contact-detail-label">General Inquiries</div>
              <div class="contact-detail-val">info@lonestarfurnishings.com</div>
            </div>
          </div>
        </div>
        <div class="contact-coops">
          <div class="contact-coops-label">Approved Co-Op Contracts</div>
          <div class="contact-coop-pills">
            <span class="coop-pill">BuyBoard</span>
            <span class="coop-pill">TIPS / TAPS</span>
            <span class="coop-pill">Choice Partners</span>
            <span class="coop-pill">TXMAS</span>
          </div>
        </div>
      </div>

      <div class="form-box">
        <div id="form-success" class="form-success">
          <div class="success-icon">${icons.check}</div>
          <h2>Project Request Received</h2>
          <p>Your territory manager has been notified and will reach out within one business day to discuss your district's specific needs.</p>
          <button onclick="resetForm()">Submit another request</button>
        </div>
        <form id="contact-form" onsubmit="handleContactSubmit(event)">
          <h2>Project Scoping Form</h2>
          <div class="form-row">
            <div class="form-group"><label>First Name *</label><input type="text" required/></div>
            <div class="form-group"><label>Last Name *</label><input type="text" required/></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>School District / Organization *</label><input type="text" required placeholder="e.g. Prosper ISD"/></div>
            <div class="form-group"><label>Your Title / Role</label><input type="text" placeholder="e.g. Director of Facilities"/></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Email Address *</label><input type="email" required/></div>
            <div class="form-group"><label>Phone Number</label><input type="tel"/></div>
          </div>
          <div class="form-divider">
            <h3>Project Details</h3>
            <div class="form-row">
              <div class="form-group">
                <label>Estimated Budget</label>
                <select>
                  <option>Under $50,000</option>
                  <option>$50,000 – $250,000</option>
                  <option>$250,000 – $1,000,000</option>
                  <option>$1,000,000+</option>
                  <option>Need Budgetary Guidance</option>
                </select>
              </div>
              <div class="form-group">
                <label>Target Timeline</label>
                <select>
                  <option>ASAP (1–3 Months)</option>
                  <option>Next Summer Break</option>
                  <option>Bond Project (1+ Years)</option>
                  <option>Exploring / No Date Yet</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Scope of Work *</label>
              <textarea rows="4" required placeholder="e.g. Refresh 15 middle school classrooms with mobile desks plus a new STEM lab. Summer install window required."></textarea>
            </div>
          </div>
          <button type="submit" class="form-submit" id="form-submit-btn">Submit Project Request ${icons.arrowRight}</button>
          <p class="form-note">Your territory manager reviews every submission personally. Response within 1 business day.</p>
        </form>
      </div>
    </div>
  </div>
  `;
}

/* ── Footer HTML ── */
function renderFooter() {
  return `
  <div class="footer-inner">
    <div class="footer-grid">
      <div>
        <div class="footer-brand">
          <div class="footer-brand-badge">LSF</div>
          <span class="footer-brand-name">Lone Star Furnishings</span>
        </div>
        <p class="footer-brand-desc">Texas's most accountable K–12 FF&E partner. When the first bell rings, every desk is in place.</p>
        <div class="footer-pills">
          <span class="footer-pill">BuyBoard</span>
          <span class="footer-pill">TIPS</span>
        </div>
      </div>
      <div class="footer-col">
        <h4>Solutions</h4>
        <ul class="footer-links">
          <li><button onclick="navigateTo('solutions')">Classroom Furniture</button></li>
          <li><button onclick="navigateTo('solutions')">Cafeteria & Commons</button></li>
          <li><button onclick="navigateTo('solutions')">Library & Media Centers</button></li>
          <li><button onclick="navigateTo('solutions')">STEM & CTE Labs</button></li>
          <li><button onclick="navigateTo('solutions')">Admin & Office</button></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Company</h4>
        <ul class="footer-links">
          <li><button onclick="navigateTo('about')">Our Story</button></li>
          <li><button onclick="navigateTo('projects')">Case Studies</button></li>
          <li><button onclick="navigateTo('home')">Find My Rep</button></li>
          <li><button onclick="navigateTo('contact')">Start a Project</button></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Contact</h4>
        <div class="footer-contact-items">
          <div class="footer-contact-item">
            ${icons.mapPin}
            <div>
              <div class="footer-contact-label">DFW HQ & Showroom</div>
              <div class="footer-contact-val">4301 Reeder Dr\nCarrollton, TX 75010</div>
            </div>
          </div>
          <div class="footer-contact-item">
            ${icons.mapPin}
            <div>
              <div class="footer-contact-label">Houston Showroom</div>
              <div class="footer-contact-val">1907 Sabine St #134\nHouston, TX 77007</div>
            </div>
          </div>
          <div class="footer-contact-item">
            ${icons.phone}
            <div class="footer-contact-val">(972) 862-9900</div>
          </div>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© ${new Date().getFullYear()} Lone Star Furnishings. All rights reserved.</span>
      <span>Privacy Policy · Terms of Service</span>
    </div>
  </div>
  `;
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  // Mobile menu
  document.getElementById('mobile-menu-btn').innerHTML = icons.menu;

  // Render pages
  document.getElementById('page-home').innerHTML = renderHome();
  document.getElementById('page-solutions').innerHTML = renderSolutions();
  document.getElementById('page-projects').innerHTML = renderProjects();
  document.getElementById('page-about').innerHTML = renderAbout();
  document.getElementById('page-contact').innerHTML = renderContact();
  document.getElementById('site-footer').innerHTML = renderFooter();

  // Nav link clicks
  document.querySelectorAll('.nav-link').forEach(btn => {
    btn.addEventListener('click', () => navigateTo(btn.dataset.page));
  });

  // Init counters
  initCounters();

  // Default to home
  navigateTo('home');
});
