// Card helper: resolves the compiled design-system namespace without hard-coding its name.
window.dsResolve = function (names) {
  for (const k of Object.keys(window)) {
    const v = window[k];
    if (v && typeof v === "object" && !Array.isArray(v) && names.every((n) => typeof v[n] === "function")) return v;
  }
  const missing = names.filter((n) => typeof (window[n]) !== "function");
  if (missing.length === 0) return names.reduce((o, n) => ((o[n] = window[n]), o), {});
  return null;
};
