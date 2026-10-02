/* Briefato — landing progressive enhancement (assets/js/site.js)
   The site works with JavaScript disabled. This file only adds:
   - a mobile navigation toggle (nav is visible by default without JS)
   - the current year in the footer
   No analytics, no external requests, no tracking. */
(function () {
  "use strict";

  // Signal that JS is available; CSS keys the mobile nav off .js / .no-js.
  var root = document.documentElement;
  root.classList.remove("no-js");
  root.classList.add("js");

  document.addEventListener("DOMContentLoaded", function () {
    // --- mobile navigation ---
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.getElementById("site-nav");
    if (toggle && nav) {
      toggle.hidden = false;
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      // Close on Escape and on outside click.
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && nav.classList.contains("is-open")) {
          nav.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
          toggle.focus();
        }
      });
      document.addEventListener("click", function (e) {
        if (!nav.classList.contains("is-open")) return;
        if (nav.contains(e.target) || toggle.contains(e.target)) return;
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    }

    // --- footer year ---
    var year = document.getElementById("year");
    if (year) year.textContent = String(new Date().getFullYear());
  });
})();
