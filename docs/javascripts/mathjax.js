window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  svg: {
    fontCache: "global"
  }
};

// Material 的 navigation.instant 不会重新执行页面脚本，切换页面后要手动重排公式
document$.subscribe(() => {
  if (!window.MathJax || !window.MathJax.startup) {
    return;
  }
  MathJax.startup.promise = MathJax.startup.promise
    .then(() => MathJax.typesetClear())
    .then(() => MathJax.typesetPromise())
    .catch((err) => console.error("MathJax typeset failed:", err));
});
