(() => {
  "use strict";
  if (window.__machHomeEnhancementsLoaded) return;
  window.__machHomeEnhancementsLoaded = true;
  let cleanup = () => {};

  function initialize() {
    cleanup();
    const hero = document.querySelector(".home-hero");
    if (!hero) return;
    const controller = new AbortController();
    const { signal } = controller;
    const header = document.querySelector(".md-header");
    const video = hero.querySelector(".hero-bg");
    const toggle = hero.querySelector("[data-hero-motion]");
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    // Start on the approved flame photograph. Fetch motion only when requested.
    let wantsVideo = false;
    let visible = true;
    let frame = 0;
    let headerHeight = header?.offsetHeight || 0;
    let layoutWidth = -1;
    const touchViewport = matchMedia("(hover: none), (pointer: coarse)");

    function measureHeader() {
      headerHeight = header?.offsetHeight || 0;
      if (header && hero.style.getPropertyValue("--home-header-offset") !== `${headerHeight}px`) {
        hero.style.setProperty("--home-header-offset", `${headerHeight}px`);
      }
    }

    function measureLayout() {
      // Safari can resize the visible viewport while its browser controls
      // retract. Do not recrop the photograph, relayout the hero, or reissue
      // video.play() partway through that same swipe. Reframe on a real width
      // change (including rotation) and leave native scroll timing in charge.
      const width = document.documentElement.clientWidth;
      if (touchViewport.matches && width === layoutWidth) return false;
      layoutWidth = width;
      hero.style.removeProperty("--hero-mobile-height");
      measureHeader();
      if (touchViewport.matches && width <= 768) {
        hero.style.setProperty("--hero-mobile-height", `${hero.getBoundingClientRect().height}px`);
      }
      return true;
    }

    function updateHeader() {
      frame = 0;
      // Scroll animation is native CSS. JavaScript only changes the header
      // palette when crossing the hero boundary, not the animated layers.
      const bounds = hero.getBoundingClientRect();
      const palette = bounds.bottom > headerHeight ? "overlay" : "scrolled";
      if (header && header.dataset.homeHero !== palette) header.dataset.homeHero = palette;
    }
    function scheduleHeader() {
      if (!frame) frame = requestAnimationFrame(updateHeader);
    }
    function updateVideoControl() {
      const label = wantsVideo ? "Pause hero video" : "Play hero video";
      toggle.dataset.playing = String(wantsVideo);
      toggle.setAttribute("aria-label", label);
    }
    function updateVideo() {
      if (!video || !toggle) return;
      toggle.hidden = false;
      updateVideoControl();
      if (!wantsVideo || !visible || document.hidden) {
        video.pause();
        return;
      }
      const src = innerWidth <= 768 ? video.dataset.mobileSrc : video.dataset.lightSrc;
      if (video.getAttribute("src") !== src) {
        video.src = src;
        video.load();
      }
      video.play().catch(() => {
        if (signal.aborted || !visible || document.hidden) return;
        wantsVideo = false;
        updateVideoControl();
      });
    }
    toggle?.addEventListener("click", () => { wantsVideo = !wantsVideo; updateVideo(); }, { signal });
    const observer = new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      updateVideo();
    });
    observer.observe(hero);

    const hotfire = document.querySelector(".home-hotfire");
    const hotfireVideo = hotfire?.querySelector(".showcase-video");
    if (hotfireVideo) {
      const revealHotfire = () => { hotfire.dataset.revealed = "true"; };
      const updateHotfirePlayback = () => {
        const playing = !hotfireVideo.paused && !hotfireVideo.ended;
        hotfire.dataset.playing = String(playing);
        // Native controls own this box. CSS never transforms the video, using
        // a content-only view box where supported and a colour-only fallback.
        hotfire.dataset.controlsReady = String(hotfireVideo.readyState >= 1);
        if (playing && matchMedia("(hover: none), (pointer: coarse)").matches) revealHotfire();
      };
      // Reveal colour on touch without intercepting native playback controls.
      // Keep that choice for this element's lifetime, including reinitialization.
      hotfireVideo.addEventListener("pointerup", event => {
        if (event.pointerType === "touch" || event.pointerType === "pen") revealHotfire();
      }, { passive: true, signal });
      hotfireVideo.addEventListener("click", () => {
        if (matchMedia("(hover: none), (pointer: coarse)").matches) revealHotfire();
      }, { passive: true, signal });
      for (const type of ["play", "pause", "ended", "loadedmetadata", "emptied"]) {
        hotfireVideo.addEventListener(type, updateHotfirePlayback, { signal });
      }
      updateHotfirePlayback();
    }

    motion.addEventListener("change", () => {
      if (motion.matches) wantsVideo = false;
      scheduleHeader(); updateVideo();
    }, { signal });
    window.addEventListener("scroll", scheduleHeader, { passive: true, signal });
    window.addEventListener("resize", () => {
      if (measureLayout()) updateVideo();
      scheduleHeader();
    }, { passive: true, signal });
    document.addEventListener("visibilitychange", updateVideo, { signal });
    measureLayout(); updateHeader(); updateVideo();
    cleanup = () => {
      controller.abort(); observer.disconnect();
      cancelAnimationFrame(frame); video?.pause(); header?.removeAttribute("data-home-hero");
      hero.style.removeProperty("--hero-mobile-height");
    };
  }
  if (window.document$?.subscribe) window.document$.subscribe(initialize);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, { once: true });
  else initialize();
})();
