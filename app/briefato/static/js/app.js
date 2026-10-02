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

  /* Copy-to-clipboard: [data-copy-target="#id"] copies the target's value/text. */
  function copyText(value) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(value);
    }
    return new Promise(function (resolve, reject) {
      try {
        var area = document.createElement("textarea");
        area.value = value;
        area.setAttribute("readonly", "");
        document.body.appendChild(area);
        area.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(area);
        if (ok) {
          resolve();
        } else {
          reject(new Error("execCommand copy failed"));
        }
      } catch (err) {
        reject(err);
      }
    });
  }

  function setFeedback(el, ok, text) {
    if (!el) return;
    el.textContent = text;
    el.classList.remove("is-ok", "is-error");
    el.classList.add(ok ? "is-ok" : "is-error");
    window.setTimeout(function () {
      el.textContent = "";
      el.classList.remove("is-ok", "is-error");
    }, 5000);
  }

  function initCopy() {
    document.addEventListener("click", function (event) {
      var btn = event.target.closest("[data-copy-target]");
      if (!btn) return;
      var target = document.querySelector(btn.getAttribute("data-copy-target"));
      if (!target) return;
      var value = target.value !== undefined ? target.value : (target.textContent || "");
      var feedback = document.querySelector("[data-copy-feedback]");
      copyText(value)
        .then(function () {
          setFeedback(feedback, true, "Text kopiert. Sie können ihn jetzt ins KIS einfügen.");
        })
        .catch(function () {
          setFeedback(feedback, false, "Kopieren nicht möglich. Bitte markieren Sie den Text und kopieren Sie mit Strg + C.");
        });
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
    initCopy();
    initHtmxErrors();
  });
})();
