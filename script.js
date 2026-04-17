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
