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

  /* Chat portal: rotating capability line above the composer, surroundings fade while the
     cursor is in the box, Enter sends / Shift+Enter adds a newline. */
  function initChat() {
    var chat = document.querySelector("[data-chat]");
    if (!chat) return;

    var composer = chat.querySelector("[data-chat-composer]");
    var input = chat.querySelector("[data-chat-input]");
    var form = chat.querySelector("[data-chat-form]");

    /* Enter sends, Shift+Enter makes a new line (a plain form POST still works without JS). */
    if (input && form) {
      input.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.isComposing) return;
        event.preventDefault();
        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
    }

    /* Focus mode: the cursor inside the composer fades the surroundings; blur or Escape
       brings them back. */
    function focusOn() {
      document.body.classList.add("is-chat-focus");
    }
    function focusOff() {
      document.body.classList.remove("is-chat-focus");
    }
    if (composer) {
      composer.addEventListener("focusin", focusOn);
      composer.addEventListener("focusout", function (event) {
        if (composer.contains(event.relatedTarget)) return;
        focusOff();
      });
      document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        focusOff();
        if (input) input.blur();
      });
      /* Chrome scrolls the textarea to the caret when the page itself scrolls, which cuts off the
         first line (the placeholder was clipped). Keep the writing area at the top. */
      if (input) {
        input.addEventListener("focus", function () {
          requestAnimationFrame(function () {
            input.scrollTop = 0;
          });
        });
      }
    }

    /* The rotating capability line: ~2.5 s, pauses as soon as the member types, and stays
       static under prefers-reduced-motion. */
    var cap = chat.querySelector("[data-chat-cap]");
    var sentences = cap ? Array.prototype.slice.call(cap.querySelectorAll("[data-chat-sentence]")) : [];
    if (sentences.length > 1 && !prefReducedMotion()) {
      var index = 0;
      var timer = null;
      var paused = false;
      var show = function (next) {
        sentences[index].classList.remove("is-active");
        index = ((next % sentences.length) + sentences.length) % sentences.length;
        sentences[index].classList.add("is-active");
      };
      var start = function () {
        if (timer === null && !paused) {
          timer = window.setInterval(function () {
            show(index + 1);
          }, 2500);
        }
      };
      var stop = function () {
        if (timer !== null) {
          window.clearInterval(timer);
          timer = null;
        }
      };
      start();
      if (input) {
        input.addEventListener("input", function () {
          paused = true;
          stop();
        });
      }
      chat.addEventListener("focusin", stop);
      chat.addEventListener("focusout", function (event) {
        if (chat.contains(event.relatedTarget)) return;
        paused = false;
        start();
      });
    }
  }

  onReady(function () {
    initCtrlEnter();
    initConfirms();
    initToasts();
    initCopy();
    initHtmxErrors();
    initWizard();
    initChat();
  });
})();
