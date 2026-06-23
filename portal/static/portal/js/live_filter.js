function initLiveFilter(inputId, itemSelector, containerSelector) {
  var input = document.getElementById(inputId);
  if (!input) return;
  var container = containerSelector ? document.querySelector(containerSelector) : document;
  if (!container) return;

  function apply() {
    var query = input.value.trim().toLowerCase();
    var items = container.querySelectorAll(itemSelector);
    items.forEach(function (item) {
      var haystack = (item.getAttribute('data-search') || item.textContent).toLowerCase();
      item.style.display = haystack.indexOf(query) === -1 ? 'none' : '';
    });
  }

  input.addEventListener('input', apply);
}
