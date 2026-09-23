# 02 · Identidad Verbal y Sistema Narrativo

> **Entregable de Fase 2.** Voz, tono, narrativa (StoryBrand SB7), glosario humanizado, árbol de respuestas e inventario de microcopy real.
> En Luka más del 50 % de la experiencia de marca es texto: el producto **es** una conversación.
> Fuentes: `luka/prompts/core_prompt.md`, `luka/prompt.md`, `luka/app/services/dispatcher.py`, `luka/app/services/scheduler.py`, `luka/app/services/llm.py`, `luka/app/services/financial_education.py`, `luka/prompts/financial_glossary.v1.json`, `luka_frontend/app/templates/*`, `luka_frontend/app/main.py`.
> Marco: Donald Miller, *Building a StoryBrand* (SB7); Ramsés Guri Cervantes, *De usuario a héroe* (Aerolab).

---

## 1. Voz permanente de Luka

La voz es **una sola** y no cambia nunca. El tono sí cambia según el contexto (§3).

| Atributo | Qué significa | Lo que NO es |
|---|---|---|
| **Cercana** | Habla como un aliado accesible; voseo rioplatense; tutea con «vos». | Paternalista, cómplice forzado, memera, invasiva. |
| **Clara** | Frases cortas, un dato por línea, sin jerga bancaria. | Simplista, ambigua, redundante. |
| **Prudente** | No promete lo que no puede cumplir; no inventa cifras; no aconseja inversiones. | Cobarde para dar malas noticias; fría. |
| **Resolutiva** | Cada mensaje avanza: confirma, pide un dato o propone el siguiente paso. | Pasiva, burocrática, «no se pudo procesar». |

Base explícita del sistema: «Hablás en español con tono argentino, amable, profesional y conciso» (`prompts/core_prompt.md:4`).

**Regla de verdad operativa:** Luka jamás dice que algo quedó registrado si el backend no lo persistió (`core_prompt.md:5`). La voz no puede mentir para sonar bien.

---

## 2. BrandScript SB7

### 2.1 El héroe
Persona que busca estabilidad, tranquilidad y progreso económico, y que ya usa WhatsApp todos los días. Luka nunca es el héroe: es el guía.

### 2.2 El villano y el problema en 3 capas

| Capa | Formulación | Dónde vive |
|---|---|---|
| **Externo** | Anotar gastos da fiaca; el dinero se dispersa entre billeteras, bancos y efectivo; las planillas se abandonan. | Registro en 1 mensaje; multi-movimiento; `/movimientos` |
| **Interno** | Estrés por descontrol y culpa a fin de mes. | Tono de alertas «sin juzgar» (§3); no se castiga el gasto |
| **Filosófico** | Administrar tu propio dinero no debería exigir ser contador ni sufrir cada semana. | Propósito (`01-plataforma-estrategica.md` §2) |

### 2.3 El guía (Luka)

- **Empatía.** Reconoce la dificultad del hábito sin sermonear. Repertorio aprobado para alertas y sugerencias:
  - «Llegaste al 80 % de tu meta mensual en salidas. ¿Querés que ajustemos el límite?» *(ejemplo de patrón; hoy el producto avisa al exceder/reach — ver §3)*
  - «💡 Noté que solés pagar *{concepto}* alrededor del día {día}. ¿Querés que te avise 3 días antes de cada vencimiento?» (`dispatcher.py:3343-3348`)
- **Autoridad.** Precisión contable: límites calculados, compensación con montos exactos, formato de moneda es-AR, glosario con fuentes BCRA/INDEC (`prompts/financial_glossary.v1.json`). La autoridad se demuestra con números exactos, no con lenguaje técnico.

### 2.4 El plan de 3 pasos

1. **Enviá un mensaje** con tu gasto o ingreso, como hablás («Gasté 5000 en nafta», `core_prompt.md:79`).
2. **Luka lo clasifica al instante** y te confirma («✅ Registré tu egreso: nafta por $5000 ARS»).
3. **Recibís balances y decisiones** cuando los pedís o cuando hacen falta (límites, recordatorios, gráficos, dashboard con `/link`).

### 2.5 Llamado a la acción

- **Directo:** «Escribime tu gasto» / «Pedime tu balance» / `/link` para el dashboard.
- **Transicional:** aceptar una mejora (crear límite, aceptar recordatorio sugerido con botones «Sí, avisame» / «No, gracias»).

