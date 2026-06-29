(() => {
  const isQuickCompareTauri = !!window.__TAURI__;

  function fileLabel(entry) {
    return entry.label || entry.path.split("/").pop();
  }

  function getGroupFileName(groupName) {
    const nameTokens = [groupName];

    trame.state.state.available_animation_tracks.forEach((name) => {
      nameTokens.push(name);
      const nDigit = Math.floor(Math.log10(trame.state.state[name].length) + 1);
      const idx = trame.state.state[`${name}_idx`];
      nameTokens.push(String(idx).padStart(nDigit, "0"));
    });

    return `${nameTokens.join("-")}.png`;
  }

  function findGroupToCapture(groupName) {
    return document.querySelector(`[data-variable-group="${groupName}"]`);
  }

  function downloadURL(dataURL, fileName) {
    const link = document.createElement("a");
    link.href = dataURL;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function tauriSave(description, dataURL, fileName) {
    const base64 = dataURL.split(",")[1];
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    window.trame.trigger("tauri_save", [description, fileName, bytes.buffer]);
  }

  async function captureTarget(target, fileName) {
    if (!target) {
      return;
    }

    const canvas = await html2canvas(target);
    const dataURL = canvas.toDataURL("image/png");

    if (isQuickCompareTauri) {
      tauriSave("Save screenshot", dataURL, fileName);
      return;
    }

    downloadURL(dataURL, fileName);
  }


  function setSimulationLabel(path, label) {
    trame.state.set(
      "simulation_configs",
      trame.state.state.simulation_configs.map((sim) =>
        sim.path === path ? { ...sim, label } : sim,
      ),
    );
  }

  function setSimulationInclude(path, include) {
    trame.state.set(
      "simulation_configs",
      trame.state.state.simulation_configs.map((sim) =>
        sim.path === path ? { ...sim, include: !!include } : sim,
      ),
    );
  }

  function loadedSimulationsText(simulationConfigs, controlPath) {
    if (!simulationConfigs?.length) {
      return "Loaded simulations:\nnone";
    }

    const lines = simulationConfigs.map((sim) => {
      const suffix = sim.path === controlPath ? " (ctrl)" : "";
      return `${fileLabel(sim)}${suffix}`;
    });

    return `Loaded simulations:\n${lines.join("\n")}`;
  }

  window.trame = window.trame || {};
  window.trame.utils = window.trame.utils || {};
  const quickcompare = window.trame.utils.quickcompare || {};

  Object.assign(quickcompare, {
    captureGroup(groupName) {
      return captureTarget(findGroupToCapture(groupName), getGroupFileName(groupName));
    },
    setSimulationLabel,
    setSimulationInclude,
    loadedSimulationsText,
  });
  window.trame.utils.quickcompare = quickcompare;
})();
