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

  /* Wizard: fade between steps, move focus to the step heading, Esc = back.
     The fade re-submits with the clicked submitter (requestSubmit) so the button's
     name/value — which carries the wizard action — is preserved. */
  function prefReducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function initWizard() {
    var heading = document.querySelector("[data-wizard-heading]");
    if (heading && typeof heading.focus === "function") {
      try {
        heading.focus();
      } catch (err) {
        /* focus can fail in odd embedding contexts; the heading is still visible */
      }
    }

    document.addEventListener("submit", function (event) {
      var form = event.target;
      if (!form || form.tagName !== "FORM") return;
      if (!form.closest("[data-wizard-form]")) return;
      if (form.dataset.wizardBypass === "1") {
        form.dataset.wizardBypass = "0";
        return;
      }
      if (prefReducedMotion() || typeof form.requestSubmit !== "function") return;
      event.preventDefault();
      var panel = form.closest(".wizard-step");
      if (panel) panel.classList.add("wizard-step--leaving");
      var submitter = event.submitter || null;
      window.setTimeout(function () {
        form.dataset.wizardBypass = "1";
        try {
          form.requestSubmit(submitter || undefined);
        } catch (err) {
          form.dataset.wizardBypass = "0";
          form.submit();
        }
      }, 180);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      var back = document.querySelector("[data-wizard-back]");
      if (!back) return;
      event.preventDefault();
      back.click();
    });
  }

  onReady(function () {
    initCtrlEnter();
    initConfirms();
    initToasts();
    initCopy();
    initHtmxErrors();
    initWizard();
  });
})();
