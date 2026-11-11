// Moves keyboard focus to a form's error summary when a page is rendered with
// one. A live region that was already in the document at load time is not
// reliably announced by screen readers, and the first thing someone needs
// after a rejected submission is the list of what was rejected.
//
// Progressive enhancement, not a dependency: with this file blocked or failing
// to load, the summary is still rendered, still role="alert", and still links
// to each field. Nothing here is required for the page to work.
(function () {
  "use strict";

  var summary = document.querySelector("[data-error-summary]");
  if (!summary) {
    return;
  }

  // Do not steal focus from a fragment the user explicitly navigated to.
  if (window.location.hash) {
    return;
  }

  summary.focus();
})();
