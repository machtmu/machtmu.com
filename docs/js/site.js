(function () {
  "use strict";
  if (window.__machSiteLoaded) return;
  window.__machSiteLoaded = true;

  let searchIndexPromise;
  let searchRevision = 0;
  let lastFocusedElement;
  let formerMemberDialog;
  let formerMemberOpener;
  let formerCaptionFitFrame;

  function fitFormerCaption(portrait) {
    // A framed image may be wider than its clipped square. Advertise actual
    // rendered image pixels in both grid/viewer, including after resizing.
    const photo = portrait.querySelector("img");
    if (photo?.srcset) photo.sizes = `${Math.ceil(photo.getBoundingClientRect().width)}px`;
    portrait.querySelectorAll(".former-member-name strong, .former-member-summary").forEach((line) => {
      line.style.fontSize = "";
      const range = document.createRange();
      const available = line.clientWidth - 0.5;
      const textWidthOf = () => {
        range.selectNodeContents(line);
        return range.getBoundingClientRect().width;
      };
      if (line.classList.contains("former-member-summary")) {
        // Prefer real role words at the existing readable size. Only a modest
        // 10% fit is allowed before narrow tiles use their compact fallback.
        // Save the fallback once so font loads/resizes can restore full labels.
        line.dataset.compactSummary ??= line.textContent;
        line.dataset.expandedSummary ??= line.dataset.compactSummary
          .replace(/^T&C Lead\b/, "Telemetry and Control Lead")
          .replace(/^PM Lead\b/, "Propellant Management Lead")
          .replace(/^Tech\. Director\b/, "Technical Director");
        const full = line.dataset.fullSummary || line.dataset.compactSummary;
        line.textContent = full;
        if (!portrait.classList.contains("former-member-portrait--detail")) {
          for (const candidate of new Set([full, line.dataset.expandedSummary, line.dataset.compactSummary])) {
            line.textContent = candidate;
            if (textWidthOf() * 0.9 <= available) break;
          }
        }
      }
      const textWidth = textWidthOf();
      if (textWidth > available && available > 0) {
        const base = parseFloat(getComputedStyle(line).fontSize);
        line.style.fontSize = `${Math.floor(base * available / textWidth * 100) / 100}px`;
      }
    });
  }

  function fitFormerCaptions() {
    cancelAnimationFrame(formerCaptionFitFrame);
    formerCaptionFitFrame = requestAnimationFrame(() => {
      document.querySelectorAll(".former-member-portrait").forEach(fitFormerCaption);
    });
  }
  window.addEventListener("resize", fitFormerCaptions);
  document.fonts.ready.then(fitFormerCaptions);

  function prepareFormerMembers() {
    // A single delegated listener/dialog survives Zensical instant navigation.
    // Never retain a removed page's profile or return focus to a detached tile.
    if (formerMemberOpener && !formerMemberOpener.isConnected) {
      if (formerMemberDialog?.open) formerMemberDialog.close();
      formerMemberDialog?.replaceChildren();
      formerMemberOpener = undefined;
    }
    document.querySelectorAll(".former-member-card").forEach((card) => {
      if (card.querySelector(".former-member-open")) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "former-member-open";
      button.setAttribute("aria-haspopup", "dialog");
      const fullSummary = card.querySelector(".former-member-summary")?.dataset.fullSummary;
      button.setAttribute("aria-label", `View ${card.querySelector("strong").textContent}'s profile details${fullSummary ? ': ' + fullSummary : ''}`);
      card.querySelector(".former-member-portrait").append(button);
      card.classList.add("former-member-card--interactive");
      card.closest(".former-members-grid").classList.add("former-members-grid--compact-ready");
    });
    fitFormerCaptions();
  }

  function openFormerMember(button) {
    if (!formerMemberDialog) {
      formerMemberDialog = document.createElement("dialog");
      formerMemberDialog.className = "former-member-dialog md-typeset";
      formerMemberDialog.setAttribute("aria-labelledby", "former-member-dialog-name");
      document.body.append(formerMemberDialog);
      formerMemberDialog.addEventListener("close", () => {
        document.body.classList.remove("former-member-dialog-open");
        if (formerMemberOpener?.isConnected) formerMemberOpener.focus({ preventScroll: true });
      });
      formerMemberDialog.addEventListener("click", (event) => {
        const bounds = formerMemberDialog.getBoundingClientRect();
        if (event.target === formerMemberDialog &&
            (event.clientX < bounds.left || event.clientX > bounds.right ||
             event.clientY < bounds.top || event.clientY > bounds.bottom)) formerMemberDialog.close();
      });
    }
    formerMemberOpener = button;
    const portrait = button.closest(".former-member-portrait").cloneNode(true);
    portrait.classList.add("former-member-portrait--detail");
    portrait.querySelector(".former-member-open").remove();
    portrait.querySelector("strong").id = "former-member-dialog-name";
    const summary = portrait.querySelector(".former-member-summary");
    if (summary) summary.textContent = summary.dataset.fullSummary;
    const image = portrait.querySelector("img");
    if (image) image.loading = "eager";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "former-member-close";
    close.setAttribute("aria-label", "Close profile details");
    close.textContent = "×";
    close.addEventListener("click", () => formerMemberDialog.close());
    portrait.prepend(close);
    const viewer = document.createElement("div");
    viewer.className = "former-member-viewer";
    viewer.append(portrait);
    const links = button.closest(".former-member-card").querySelector(".former-member-links")?.cloneNode(true);
    if (links) viewer.append(links);
    formerMemberDialog.classList.toggle("former-member-dialog--has-links", Boolean(links));
    formerMemberDialog.replaceChildren(viewer);
    formerMemberDialog.showModal();
    // Responsive delivery must describe the expanded photo, not its source
    // thumbnail. The browser still chooses only existing native variants.
    if (image) image.sizes = `${Math.ceil(image.getBoundingClientRect().width)}px`;
    fitFormerCaption(portrait);
    document.body.classList.add("former-member-dialog-open");
    close.focus();
  }

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
    prepareFormerMembers();
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
    const formerMemberButton = event.target.closest(".former-member-open");
    if (formerMemberButton) {
      openFormerMember(formerMemberButton);
      return;
    }
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
