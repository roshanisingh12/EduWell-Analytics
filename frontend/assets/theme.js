// Applies the saved colour theme before first paint to avoid a light/dark flash.
(function () {
  try {
    var saved = localStorage.getItem('eduwell-theme');
    if (saved === 'light' || saved === 'dark') document.documentElement.setAttribute('data-theme', saved);
  } catch (e) { /* storage unavailable: follow the system theme */ }
})();
