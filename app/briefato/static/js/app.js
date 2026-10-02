/* Briefato portal — progressive enhancement only. No inline scripts (CSP: script-src 'self'). */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  /* Ctrl+Enter (or Cmd+Enter) submits the surrounding form quickly. */
  function initCtrlEnter() {
    document.addEventListener("keydown", function (event) {
      if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;
      var el = event.target;
      if (!el || !el.form) return;
      if (!el.form.hasAttribute("data-ctrl-enter")) return;
      event.preventDefault();
      if (typeof el.form.requestSubmit === "function") {
        el.form.requestSubmit();
      } else {
        el.form.submit();
      }
    });
  }

  /* data-confirm="Frage?" on a submit button guards destructive actions. */
  function initConfirms() {
    document.addEventListener("click", function (event) {
      var btn = event.target.closest("[data-confirm]");
      if (!btn) return;
      var message = btn.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    });
  }

  /* Toasts dismiss on click or after a delay. */
  function dismiss(el) {
    el.style.opacity = "0";
    window.setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 150);
  }

  function initToasts() {
    document.querySelectorAll("[data-toast]").forEach(function (toast) {
      var close = toast.querySelector("[data-toast-close]");
      if (close) {
        close.addEventListener("click", function () {
          dismiss(toast);
        });
      }
      var delay = parseInt(toast.getAttribute("data-toast-timeout"), 10);
      if (!isNaN(delay) && delay > 0) {
        window.setTimeout(function () {
          dismiss(toast);
        }, delay);
      }
    });
  }

  /* Server-rendered toasts use 200 OK; failed HTMX requests keep the page usable. */
  function initHtmxErrors() {
    document.addEventListener("htmx:responseError", function (event) {
      var detail = event.detail || {};
      var xhr = detail.xhr;
      if (xhr && xhr.status === 403) {
        window.location.reload();
      }
    });
  }

  onReady(function () {
    initCtrlEnter();
    initConfirms();
    initToasts();
    initHtmxErrors();
  });
})();