### 2.6 Éxito y fracaso

- **Éxito (lo que el usuario gana):** claridad, control, tiempo libre; «una persona financiera consciente».
- **Fracaso (el costo de no actuar):** fin de mes sin saber en qué se fue la plata; decisiones a ciegas; culpa.

---

## 3. Matriz de voz y tono

### 3.1 Modulación por contexto

| Contexto del evento | Tono | Ejemplo canónico real |
|---|---|---|
| Registro exitoso | Ágil, sobrio, positivo | «✅ Registré tu egreso: nafta por $5000 ARS.» (`dispatcher.py:137`) |
| Registro con categoría | Confirmatorio, ofrece control | «📁 Detecté la categoría *Comida*. ¿Confirmás que es correcta? Respondé 'sí' para confirmar o decime la categoría correcta.» (`dispatcher.py:181-182`) |
| Duplicado | Neutro, informativo | «Este movimiento ya había sido registrado, no lo dupliqué.» (`dispatcher.py:194`) |
| Faltan datos | Pedagógico, sin culpar | «No pude registrar el movimiento porque me faltan datos claros. ¿Podés reenviarlo con monto, descripción y si es ingreso o egreso?» (`dispatcher.py:200-203`) |
| No era un movimiento | Orientador con ejemplo | «No identifiqué un movimiento financiero para registrar. Podés escribir algo como: 'Gasté 5000 en supermercado'.» (`dispatcher.py:208-212`) |
| Fallo técnico | Sobrio, honesto, con salida | «Hubo un problema registrando el movimiento. Por favor, intentá nuevamente en unos minutos.» (`dispatcher.py:206`) |
| LLM no disponible | Honesto, pide reformular | «No he podido analizar tu mensaje en este momento. ¿Podés reformularlo e intentar de nuevo?» (`llm.py:408-409`) |
| Desvío/exceso de límite | Alerta preventiva, sin juzgar | «⚠️ *Comida — agosto 2026* Gastaste $90.000 ARS de $80.000 ARS. Te quedan $-10.000 ARS (112 % usado). Superaste el límite en $10.000 ARS.» (`dispatcher.py:1277-1282`) |
| Límite alcanzado | Hito neutro | «🎯 ... Alcanzaste tu límite.» (`dispatcher.py:1291`) |
| Oferta de compensación | Propuesta, reversible, con vencimiento | «Detecté que *Comida* superó su límite. 💡 Podés compensarlo moviendo $... El total se mantiene. Vence en 30 minutos. Respondé *confirmar compensación* o *no por ahora*.» (`dispatcher.py:1324-1329`) |
| Cancelación / sin cambios | Cierre limpio, sin drama | «Listo, no hice ningún cambio.» (`dispatcher.py:3630`); «Listo, cancelé la operación pendiente.» (`dispatcher.py:3624`) |
| Recordatorio proactivo | Cálido, breve, se apaga fácil | «👋 ¡Ey! ¿Tuviste algún gasto hoy que no registraste? Contame y lo anoto. (Si no querés estos avisos, pedime que no te escriba más.)» (`scheduler.py:35`) |
| Fuera de alcance | Amable, firme, con derivación | «Solo puedo ayudarte con el registro de movimientos de tus finanzas personales.»; «No puedo brindar asesoramiento financiero profesional. Te sugiero consultar a un profesional matriculado.» (`prompt.md:696-731`) |
| Onboarding web | Cercano y burocráticamente mínimo | «Creá tu acceso seguro» / «Registrá tu cuenta» / «Vamos a vincular tu cuenta con el WhatsApp desde el cual recibiste este enlace.» (`registro.html:32-37`) |

### 3.2 Pendiente de tono (deuda declarada)
Cuando Redis cae, los mensajes actuales («Se perdió el contexto. Volvé a registrar el movimiento.», `dispatcher.py:2596`, `2629`, `2671`, `2829`, `2885`, `3675`, `3774`) suenan a log de sistema. El backlog lo marca como el peor momento para sonar máquina (`luka-backlog-arquitectura-interaccion.md:113-121`). **Regla:** toda degradación debe explicar qué pasó y qué hacer, en voz Luka (ej.: «Me perdí el hilo de lo que estábamos haciendo. Escribime de nuevo el gasto y lo anoto.»). *(Copy aprobado 2026-09-23; deuda de producto pendiente de implementación.)*

