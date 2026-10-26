/* Informational preview only; Django validates and calculates the saved result. */
(() => {
  const form = document.getElementById('wtb-analysis-form');
  if (!form) return;
  const price = form.elements.price;
  const wears = form.elements.expected_wears;
  const amount = document.getElementById('wtb-cpw');
  const note = document.getElementById('wtb-preview-note');
  const integerFormat = new Intl.NumberFormat('id-ID');
  const reset = () => {
    amount.textContent = '—';
    note.textContent = 'Isi harga dan total pemakaian untuk melihat perkiraannya.';
  };
  function preview() {
    // Integer cents avoid rounding drift for money (same half-up rule as server).
    if (!/^\d+(\.\d{1,2})?$/.test(price.value) || !/^\d+$/.test(wears.value)
        || !price.validity.valid || !wears.validity.valid) return reset();
    const [whole, fraction = ''] = price.value.split('.');
    const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
    const count = BigInt(wears.value);
    if (cents <= 0n || count <= 0n) return reset();
    const rounded = (2n * cents + count) / (2n * count);
    amount.textContent = `Rp${integerFormat.format(rounded / 100n)},${String(rounded % 100n).padStart(2, '0')}`;
    note.textContent = `Harga dibagi ${integerFormat.format(count)} kali pemakaian. Ini perkiraan, belum hasil rekomendasi.`;
  }
  price.addEventListener('input', preview);
  wears.addEventListener('input', preview);
  preview();
  // Error-summary links must reveal fields inside optional sections.
  const errors = document.getElementById('wtb-errors');
  if (errors) {
    errors.focus();
    errors.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (!link) return;
      const field = document.getElementById(link.hash.slice(1));
      if (!field) return;
      const details = field.closest('details');
      if (details) details.open = true;
      field.focus();
    });
  }
})();
