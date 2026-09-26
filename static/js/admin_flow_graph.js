/* Read-only projection of the editor definition; never persists layout or content. */
(() => {
  const CARD_WIDTH = 260;
  const COLUMN_GAP = 96;
  const PADDING = 36;
  const actionNames = {
    confirm_category: "Crear categoría y registrar",
    reject_category: "Rechazar categoría",
    cancel_pending_operation: "Cancelar operación",
    request_category_change: "Pedir otra categoría",
    confirm_compensation: "Confirmar compensación",
    reject_compensation: "Rechazar compensación",
    confirm_limit_year: "Confirmar año",
    confirm_limit_category: "Confirmar categoría del límite",
    reject_limit: "Cancelar límite",
  };
  const make = (tag, className, text) => {
    const item = document.createElement(tag);
    item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  };
  const svgElement = (tag, attributes) => {
    const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value));
    return item;
  };
  const optionsOf = (node) => node.type === "reply_button" ? node.options || []
    : node.type === "list" ? (node.sections || []).flatMap((section) => section.options || []) : [];

  class LukaFlowGraph {
    constructor(root, onSelect) {
      this.root = root;
      this.onSelect = onSelect;
      this.scale = 1;
      this.initialized = false;
      this.frame = make("div", "flow-map-frame");
      this.stage = make("div", "flow-map-stage");
      this.frame.append(this.stage);
      root.append(this.frame);
      document.getElementById("flow-map-zoom-in").addEventListener("click", () => this.zoom(this.scale + .15));
      document.getElementById("flow-map-zoom-out").addEventListener("click", () => this.zoom(this.scale - .15));
      document.getElementById("flow-map-fit").addEventListener("click", () => this.fit());
    }

    zoom(value) {
      this.scale = Math.max(.2, Math.min(1.5, value));
      this.stage.style.transform = `scale(${this.scale})`;
      this.frame.style.width = `${this.width * this.scale}px`;
      this.frame.style.height = `${this.height * this.scale}px`;
      document.getElementById("flow-map-zoom").textContent = `${Math.round(this.scale * 100)}%`;
    }

    fit() {
      const availableHeight = parseFloat(getComputedStyle(this.root).maxHeight) - 16;
      this.zoom(Math.min(1, (this.root.clientWidth - 16) / this.width, availableHeight / this.height));
      this.root.scrollTo(0, 0);
    }

    update(definition) {
      this.stage.replaceChildren();
      this.stage.style.transform = "none";
      const nodes = definition.nodes || [];
      const byId = new Map();
      const duplicates = new Set();
      nodes.forEach((node, index) => {
        if (byId.has(node.id)) duplicates.add(node.id);
        else byId.set(node.id, index);
      });
      // Breadth-first levels keep branches aligned and terminate even for draft cycles.
      const levels = new Map();
      const start = byId.get(definition.start_node);
      const queue = start === undefined ? [] : [start];
      if (start !== undefined) levels.set(start, 0);
      for (let cursor = 0; cursor < queue.length; cursor += 1) {
        const index = queue[cursor];
        optionsOf(nodes[index]).forEach((option) => {
          const next = byId.get(option.next_node);
          if (!option.action && next !== undefined && !levels.has(next)) {
            levels.set(next, levels.get(index) + 1);
            queue.push(next);
          }
        });
      }
      const disconnectedLevel = Math.max(0, ...levels.values()) + 1;
      const cards = [];
      const edges = [];
      const messages = [];
      let missing = 0;
      nodes.forEach((node, index) => {
        const card = make("button", "flow-map-card flow-map-message");
        card.type = "button";
        card.dataset.nodeIndex = index;
        card.setAttribute("aria-label", `Editar mensaje ${node.id || index + 1}`);
        card.addEventListener("click", () => this.onSelect(index));
        const badges = make("span", "flow-map-badges");
        badges.append(make("span", "", { text: "Texto", reply_button: "Botones", list: "Lista" }[node.type] || node.type));
        if (index === start) badges.append(make("span", "flow-map-start", "Inicio"));
        if (node.type === "text") badges.append(make("span", "", "Fin"));
        if (!levels.has(index) || duplicates.has(node.id)) {
          card.classList.add("flow-map-warning");
          badges.append(make("span", "", duplicates.has(node.id) ? "ID repetido" : "Sin conexión desde el inicio"));
        }
        card.append(badges, make("strong", "flow-map-title", node.id || "Mensaje sin ID"));
        if (node.header) card.append(make("span", "flow-map-header", node.header));
        const body = make("span", "flow-map-body", node.body || "Mensaje sin contenido");
        body.title = node.body || "";
        card.append(body);
        if (node.footer) card.append(make("span", "flow-map-footer", node.footer));
        if (node.type === "list") card.append(make("span", "flow-map-list-button", node.button || "Ver opciones"));
        const ports = [];
        const appendOptions = (options) => options.forEach((option) => {
          const port = make("span", "flow-map-option", option.title || "Opción sin texto");
          port.append(make("span", "flow-map-port", "→"));
          port.title = option.action ? `Acción: ${option.action}` : `Siguiente mensaje: ${option.next_node || "sin destino"}`;
          card.append(port);
          ports.push({ port, option });
        });
        if (node.type === "list") {
          (node.sections || []).forEach((section) => {
            if (section.title) card.append(make("span", "flow-map-section-label", section.title));
            appendOptions(section.options || []);
          });
        } else appendOptions(optionsOf(node));
        const model = { card, index, level: levels.get(index) ?? disconnectedLevel, ports };
        messages.push(model);
        cards.push(model);
      });

      messages.forEach((source) => source.ports.forEach(({ port, option }) => {
        let target;
        if (option.action || !byId.has(option.next_node)) {
          const isAction = Boolean(option.action);
          const card = make("div", `flow-map-card ${isAction ? "flow-map-action" : "flow-map-warning"}`);
          card.append(
            make("span", "flow-map-badges", isAction ? "Acción · fin del recorrido" : "Destino faltante"),
            make("strong", "flow-map-title", isAction ? actionNames[option.action] || option.action.replaceAll("_", " ") : option.next_node || "Elegí un destino"),
          );
          if (isAction) card.append(make("code", "flow-map-action-key", option.action));
          else missing += 1;
          target = { card, level: source.level + 1 };
          cards.push(target);
        } else target = messages[byId.get(option.next_node)];
        edges.push({ source, target, port, action: Boolean(option.action) });
      }));

      const svg = svgElement("svg", { class: "flow-map-edges", "aria-hidden": "true" });
      const defs = svgElement("defs", {});
      ["message", "action", "warning"].forEach((kind) => {
        const marker = svgElement("marker", { id: `flow-arrow-${kind}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" });
        marker.append(svgElement("path", { d: "M 0 0 L 10 5 L 0 10 z", class: `flow-arrow-${kind}` }));
        defs.append(marker);
      });
      svg.append(defs);
      this.stage.append(svg);
      const columns = new Map();
      cards.forEach((card) => {
        card.x = PADDING + card.level * (CARD_WIDTH + COLUMN_GAP);
        card.y = columns.get(card.level) || PADDING;
        card.card.style.left = `${card.x}px`;
        card.card.style.top = `${card.y}px`;
        this.stage.append(card.card);
        card.height = card.card.offsetHeight;
        columns.set(card.level, card.y + card.height + 36);
      });
      const bottom = Math.max(PADDING, ...columns.values());
      let returnLanes = 0;
      edges.forEach(({ source, target, port, action }) => {
        const x1 = source.x + CARD_WIDTH;
        const y1 = source.y + port.offsetTop + port.offsetHeight / 2;
        const x2 = target.x;
        const y2 = target.y + Math.min(60, target.height / 2);
        let d;
        if (target.level > source.level) {
          const bend = Math.min(COLUMN_GAP / 2, (x2 - x1) / 2);
          d = `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2 - 4} ${y2}`;
        } else {
          const lane = bottom + (++returnLanes * 22);
          d = `M ${x1} ${y1} H ${x1 + 28} V ${lane} H ${x2 - 24} V ${y2} H ${x2 - 4}`;
        }
        const kind = target.card.classList.contains("flow-map-warning") ? "warning" : action ? "action" : "message";
        svg.append(svgElement("path", { d, class: `flow-map-edge flow-map-edge-${kind}`, "marker-end": `url(#flow-arrow-${kind})` }));
      });
      this.width = Math.max(400, ...cards.map((card) => card.x + CARD_WIDTH + PADDING));
      this.height = bottom + returnLanes * 22 + PADDING;
      this.stage.style.width = `${this.width}px`;
      this.stage.style.height = `${this.height}px`;
      svg.setAttribute("width", this.width);
      svg.setAttribute("height", this.height);
      const unreachable = nodes.length - levels.size;
      document.getElementById("flow-map-summary").textContent = [
        `${nodes.length} mensajes`, `${edges.length} conexiones`,
        start === undefined ? "Falta el mensaje inicial" : "",
        unreachable ? `${unreachable} sin conexión desde el inicio` : "",
        missing ? `${missing} destinos faltantes` : "",
        duplicates.size ? "Hay identificadores repetidos" : "",
      ].filter(Boolean).join(" · ");
      if (!this.initialized) {
        this.fit();
        this.initialized = true;
      } else this.zoom(this.scale);
    }
  }
  window.LukaFlowGraph = LukaFlowGraph;
})();
