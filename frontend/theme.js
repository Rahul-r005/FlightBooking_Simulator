(function () {
  const key = "skybook-theme";
  const saved = localStorage.getItem(key);
  const theme = saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
  document.documentElement.dataset.theme = theme;
})();
