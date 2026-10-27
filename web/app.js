const dimensionNames = [
  "Stack compatibility",
  "Security risk",
  "Maintenance health",
  "Ecosystem maturity",
  "Production adoption",
  "Learning curve",
];

const reports = {
  adopt: {
    package: "zod", repo: "TypeScript API", logo: "/brand/dependencies/zod.svg", color: "#62e6a7", verdict: "Adopt", score: 82, confidence: 88,
    take: "Zod fits this TypeScript API without displacing an existing validator. Adopt it for new boundary validation.",
    dimensions: [[92,"Clean fit with the existing runtime."],[90,"No material unpatched risk found."],[78,"Consistent releases and contributor activity."],[74,"Healthy package trajectory and alternatives."],[68,"Broad use across TypeScript projects."],[72,"Small API with strong documentation."]],
  },
  keep: {
    package: "djangorestframework", repo: "Wagtail, Python", logo: "/brand/dependencies/djangorestframework.svg", color: "#dfff35", verdict: "Keep", score: 72.6, confidence: 95,
    take: "Django REST Framework is already part of this Wagtail stack. Keep it, but watch the version ceiling before a future DRF 4.x upgrade.",
    dimensions: [[90,"Already declared in this repository."],[100,"No known unpatched vulnerabilities."],[48,"Healthy project with a version ceiling."],[70,"Established framework and ecosystem."],[52,"Your repository counts as first-party use."],[67,"Strong documentation and familiar APIs."]],
  },
  trial: {
    package: "temporalio", repo: "Node worker service", logo: "/brand/dependencies/temporal.svg", color: "#83a6ff", verdict: "Trial", score: 66.4, confidence: 81,
    take: "Temporal could improve workflow reliability, but replacing cron and queue logic should begin with one bounded worker pilot.",
    dimensions: [[74,"Plausible fit for this worker service."],[88,"No urgent unpatched risk found."],[56,"Healthy, but operationally demanding."],[68,"Mature workflow orchestration category."],[61,"Credible production references."],[59,"A meaningful new operating model."]],
  },
  hold: {
    package: "langchain", repo: "Regulated support workflow", logo: "/brand/dependencies/langchain.svg", color: "#ffbd4a", verdict: "Hold", score: 52.3, confidence: 67,
    take: "LangChain is plausible for this support workflow, but privacy controls and operating evidence need resolution first.",
    dimensions: [[62,"The integration fits, with governance gaps."],[70,"No immediate veto, but review transitive risk."],[36,"Fast change creates upgrade pressure."],[48,"The ecosystem is broad but volatile."],[41,"Evidence is uneven for regulated support."],[51,"Many abstractions increase debugging cost."]],
  },
  avoid: {
    package: "celery", repo: "Browser-only React client", logo: "/brand/dependencies/celery.svg", color: "#ff6f68", verdict: "Avoid", score: 28.1, confidence: 92,
    take: "Celery requires Python worker infrastructure. It does not belong in a browser-only React client, so avoid this dependency here.",
    dimensions: [[8,"The runtime does not match this repository."],[84,"Security is not the blocking issue."],[42,"Maintenance cannot overcome the mismatch."],[20,"The ecosystem is irrelevant to this client."],[26,"Production use exists in another context."],[35,"Adoption would add a second runtime."]],
  },
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const tabs = [...document.querySelectorAll(".report-tabs [role='tab']")];
const readouts = [...document.querySelectorAll(".dimension-readout")];
const reportDimensions = [...document.querySelectorAll("[data-report-dimension]")];
const reportConsole = document.querySelector(".report-console");
const status = document.querySelector("#analysis-status");
const resolutionOrder = [0, 3, 1, 5, 2, 4];
const reportKeys = Object.keys(reports);
const scoreBand = (score) => score >= 85 ? "strong" : score >= 70 ? "solid" : score >= 55 ? "mixed" : score >= 40 ? "watch" : "weak";
let desktopStoryTrigger;
let sequenceTimers = [];
let sequenceToken = 0;
let autoCycleTimer;

function animateNumber(element, target, duration = 430, decimals = 0) {
  if (reducedMotion) { element.textContent = Number(target).toFixed(decimals); return; }
  const start = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = (target * eased).toFixed(decimals).padStart(decimals ? 1 : 2, "0");
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function clearSequence() {
  sequenceTimers.forEach(clearTimeout);
  sequenceTimers = [];
  clearTimeout(autoCycleTimer);
  sequenceToken += 1;
}

function paintReport(key) {
  const report = reports[key];
  document.querySelector("#summary-icon").src = report.logo;
  document.querySelector("#report-package").textContent = report.package;
  document.querySelector("#report-repo").textContent = report.repo;
  document.querySelector("#report-verdict").textContent = report.verdict;
  document.querySelector("#report-confidence").textContent = `${report.confidence}%`;
  document.querySelector("#report-take").textContent = report.take;

  reportDimensions.forEach((card, index) => {
    const [value, note] = report.dimensions[index];
    card.querySelector("header span").textContent = dimensionNames[index];
    card.querySelector("header b").textContent = value;
    card.querySelector("div i").style.setProperty("--score", `${value}%`);
    card.querySelector("p").textContent = note;
  });
}

function runAnalysis(key, { updateUrl = true } = {}) {
  const report = reports[key];
  const token = sequenceToken + 1;
  clearSequence();

  document.querySelector("#hero-icon").src = report.logo;
  document.querySelector("#hero-package").textContent = report.package;
  document.querySelector("#hero-repo").textContent = `against ${report.repo}`;
  document.querySelector("#hero-verdict").textContent = "Processing";
  document.querySelector("#hero-score").textContent = "";
  document.querySelector("#hero-confidence").textContent = "Verdict pending";
  document.querySelector(".analysis-machine").style.setProperty("--verdict-color", report.color);
  reportConsole.style.setProperty("--verdict-color", report.color);

  tabs.forEach((tab) => {
    const selected = tab.dataset.record === key;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  });
  document.querySelector("#report-panel").setAttribute("aria-labelledby", `tab-${key}`);
  paintReport(key);

  document.body.classList.remove("analysis-complete");
  reportConsole.classList.remove("is-ready");
  status.textContent = `Reading ${report.repo}`;
  document.querySelector("#report-score").textContent = "0.0";
  readouts.forEach((readout, index) => {
    readout.classList.remove("is-scanning", "is-resolved");
    readout.querySelector("b").textContent = "00";
    readout.dataset.value = report.dimensions[index][0];
    readout.style.setProperty("--meter", `${report.dimensions[index][0]}%`);
    readout.querySelector("em").textContent = "waiting";
  });
  document.querySelectorAll(".scene-fallback span").forEach((plate) => plate.classList.remove("is-active"));

  window.ARISScene?.reset?.();
  const delay = reducedMotion ? 0 : 440;
  const cadence = reducedMotion ? 0 : 470;

  resolutionOrder.forEach((index, step) => {
    const readout = readouts[index];
    const scanTimer = setTimeout(() => {
      if (token !== sequenceToken) return;
      readout.classList.add("is-scanning");
      readout.querySelector("em").textContent = "checking";
      status.textContent = `Comparing ${dimensionNames[index].toLowerCase()} evidence`;
    }, delay + step * cadence);
    const resolveTimer = setTimeout(() => {
      if (token !== sequenceToken) return;
      readout.classList.remove("is-scanning");
      readout.classList.add("is-resolved");
      readout.querySelector("em").textContent = scoreBand(report.dimensions[index][0]);
      animateNumber(readout.querySelector("b"), report.dimensions[index][0], reducedMotion ? 0 : 360);
    }, delay + step * cadence + (reducedMotion ? 0 : 250));
    sequenceTimers.push(scanTimer, resolveTimer);
  });

  const doneTimer = setTimeout(() => {
    if (token !== sequenceToken) return;
    document.body.classList.add("analysis-complete");
    reportConsole.classList.add("is-ready");
    status.textContent = `${report.verdict} report ready`;
    document.querySelector("#hero-verdict").textContent = report.verdict;
    document.querySelector("#hero-confidence").textContent = `${report.confidence}% confidence`;
    animateNumber(document.querySelector("#hero-score"), report.score, reducedMotion ? 0 : 650, 1);
    animateNumber(document.querySelector("#report-score"), report.score, reducedMotion ? 0 : 650, 1);
    window.ARISScene?.complete?.();
    const nextKey = reportKeys[(reportKeys.indexOf(key) + 1) % reportKeys.length];
    autoCycleTimer = setTimeout(() => runAnalysis(nextKey, { updateUrl: false }), reducedMotion ? 4200 : 2200);
  }, delay + readouts.length * cadence + (reducedMotion ? 0 : 420));
  sequenceTimers.push(doneTimer);

  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set("report", key);
    history.replaceState(null, "", url);
  }
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => runAnalysis(tab.dataset.record));
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    tabs[next].focus();
    runAnalysis(tabs[next].dataset.record);
  });
});

