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
 *
 * Usabilidade: erros aparecem junto ao campo e o foco vai para o primeiro
 * campo inválido; resultados e cópias são anunciados a leitores de tela pela
 * região `#status`; o foco é levado às senhas geradas. As senhas podem ser
 * ocultadas (compartilhamento de tela) e limpas da tela; cada caractere é
 * colorido por tipo para facilitar a leitura. O tema escolhido vale apenas
 * para a visita atual, pois a página não grava nada no navegador.
 */
"use strict";

const API_URL = "/api/v1/passwords/generate";
const COPY_FEEDBACK_MS = 1500;

// Faixas apenas para rotular a estimativa; não representam garantia de segurança.
const ENTROPY_LEVELS = [
  {
    minBits: 100,
    key: "very-strong",
    label: "muito forte",
    tip: "Adequada inclusive para contas críticas, como e-mail principal e senhas mestras.",
  },
  {
    minBits: 80,
    key: "strong",
    label: "forte",
    tip: "Adequada para a maioria das contas.",
  },
  {
    minBits: 60,
    key: "fair",
    label: "razoável",
    tip: "Aceitável para contas de pouca importância. Para contas importantes, prefira 80 bits ou mais.",
  },
  {
    minBits: 0,
    key: "weak",
    label: "fraca",
    tip: "Aumente o comprimento ou inclua mais tipos de caracteres.",
  },
];

const THEMES = [
  { value: "auto", label: "Automático", description: "automático (segue o sistema)" },
  { value: "light", label: "Claro", description: "claro" },
  { value: "dark", label: "Escuro", description: "escuro" },
];

const CHARACTER_CLASSES = [
  { pattern: /[0-9]/, className: "char-number" },
  { pattern: /[A-Z]/, className: "char-upper" },
  { pattern: /[a-z]/, className: "char-lower" },
];

const elements = {
  form: document.getElementById("generator-form"),
  length: document.getElementById("length"),
  lengthRange: document.getElementById("length-range"),
  count: document.getElementById("count"),
  categories: document.querySelectorAll("input[type=checkbox][data-pool-size]"),
  excludeAmbiguous: document.getElementById("exclude-ambiguous"),
  presets: document.querySelectorAll(".preset"),
  strength: document.getElementById("strength"),
  entropyValue: document.getElementById("entropy-value"),
  entropyMeter: document.getElementById("entropy-meter"),
  entropyTip: document.getElementById("entropy-tip"),
  message: document.getElementById("form-message"),
  generateButton: document.getElementById("generate-button"),
  resetButton: document.getElementById("reset-button"),
  regenerateButton: document.getElementById("regenerate-button"),
  copyAllButton: document.getElementById("copy-all-button"),
  visibilityButton: document.getElementById("visibility-button"),
  clearButton: document.getElementById("clear-button"),
  themeButton: document.getElementById("theme-button"),
  themeLabel: document.getElementById("theme-label"),
  results: document.getElementById("results"),
  resultsTitle: document.getElementById("results-title"),
  resultsEmpty: document.getElementById("results-empty"),
  resultsFooter: document.getElementById("results-footer"),
  passwordList: document.getElementById("password-list"),
  status: document.getElementById("status"),
  lengthError: document.getElementById("length-error"),
  countError: document.getElementById("count-error"),
  categoriesError: document.getElementById("categories-error"),
};

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

// Só valida a cada alteração depois da primeira tentativa de envio, para não
// exibir erros enquanto a pessoa ainda está digitando pela primeira vez.
let validateWhileEditing = false;
let currentPasswords = [];
let isLoading = false;
let passwordsHidden = false;
let themeIndex = 0;

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

function entropyLevel(bits) {
  return ENTROPY_LEVELS.find((level) => bits >= level.minBits);
}

function updateEntropyIndicator() {
  const length = readInteger(elements.length);
  // Os tamanhos dos conjuntos (com e sem ambíguos) vêm do backend via data-*.
  const sizeKey = elements.excludeAmbiguous.checked ? "poolSizeUnambiguous" : "poolSize";
  const poolSize = selectedCategories().reduce(
    (total, checkbox) => total + Number(checkbox.dataset[sizeKey]),
    0,
  );

  if (!isWithinLimits(length, elements.length) || poolSize === 0) {
    elements.entropyValue.textContent = "—";
    elements.entropyMeter.value = 0;
    elements.entropyTip.textContent = "";
    elements.strength.dataset.level = "none";
    return;
  }

  // Arredonda para baixo: a estimativa nunca deve superestimar a força.
  const bits = Math.floor(estimateEntropyBits(length, poolSize));
  const level = entropyLevel(bits);
  elements.entropyValue.textContent = `≈ ${bits} bits (${level.label})`;
  elements.entropyMeter.value = Math.min(bits, Number(elements.entropyMeter.max));
  elements.entropyTip.textContent = level.tip;
  elements.strength.dataset.level = level.key;
}

function setFieldError(errorElement, input, text) {
  errorElement.textContent = text;
  errorElement.hidden = text === "";
  input?.setAttribute("aria-invalid", String(text !== ""));
}

