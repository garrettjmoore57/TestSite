const menuToggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');

if (menuToggle && nav) {
  menuToggle.addEventListener('click', () => {
    const isOpen = nav.dataset.open === 'true';
    nav.dataset.open = String(!isOpen);
    menuToggle.setAttribute('aria-expanded', String(!isOpen));
  });

  nav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      nav.dataset.open = 'false';
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

const leadForm = document.querySelector('.lead-form');
const formNote = document.querySelector('.form-note');

if (leadForm && formNote) {
  leadForm.addEventListener('submit', (event) => {
    const formData = new FormData(leadForm);
    const requiredFields = ['name', 'email', 'organization', 'scope'];
    const hasMissing = requiredFields.some((field) => !String(formData.get(field) || '').trim());

    if (hasMissing) {
      event.preventDefault();
      formNote.textContent = 'Please complete all required fields before submitting.';
      return;
    }

    formNote.textContent = 'Opening your email client with project details...';
  });
}

const catalogProducts = [
  { id: 1, name: 'Virco 9000 Series Student Desk', brand: 'Virco', material: 'Metal', grade: '6-8', ada: true, price: 189, desc: 'Adjustable, contract-grade desk for high-use classrooms.' },
  { id: 2, name: 'KI Postura Plus Chair', brand: 'KI Furniture', material: 'Plastic', grade: 'K-5', ada: true, price: 79, desc: 'Lightweight stack chair with reinforced shell and glide options.' },
  { id: 3, name: 'Marco Group Makerspace Table', brand: 'Marco Group', material: 'Wood', grade: '9-12', ada: false, price: 649, desc: 'Large STEM-ready collaborative table with locking casters.' },
  { id: 4, name: 'Learniture Soft Seating Pod', brand: 'Learniture', material: 'Upholstered', grade: 'Higher Ed', ada: false, price: 739, desc: 'Modular lounge piece for media centers and commons spaces.' },
  { id: 5, name: 'AmTab Cafeteria Fold Table', brand: 'AmTab', material: 'Metal', grade: '6-8', ada: true, price: 1249, desc: 'Mobile fold-and-nest cafeteria table for quick turnovers.' },
  { id: 6, name: 'Smith System Active Learning Desk', brand: 'Smith System', material: 'Wood', grade: '9-12', ada: true, price: 329, desc: 'Mobile desk with bag hook and quick transition geometry.' }
];

const quoteState = new Map();
const brandSelect = document.getElementById('filter-brand');
const materialSelect = document.getElementById('filter-material');
const gradeSelect = document.getElementById('filter-grade');
const adaOnlyInput = document.getElementById('filter-ada');
const resetButton = document.getElementById('tool-reset');
const catalogGrid = document.getElementById('catalog-grid');
const resultsLabel = document.getElementById('catalog-results');
const quoteItems = document.getElementById('quote-items');
const quoteTotal = document.getElementById('quote-total');
const runBudgetButton = document.getElementById('run-budget');
const budgetOutput = document.getElementById('budget-output');

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

function buildBrandOptions() {
  if (!brandSelect) return;
  const brands = [...new Set(catalogProducts.map((item) => item.brand))];
  brands.forEach((brand) => {
    const option = document.createElement('option');
    option.value = brand;
    option.textContent = brand;
    brandSelect.append(option);
  });
}

function getFilteredProducts() {
  return catalogProducts.filter((item) => {
    const brandMatch = !brandSelect || brandSelect.value === 'All' || item.brand === brandSelect.value;
    const materialMatch = !materialSelect || materialSelect.value === 'All' || item.material === materialSelect.value;
    const gradeMatch = !gradeSelect || gradeSelect.value === 'All' || item.grade === gradeSelect.value;
    const adaMatch = !adaOnlyInput || !adaOnlyInput.checked || item.ada;
    return brandMatch && materialMatch && gradeMatch && adaMatch;
  });
}

function renderCatalog() {
  if (!catalogGrid || !resultsLabel) return;
  const filtered = getFilteredProducts();
  resultsLabel.textContent = `Showing ${filtered.length} of ${catalogProducts.length} products`;
  catalogGrid.innerHTML = filtered
    .map(
      (item) => `
      <article class="tool-card">
        <h3>${item.name}</h3>
        <p>${item.desc}</p>
        <div class="tool-meta"><span>${item.brand} • ${item.grade}</span><strong>${formatCurrency(item.price)}</strong></div>
        <button class="btn btn-primary" type="button" data-product-id="${item.id}">Add to Quote</button>
      </article>
    `
    )
    .join('');

  catalogGrid.querySelectorAll('[data-product-id]').forEach((button) => {
    button.addEventListener('click', () => {
      const id = Number(button.getAttribute('data-product-id'));
      quoteState.set(id, (quoteState.get(id) || 0) + 1);
      renderQuote();
    });
  });
}

function renderQuote() {
  if (!quoteItems || !quoteTotal) return;
  const lines = [...quoteState.entries()].map(([id, qty]) => {
    const item = catalogProducts.find((product) => product.id === id);
    return { name: item?.name || 'Unknown', qty, total: (item?.price || 0) * qty };
  });

  quoteItems.innerHTML = lines.length
    ? lines
        .map((line) => `<div class="quote-row"><span>${line.name} × ${line.qty}</span><strong>${formatCurrency(line.total)}</strong></div>`)
        .join('')
    : '<p class="section-intro">No products added yet.</p>';

  const grandTotal = lines.reduce((sum, line) => sum + line.total, 0);
  quoteTotal.textContent = formatCurrency(grandTotal);
}

function resetFilters() {
  if (brandSelect) brandSelect.value = 'All';
  if (materialSelect) materialSelect.value = 'All';
  if (gradeSelect) gradeSelect.value = 'All';
  if (adaOnlyInput) adaOnlyInput.checked = false;
  renderCatalog();
}

function runBudgetEstimator() {
  if (!budgetOutput) return;
  const classrooms = Number(document.getElementById('budget-classrooms')?.value || 0);
  const students = Number(document.getElementById('budget-students')?.value || 0);
  const tier = String(document.getElementById('budget-tier')?.value || 'standard');
  const seatCostMap = { budget: 210, standard: 315, premium: 465 };
  const seatCost = seatCostMap[tier] || seatCostMap.standard;
  const total = classrooms * students * seatCost;

  budgetOutput.textContent = `Estimated project spend: ${formatCurrency(total)} (${formatCurrency(seatCost)} per seat for ${classrooms} classrooms).`;
}

if (catalogGrid) {
  buildBrandOptions();
  renderCatalog();
  renderQuote();

  [brandSelect, materialSelect, gradeSelect, adaOnlyInput].forEach((input) => {
    input?.addEventListener('change', renderCatalog);
  });

  resetButton?.addEventListener('click', resetFilters);
  runBudgetButton?.addEventListener('click', runBudgetEstimator);
}