---

## 4. Reglas de estilo obligatorias

### 4.1 Lengua
- **Voseo rioplatense** en todo el producto: «podés», «escribime», «decime», «volvé».
- Frases **cortas** (ideal ≤ 2 líneas por párrafo). Un dato por línea en respuestas compuestas.
- Sin signos de exclamación salvo el saludo proactivo aprobado («¡Ey!»).
- Preguntas con signos de apertura y cierre («¿Cuánto pagaste?», `core_prompt.md:87`).

### 4.2 Nombres propios
- **LUKA** → solo en logotipo y marca gráfica (wordmark, isotipo, títulos de pantalla, `<title>`).
- **Luka** → en prosa, mensajes del bot, documentación y UI textual.
- Regla: nunca «LUKA» en medio de una frase («Escribile a Luka», no «Escribile a LUKA»).

### 4.3 Números y dinero
- Formato es-AR: miles con punto, decimales con coma; **sin decimales si son cero** (`docs/movement-charts.md:63`).
- Moneda siempre explícita en respuestas de montos: `$5000 ARS`.
- Porcentajes con espacio fino: «80 % usado» (en chat puede ir sin espacio: «80% usado», `dispatcher.py:1281`).

### 4.4 Emojis funcionales (set permitido)
Los emojis son **señalética**, no decoración. Set aprobado y su significado:

**Set oficial reducido a 5 (D2.4, aprobado 2026-09-23):**

| Emoji | Significado | Ejemplo |
|---|---|---|
| ✅ | Operación confirmada | «✅ Registré tu egreso…» |
| 📁 | Categoría | «📁 Detecté la categoría…» |
| ⚠️ | Advertencia de límite excedido | «⚠️ *Comida — agosto*…» |
| 🎯 | Límite alcanzado / meta | «🎯 … Alcanzaste tu límite.» |
| 🔔 | Aviso de vencimiento | «🔔 ¡Ey! Mañana vence tu pago de *wifi*.» |

- **Deprecados** (hoy en producción): 📊 📌 💰 💡 👋 ⏸️ — al tocar cada copy, migrar a texto plano; no se usan en piezas nuevas.
- `⏳` y `❌` no son emojis de texto: son **reacciones de WhatsApp** del contrato de feedback (`04-ux-conductual.md` §7).
- No se agregan emojis fuera de este set sin pasar por gobernanza (`05-gobernanza-manual-vivo.md`).

### 4.5 Longitud de mensajes
- Confirmaciones: **una línea**.
- Alertas y propuestas: máximo **4 líneas + botones**.
- Listas: máximo 10 ítems visibles antes de paginar/limitar.

---

## 5. Claridad sobre ingenio (*Clarity Over Cuteness*)

Miller: la ambigüedad y el ingenio destruyen la conversión. En un producto financiero, además, destruyen la confianza.

### 5.1 Decir / Evitar

| Decir | Evitar | Por qué |
|---|---|---|
| Movimiento | Transacción | El lenguaje conversacional no debe sonar bancario (`docs/conversation-flows.md`) |
| Límite (de gasto) | Presupuesto técnico / «budget» | El usuario pidió «límite»: es la palabra del producto en el chat (`create_limit`, `list_limits`) |
| Vincular / conectar tu cuenta | Onboarding, aprovisionamiento | «Vinculación» ya se usa en onboarding; «crear usuario» es interno |
| Cobraste / te pagaron | Acreditación recibida | El chat usa «ingreso» y «egreso» como tipos, pero en prosa se prefiere el verbo humano |
| No pude registrar | Error 500 / fallo de persistencia | La voz nunca expone el sistema |
| Te quedan $X | Saldo disponible restante | Igual de claro, más natural |
| Ajustar / compensar | Rearmado presupuestario | «Compensar» ya existe en el producto, siempre explicado con montos y sin jerga (`dispatcher.py:1354-1357`) |
| Gastos hormiga | Gastos discrecionales de baja cuantía | Directo, humano |
| Interés compuesto (en educación) | TNA / TEA / CFT mal explicado | CFT se explica y se compara con ejemplo; nunca se da una tasa actual (`core_prompt.md:30`) |

