// Loads the kit's JSX (which uses ES imports for editor clarity) into one Babel-compiled
// scope. Component and screen names are globally unique, so imports are simply stripped.
(async function () {
  const FILES = [
    "../../components/core/Icon.jsx",
    "../../components/core/Button.jsx",
    "../../components/core/IconButton.jsx",
    "../../components/core/Card.jsx",
    "../../components/core/Badge.jsx",
    "../../components/forms/Input.jsx",
    "../../components/forms/Textarea.jsx",
    "../../components/forms/Select.jsx",
    "../../components/forms/Checkbox.jsx",
    "../../components/forms/Switch.jsx",
    "../../components/forms/Field.jsx",
    "../../components/data/StatusPill.jsx",
    "../../components/data/AmountCell.jsx",
    "../../components/data/DataTable.jsx",
    "../../components/data/DigestValue.jsx",
    "../../components/data/KeyValueList.jsx",
    "../../components/feedback/Banner.jsx",
    "../../components/feedback/Dialog.jsx",
    "../../components/feedback/ProgressBar.jsx",
    "../../components/feedback/EmptyState.jsx",
    "../../components/navigation/CompanySwitcher.jsx",
    "../../components/navigation/SidebarNav.jsx",
    "../../components/navigation/PageHeader.jsx",
    "../../components/navigation/Tabs.jsx",
    "./AppShell.jsx",
    "./SignIn.jsx",
    "./OverviewScreen.jsx",
    "./JournalsScreen.jsx",
    "./InquiryScreen.jsx",
    "./CloseScreen.jsx",
    "./ReportsScreen.jsx",
    "./MigrationScreen.jsx",
    "./App.jsx",
  ];
  const sources = await Promise.all(FILES.map((f) => fetch(f).then((r) => r.text())));
  // Each file gets its own scope (module-private consts collide otherwise); named exports
  // are published on window so later files can reference them.
  const code = sources
    .map((src) => {
      const names = [...src.matchAll(/export\s+function\s+(\w+)/g)].map((m) => m[1]);
      const body = src.replace(/^\s*import[^\n]*;\s*$/gm, "").replace(/^export\s+function/gm, "function");
      return "(function(){\n" + body + "\n" + names.map((n) => "window." + n + " = " + n + ";").join("\n") + "\n})();";
    })
    .join("\n");
  const compiled = Babel.transform(code, { presets: [["react", { runtime: "classic" }]] }).code;
  new Function("React", "ReactDOM", compiled)(window.React, window.ReactDOM);
  ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(window.__CTecApp));
})();
