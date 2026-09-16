(() => {
  const editor = document.getElementById("flow-editor");
  if (!editor) return;

  const contract = JSON.parse(document.getElementById("flow-contract-data").textContent);
  let flow = JSON.parse(document.getElementById("flow-record-data").textContent);
  const events = new Map(contract.events.map((event) => [event.event_key, event]));
  const nameInput = document.getElementById("flow-name");
  const slugInput = document.getElementById("flow-slug");
  const eventSelect = document.getElementById("flow-event");
  const eventHelp = document.getElementById("event-help");
  const startSelect = document.getElementById("flow-start-node");
  const nodesRoot = document.getElementById("flow-nodes");
  const notice = document.getElementById("flow-notice");
  const addNodeActions = document.getElementById("add-node-actions");

  const initialDefinition = flow?.draft?.definition || flow?.published?.definition || {
    start_node: "mensaje-inicial",
    nodes: [{ id: "mensaje-inicial", type: "text", body: "", terminal: true }],
  };
  let definition = structuredClone(initialDefinition);
  let slugTouched = Boolean(flow);

  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const field = (label, control, className = "") => {
    const wrapper = element("label", `flow-field ${className}`.trim());
    wrapper.append(element("span", "", label), control);
    return wrapper;
  };

  const input = (value, maxLength, onInput, placeholder = "") => {
    const control = document.createElement("input");
    control.value = value || "";
    control.maxLength = maxLength;
    control.placeholder = placeholder;
    control.addEventListener("input", () => onInput(control.value));
    return control;
  };

  const textarea = (value, maxLength, onInput) => {
    const control = document.createElement("textarea");
    control.value = value || "";
    control.maxLength = maxLength;
    control.addEventListener("input", () => onInput(control.value));
    return control;
  };

  const select = (items, value, onChange) => {
    const control = document.createElement("select");
    items.forEach(({ value: optionValue, label }) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = label;
      control.append(option);
    });
    control.value = value || items[0]?.value || "";
    control.addEventListener("change", () => onChange(control.value));
    return control;
  };

  const currentPolicy = () => events.get(eventSelect.value) || {
    variables: [], actions: [], terminal_only: false,
  };

  function showNotice(kind, message, errors = []) {
    notice.hidden = false;
    notice.className = `flow-alert flow-alert-${kind}`;
    notice.replaceChildren(element("strong", "", message));
    if (errors.length) {
      const list = element("ul", "flow-error-list");
      errors.forEach((error) => {
        list.append(element("li", "", `${error.path}: ${error.message}`));
      });
      notice.append(list);
    }
    notice.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function hideNotice() {
    notice.hidden = true;
    notice.replaceChildren();
  }

  function configureEventSelect() {
    contract.events.forEach((event) => {
      const option = document.createElement("option");
      option.value = event.event_key;
      option.textContent = event.event_key;
      eventSelect.append(option);
    });
    eventSelect.value = flow?.event_key || contract.events[0]?.event_key || "";
    eventSelect.addEventListener("change", () => {
      const policy = currentPolicy();
      if (policy.terminal_only) {
        definition = {
          start_node: "mensaje-inicial",
          nodes: [{ id: "mensaje-inicial", type: "text", body: "", terminal: true }],
        };
      }
      render();
    });
  }

  function updateEventHelp() {
    const policy = currentPolicy();
    const variables = policy.variables.length
      ? `Variables: ${policy.variables.map((value) => `{${value}}`).join(", ")}.`
      : "Este evento no expone variables.";
    eventHelp.textContent = policy.terminal_only
      ? `${variables} Respuesta terminal: no deja opciones pendientes.`
      : `${variables} Acciones disponibles: ${policy.actions.join(", ") || "ninguna"}.`;
    addNodeActions.querySelectorAll("[data-add-node]").forEach((button) => {
      button.disabled = policy.terminal_only && button.dataset.addNode !== "text";
    });
  }

  function nodeKindLabel(type) {
    return { text: "Texto", reply_button: "Botones", list: "Lista" }[type] || type;
  }

  function uniqueNodeId(type) {
    const prefix = type === "text" ? "mensaje" : type === "list" ? "lista" : "opciones";
    let counter = definition.nodes.length + 1;
    while (definition.nodes.some((node) => node.id === `${prefix}-${counter}`)) counter += 1;
    return `${prefix}-${counter}`;
  }

  function defaultOption(index = 1) {
    const actions = currentPolicy().actions;
    if (definition.nodes.length > 1) {
      return { id: `opcion-${index}`, title: `Opción ${index}`, next_node: definition.nodes[0].id };
    }
    if (actions.length) {
      return { id: `opcion-${index}`, title: `Opción ${index}`, action: actions[0] };
    }
    return { id: `opcion-${index}`, title: `Opción ${index}`, next_node: definition.nodes[0]?.id || "mensaje-inicial" };
  }

  function addNode(type) {
    if (currentPolicy().terminal_only && type !== "text") return;
    const id = uniqueNodeId(type);
    if (type === "text") {
      definition.nodes.push({ id, type, body: "", terminal: true });
    } else if (type === "reply_button") {
      definition.nodes.push({ id, type, body: "", terminal: false, options: [defaultOption()] });
    } else {
      definition.nodes.push({
        id, type, body: "", button: "Ver opciones", terminal: false,
        sections: [{ title: "Opciones", options: [defaultOption()] }],
      });
    }
    render();
  }

  function removeNode(index) {
    if (definition.nodes.length === 1) {
      showNotice("error", "El recorrido necesita al menos un mensaje.");
      return;
    }
    const removedId = definition.nodes[index].id;
    definition.nodes.splice(index, 1);
    if (definition.start_node === removedId) definition.start_node = definition.nodes[0].id;
    render();
  }

  function changeNodeId(node, nextId) {
    const previousId = node.id;
    node.id = nextId;
    if (definition.start_node === previousId) definition.start_node = nextId;
    definition.nodes.forEach((candidate) => {
      const options = candidate.type === "reply_button"
        ? candidate.options
        : candidate.type === "list"
          ? candidate.sections.flatMap((section) => section.options)
          : [];
      options.forEach((option) => {
        if (option.next_node === previousId) option.next_node = nextId;
      });
    });
    renderStartOptions();
  }

  function changeNodeType(index, type) {
    const old = definition.nodes[index];
    const base = { id: old.id, type, body: old.body || "" };
    if (type === "text") definition.nodes[index] = { ...base, terminal: true };
    if (type === "reply_button") definition.nodes[index] = { ...base, terminal: false, options: [defaultOption()] };
    if (type === "list") {
      definition.nodes[index] = {
        ...base, button: "Ver opciones", terminal: false,
        sections: [{ title: "Opciones", options: [defaultOption()] }],
      };
    }
    render();
  }

  function renderStartOptions() {
    startSelect.replaceChildren();
    definition.nodes.forEach((node) => {
      const option = document.createElement("option");
      option.value = node.id;
      option.textContent = node.id || "Sin identificador";
      startSelect.append(option);
    });
    startSelect.value = definition.start_node;
  }

  function renderVariables(container) {
    const variables = currentPolicy().variables;
    const help = element("div", "flow-variable-help");
    help.textContent = variables.length
      ? `Podés insertar: ${variables.map((value) => `{${value}}`).join(" · ")}`
      : "Este evento no ofrece variables dinámicas.";
    container.append(help);
  }

  function normalizeTarget(option, mode) {
    if (mode === "action") {
      delete option.next_node;
      option.action = currentPolicy().actions[0] || "";
    } else {
      delete option.action;
      option.next_node = definition.nodes[0]?.id || "";
    }
  }

  function renderOption(option, onRemove, allowDescription = false) {
    const wrapper = element("div", "flow-option");
    const grid = element("div", "flow-option-grid");
    grid.append(
      field("ID estable", input(option.id, 200, (value) => { option.id = value; })),
      field("Texto visible", input(option.title, allowDescription ? 24 : 20, (value) => { option.title = value; })),
    );

    const policy = currentPolicy();
    const targetModes = [{ value: "next", label: "Siguiente mensaje" }];
    if (policy.actions.length) targetModes.push({ value: "action", label: "Acción permitida" });
    const mode = option.action ? "action" : "next";
    const modeSelect = select(targetModes, mode, (value) => {
      normalizeTarget(option, value);
      render();
    });
    grid.append(field("Destino", modeSelect));

    const destination = option.action
      ? select(
          policy.actions.map((action) => ({ value: action, label: action })),
          option.action,
          (value) => { option.action = value; },
        )
      : select(
          definition.nodes.map((node) => ({ value: node.id, label: node.id || "Sin ID" })),
          option.next_node,
          (value) => { option.next_node = value; },
        );
    grid.append(field(option.action ? "Acción" : "Mensaje", destination));

    const remove = element("button", "flow-icon-button", "Eliminar");
    remove.type = "button";
    remove.addEventListener("click", onRemove);
    grid.append(remove);
    if (allowDescription) {
      grid.append(field("Descripción opcional", input(option.description || "", 72, (value) => {
        if (value) option.description = value;
        else delete option.description;
      }), "flow-field-wide"));
    }
    wrapper.append(grid);
    return wrapper;
  }

  function renderButtonOptions(node, container) {
    const options = element("div", "flow-options");
    const header = element("div", "flow-options-header");
    header.append(element("strong", "", `Botones (${node.options.length}/3)`));
    const add = element("button", "flow-button flow-button-secondary", "+ Botón");
    add.type = "button";
    add.disabled = node.options.length >= 3;
    add.addEventListener("click", () => {
      node.options.push(defaultOption(node.options.length + 1));
      render();
    });
    header.append(add);
    options.append(header);
    node.options.forEach((option, index) => {
      options.append(renderOption(option, () => {
        node.options.splice(index, 1);
        render();
      }));
    });
    container.append(options);
  }

  function renderListSections(node, container) {
    const options = element("div", "flow-options");
    const header = element("div", "flow-options-header");
    header.append(element("strong", "", `Secciones (${node.sections.length}/10)`));
    const addSection = element("button", "flow-button flow-button-secondary", "+ Sección");
    addSection.type = "button";
    addSection.disabled = node.sections.length >= 10;
    addSection.addEventListener("click", () => {
      node.sections.push({ title: `Sección ${node.sections.length + 1}`, options: [defaultOption()] });
      render();
    });
    header.append(addSection);
    options.append(header);

    node.sections.forEach((section, sectionIndex) => {
      const sectionRoot = element("div", "flow-section");
      const sectionHeader = element("div", "flow-section-header");
      sectionHeader.append(field("Título de sección", input(section.title || "", 24, (value) => {
        if (value) section.title = value;
        else delete section.title;
      })));
      const actions = element("div", "flow-section-actions");
      const addRow = element("button", "flow-button flow-button-secondary", "+ Fila");
      addRow.type = "button";
      const rowCount = node.sections.reduce((count, current) => count + current.options.length, 0);
      addRow.disabled = rowCount >= 10;
      addRow.addEventListener("click", () => {
        section.options.push(defaultOption(rowCount + 1));
        render();
      });
      const removeSection = element("button", "flow-icon-button", "Eliminar sección");
      removeSection.type = "button";
      removeSection.addEventListener("click", () => {
        node.sections.splice(sectionIndex, 1);
        render();
      });
      actions.append(addRow, removeSection);
      sectionHeader.append(actions);
      sectionRoot.append(sectionHeader);
      section.options.forEach((option, optionIndex) => {
        sectionRoot.append(renderOption(option, () => {
          section.options.splice(optionIndex, 1);
          render();
        }, true));
      });
      options.append(sectionRoot);
    });
    container.append(options);
  }

  function renderNode(node, index) {
    const root = element("article", "flow-node");
    const header = element("div", "flow-node-header");
    const title = element("div", "flow-node-title");
    title.append(
      element("span", "flow-node-kind", nodeKindLabel(node.type)),
      element("strong", "", node.id || "Mensaje sin ID"),
    );
    const remove = element("button", "flow-icon-button", "Eliminar mensaje");
    remove.type = "button";
    remove.addEventListener("click", () => removeNode(index));
    header.append(title, remove);

    const content = element("div", "flow-node-content");
    const allowedNodeTypes = currentPolicy().terminal_only ? ["text"] : contract.node_types;
    content.append(
      field("ID del mensaje", input(node.id, 100, (value) => changeNodeId(node, value))),
      field("Tipo", select(
        allowedNodeTypes.map((type) => ({ value: type, label: nodeKindLabel(type) })),
        node.type,
        (value) => changeNodeType(index, value),
      )),
      field("Contenido", textarea(node.body, node.type === "text" ? 4096 : 1024, (value) => { node.body = value; }), "flow-field-body"),
    );
    renderVariables(content);

    if (node.type !== "text") {
      content.append(
        field("Encabezado opcional", input(node.header || "", 60, (value) => {
          if (value) node.header = value;
          else delete node.header;
        })),
        field("Pie opcional", input(node.footer || "", 60, (value) => {
          if (value) node.footer = value;
          else delete node.footer;
        })),
      );
    }
    if (node.type === "reply_button") renderButtonOptions(node, content);
    if (node.type === "list") {
      content.append(field("Texto del botón", input(node.button, 20, (value) => { node.button = value; })));
      renderListSections(node, content);
    }
    root.append(header, content);
    return root;
  }

  function render() {
    updateEventHelp();
    renderStartOptions();
    nodesRoot.replaceChildren(...definition.nodes.map(renderNode));
  }

  function payload() {
    return {
      name: nameInput.value.trim(),
      definition: structuredClone(definition),
    };
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || "No se pudo completar la operación.");
      error.validationErrors = data.errors || [];
      throw error;
    }
    return data;
  }

  function setBusy(busy) {
    editor.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
  }

  async function validateFlow() {
    hideNotice();
    const result = await api("/admin/flujos/api/validar", {
      method: "POST",
      body: JSON.stringify({ event_key: eventSelect.value, definition }),
    });
    definition = result.definition;
    showNotice("success", "El recorrido es válido y compatible con WhatsApp.");
    return result;
  }

  async function saveFlow({ redirect = true } = {}) {
    await validateFlow();
    let saved;
    if (flow) {
      saved = await api(`/admin/flujos/api/${flow.id}/borrador`, {
        method: "PUT",
        body: JSON.stringify(payload()),
      });
    } else {
      saved = await api("/admin/flujos/api", {
        method: "POST",
        body: JSON.stringify({
          slug: slugInput.value.trim(),
          event_key: eventSelect.value,
          ...payload(),
        }),
      });
      flow = saved;
    }
    if (redirect) window.location.assign(`/admin/flujos/${saved.id}`);
    return saved;
  }

  async function run(action, successMessage) {
    setBusy(true);
    hideNotice();
    try {
      await action();
      if (successMessage) showNotice("success", successMessage);
    } catch (error) {
      showNotice("error", error.message, error.validationErrors || []);
    } finally {
      setBusy(false);
      render();
    }
  }

  nameInput.value = flow?.name || "";
  slugInput.value = flow?.slug || "";
  nameInput.addEventListener("input", () => {
    if (!slugTouched) {
      slugInput.value = nameInput.value.toLowerCase().normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
    }
  });
  slugInput.addEventListener("input", () => { slugTouched = true; });
  startSelect.addEventListener("change", () => { definition.start_node = startSelect.value; });
  addNodeActions.addEventListener("click", (event) => {
    const type = event.target.dataset.addNode;
    if (type) addNode(type);
  });
  editor.addEventListener("submit", (event) => {
    event.preventDefault();
    run(() => saveFlow(), null);
  });
  document.getElementById("validate-flow")?.addEventListener("click", () => run(validateFlow));
  document.getElementById("publish-flow")?.addEventListener("click", () => run(async () => {
    const saved = await saveFlow({ redirect: false });
    await api(`/admin/flujos/api/${saved.id}/publicar`, { method: "POST", body: "{}" });
    window.location.assign(`/admin/flujos/${saved.id}`);
  }));
  document.getElementById("discard-flow")?.addEventListener("click", () => {
    if (!window.confirm("¿Descartar el borrador actual? La versión publicada seguirá activa.")) return;
    run(async () => {
      await api(`/admin/flujos/api/${flow.id}/borrador`, { method: "DELETE" });
      window.location.reload();
    });
  });
  document.getElementById("archive-flow")?.addEventListener("click", () => {
    if (!window.confirm("¿Retirar este flujo? Dejará de usarse para conversaciones nuevas.")) return;
    run(async () => {
      await api(`/admin/flujos/api/${flow.id}/retirar`, { method: "POST", body: "{}" });
      window.location.assign("/admin/flujos");
    });
  });

  configureEventSelect();
  render();
})();
