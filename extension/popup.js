// Popup — récupère le payload depuis Imatra local et l'envoie au content script.

const IMATRA_API = "http://localhost:8001";

const $ref = document.getElementById("ref");
const $btn = document.getElementById("fill");
const $status = document.getElementById("status");

// Restaurer la dernière référence saisie
chrome.storage.local.get(["last_ref"], (data) => {
  if (data.last_ref) $ref.value = data.last_ref;
});

function setStatus(message, type) {
  $status.textContent = message;
  $status.className = "status " + (type || "");
}

$btn.addEventListener("click", async () => {
  const ref = ($ref.value || "").trim();
  if (!ref) {
    setStatus("Saisissez une référence de dossier.", "err");
    return;
  }
  chrome.storage.local.set({ last_ref: ref });
  $btn.disabled = true;
  setStatus("Récupération du dossier…");

  try {
    const r = await fetch(`${IMATRA_API}/dossiers/siv-payload?ref=${encodeURIComponent(ref)}`);
    if (!r.ok) {
      const msg = r.status === 404 ? "Dossier introuvable." : `Erreur ${r.status}`;
      setStatus(msg, "err");
      $btn.disabled = false;
      return;
    }
    const payload = await r.json();

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      setStatus("Aucun onglet actif.", "err");
      $btn.disabled = false;
      return;
    }

    const response = await chrome.tabs.sendMessage(tab.id, {
      action: "fill_siv_form",
      payload,
    });

    if (response && response.ok) {
      setStatus(`✅ ${response.filled} champ(s) pré-rempli(s).`, "ok");
    } else {
      setStatus(response?.error || "Aucun champ détecté sur cette page.", "err");
    }
  } catch (e) {
    setStatus(`Erreur : ${e.message}`, "err");
  } finally {
    $btn.disabled = false;
  }
});
