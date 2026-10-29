(function () {
  const table = document.getElementById("lc-table");
  if (!table) return;

  const rows = document.getElementById("lc-rows");
  const empty = document.getElementById("lc-empty");
  const message = document.getElementById("lc-message");
  const filterForm = document.getElementById("lc-filter");
  const createForm = document.getElementById("lc-create-form");
  const csrfToken = createForm.querySelector("[name=csrfmiddlewaretoken]").value;
  const statusChoices = JSON.parse(document.getElementById("lc-status-choices").textContent);
  const PLACEHOLDER = "00000000-0000-0000-0000-000000000000";

  function urlFor(template, id) {
    return template.replace(PLACEHOLDER, id);
  }

  function showMessage(text, isError) {
    message.textContent = text;
    message.classList.toggle("is-error", Boolean(isError));
  }

  function toggleEmpty() {
    const isEmpty = rows.children.length === 0;
    table.hidden = isEmpty;
    empty.hidden = !isEmpty;
  }

  function cell(text) {
    const td = document.createElement("td");
    td.textContent = text;
    return td;
  }

  function buildRow(record) {
    const tr = document.createElement("tr");
    tr.append(
      cell(record.item),
      cell(record.condition_display),
      cell(record.damage_description || "-"),
      cell(record.recommendation_display)
    );

    const select = document.createElement("select");
    select.setAttribute("aria-label", "Status " + record.item);
    statusChoices.forEach(function ([value, label]) {
      select.add(new Option(label, value, false, value === record.status));
    });
    select.dataset.previous = record.status;
    select.addEventListener("change", function () {
      updateStatus(record.id, select);
    });
    const statusCell = document.createElement("td");
    statusCell.append(select);

    const edit = document.createElement("a");
    edit.href = urlFor(table.dataset.editUrl, record.id);
    edit.textContent = "Edit";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Hapus";
    remove.addEventListener("click", function () {
      deleteRecord(record, tr);
    });
    const actions = document.createElement("td");
    actions.append(edit, " ", remove);

    tr.append(statusCell, actions);
    return tr;
  }

  async function loadRecords() {
    const params = new URLSearchParams(new FormData(filterForm));
    try {
      const response = await fetch(table.dataset.jsonUrl + "?" + params);
      if (!response.ok) throw new Error(response.status);
      const data = await response.json();
      rows.replaceChildren(...data.records.map(buildRow));
      toggleEmpty();
    } catch (error) {
      showMessage("Gagal memuat data. Coba muat ulang halaman.", true);
    }
  }

  async function post(url, body) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: body,
      });
      const data = await response.json().catch(function () { return {}; });
      return { ok: response.ok, data: data };
    } catch (error) {
      return { ok: false, data: {} };
    }
  }

  async function updateStatus(id, select) {
    const body = new FormData();
    body.append("status", select.value);
    const result = await post(urlFor(table.dataset.statusUrl, id), body);
    if (result.ok) {
      select.dataset.previous = select.value;
      showMessage("Status diperbarui.");
      if (filterForm.elements.status.value) loadRecords();
    } else {
      select.value = select.dataset.previous;
      showMessage("Status gagal diperbarui.", true);
    }
  }

  async function deleteRecord(record, tr) {
    if (!confirm("Hapus catatan kondisi " + record.item + "?")) return;
    const next = tr.nextSibling;
    tr.remove();
    toggleEmpty();
    const result = await post(urlFor(table.dataset.deleteUrl, record.id), new FormData());
    if (result.ok) {
      showMessage("Catatan kondisi dihapus.");
    } else {
      rows.insertBefore(tr, next);
      toggleEmpty();
      showMessage("Gagal menghapus catatan.", true);
    }
  }

  createForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const result = await post(createForm.dataset.ajaxUrl, new FormData(createForm));
    if (result.ok) {
      createForm.reset();
      showMessage("Catatan ditambahkan. Rekomendasi: " + result.data.record.recommendation_display + ".");
      loadRecords();
    } else {
      const errors = Object.values(result.data.errors || {}).flat().map(function (e) { return e.message; });
      showMessage(errors.join(" ") || "Data belum valid.", true);
    }
  });

  filterForm.addEventListener("change", loadRecords);
  filterForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loadRecords();
  });

  loadRecords();
})();