/**
 * Valida o formulário, exibe os erros junto a cada campo e devolve os campos
 * inválidos na ordem da página (o primeiro recebe o foco).
 */
function validateForm() {
  const invalidFields = [];
  const lengthValid = isWithinLimits(readInteger(elements.length), elements.length);
  const countValid = isWithinLimits(readInteger(elements.count), elements.count);
  const hasCategory = selectedCategories().length > 0;

  const lengthText = lengthValid
    ? ""
    : `Informe um número inteiro entre ${elements.length.min} e ${elements.length.max}.`;
  const countText = countValid
    ? ""
    : `Informe um número inteiro entre ${elements.count.min} e ${elements.count.max}.`;
  const categoriesText = hasCategory ? "" : "Selecione pelo menos uma categoria de caracteres.";

  setFieldError(elements.lengthError, elements.length, lengthText);
  setFieldError(elements.countError, elements.count, countText);
  setFieldError(elements.categoriesError, null, categoriesText);

  if (!lengthValid) invalidFields.push(elements.length);
  if (!hasCategory) invalidFields.push(elements.categories[0]);
  if (!countValid) invalidFields.push(elements.count);
  return invalidFields;
}

function announce(text) {
  // Limpa antes de escrever para que mensagens repetidas sejam anunciadas.
  elements.status.textContent = "";
  window.setTimeout(() => {
    elements.status.textContent = text;
  }, 50);
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
  payload.exclude_ambiguous = elements.excludeAmbiguous.checked;
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

function showCopiedFeedback(button, originalText) {
  button.textContent = "Copiado!";
  button.classList.add("button--copied");
  setTimeout(() => {
    button.textContent = originalText;
    button.classList.remove("button--copied");
  }, COPY_FEEDBACK_MS);
}

function selectText(element) {
  const range = document.createRange();
  range.selectNodeContents(element);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

/**
 * Copia o texto para a área de transferência. Se a API não estiver disponível
 * (ex.: página fora de HTTPS/localhost), seleciona o texto para cópia manual.
 */
async function copyText(text, button, fallbackElement, successMessage) {
  const originalText = button.textContent;
  try {
    await navigator.clipboard.writeText(text);
    showCopiedFeedback(button, originalText);
    announce(successMessage);
  } catch {
    // A seleção manual precisa do texto real, então as senhas voltam a aparecer.
    setPasswordsHidden(false);
    selectText(fallbackElement);
    showMessage(
      "Não foi possível copiar automaticamente. O texto foi selecionado: pressione Ctrl+C (ou ⌘+C).",
    );
  }
}

function characterClass(character) {
  const match = CHARACTER_CLASSES.find(({ pattern }) => pattern.test(character));
  return match ? match.className : "char-symbol";
}

/** Monta a senha caractere a caractere (via textContent), colorida por tipo. */
function buildPasswordText(password) {
  const text = document.createElement("span");
  text.className = "password-text";
  for (const character of password) {
    const span = document.createElement("span");
    span.className = characterClass(character);
    span.textContent = character;
    text.append(span);
  }
  return text;
}

function buildPasswordMask(password) {
  const mask = document.createElement("span");
  mask.className = "password-mask";
  mask.textContent = "•".repeat(Math.min(password.length, 24));
  mask.setAttribute("aria-label", "Senha oculta");
  return mask;
}

function renderPasswords(passwords) {
  const items = passwords.map((password, index) => {
    const item = document.createElement("li");
    item.className = "password-item";

    const code = document.createElement("code");
    const text = buildPasswordText(password);
    code.append(text, buildPasswordMask(password));

    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button--small";
    button.textContent = "Copiar";
    button.setAttribute("aria-label", `Copiar senha ${index + 1}`);
    button.addEventListener("click", () =>
      copyText(password, button, text, `Senha ${index + 1} copiada.`),
    );

    item.append(code, button);
    return item;
  });

  currentPasswords = passwords;
  elements.passwordList.replaceChildren(...items);
  elements.copyAllButton.hidden = passwords.length < 2;
  setResultsVisible(true);
}

/** Alterna entre o estado vazio do cartão de resultados e a lista de senhas. */
function setResultsVisible(visible) {
  elements.resultsEmpty.hidden = visible;
  elements.resultsFooter.hidden = !visible;
  elements.visibilityButton.hidden = !visible;
}

function setPasswordsHidden(hidden) {
  passwordsHidden = hidden;
  elements.passwordList.classList.toggle("password-list--hidden", hidden);
  elements.visibilityButton.setAttribute("aria-pressed", String(hidden));
  elements.visibilityButton.textContent = hidden ? "Mostrar senhas" : "Ocultar senhas";
}

function togglePasswordsVisibility() {
  setPasswordsHidden(!passwordsHidden);
  announce(passwordsHidden ? "Senhas ocultadas." : "Senhas visíveis.");
}

function clearPasswords() {
  currentPasswords = [];
  elements.passwordList.replaceChildren();
  setResultsVisible(false);
  clearMessage();
  // O foco não pode ficar em um elemento que deixou de existir na tela.
  elements.generateButton.focus();
  announce("Senhas removidas da tela.");
}

function applyTheme(index) {
  themeIndex = index;
  const theme = THEMES[index];
  if (theme.value === "auto") {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = theme.value;
  }
  elements.themeLabel.textContent = theme.label;
  elements.themeButton.setAttribute(
    "aria-label",
    `Tema da página: ${theme.description}. Clique para alternar.`,
  );
}

function presetMatchesForm(preset) {
  const categories = preset.dataset.presetCategories.split(" ");
  return (
    elements.length.value === preset.dataset.presetLength &&
    Array.from(elements.categories).every(
      (checkbox) => checkbox.checked === categories.includes(checkbox.name),
    ) &&
    String(elements.excludeAmbiguous.checked) === preset.dataset.presetExcludeAmbiguous
  );
}

/** Destaca o perfil que corresponde exatamente às opções atuais (se houver). */
function updatePresetState() {
  elements.presets.forEach((preset) =>
    preset.setAttribute("aria-pressed", String(presetMatchesForm(preset))),
  );
}

function applyPreset(preset) {
  const categories = preset.dataset.presetCategories.split(" ");
  elements.length.value = preset.dataset.presetLength;
  elements.lengthRange.value = preset.dataset.presetLength;
  elements.categories.forEach((checkbox) => {
    checkbox.checked = categories.includes(checkbox.name);
  });
  elements.excludeAmbiguous.checked = preset.dataset.presetExcludeAmbiguous === "true";
  handleOptionsChange();
  const label = preset.querySelector(".preset__label").textContent;
  announce(`Perfil ${label} aplicado.`);
}

function revealResults() {
  elements.resultsTitle.focus({ preventScroll: true });
  elements.results.scrollIntoView({
    behavior: prefersReducedMotion.matches ? "auto" : "smooth",
    block: "start",
  });
}

function setLoading(loading) {
  // aria-disabled em vez de disabled: um botão desabilitado perde o foco do
  // teclado, que voltaria para o início da página.
  isLoading = loading;
  elements.generateButton.setAttribute("aria-disabled", String(loading));
  elements.regenerateButton.setAttribute("aria-disabled", String(loading));
  elements.results.setAttribute("aria-busy", String(loading));
  elements.generateButton.textContent = loading ? "Gerando…" : "Gerar senhas";
}

/**
 * Solicita senhas ao backend.
 *
 * @param {boolean} moveFocus Leva o foco às senhas geradas (falso ao regenerar,
 *   para o foco permanecer no botão que a pessoa acabou de usar).
 */
async function generatePasswords(moveFocus) {
  if (isLoading) {
    return;
  }
  clearMessage();
  validateWhileEditing = true;
  const invalidFields = validateForm();
  if (invalidFields.length > 0) {
    invalidFields[0].focus();
    announce("Corrija os campos indicados para gerar as senhas.");
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
    const total = body.passwords.length;
    announce(total === 1 ? "1 senha gerada." : `${total} senhas geradas.`);
    if (moveFocus) {
      revealResults();
    }
  } catch {
    showMessage("Falha de comunicação com o servidor. Verifique se a aplicação está em execução.");
  } finally {
    setLoading(false);
  }
}

function handleOptionsChange() {
  updateEntropyIndicator();
  updatePresetState();
  if (validateWhileEditing) {
    validateForm();
  }
}

function syncLengthInputs(source, target) {
  target.value = source.value;
  handleOptionsChange();
}

function resetOptions() {
  // form.reset() volta aos valores do HTML, que vêm das constantes do backend.
  elements.form.reset();
  validateWhileEditing = false;
  clearMessage();
  validateForm();
  updateEntropyIndicator();
  updatePresetState();
  announce("Opções restauradas para os valores padrão.");
}

elements.lengthRange.addEventListener("input", () =>
  syncLengthInputs(elements.lengthRange, elements.length),
);
elements.length.addEventListener("input", () =>
  syncLengthInputs(elements.length, elements.lengthRange),
);
elements.count.addEventListener("input", handleOptionsChange);
elements.categories.forEach((checkbox) =>
  checkbox.addEventListener("change", handleOptionsChange),
);
elements.excludeAmbiguous.addEventListener("change", handleOptionsChange);
elements.presets.forEach((preset) =>
  preset.addEventListener("click", () => applyPreset(preset)),
);
elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  generatePasswords(true);
});
elements.resetButton.addEventListener("click", resetOptions);
elements.regenerateButton.addEventListener("click", () => generatePasswords(false));
elements.copyAllButton.addEventListener("click", () =>
  copyText(
    currentPasswords.join("\n"),
    elements.copyAllButton,
    elements.passwordList,
    `${currentPasswords.length} senhas copiadas, uma por linha.`,
  ),
);
elements.visibilityButton.addEventListener("click", togglePasswordsVisibility);
elements.clearButton.addEventListener("click", clearPasswords);
elements.themeButton.addEventListener("click", () =>
  applyTheme((themeIndex + 1) % THEMES.length),
);

updateEntropyIndicator();
updatePresetState();
