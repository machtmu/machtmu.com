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
    let wantsVideo = !motion.matches && innerWidth > 768 && !navigator.connection?.saveData;
    let visible = true;
    let frame = 0;

    function updateHeader() {
      frame = 0;
      if (!header) return;
      hero.style.setProperty("--home-header-offset", `${header.offsetHeight}px`);
      header.dataset.homeHero = hero.getBoundingClientRect().bottom > header.offsetHeight ? "overlay" : "scrolled";
    }
    function scheduleHeader() {
      if (!frame) frame = requestAnimationFrame(updateHeader);
    }
    function updateVideoControl() {
      const label = wantsVideo ? "Pause background video" : "Play background video";
      toggle.dataset.playing = String(wantsVideo);
      toggle.setAttribute("aria-label", label);
      toggle.title = label;
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

    const images = [...document.querySelectorAll(".slideshow-image")];
    const caption = document.querySelector(".slideshow-caption");
    const slideToggle = document.querySelector("[data-slide-motion]");
    const controls = document.querySelector(".slideshow-controls");
    let index = 0;
    let slidesPlaying = !motion.matches && innerWidth > 768;
    let timer;
    function showSlide(next) {
      if (!images.length) return;
      index = (next + images.length) % images.length;
      images.forEach((image, i) => {
        image.style.opacity = i === index ? "1" : "0";
        image.setAttribute("aria-hidden", String(i !== index));
      });
      if (caption) caption.textContent = images[index].alt;
    }
    function updateSlideshow() {
      clearInterval(timer);
      if (slideToggle) {
        slideToggle.textContent = slidesPlaying ? "Pause slideshow" : "Play slideshow";
        slideToggle.setAttribute("aria-pressed", String(slidesPlaying));
      }
      if (slidesPlaying && !document.hidden && images.length > 1) {
        timer = setInterval(() => showSlide(index + 1), 5000);
      }
    }
    if (controls) controls.hidden = false;
    slideToggle?.addEventListener("click", () => { slidesPlaying = !slidesPlaying; updateSlideshow(); }, { signal });
    for (const [selector, direction] of [["[data-slide-previous]", -1], ["[data-slide-next]", 1]]) {
      document.querySelector(selector)?.addEventListener("click", () => {
        slidesPlaying = false;
        showSlide(index + direction);
        updateSlideshow();
      }, { signal });
    }
    motion.addEventListener("change", () => {
      if (motion.matches) { wantsVideo = false; slidesPlaying = false; }
      updateVideo(); updateSlideshow();
    }, { signal });
    window.addEventListener("scroll", scheduleHeader, { passive: true, signal });
    window.addEventListener("resize", () => { scheduleHeader(); updateVideo(); }, { passive: true, signal });
    document.addEventListener("visibilitychange", () => { updateVideo(); updateSlideshow(); }, { signal });
    updateHeader(); updateVideo(); showSlide(0); updateSlideshow();
    cleanup = () => {
      controller.abort(); observer.disconnect(); clearInterval(timer);
      cancelAnimationFrame(frame); video?.pause(); header?.removeAttribute("data-home-hero");
    };
  }
  if (window.document$?.subscribe) window.document$.subscribe(initialize);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, { once: true });
  else initialize();
})();
