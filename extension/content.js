// Content script — pré-remplit les champs du portail SIV/ANTS.
//
// La structure HTML exacte du portail SIV n'est pas publique et change
// régulièrement. Cette table de correspondance est à calibrer en inspectant
// le DOM réel via les DevTools sur une session ouverte.
//
// Le mapping fonctionne par sélecteurs CSS multiples (les premiers trouvés
// gagnent). Ajoutez des sélecteurs sans crainte : les inconnus sont ignorés.

const FIELD_MAP = {
  // Véhicule
  immatriculation: [
    'input[name*="immatriculation" i]',
    'input[id*="immatriculation" i]',
    'input[name*="plaque" i]',
  ],
  vin: [
    'input[name*="vin" i]',
    'input[id*="vin" i]',
    'input[name*="numero_serie" i]',
  ],
  marque: ['input[name*="marque" i]', 'input[id*="marque" i]'],
  modele: ['input[name*="modele" i]', 'input[id*="modele" i]'],
  date_premiere_immat: [
    'input[name*="date_premiere" i]',
    'input[name*="premiere_immat" i]',
  ],

  // Titulaire (acheteur)
  titulaire_nom: ['input[name*="nom" i]:not([name*="prenom" i])'],
  titulaire_prenom: ['input[name*="prenom" i]'],
  titulaire_date_naissance: ['input[name*="naissance" i]'],
  titulaire_email: ['input[type="email"]', 'input[name*="email" i]'],
  titulaire_telephone: ['input[type="tel"]', 'input[name*="telephone" i]'],
  titulaire_adresse: ['input[name*="adresse" i]', 'textarea[name*="adresse" i]'],
  titulaire_code_postal: ['input[name*="code_postal" i]', 'input[name*="cp" i]'],
  titulaire_ville: ['input[name*="ville" i]'],
};

function setNativeValue(el, value) {
  // Compatible React/Vue/Angular — déclenche un vrai input event
  const proto = Object.getPrototypeOf(el);
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  if (setter) {
    setter.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillField(value, selectors) {
  if (value === null || value === undefined || value === "") return false;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && !el.disabled && !el.readOnly) {
      setNativeValue(el, String(value));
      return true;
    }
  }
  return false;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action !== "fill_siv_form") return;
  const payload = msg.payload || {};
  let filled = 0;
  for (const [key, selectors] of Object.entries(FIELD_MAP)) {
    if (fillField(payload[key], selectors)) filled++;
  }
  sendResponse({ ok: true, filled });
  return true;
});