### 5.2 Prohibiciones de copy
1. Tecnicismos bancarios sin traducción inmediata.
2. Promesas de resultado («vas a ahorrar más», «mejorá tus finanzas garantizado»).
3. Recomendaciones de inversión o trading (`core_prompt.md:29-30`).
4. Cifras o tasas actuales sin fuente oficial (`financial_education.py:130-131`).
5. Confirmaciones vacías («Listo», sin qué se hizo o qué sigue).
6. Culpa o vergüenza por gastar («otra vez gastaste de más»).

**Alcance (D2.5, aprobado 2026-09-23):** estas prohibiciones son **guía de estilo recomendada**, no un gate bloqueante. Las revisiones de copy las usan como referencia y pueden documentar desvíos deliberados.

---

## 6. Glosario humanizado

Fuente canónica: `prompts/financial_glossary.v1.json` v1.0.0 (revisado 2026-09-21). Fuente de cada término: BCRA e INDEC (`docs/financial-glossary.md:10-13`).

| Término | Cómo lo dice Luka en chat | Ejemplo aprobado |
|---|---|---|
| Presupuesto | «plan para decidir cuánto dinero querés destinar a distintos gastos o metas durante un período» | «Si definís $80.000 para comida este mes, ese monto funciona como una referencia…» |
| Gasto fijo | «gasto que suele repetirse con una frecuencia y un importe relativamente previsible» | «El alquiler o un abono mensual…» |
| Gasto variable | «gasto cuyo importe o frecuencia puede cambiar de un período a otro» | «La comida o las salidas…» |
| Ahorro | «parte de tus ingresos que decidís no gastar hoy para usarla más adelante» | «Si cobrás $100.000 y reservás $10.000 para una meta, esos $10.000 son ahorro.» |
| Interés simple | «se calcula siempre sobre el monto inicial, sin sumar los intereses acumulados» | «$1.000 al 10 % simple anual → $100 por año…» |
| Interés compuesto | «se calcula sobre el monto inicial y también sobre los intereses acumulados» | Ejemplo ilustrativo con $1.000 al 10 %. |
| Inflación | «aumento general y sostenido de los precios, que reduce cuánto podés comprar con la misma cantidad de dinero» | «Si algo costaba $1.000 y después $1.100…» |
| Deuda | «obligación de devolver dinero o cumplir un pago acordado, a veces con intereses y otros cargos» | «Una compra en cuotas genera compromisos futuros…» |
| Costo financiero total (CFT) | «medida que reúne el costo de un crédito, incluyendo intereses, comisiones, seguros y otros cargos» | «Dos préstamos con la misma tasa pueden tener distinto CFT…» |

**Reglas del glosario:**
- Si el término es ambiguo, Luka repregunta: «¿Te referís a interés simple o interés compuesto?» (`financial_education.py:141-142`).
- Si piden tasas o valores actuales: «No puedo confirmar valores o tasas actuales desde este glosario. Para una cifra vigente, consultá una fuente oficial actualizada.» (`financial_education.py:130-131`).
- Si el término no está: «No tengo una definición verificada de ese concepto en mi glosario actual…» (`financial_education.py:153-154`).
- Toda definición se puede ampliar; ninguna se puede inventar.

**Términos internos del producto que nunca llegan al usuario:** `intent`, `dispatcher`, `payload`, `webhook`, `endpoint`, `persistencia`, `caché`, `service message`, `token`, `sha256`, `Supabase`, `Redis`, `LLM`.

---

## 7. Árbol de respuestas (referencia)

```
Mensaje entrante
├── ¿Es comando? (/link, /movimientos, /egresos, /ayuda)
│     └── Respuesta terminal, un único texto (no captura al usuario)
├── ¿Hay operación pendiente? (categoría, compensación, borrado, recordatorio)
│     ├── A favor  → confirmar y ejecutar
│     ├── En contra → "Listo, no hice ningún cambio."
│     └── Texto libre → abandona el recorrido y vuelve al dispatcher (nunca se obliga a terminar)
├── Clasificación LLM
│     ├── Registro 1..N movimientos → confirmación tras persistir
│     ├── Consulta → datos reales, formato es-AR, nunca cifras inventadas
│     ├── Corrección / anulación → confirmación del cambio exacto
│     ├── Recordatorio → 1 pregunta por dato faltante
│     ├── Límite / compensación → cálculo del backend, confirmación explícita
│     ├── Educación → glosario versionado + límites declarados
│     ├── Fuera de alcance → rechazo amable + derivación
│     └── Fallo LLM → pedir reformular (nunca crash silencioso)
└── Degradación (Redis caído, sin cuenta, error persistencia)
      └── Explicar qué pasó + qué hacer. Nunca confirmar un éxito falso.
```

