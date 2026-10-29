/* Interaksi ringan untuk modul Carbon Footprint (melengkapi HTMX). Tanpa dependensi. */
(function () {
  "use strict";

  /* ---------- Notifikasi kecil ----------
     Server mengirim header HX-Trigger: {"cf:toast": {"message": "..."}}; HTMX mengubahnya
     menjadi event DOM "cf:toast" yang ditangkap di sini. */
  function toast(message) {
    if (!message) return;
    var box = document.getElementById("cf-toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "cf-toasts";
      box.className = "cf-toasts";
      box.setAttribute("role", "status");
      document.body.appendChild(box);
    }
    var el = document.createElement("p");
    el.className = "cf-toast";
    el.textContent = message;
    box.appendChild(el);
    setTimeout(function () {
      el.classList.add("is-leaving");
      setTimeout(function () { el.remove(); }, 300);
    }, 3000);
  }

  document.addEventListener("cf:toast", function (e) {
    toast(e.detail && (e.detail.message || e.detail.value));
  });

  /* Kegagalan jaringan atau server: beri tahu user, jangan diam saja. */
  /* Ruang Analyzer berbahasa Indonesia, halaman user berbahasa Inggris. */
  function inWorkspace() { return !!document.querySelector(".cf--ws"); }
  document.addEventListener("htmx:responseError", function () {
    toast(inWorkspace() ? "Terjadi kesalahan. Coba lagi." : "Something went wrong. Please try again.");
  });
  document.addEventListener("htmx:sendError", function () {
    toast(inWorkspace() ? "Server tidak terjangkau." : "Could not reach the server.");
  });

  /* ---------- Form: placeholder berat mengikuti kategori ---------- */
  function initWeightHint() {
    var data = document.getElementById("cf-weights");
    var category = document.getElementById("id_category");
    var weight = document.getElementById("id_weight_kg");
    if (!data || !category || !weight) return;
    var weights = JSON.parse(data.textContent);
    function update() {
      var w = weights[category.value];
      weight.placeholder = w ? "Default " + w + " kg" : "";
    }
    category.addEventListener("change", update);
    update();
  }

  /* ---------- Pintasan: tekan "/" untuk fokus ke kolom cari ---------- */
  function initSearchShortcut() {
    var search = document.getElementById("cf-q");
    if (!search) return;
    document.addEventListener("keydown", function (e) {
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(tag)) {
        e.preventDefault();
        search.focus();
      }
    });
  }

  /* ---------- Form faktor (Analyzer): tandai kolom yang berbeda dari nilai bawaan ----------
     Server sudah menandai nilai tersimpan (class "is-changed"); di sini penandanya ikut berubah saat mengetik.
     Delegasi event di document supaya tetap jalan setelah HTMX mengganti form. */
  document.addEventListener("input", function (e) {
    var el = e.target;
    if (!el.matches || !el.matches("input[data-default]")) return;
    var field = el.closest(".wtb-field");
    if (!field) return;
    var value = parseFloat(el.value), base = parseFloat(el.dataset["default"]);
    field.classList.toggle("is-changed", !isNaN(value) && Math.abs(value - base) > 0.0000001);
  });

  function init() {
    initWeightHint();
    initSearchShortcut();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
