/**
 * SecurePass — comportamento da interface web.
 *
 * Este script NÃO gera senhas: toda geração ocorre no backend
 * (POST /api/v1/passwords/generate), que usa o módulo `secrets` do Python.
 * Aqui ficam apenas validação de formulário para feedback rápido, cálculo
 * do indicador de entropia e exibição/cópia dos resultados.
 *
 * Cuidados de segurança: senhas não são gravadas em localStorage, cookies ou
 * URL, e são inseridas no DOM somente via `textContent` (nunca `innerHTML`).
 */
"use strict";

const API_URL = "/api/v1/passwords/generate";
const COPY_FEEDBACK_MS = 1500;

// Faixas apenas para rotular a estimativa; não representam garantia de segurança.
const ENTROPY_LEVELS = [
  { minBits: 100, label: "muito forte" },
  { minBits: 80, label: "forte" },
  { minBits: 60, label: "razoável" },
  { minBits: 0, label: "fraca" },
];

const elements = {
  form: document.getElementById("generator-form"),
  length: document.getElementById("length"),
  lengthRange: document.getElementById("length-range"),
  count: document.getElementById("count"),
  categories: document.querySelectorAll("input[type=checkbox][data-pool-size]"),
  entropyValue: document.getElementById("entropy-value"),
  entropyMeter: document.getElementById("entropy-meter"),
  message: document.getElementById("form-message"),
  generateButton: document.getElementById("generate-button"),
  regenerateButton: document.getElementById("regenerate-button"),
  results: document.getElementById("results"),
  passwordList: document.getElementById("password-list"),
};

function readInteger(input) {
  const value = input.value.trim();
  return /^\d+$/.test(value) ? Number(value) : NaN;
}

function isWithinLimits(value, input) {
  return Number.isInteger(value) && value >= Number(input.min) && value <= Number(input.max);
}

function selectedCategories() {
  return Array.from(elements.categories).filter((checkbox) => checkbox.checked);
}

/** Entropia estimada = comprimento × log2(tamanho do conjunto combinado). */
function estimateEntropyBits(length, poolSize) {
  return poolSize > 0 ? length * Math.log2(poolSize) : 0;
}

function entropyLabel(bits) {
  return ENTROPY_LEVELS.find((level) => bits >= level.minBits).label;
}

function updateEntropyIndicator() {
  const length = readInteger(elements.length);
  const poolSize = selectedCategories().reduce(
    (total, checkbox) => total + Number(checkbox.dataset.poolSize),
    0,
  );

  if (!isWithinLimits(length, elements.length) || poolSize === 0) {
    elements.entropyValue.textContent = "—";
    elements.entropyMeter.value = 0;
    return;
  }

  // Arredonda para baixo: a estimativa nunca deve superestimar a força.
  const bits = Math.floor(estimateEntropyBits(length, poolSize));
  elements.entropyValue.textContent = `≈ ${bits} bits (${entropyLabel(bits)})`;
  elements.entropyMeter.value = Math.min(bits, Number(elements.entropyMeter.max));
}

function validateForm() {
  const errors = [];
  const length = readInteger(elements.length);
  const count = readInteger(elements.count);
  const lengthValid = isWithinLimits(length, elements.length);
  const countValid = isWithinLimits(count, elements.count);

  elements.length.setAttribute("aria-invalid", String(!lengthValid));
  elements.count.setAttribute("aria-invalid", String(!countValid));

  if (!lengthValid) {
    errors.push(
      `O comprimento deve ser um número inteiro entre ${elements.length.min} e ${elements.length.max}.`,
    );
  }
  if (!countValid) {
    errors.push(
      `A quantidade deve ser um número inteiro entre ${elements.count.min} e ${elements.count.max}.`,
    );
  }
  if (selectedCategories().length === 0) {
    errors.push("Selecione pelo menos uma categoria de caracteres.");
  }
  return errors;
}

function showMessage(text) {
  elements.message.textContent = text;
  elements.message.classList.add("message--error");
  elements.message.hidden = false;
}

function clearMessage() {
  elements.message.textContent = "";
  elements.message.hidden = true;
}

function buildPayload() {
  const payload = {
    length: readInteger(elements.length),
    count: readInteger(elements.count),
  };
  elements.categories.forEach((checkbox) => {
    payload[checkbox.name] = checkbox.checked;
  });
  return payload;
}

/** Converte o corpo de erro do FastAPI (string ou lista do Pydantic) em texto. */
function describeApiError(body) {
  if (typeof body?.detail === "string") {
    return body.detail;
  }
  if (Array.isArray(body?.detail)) {
    return body.detail.map((issue) => issue.msg).join(" ");
  }
  return "Não foi possível gerar as senhas. Tente novamente.";
}

async function copyPassword(password, button) {
  try {
    await navigator.clipboard.writeText(password);
    button.textContent = "Copiada!";
    button.classList.add("button--copied");
    setTimeout(() => {
      button.textContent = "Copiar";
      button.classList.remove("button--copied");
    }, COPY_FEEDBACK_MS);
  } catch {
    showMessage("Não foi possível copiar automaticamente. Selecione a senha e copie manualmente.");
  }
}

function renderPasswords(passwords) {
  const items = passwords.map((password, index) => {
    const item = document.createElement("li");
    item.className = "password-item";

    const code = document.createElement("code");
    code.textContent = password;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button--small";
    button.textContent = "Copiar";
    button.setAttribute("aria-label", `Copiar senha ${index + 1}`);
    button.addEventListener("click", () => copyPassword(password, button));

    item.append(code, button);
    return item;
  });

  elements.passwordList.replaceChildren(...items);
  elements.results.hidden = false;
}

function setLoading(isLoading) {
  elements.generateButton.disabled = isLoading;
  elements.regenerateButton.disabled = isLoading;
  elements.generateButton.textContent = isLoading ? "Gerando…" : "Gerar senhas";
}

async function generatePasswords() {
  clearMessage();
  const errors = validateForm();
  if (errors.length > 0) {
    showMessage(errors.join(" "));
    return;
  }

  setLoading(true);
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
      cache: "no-store",
      credentials: "same-origin",
    });
    const body = await response.json().catch(() => null);

    if (!response.ok) {
      showMessage(describeApiError(body));
      return;
    }
    renderPasswords(body.passwords);
  } catch {
    showMessage("Falha de comunicação com o servidor. Verifique se a aplicação está em execução.");
  } finally {
    setLoading(false);
  }
}

function syncLengthInputs(source, target) {
  target.value = source.value;
  updateEntropyIndicator();
}

elements.lengthRange.addEventListener("input", () =>
  syncLengthInputs(elements.lengthRange, elements.length),
);
elements.length.addEventListener("input", () =>
  syncLengthInputs(elements.length, elements.lengthRange),
);
elements.categories.forEach((checkbox) =>
  checkbox.addEventListener("change", updateEntropyIndicator),
);
elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  generatePasswords();
});
elements.regenerateButton.addEventListener("click", generatePasswords);

updateEntropyIndicator();