let analysisStarted = false;
function startInitialAnalysis() {
  if (analysisStarted) return;
  analysisStarted = true;
  const requested = new URL(location.href).searchParams.get("report");
  runAnalysis(reports[requested] ? requested : "keep", { updateUrl: false });
}
window.addEventListener("aris:scene-ready", startInitialAnalysis, { once: true });
setTimeout(startInitialAnalysis, 900);

const nav = document.querySelector("#site-nav");
const updateNav = () => nav.classList.toggle("is-scrolled", scrollY > 10);
updateNav();
addEventListener("scroll", updateNav, { passive: true });

const poster = document.querySelector("#video-poster");
poster.addEventListener("click", () => {
  const video = document.querySelector("#demo-video");
  video.src = video.dataset.src;
  video.closest(".video-frame").classList.add("is-playing");
});

if (window.gsap && window.ScrollTrigger && !reducedMotion) {
  gsap.registerPlugin(ScrollTrigger);
  const mm = gsap.matchMedia();
  mm.add("(min-width: 781px) and (min-height: 520px)", () => {
    const travel = () => -(Math.max(700, innerHeight) - 386);
    const timeline = gsap.timeline({
      scrollTrigger: {
        trigger: ".analysis-story",
        start: "top top",
        end: "+=220%",
        pin: ".analysis-stage",
        scrub: .75,
        snap: { snapTo: [0, .46, 1], duration: { min: .18, max: .42 }, delay: .06, ease: "power2.out" },
        anticipatePin: 1,
        invalidateOnRefresh: true,
      },
    });
    desktopStoryTrigger = timeline.scrollTrigger;
    timeline
      .to(".hero-copy", { opacity: .08, ease: "none", duration: .42 }, 0)
      .to(".analysis-machine", { y: -70, scale: .94, opacity: .16, ease: "none", duration: .5 }, .08)
      .to(".report-console", { y: travel, ease: "none", duration: .62 }, .12)
      .to({}, { duration: .82 });

    let wheelLocked = false;
    const stepThroughStory = (event) => {
      if (Math.abs(event.deltaY) < 8) return;
      const trigger = timeline.scrollTrigger;
      const reportStop = trigger.start + (trigger.end - trigger.start) * .46;

      if (wheelLocked) {
        event.preventDefault();
        return;
      }

      if (event.deltaY > 0 && scrollY < reportStop * .72) {
        event.preventDefault();
        wheelLocked = true;
        scrollTo({ top: reportStop, behavior: "smooth" });
        setTimeout(() => { wheelLocked = false; }, 900);
      } else if (event.deltaY < 0 && scrollY > 0 && scrollY < reportStop * 1.35) {
        event.preventDefault();
        wheelLocked = true;
        scrollTo({ top: 0, behavior: "smooth" });
        setTimeout(() => { wheelLocked = false; }, 900);
      }
    };
    addEventListener("wheel", stepThroughStory, { passive: false });

    return () => {
      removeEventListener("wheel", stepThroughStory);
      desktopStoryTrigger = undefined;
      timeline.scrollTrigger?.kill();
      timeline.revert();
      gsap.set([".hero-copy", ".analysis-machine", ".report-console"], { clearProps: "transform,opacity" });
    };
  });
}

document.querySelector(".nav-links a[href='#report']")?.addEventListener("click", (event) => {
  if (!desktopStoryTrigger) return;
  event.preventDefault();
  const reportStop = desktopStoryTrigger.start + (desktopStoryTrigger.end - desktopStoryTrigger.start) * .46;
  history.replaceState(null, "", "#report");
  scrollTo({ top: reportStop, behavior: "smooth" });
});
