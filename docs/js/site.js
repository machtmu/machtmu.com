(function () {
  "use strict";
  if (window.__machSiteLoaded) return;
  window.__machSiteLoaded = true;

  let searchIndexPromise;
  let searchRevision = 0;
  let lastFocusedElement;

  const getDialog = () => document.querySelector("[data-mach-search-input]")?.closest("[role='dialog']");

  function prepareLogos() {
    const scheme = document.body.dataset.mdColorScheme;
    const dark = scheme ? scheme === "slate" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.querySelectorAll(".md-logo .mach-logo").forEach((logo) => {
      const source = logo.querySelector(".mach-logo__picture source");
      const overlay = logo.closest(".md-header")?.dataset.homeHero === "overlay";
      // One native image surface: source selection cannot paint two sibling
      // logos during instant navigation or a system-theme transition.
      const media = dark || overlay ? "all" : "not all";
      if (source && source.media !== media) source.media = media;
      const hdr = logo.querySelector(".mach-logo__hdr");
      const image = logo.querySelector(".mach-logo__image");
      // Do not brighten an old black frame while a new white source is loading.
      if (hdr) hdr.hidden = !dark || overlay || !image?.complete || !image.currentSrc.endsWith("/logo-header-dark.png");
    });
  }

  const logoObserver = new MutationObserver(prepareLogos);
  logoObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });
  const logoHeader = document.querySelector(".md-header");
  if (logoHeader) logoObserver.observe(logoHeader, { attributes: true, attributeFilter: ["data-home-hero"] });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", prepareLogos);
  document.addEventListener("load", (event) => {
    if (event.target.matches?.(".mach-logo__image")) prepareLogos();
  }, true);

  function preparePage() {
    prepareLogos();
    // The theme keeps the header during instant navigation. Derive visibility
    // from the current page rather than the page that first created it.
    const headerLogo = document.querySelector('.md-header [data-md-component="logo"]');
    if (headerLogo) {
      const home = Boolean(document.querySelector(".home-hero"));
      headerLogo.dataset.machHome = String(home);
      if (home) headerLogo.setAttribute("aria-current", "page");
      else headerLogo.removeAttribute("aria-current");
    }

    document.querySelectorAll(".md-logo[title], .md-logo [title], .home-hero__logo[title]").forEach((logo) => {
      logo.removeAttribute("title");
    });

    document.querySelectorAll(".md-overlay[aria-label]").forEach((overlay) => {
      overlay.removeAttribute("aria-label");
    });

    const drawer = document.getElementById("__drawer");
    const toggle = document.querySelector("[data-mach-drawer-toggle]");
    if (drawer && toggle) toggle.setAttribute("aria-expanded", String(drawer.checked));

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
        .then((data) => {
          const items = Array.isArray(data) ? data : (data.items || data.docs || []);
          return items.map((item) => ({
            ...item,
            title: stripMarkup(item.title),
            text: stripMarkup(item.text || item.content),
          }));
        })
        .catch((error) => {
          searchIndexPromise = undefined;
          throw error;
        });
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
    const revision = ++searchRevision;
    const query = value.trim().toLocaleLowerCase();
    if (!query) {
      renderResults([], "");
      return;
    }

    setStatus("Searching…");
    loadSearchIndex()
      .then((items) => {
        if (revision !== searchRevision || getDialog()?.hidden) return;
        const terms = query.split(/\s+/).filter(Boolean);
        const ranked = items
          .map((item) => {
            const title = item.title.toLocaleLowerCase();
            const text = item.text.toLocaleLowerCase();
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
      .catch(() => {
        if (revision === searchRevision && !getDialog()?.hidden) setStatus("Search is unavailable. Try searching again.");
      });
  }

  function openSearch() {
    const dialog = getDialog();
    if (!dialog || !dialog.hidden) return;
    lastFocusedElement = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("mach-search-open");
    const input = dialog.querySelector("[data-mach-search-input]");
    input?.focus();
    runSearch(input?.value || "");
  }

  function closeSearch() {
    const dialog = getDialog();
    if (!dialog || dialog.hidden) return;
    searchRevision++;
    dialog.hidden = true;
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
      const drawer = document.getElementById("__drawer");
      if (drawer?.checked) {
        drawer.checked = false;
        drawer.dispatchEvent(new Event("change", { bubbles: true }));
        document.querySelector("[data-mach-drawer-toggle]")?.focus();
      }
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