Reglas estructurales: `luka/docs/conversation-flows.md:9-24, 193-218`.

---

## 8. Anexo A · Inventario de microcopy real (extracto curado)

> Copys tomados del producto en producción (rama `main`, 2026-09-23). Este anexo es la fuente de verdad para consistencia; al agregar mensajes, reutilizar patrones existentes.
> **Nota de emojis (D2.4):** los copys de este anexo conservan los emojis que hoy están en producción (📊 📌 💰 💡 👋 ⏸️); quedaron **deprecados**. Al tocar cada mensaje, migrarlos al set oficial (✅ 📁 ⚠️ 🎯 🔔) o a texto plano.

### 8.1 Registro y clasificación

| Evento | Copy | Ref |
|---|---|---|
| Registro simple | «✅ Registré tu egreso: supermercado por $15000 ARS.» | `dispatcher.py:1063` |
| Categoría asignada | «✅ Registré tu egreso: … por $… ARS. 📁 Categoría: ….» | `dispatcher.py:1063-1065` |
| Sugerir cambio | «¿No estás de acuerdo con la categoría? Indicame y lo cambiamos.» + botón «Cambiar categoría» | `dispatcher.py:140-176` |
| Confirmar categoría | «📁 Detecté la categoría *X*. ¿Confirmás que es correcta? Respondé 'sí' para confirmar o decime la categoría correcta.» | `dispatcher.py:179-183` |
| Duplicado | «Este movimiento ya había sido registrado, no lo dupliqué.» | `dispatcher.py:194` |
| Sin cuenta | «No encontré una cuenta vinculada a este WhatsApp. No pude registrar el movimiento.» | `dispatcher.py:197` |
| Datos faltantes | «No pude registrar el movimiento porque me faltan datos claros. ¿Podés reenviarlo con monto, descripción y si es ingreso o egreso?» | `dispatcher.py:200-203` |
| Error técnico | «Hubo un problema registrando el movimiento. Por favor, intentá nuevamente en unos minutos.» | `dispatcher.py:206` |
| No es movimiento | «No identifiqué un movimiento financiero para registrar. Podés escribir algo como: 'Gasté 5000 en supermercado'.» | `dispatcher.py:208-212` |
| Multiop parcial | «✅ Registré {registered} de {total} movimientos. Algunos faltan datos (monto, descripción o tipo). ¿Los reenvías?» | `dispatcher.py:254-257` |
| Multiop total | «✅ Registré los {total} movimientos.» | `dispatcher.py:244` |
| Falta monto | «¿Cuánto pagaste?» | `core_prompt.md:87` |

### 8.2 Corrección y anulación

| Evento | Copy | Ref |
|---|---|---|
| Corregido | «✅ Corregí {desc}: ahora es $… Categoría: …» | `dispatcher.py:436-438` |
| Eliminado | «✅ Eliminé {desc} por $…» | `dispatcher.py:459` |
| Lote eliminado | «✅ Eliminé N movimientos: …» | `dispatcher.py:494` |
| Movimiento viejo | «Ese movimiento ya no está disponible.» | `dispatcher.py:423-431` |
| Cambió desde que se mostró | «Ese movimiento cambió desde que lo mostramos. Consultá /movimientos otra vez.» | `dispatcher.py:423-431` |
| No modificable | «No pude modificar ese movimiento. Revisá los datos e intentá de nuevo.» | `dispatcher.py:423-431` |
| Ambiguo | «No pude identificar un único movimiento de {name}. Consultá /movimientos e indicame cuáles querés eliminar.» | `dispatcher.py:546-547` |
| Pedir selección | «Indicame entre 2 y 5 movimientos recientes para eliminar.» | `dispatcher.py:515` |

### 8.3 Límites y presupuesto

