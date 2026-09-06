(() => {
  "use strict";
  if (window.__machExploreLoaded) return;
  window.__machExploreLoaded = true;
  let viewer;
  let opener;
  let zoom = 1;

  function createViewer() {
    if (viewer) return;
    viewer = document.createElement("dialog");
    viewer.className = "plot-viewer";
    viewer.setAttribute("aria-labelledby", "plot-viewer-title");
    viewer.innerHTML = `<header class="plot-viewer__header">
      <h2 id="plot-viewer-title">Telemetry plot</h2>
      <button class="mach-control" type="button" data-plot-close autofocus>Close</button>
    </header><div class="plot-viewer__toolbar">
      <button class="mach-control" type="button" data-plot-fit>Fit</button>
      <button class="mach-control" type="button" data-plot-minus aria-label="Zoom out">−</button>
      <output data-plot-zoom aria-live="polite">Fit</output>
      <button class="mach-control" type="button" data-plot-plus aria-label="Zoom in">+</button>
      <a class="mach-control" data-plot-original target="_blank" rel="noopener">Open original</a>
    </div><div class="plot-viewer__stage" tabindex="0" aria-label="Plot; scroll to pan when zoomed"><img alt=""></div>
    <p class="plot-viewer__hint">Zoom in, then scroll or swipe to explore the plot.</p>`;
    document.body.append(viewer);
    const stage = viewer.querySelector(".plot-viewer__stage");
    const img = stage.querySelector("img");
    function resize() {
      if (!viewer.open || !img.naturalWidth) return;
      const ratio = img.naturalWidth / img.naturalHeight;
      const fitted = Math.min(img.naturalWidth, stage.clientWidth - 24, (stage.clientHeight - 24) * ratio);
      img.style.width = `${Math.max(1, fitted * zoom)}px`;
      viewer.querySelector("[data-plot-zoom]").textContent = zoom === 1 ? "Fit" : `${zoom}×`;
      viewer.querySelector("[data-plot-minus]").disabled = zoom <= 1;
      viewer.querySelector("[data-plot-plus]").disabled = zoom >= 6;
    }
    function setZoom(value) {
      zoom = Math.max(1, Math.min(6, value));
      resize();
      if (zoom === 1) stage.scrollTo(0, 0);
    }
    viewer.querySelector("[data-plot-close]").addEventListener("click", () => viewer.close());
    viewer.querySelector("[data-plot-fit]").addEventListener("click", () => setZoom(1));
    viewer.querySelector("[data-plot-minus]").addEventListener("click", () => setZoom(zoom - 1));
    viewer.querySelector("[data-plot-plus]").addEventListener("click", () => setZoom(zoom + 1));
    viewer.addEventListener("close", () => {
      document.body.classList.remove("plot-viewer-open");
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    });
    viewer.addEventListener("click", e => { if (e.target === viewer) viewer.close(); });
    viewer.addEventListener("keydown", e => {
      if (e.key === "+" || e.key === "=") { e.preventDefault(); setZoom(zoom + 1); }
      if (e.key === "-") { e.preventDefault(); setZoom(zoom - 1); }
    });
    img.addEventListener("load", resize);
    new ResizeObserver(resize).observe(stage);
  }

  function openPlot(image, button) {
    createViewer();
    opener = button;
    zoom = 1;
    const full = image.closest("a")?.href || image.src;
    const img = viewer.querySelector("img");
    img.alt = image.alt;
    img.style.width = "";
    viewer.querySelector("[data-plot-original]").href = full;
    viewer.querySelector("[data-plot-zoom]").textContent = "Fit";
    img.src = full;
    viewer.showModal();
    document.body.classList.add("plot-viewer-open");
    viewer.querySelector(".plot-viewer__stage").scrollTo(0, 0);
  }

  function enhancePlots() {
    const names = /(?:burn-telemetry|double-hotfire|propellant-loading|hotfire3-perf|coldflow-test\d+)\.png$/i;
    document.querySelectorAll(".md-content img").forEach(img => {
      if (!names.test(new URL(img.src).pathname) || img.dataset.plotEnhanced) return;
      img.dataset.plotEnhanced = "true";
      img.classList.add("mach-plot");
      const actions = document.createElement("div");
      actions.className = "plot-actions";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "mach-control";
      button.textContent = "Expand plot";
      button.setAttribute("aria-label", `Expand plot: ${img.alt}`);
      button.setAttribute("aria-haspopup", "dialog");
      button.addEventListener("click", () => openPlot(img, button));
      actions.append(button);
      const target = img.closest("a") || img;
      target.after(actions);
      const link = img.closest("a");
      if (link) link.addEventListener("click", e => {
        if (e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
        e.preventDefault(); openPlot(img, button);
      });
    });
  }

  function enhanceTimeline() {
    const list = document.querySelector("ol.gare-timeline");
    if (!list || list.dataset.filtered) return;
    list.dataset.filtered = "true";
    const headings = [...list.querySelectorAll(".gare-timeline__year")];
    const events = [...list.querySelectorAll(".gare-timeline__event")];
    const projects = ["Seraphina", "SPRINT", "GAR-E / Spender", "Chimera", "SABRE", "Borealis"];
    const patterns = [/seraphina/i, /sprint/i, /gar-e|spender/i, /chimera/i, /sabre/i, /borealis/i];
    let section;
    for (const item of list.children) {
      if (item.classList.contains("gare-timeline__year")) {
        section = item;
        item.dataset.year = item.textContent.match(/\d{4}/)[0];
        item.id = `year-${item.dataset.year}`;
      } else {
        item.dataset.year = section.dataset.year;
        item.dataset.projects = projects.filter((_, i) => patterns[i].test(item.textContent)).join("|");
        const tag = item.querySelector(".gare-tag");
        item.dataset.type = [...(tag?.classList || [])].find(c => c.startsWith("gare-tag--"))?.replace("gare-tag--", "") || "organization";
      }
    }
    const toolbar = document.createElement("div");
    toolbar.className = "timeline-controls";
    toolbar.innerHTML = `<div class="timeline-filters">
      <label>Year<select data-filter="year"><option value="">All years</option></select></label>
      <label>Project<select data-filter="project"><option value="">All projects</option></select></label>
      <label>Event type<select data-filter="type"><option value="">All events</option>
        <option value="hotfire">Ignition / hot fire</option><option value="coldflow">Cold flow</option>
        <option value="component">Component / pressure test</option><option value="program">Design milestone</option>
        <option value="organization">Organization</option></select></label>
      <button type="button" class="mach-control" data-filter-clear>Clear filters</button>
    </div><nav class="timeline-years" aria-label="Jump to year"></nav>
    <p class="timeline-filter-status" role="status"></p>`;
    const year = toolbar.querySelector('[data-filter="year"]');
    const project = toolbar.querySelector('[data-filter="project"]');
    const type = toolbar.querySelector('[data-filter="type"]');
    const nav = toolbar.querySelector("nav");
    for (const heading of headings) {
      year.add(new Option(heading.dataset.year, heading.dataset.year));
      const a = document.createElement("a");
      a.href = `#${heading.id}`;
      a.textContent = heading.dataset.year;
      nav.append(a);
    }
    projects.filter(p => events.some(e => e.dataset.projects.split("|").includes(p))).forEach(p => project.add(new Option(p, p)));
    function filter() {
      events.forEach(e => {
        e.hidden = Boolean((year.value && e.dataset.year !== year.value) ||
          (project.value && !e.dataset.projects.split("|").includes(project.value)) ||
          (type.value && e.dataset.type !== type.value));
      });
      headings.forEach(h => {
        h.hidden = !events.some(e => !e.hidden && e.dataset.year === h.dataset.year);
        nav.querySelector(`[href="#${h.id}"]`).hidden = h.hidden;
      });
      const count = events.filter(e => !e.hidden).length;
      toolbar.querySelector(".timeline-filter-status").textContent = count ? `${count} of ${events.length} events` : "No events match these filters.";
    }
    toolbar.addEventListener("change", filter);
    toolbar.querySelector("[data-filter-clear]").addEventListener("click", () => {
      year.value = ""; project.value = ""; type.value = ""; filter();
    });
    const legend = document.querySelector(".gare-timeline-legend");
    (legend || list).before(toolbar);
    filter();
  }

  function prepare() {
    if (viewer?.open) viewer.close();
    enhancePlots(); enhanceTimeline();
  }
  if (window.document$?.subscribe) window.document$.subscribe(prepare);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", prepare, { once: true });
  else prepare();
})();
