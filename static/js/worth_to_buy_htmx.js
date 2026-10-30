/* Friendly request feedback; forms and links also work without HTMX. */
(() => {
  const error = document.getElementById('wtb-request-error');
  function show(message) {
    if (!error) return;
    error.textContent = message;
    error.hidden = false;
    error.scrollIntoView({block: 'nearest'});
  }
  document.addEventListener('htmx:beforeRequest', (event) => {
    if (error) error.hidden = true;
    if (event.detail.target) event.detail.target.setAttribute('aria-busy', 'true');
  });
  document.addEventListener('htmx:afterRequest', (event) => {
    if (event.detail.target) event.detail.target.removeAttribute('aria-busy');
  });
  document.addEventListener('htmx:responseError', (event) => {
    show(event.detail.xhr.status === 403
      ? 'Akses tidak diizinkan atau sesi sudah berubah. Muat ulang halaman dan coba lagi.'
      : 'Permintaan belum berhasil. Coba lagi atau muat ulang halaman.');
  });
  document.addEventListener('htmx:sendError', () => show('Koneksi terputus. Periksa koneksimu, lalu coba lagi.'));
})();