| Evento | Copy | Ref |
|---|---|---|
| Normal | «📊 *{cat} — {mes}* Gastaste $X de $Y. Te quedan $Z (n% usado).» | `dispatcher.py:1294-1297` |
| Alcanzado | «🎯 … Te quedan $… (n% usado). Alcanzaste tu límite.» | `dispatcher.py:1284-1292` |
| Excedido | «⚠️ … Superaste el límite en $W.» | `dispatcher.py:1274-1283` |
| Compensación propuesta | «Detecté que *{cat}* superó su límite. 💡 Podés compensarlo moviendo $… El total se mantiene. Vence en 30 minutos. Respondé *confirmar compensación* o *no por ahora*.» | `dispatcher.py:1324-1329` |
| Compensación aplicada | «✅ Compensé *{cat}* con $… No se modificó ningún movimiento.» | `dispatcher.py:1354-1357` |
| Compensación vencida/desactualizada | «La propuesta venció…» / «Los saldos cambiaron desde que armé la propuesta. Pedime un nuevo cálculo.» | `dispatcher.py:1366-1371` |
| Límite creado | «✅ Registré tu límite para {mes}. 📁 Categoría: …. 🎯 Límite a gastar: $….» + «¿No te convence algo? Indícame y lo cambiamos.» | `dispatcher.py:1423-1431` |
| Listar | «🎯 *Tus límites de gasto:*» | `dispatcher.py:1456` |
| Desambiguar | «Tengo varios límites de {cat}. ¿A cuál te referís?» | `dispatcher.py:1465` |

### 8.4 Recordatorios

| Evento | Copy | Ref |
|---|---|---|
| Creado | «✅ Dale, te aviso que pagués {concepto} (${monto} ARS) el día {día} de cada mes.» | `dispatcher.py:667` |
| Lista | «📌 *Tus recordatorios:*» + «⏸️• *{título}* — día {día} — $monto» | `dispatcher.py:689-700` |
| Actualizado | «✅ Listo, actualicé el recordatorio.» | `dispatcher.py:706` |
| Pausado | «✅ Dale, pausé ese recordatorio. Aviáme si querés reactivarlo.» | `dispatcher.py:721` |
| Reactivado | «✅ Listo, reactivé el recordatorio.» | `dispatcher.py:722` |
| Eliminado | «✅ Listo, eliminé el recordatorio.» | `dispatcher.py:747` |
| No encontrado | «No encontré ese recordatorio. Chequeá el nombre con *mis recordatorios*.» | `dispatcher.py:710` |
| Vencimiento (3 días) | «🔔 ¡Ey! En 3 días vence tu pago de *{título}* ({fecha}).» | `scheduler.py:225-229` |
| Vencimiento (mañana) | «🔔 ¡Ey! Mañana vence tu pago de *{título}*.» | `scheduler.py:227` |
| Proactivo diario | «👋 ¡Ey! ¿Tuviste algún gasto hoy que no registraste? Contame y lo anoto. (Si no querés estos avisos, pedime que no te escriba más.)» | `scheduler.py:35` |
| Activar proactivos | «Listo, activé los recordatorios proactivos. Te voy a escribir si no registrás tus gastos del día.» | `reminder.py:447-448` |
| Desactivar proactivos | «Listo, no te voy a escribir más para recordarte gastos no registrados. Si querés que retome, avisame.» | `reminder.py:452-453` |
| Sugerencia recurrente | «💡 Noté que solés pagar *{concepto}* alrededor del día {día}. ¿Querés que te avise 3 días antes de cada vencimiento?» + «Sí, avisame» / «No, gracias» | `dispatcher.py:3343-3348` |
| Sugerencia aceptada | «¡Listo! Agendé el recordatorio para *{título}* los días {día} de cada mes con aviso 3 días antes.» | `dispatcher.py:3455` |
| Sugerencia rechazada | «Entendido, no volveré a sugerirte este recordatorio.» | `dispatcher.py:3519` |

### 8.5 Consultas, onboarding y dashboard

