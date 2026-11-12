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
  for (const form of document.querySelectorAll('[data-billing-form]')) form.addEventListener('submit', () => {
    const button = form.querySelector('button[type=submit], button:not([type])');
    if (!button) return;
    button.disabled = true;
    button.textContent = 'Procesando…';
  });
});
