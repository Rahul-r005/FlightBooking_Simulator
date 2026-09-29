(function () {
  const key = "skybook-theme";
  function applyTheme() {
    const saved = localStorage.getItem(key);
    const theme = saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
    document.documentElement.dataset.theme = theme;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = (theme === "dark" || (theme === "system" && media.matches)) ? "#0b1220" : "#3157d5";
  }
  applyTheme();
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  if (media.addEventListener) media.addEventListener("change", applyTheme);
  else if (media.addListener) media.addListener(applyTheme);
  window.addEventListener("storage", (event) => { if (event.key === key) applyTheme(); });
})();
