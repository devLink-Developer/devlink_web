document.addEventListener('DOMContentLoaded', () => {
  const lines = document.getElementById('invoice-lines');
  const counter = document.getElementById('id_lines-TOTAL_FORMS');
  const add = document.getElementById('add-line');
  const money = new Intl.NumberFormat('es-AR', {style:'currency', currency:'ARS'});
  function updateTotal() {
    if (!lines) return;
    let total = 0;
    for (const line of lines.querySelectorAll('.invoice-line')) {
      if (line.querySelector('[name$="-DELETE"]')?.checked) continue;
      const quantity = Number(line.querySelector('[name$="-quantity"]').value || 0);
      const price = Number(line.querySelector('[name$="-unit_price"]').value || 0);
      total += Math.round((quantity * price + Number.EPSILON) * 100) / 100;
    }
    document.getElementById('preview-total').textContent = money.format(total);
  }
  if (add) add.addEventListener('click', () => {
    const index = Number(counter.value);
    if (index >= 50) return;
    const source = document.getElementById('empty-line').innerHTML.replaceAll('__prefix__', String(index));
    lines.insertAdjacentHTML('beforeend', source);
    counter.value = index + 1;
    if (index + 1 >= 50) add.disabled = true;
    lines.lastElementChild.querySelector('input:not([type=hidden])').focus();
    updateTotal();
  });
  lines?.addEventListener('input', updateTotal);
  lines?.addEventListener('change', updateTotal);
  updateTotal();

  const cancellationForm = document.querySelector('[data-cancellation-form]');
  if (cancellationForm) {
    const checkboxes = [...cancellationForm.querySelectorAll('input[name="invoices"]:not(:disabled)')];
    const reason = cancellationForm.querySelector('[name="reason"]');
    const submit = cancellationForm.querySelector('[data-cancellation-submit]');
    const countOutput = cancellationForm.querySelector('[data-selected-count]');
    const totalOutput = cancellationForm.querySelector('[data-selected-total]');
    const refreshSelection = () => {
      const selected = checkboxes.filter((checkbox) => checkbox.checked);
      const total = selected.reduce((sum, checkbox) => {
        const raw = checkbox.closest('[data-cancellation-row]')?.dataset.available || '0';
        return sum + Number(raw.replace(',', '.'));
      }, 0);
      countOutput.textContent = String(selected.length);
      totalOutput.textContent = money.format(total);
      submit.disabled = selected.length === 0 || !reason.value.trim();
    };
    cancellationForm.addEventListener('change', refreshSelection);
    reason.addEventListener('input', refreshSelection);
    refreshSelection();
  }

  const partialForm = document.querySelector('[data-partial-form]');
  if (partialForm) {
    const totalOutput = partialForm.querySelector('[data-partial-total]');
    const refreshPartial = () => {
      let total = 0;
      for (const row of partialForm.querySelectorAll('[data-partial-row]')) {
        const quantity = Number((row.querySelector('input[type="number"]')?.value || '0').replace(',', '.'));
        const price = Number((row.dataset.unitPrice || '0').replace(',', '.'));
        total += Math.round((quantity * price + Number.EPSILON) * 100) / 100;
      }
      totalOutput.textContent = money.format(total);
    };
    partialForm.addEventListener('input', refreshPartial);
    refreshPartial();
  }

  for (const form of document.querySelectorAll('[data-discard-credit]')) {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('¿Descartar este borrador de nota de crédito? Esta acción no se puede deshacer.')) {
        event.preventDefault();
      }
    });
  }

  for (const form of document.querySelectorAll('[data-billing-form]')) form.addEventListener('submit', () => {
    const button = form.querySelector('button[type=submit], button:not([type])');
    if (!button) return;
    button.disabled = true;
    button.textContent = 'Procesando…';
  });
});
