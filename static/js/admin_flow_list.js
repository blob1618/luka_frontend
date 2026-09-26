(() => {
  const filters = document.getElementById("flow-list-filters");
  if (!filters) return;

  const search = document.getElementById("flow-search");
  const status = document.getElementById("flow-status-filter");
  const count = document.getElementById("flow-list-count");
  const empty = document.getElementById("flow-list-empty");
  const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  const cards = Array.from(document.querySelectorAll("#flow-list .flow-card"), (card) => ({
    element: card,
    text: normalize(card.dataset.flowSearch),
    status: card.dataset.flowStatus,
  }));

  function applyFilters() {
    const query = normalize(search.value);
    let visible = 0;
    cards.forEach((card) => {
      const matches = card.text.includes(query) && (status.value === "all" || card.status === status.value);
      card.element.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} de ${cards.length} flujos`;
    empty.hidden = visible !== 0;
  }

  filters.addEventListener("submit", (event) => event.preventDefault());
  search.addEventListener("input", applyFilters);
  status.addEventListener("change", applyFilters);
  filters.addEventListener("reset", (event) => {
    event.preventDefault();
    search.value = "";
    status.value = "all";
    applyFilters();
    search.focus();
  });
  applyFilters();
})();
