(function () {
  "use strict";

  let searchIndexPromise;
  let lastFocusedElement;

  const getDialog = () => document.querySelector("[data-mach-search-input]")?.closest("[role='dialog']");
  const getSearchButton = () => document.querySelector("[data-mach-search-open]");

  function preparePage() {
    document.querySelectorAll(".md-overlay[aria-label]").forEach((overlay) => {
      overlay.removeAttribute("aria-label");
    });

    const drawer = document.getElementById("__drawer");
    const toggle = document.querySelector("[data-mach-drawer-toggle]");
    if (drawer && toggle) toggle.setAttribute("aria-expanded", String(drawer.checked));

    const shortcut = document.querySelector(".mach-search-toggle__shortcut");
    if (shortcut) shortcut.textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl+K";
  }

  function stripMarkup(value) {
    const element = document.createElement("div");
    element.innerHTML = value || "";
    return (element.textContent || "").replace(/\s+/g, " ").trim();
  }

  function loadSearchIndex() {
    if (!searchIndexPromise) {
      searchIndexPromise = fetch("/search.json", { credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw new Error("Search index unavailable");
          return response.json();
        })
        .then((data) => Array.isArray(data) ? data : (data.items || data.docs || []));
    }
    return searchIndexPromise;
  }

  function setStatus(message) {
    const status = document.querySelector("[data-mach-search-status]");
    if (status) status.textContent = message;
  }

  function renderResults(items, query) {
    const results = document.querySelector("[data-mach-search-results]");
    if (!results) return;
    results.replaceChildren();

    if (!query) {
      setStatus("Type to search");
      return;
    }

    if (!items.length) {
      setStatus("No results");
      return;
    }

    setStatus(`${items.length} ${items.length === 1 ? "result" : "results"}`);
    items.forEach((item) => {
      const listItem = document.createElement("li");
      const link = document.createElement("a");
      const title = document.createElement("span");
      const excerpt = document.createElement("span");
      const location = String(item.location || item.url || "").replace(/^\/+/, "");
      const text = stripMarkup(item.text || item.content || "");

      link.href = `/${location}`;
      title.className = "mach-search-results__title";
      title.textContent = stripMarkup(item.title) || location || "MACH";
      excerpt.className = "mach-search-results__text";
      excerpt.textContent = text.length > 180 ? `${text.slice(0, 177)}…` : text;
      link.append(title);
      if (excerpt.textContent) link.append(excerpt);
      listItem.append(link);
      results.append(listItem);
    });
  }

  function runSearch(value) {
    const query = value.trim().toLocaleLowerCase();
    if (!query) {
      renderResults([], "");
      return;
    }

    setStatus("Searching…");
    loadSearchIndex()
      .then((items) => {
        const terms = query.split(/\s+/).filter(Boolean);
        const ranked = items
          .map((item) => {
            const title = stripMarkup(item.title).toLocaleLowerCase();
            const text = stripMarkup(item.text || item.content).toLocaleLowerCase();
            const location = String(item.location || item.url || "").toLocaleLowerCase();
            const matches = terms.every((term) => title.includes(term) || text.includes(term) || location.includes(term));
            if (!matches) return null;
            let score = 0;
            terms.forEach((term) => {
              if (title === term) score += 12;
              else if (title.includes(term)) score += 8;
              if (location.includes(term)) score += 3;
              if (text.includes(term)) score += 1;
            });
            return { item, score };
          })
          .filter(Boolean)
          .sort((a, b) => b.score - a.score)
          .slice(0, 12)
          .map((entry) => entry.item);
        renderResults(ranked, query);
      })
      .catch(() => setStatus("Search is unavailable"));
  }

  function openSearch() {
    const dialog = getDialog();
    const button = getSearchButton();
    if (!dialog || !button || !dialog.hidden) return;
    lastFocusedElement = document.activeElement;
    dialog.hidden = false;
    button.setAttribute("aria-expanded", "true");
    document.body.classList.add("mach-search-open");
    const input = dialog.querySelector("[data-mach-search-input]");
    input?.focus();
    setStatus(input?.value ? "Searching…" : "Type to search");
    loadSearchIndex().catch(() => setStatus("Search is unavailable"));
  }

  function closeSearch() {
    const dialog = getDialog();
    const button = getSearchButton();
    if (!dialog || dialog.hidden) return;
    dialog.hidden = true;
    button?.setAttribute("aria-expanded", "false");
    document.body.classList.remove("mach-search-open");
    if (lastFocusedElement instanceof HTMLElement && document.contains(lastFocusedElement)) lastFocusedElement.focus();
  }

  document.addEventListener("click", (event) => {
    const drawerToggle = event.target.closest("[data-mach-drawer-toggle]");
    if (drawerToggle) {
      const drawer = document.getElementById("__drawer");
      if (drawer) {
        drawer.checked = !drawer.checked;
        drawer.dispatchEvent(new Event("change", { bubbles: true }));
        drawerToggle.setAttribute("aria-expanded", String(drawer.checked));
      }
      return;
    }

    if (event.target.closest("[data-mach-search-open]")) openSearch();
    if (event.target.closest("[data-mach-search-close]")) closeSearch();
  });

  document.addEventListener("change", (event) => {
    if (event.target.id === "__drawer") preparePage();
  });

  document.addEventListener("input", (event) => {
    if (event.target.matches("[data-mach-search-input]")) runSearch(event.target.value);
  });

  document.addEventListener("keydown", (event) => {
    const isEditable = event.target.matches("input, textarea, select, [contenteditable='true']");
    if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
      event.preventDefault();
      openSearch();
    } else if (event.key === "/" && !isEditable) {
      event.preventDefault();
      openSearch();
    } else if (event.key === "Escape") {
      closeSearch();
    }
  });

  document.addEventListener("focusin", (event) => {
    const dialog = getDialog();
    if (!dialog || dialog.hidden || dialog.contains(event.target)) return;
    dialog.querySelector("[data-mach-search-input]")?.focus();
  });

  preparePage();
  if (typeof document$ !== "undefined") document$.subscribe(preparePage);
})();
