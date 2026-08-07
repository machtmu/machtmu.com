(() => {
  "use strict";

  if (window.__machHomeEnhancementsLoaded) return;
  window.__machHomeEnhancementsLoaded = true;

  const captions = [
    "Tank assembly showing integrated propulsion system components",
    "MACH team members working alongside the latest propulsion system development",
    "Complete SPRINT system overview showing integrated test setup and components"
  ];

  let cleanupCurrentPage = () => {};

  function initializeHomepage() {
    const hero = document.querySelector(".home-hero");
    if (!hero) return () => {};

    const header = document.querySelector(".md-header");
    const heroContent = hero.querySelector(".home-hero__inner");
    const heroVideo = hero.querySelector(".hero-bg");
    const starsContainer = document.getElementById("stars-container");
    const showcaseVideo = document.querySelector(".showcase-video");
    const slideshowImages = [...document.querySelectorAll(".slideshow-image")];
    const slideshowCaption = document.querySelector(".slideshow-caption");
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const abortController = new AbortController();
    const { signal } = abortController;

    let reducedMotion = motionPreference.matches;
    let heroVisible = hero.getBoundingClientRect().bottom > 0;
    let animationFrame = 0;
    let slideshowTimer = 0;
    let currentSlide = 0;

    function setHeaderOffset() {
      if (header) {
        hero.style.setProperty("--home-header-offset", `${header.offsetHeight}px`);
      }
    }

    function updateHeaderAndParallax() {
      animationFrame = 0;
      const heroRect = hero.getBoundingClientRect();
      const headerHeight = header ? header.offsetHeight : 0;

      if (header) {
        header.dataset.homeHero = heroRect.bottom > headerHeight ? "overlay" : "scrolled";
      }

      if (!heroContent || !heroVideo) return;

      if (reducedMotion || heroRect.bottom <= 0 || heroRect.top >= window.innerHeight) {
        heroContent.style.transform = "none";
        heroVideo.style.transform = "scale(1.025)";
        return;
      }

      const travelled = Math.min(Math.max(-heroRect.top, 0), heroRect.height);
      heroContent.style.transform = `translate3d(0, ${travelled * -0.12}px, 0)`;
      heroVideo.style.transform = `translate3d(0, ${travelled * 0.04}px, 0) scale(1.025)`;
    }

    function scheduleVisualUpdate() {
      if (!animationFrame) {
        animationFrame = window.requestAnimationFrame(updateHeaderAndParallax);
      }
    }

    function activeScheme() {
      return document.body.dataset.mdColorScheme === "slate" ? "dark" : "light";
    }

    function updateHeroPlayback() {
      if (!heroVideo) return;
      if (!reducedMotion && heroVisible && !document.hidden) {
        heroVideo.play().catch(() => {});
      } else {
        heroVideo.pause();
      }
    }

    function updateHeroMedia() {
      if (!heroVideo) return;
      const scheme = activeScheme();
      const source = scheme === "dark" ? heroVideo.dataset.darkSrc : heroVideo.dataset.lightSrc;
      const poster = scheme === "dark" ? heroVideo.dataset.darkPoster : heroVideo.dataset.lightPoster;

      if (poster) heroVideo.poster = poster;

      if (reducedMotion) {
        heroVideo.pause();
        if (heroVideo.hasAttribute("src")) {
          heroVideo.removeAttribute("src");
          heroVideo.load();
        }
        return;
      }

      if (source && heroVideo.getAttribute("src") !== source) {
        heroVideo.pause();
        heroVideo.src = source;
        heroVideo.preload = "auto";
        heroVideo.load();
      }
      updateHeroPlayback();
    }

    function createStars() {
      if (!starsContainer) return;
      starsContainer.replaceChildren();
      const count = window.innerWidth <= 768 ? 45 : 90;
      const fragment = document.createDocumentFragment();

      for (let index = 0; index < count; index += 1) {
        const star = document.createElement("span");
        const size = Math.random() * 2.5 + 0.35;
        star.className = "star";
        star.style.width = `${size}px`;
        star.style.height = `${size}px`;
        star.style.top = `${Math.random() * 100}%`;
        star.style.left = `${Math.random() * 100}%`;
        star.style.animationDuration = `${Math.random() * 5 + 2}s`;
        star.style.animationDelay = `${Math.random() * 3}s`;
        fragment.appendChild(star);
      }

      starsContainer.appendChild(fragment);
    }

    function showSlide(index) {
      currentSlide = index;
      slideshowImages.forEach((image, imageIndex) => {
        image.style.opacity = imageIndex === currentSlide ? "1" : "0";
      });
      if (slideshowCaption) {
        slideshowCaption.textContent = captions[currentSlide] || "";
      }
    }

    function updateSlideshow() {
      window.clearInterval(slideshowTimer);
      slideshowTimer = 0;
      showSlide(0);

      if (!reducedMotion && slideshowImages.length > 1) {
        slideshowTimer = window.setInterval(() => {
          showSlide((currentSlide + 1) % slideshowImages.length);
        }, 4000);
      }
    }

    function updateShowcasePlayback(isVisible = false) {
      if (!showcaseVideo) return;
      if (!reducedMotion && isVisible && !document.hidden) {
        showcaseVideo.play().catch(() => {});
      } else {
        showcaseVideo.pause();
      }
    }

    const heroObserver = "IntersectionObserver" in window && heroVideo
      ? new IntersectionObserver(entries => {
          heroVisible = entries[0]?.isIntersecting ?? false;
          updateHeroPlayback();
        }, { rootMargin: "100px 0px" })
      : null;

    if (heroObserver) heroObserver.observe(hero);

    const showcaseObserver = "IntersectionObserver" in window && showcaseVideo
      ? new IntersectionObserver(entries => {
          updateShowcasePlayback(entries[0]?.isIntersecting ?? false);
        }, { rootMargin: "200px 0px" })
      : null;

    if (showcaseObserver) showcaseObserver.observe(showcaseVideo);

    const schemeObserver = new MutationObserver(mutations => {
      if (mutations.some(mutation => mutation.attributeName === "data-md-color-scheme")) {
        updateHeroMedia();
      }
    });
    schemeObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"]
    });

    function handleMotionPreference() {
      reducedMotion = motionPreference.matches;
      document.body.classList.toggle("home-reduced-motion", reducedMotion);
      updateHeroMedia();
      updateSlideshow();
      updateShowcasePlayback(false);
      scheduleVisualUpdate();
    }

    function handleResize() {
      setHeaderOffset();
      scheduleVisualUpdate();
    }

    function handleVisibilityChange() {
      updateHeroPlayback();
      if (document.hidden) updateShowcasePlayback(false);
    }

    window.addEventListener("scroll", scheduleVisualUpdate, { passive: true, signal });
    window.addEventListener("resize", handleResize, { passive: true, signal });
    document.addEventListener("visibilitychange", handleVisibilityChange, { signal });
    motionPreference.addEventListener("change", handleMotionPreference);

    setHeaderOffset();
    createStars();
    updateHeroMedia();
    updateSlideshow();
    updateHeaderAndParallax();

    return () => {
      abortController.abort();
      motionPreference.removeEventListener("change", handleMotionPreference);
      heroObserver?.disconnect();
      showcaseObserver?.disconnect();
      schemeObserver.disconnect();
      window.clearInterval(slideshowTimer);
      if (animationFrame) window.cancelAnimationFrame(animationFrame);
      heroVideo?.pause();
      showcaseVideo?.pause();
      header?.removeAttribute("data-home-hero");
      document.body.classList.remove("home-reduced-motion");
    };
  }

  function activateCurrentPage() {
    cleanupCurrentPage();
    cleanupCurrentPage = initializeHomepage();
  }

  activateCurrentPage();

  if (window.document$?.subscribe) {
    window.document$.subscribe(activateCurrentPage);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", activateCurrentPage, { once: true });
  }
})();
