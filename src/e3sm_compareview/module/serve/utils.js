(() => {
  const isQuickCompareTauri = !!window.__TAURI__;

  function getGroupFileName(groupName) {
    const state = trame.state.state;
    const nameTokens = [groupName];

    state.available_animation_tracks.forEach((name) => {
      nameTokens.push(name);
      const nDigit = Math.floor(Math.log10(state[name].length) + 1);
      const idx = state[`${name}_idx`];
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

  window.trame = window.trame || {};
  window.trame.utils = window.trame.utils || {};
  window.trame.utils.quickcompare = {
    async captureGroup(groupName) {
      await captureTarget(findGroupToCapture(groupName), getGroupFileName(groupName));
    },
  };
})();