| Evento | Copy | Ref |
|---|---|---|
| Categorías | «📊 *Tus categorías:*» + «💰 $ingreso ingreso \| 💸 $egreso egreso» | `dispatcher.py:815-825` |
| Invitación a registrarse | «Para usar Luka, primero registrate y vinculá este WhatsApp: {url}. El enlace vence en {ttl} minutos.» | `dispatcher.py:777-781` |
| Enlace al dashboard | «Accedé a tu dashboard acá: {url}. El enlace vence en {ttl} minutos y sólo se puede usar una vez.» | `dispatcher.py:785-789` |
| Sin cuenta (link) | «Todavía no tenés una cuenta vinculada. Escribime cualquier mensaje para empezar.» | `dispatcher.py:793-794` |
| Reset de contexto | «Listo, arrancamos de cero. Olvidé lo anterior.» | `dispatcher.py:886` |
| Onboarding web | «Creá tu acceso seguro» / «Registrá tu cuenta» / «Vamos a vincular tu cuenta con el WhatsApp desde el cual recibiste este enlace.» / «Continuar con Google» | `registro.html:32-69` |
| Registro completado | «Tu registro se completó correctamente.» / «Ya podés volver a WhatsApp y comenzar a usar Luka.» | `registro_completado.html:22-23` |
| Login | «Tu asistente financiero personal» / «Abrí **WhatsApp** y enviá el mensaje `/link` a LUKA» / «¡Listo! Accedés automáticamente a tu dashboard» | `login.html:26-48` |
| Enlace vencido | «Este enlace venció. Escribile nuevamente a **Luka** para recibir otro.» | `registro.html:90-98` |
| Enlace usado | «Este enlace ya fue utilizado. Iniciá sesión para continuar.» | `registro.html:83-89` |
| Sin transacciones | «Sin transacciones» / «Enviá gastos a LUKA por WhatsApp para verlos acá.» | `partials/transactions.html:30-31` |

### 8.6 Estados y errores del negocio

| Evento | Copy | Ref |
|---|---|---|
| Sin recordatorios | «No tenés recordatorios activos por ahora.» | `dispatcher.py:687` |
| Sin categorías | «No tenés categorías todavía. Cuando registres movimientos se irán creando.» | `dispatcher.py:815` |
| Contexto perdido (**a corregir**) | «Se perdió el contexto. Volvé a registrar el movimiento.» | `dispatcher.py:3675` |
| Cancelación | «Listo, no hice ningún cambio.» / «Listo, cancelé la operación pendiente.» | `dispatcher.py:3624-3630` |
| Botón vencido | «Esa opción ya no está disponible. Escribime qué querés hacer.» | `dispatcher.py:3666` |
| Notas de voz | «Aun no proceso notas de voz.» | `llm.py:423` |
| Imágenes | «Aun no proceso imagenes de comprobantes.» | `llm.py:434` |
| Fuera de alcance | «Solo puedo ayudarte con el registro de movimientos de tus finanzas personales.» | `prompt.md:696-731` |
| Asesoramiento | «No puedo brindar asesoramiento financiero profesional. Te sugiero consultar a un profesional matriculado.» | `prompt.md:696-731` |

**Nota:** «Aun no proceso notas de voz / imagenes» tiene dos defectos de estilo (sin tilde en «aún», «imagenes» sin tilde). **Regla de estilo:** todo copy pasa por corrector ortográfico antes de publicarse (`05-gobernanza-manual-vivo.md` §2).

---

## 9. Decisiones de esta fase

| # | Decisión | Estado |
|---|---|---|
| D2.1 | Voz permanente: cercana, clara, prudente, resolutiva (definiciones §1) | ✅ Aprobado 2026-09-23 |
| D2.2 | BrandScript SB7 como narrativa oficial | ✅ Aprobado 2026-09-23 |
| D2.3 | Regla `LUKA` (marca gráfica) vs `Luka` (prosa) | ✅ Aprobado 2026-09-23 |
| D2.4 | Set de emojis reducido a 5 oficiales (✅ 📁 ⚠️ 🎯 🔔); resto deprecado | ✅ Aprobado 2026-09-23 |
| D2.5 | Prohibiciones de copy como guía de estilo (no bloqueante) | ✅ Aprobado 2026-09-23 |
| D2.6 | Reemplazo de mensajes «Se perdió el contexto» por voz Luka | ✅ Copy aprobado — implementación pendiente |

---

## 10. Fuentes

- `luka/prompts/core_prompt.md`, `luka/prompt.md`, `luka/prompts/financial_glossary.v1.json`
- `luka/app/services/dispatcher.py`, `scheduler.py`, `reminder.py`, `llm.py`, `financial_education.py`
- `luka/docs/conversation-flows.md`, `features.md`, `financial-glossary.md`
- `luka/luka-backlog-arquitectura-interaccion.md` (no versionado)
- `luka_frontend/app/templates/*.html`, `app/main.py`
- Miller, D. *Building a StoryBrand*; Cervantes, R. G. *De usuario a héroe* (Aerolab).
