# 03 · Identidad Visual y Diseño Visceral

> **Entregable de Fase 3.** Nivel visceral (Norman): la reacción sensorial inmediata — color, forma, tipografía, aire. Un producto visualmente sereno reduce el estrés operativo de mirar dinero.
> Dirección aprobada: **paleta nueva** (azul profundo tecnológico + esmeralda de logro), sustituyendo el indigo actual del dashboard.
> **Decisiones de esta fase cerradas 2026-09-23** (ver §10): paleta aprobada, isotipo definitivo integrado, categorías unificadas con tildes.
> Fuentes: `luka_frontend/static/css/style.css`, `registro.css`, `admin_flows.css`, `app/templates/**`, `app/dashboard.py`, `luka/app/services/movement_chart.py`, `luka/public/*`, `luka/testing/.streamlit/config.toml`.
> Tokens: `tokens/design-tokens.json` (fuente de verdad) y `tokens/tokens.css` (implementación).

---

## 1. Principios visuales

1. **Calma sobre densidad.** Fondos profundos, superficies limpias, aire generoso. El dinero ya estresa; el tablero no debe hacerlo.
2. **Oscuro por defecto, claro por derecho.** El producto vive en modo oscuro (WhatsApp de noche incluido); el tema claro es una variante completa, no un parche.
3. **El color comunica, no decora.** Cada color semántico tiene un único significado (ahorro, advertencia, gasto, error). Nunca se usa rojo para un gasto normal.
4. **Los números son protagonistas.** Cifras tabulares, formato es-AR, jerarquía tipográfica clara.
5. **Movimiento discreto.** Micro-animaciones al servicio de la comprensión (fadeUp, feedback), nunca espectáculo.

---

## 2. Logomarca

### 2.1 Estructura de marca

| Elemento | Qué es | Estado |
|---|---|---|
| **Wordmark** | «LUKA» geométrico (PNG en `luka/public/logo-luka-texto.png`, fondo transparente, casi blanco `#F8F8FF`) | Vigente; pendiente exportar SVG vectorial |
| **Isotipo** | Símbolo definitivo (D3.3): burbuja de diálogo entrelazada, dos formas orgánicas con gradiente azul→esmeralda; variantes color/claro/oscuro/mono | ✅ Definido e integrado 2026-09-23 (`public/` + `assets/`) |
| **Favicon** | Derivado del isotipo (viewBox recortado al contenido) + PNG 32/512 y apple-touch 180 | ✅ Integrado 2026-09-23 |

**Criterio (D3.3):** se descarta unificar hacia el monograma K (y también el «A» del frontend): el isotipo es el símbolo nuevo. Los archivos K fueron eliminados de `assets/` y no deben usarse en piezas nuevas.

### 2.2 Construcción y variantes

- Construcción: símbolo orgánico de dos formas entrelazadas que sugiere una burbuja de diálogo; 6 paths con curvas continuas, viewBox `0 0 333 295` (contenido medido: x 5.8→330.1, y 4.3→292.7).
- Colores propios del símbolo (no se recolorean): sólidos `#0667EE`, `#0689AF`, `#0EA099` + gradientes `#0EB86B → #0687B5` y `#0C8CBB → #0B72E5`.
- Variantes (set canónico en `docs/marca/assets/`; copias de producción en `luka_frontend/public/`):
  | Archivo | Uso |
  |---|---|
  | `assets/isotipo-color.svg` (`public/logo-luka.svg`) | Por defecto: fondos claros y oscuros, espacios de marca |
  | `assets/isotipo-claro.svg` (`public/logo-luka-claro.svg`) | Fondos oscuros: navy, fotos o superficies de bajo contraste |
  | `assets/isotipo-oscuro.svg` (`public/logo-luka-oscuro.svg`) | Fondos claros: una tinta negra |
  | `assets/isotipo-mono.svg` (`public/logo-luka-mono.svg`) | Monocromo `currentColor`: sellos, marcas de agua, impresión a una tinta, integraciones de terceros |
  | `assets/favicon.svg` (`public/favicon.svg`) | Favicon: viewBox recortado al contenido `4 2 328 292` |
- PNG derivados (`luka_frontend/public/`): `favicon-32.png` y `favicon-512.png` (fondo transparente); `apple-touch-icon.png` (180×180, fondo navy `#0A1626` con isotipo color).
- **Zona de resguardo:** margen mínimo = 25 % del ancho del símbolo. Nada entra en ese perímetro.
- **Tamaños mínimos:** 16 px (verificado a 16/24/32/48 px); por debajo, no usar.
- **Contraste:** usar la variante correcta según fondo (claro sobre oscuro, oscuro sobre claro); la variante color exige contraste ≥ 3:1.

### 2.3 Usos indebidos

- No rotar, estirar, inclinar ni aplicar sombras/contornos/biseles.
- No cambiar el ángulo ni los colores del gradiente; no usar degradados adicionales.
- No recrear el wordmark con otra tipografía ni separarlo del isotipo dentro de una misma pieza sin respetar el lockup.
- No poner el isotipo claro sobre fondos con contraste < 3:1.
- No recolorear ni alterar las variantes: los colores del símbolo son fijos.
- No descomponer el símbolo: no separar las formas entrelazadas, no recortar partes ni cambiar su relación de entrelazado.
- No usar la variante de color sobre fondos con contraste < 3:1 (usar `isotipo-claro`, `isotipo-oscuro` o `isotipo-mono`).
- No usar el «A» triangular del template (`logo_login.svg`) ni los assets K (eliminados) en piezas nuevas: deprecados a nivel de marca (ver §9).

### 2.4 Cumplimiento del brief (D3.3)

El símbolo entregado cumple el brief: es abstracto y propio, evoca **fluidez, diálogo** (burbuja entrelazada) y **balance**, sin clichés (globo, *swoosh*, monedas, alcancías) ni los monogramas K/A; es legible a 16 px (QA a 16/24/32/48 px) y está disponible en una tinta (`isotipo-mono.svg`, `currentColor`). Assets de producción en `luka_frontend/public/` y set canónico en `docs/marca/assets/`.

---

## 3. Sistema de color

### 3.1 Decisión de psicología y semiótica financiera

| Rol | Color | Por qué |
|---|---|---|
| Primario / acción | **Azul profundo** (`#2563EB`, base navy `#0A1626`) | Solidez y serenidad con matiz tecnológico; el azul es el color de la confianza financiera y el más seguro para acciones |
| Logro / ahorro / ingreso | **Esmeralda balanceado** (`#0E9F6E` / `#34D399`) | Verde de crecimiento sin fosforescencia: celebra sin gritar |
| Advertencia de presupuesto | **Ámbar cálido** (`#B45309` / `#FBBF24`) | Alerta preventiva y constructiva; no es fracaso |
| Gasto / consumo | **Grafito neutro** (`#64748B` / `#94A3B8`) | **Nunca rojo para gastar**: el rojo genera aversión psicológica al registro (la gente deja de anotar) |
| Error / pérdida / riesgo | **Rojo** (`#DC2626` / `#F87171`) | Reservado a errores reales, acciones destructivas y estados críticos |
| Superficies | Navy `#0A1626` / `#102138` / `#17304D` | Profundidad sin negro puro; menos fatiga visual |
| Espacio en blanco | Aire generoso (`--space-6` a `--space-16`) | Evita la sobrecarga cognitiva de los tableros financieros densos |

**Regla de oro:** el rojo no se usa para egresos, montos negativos normales ni categorías; solo para error/riesgo/destructivo. (Hoy el dashboard usa `#f87171` para montos negativos y exceso: se corrige en la adopción.)

### 3.2 Primitivos

| Token | HEX | Uso |
|---|---|---|
| `navy-950` | `#06101F` | Fondos de overlays/hero |
| `navy-900` | `#0A1626` | Fondo base (dark) |
| `navy-800` | `#102138` | Superficie (cards, sidebar) |
| `navy-700` | `#17304D` | Superficie elevada |
| `navy-600` | `#1F4166` | Bordes fuertes/estados hover |
| `blue-700` | `#1D4ED8` | Acción en tema claro |
| `blue-600` | `#2563EB` | Acción por defecto (dark), gradiente |
| `blue-500` | `#3B82F6` | Hover |
| `blue-400` | `#6EA8FF` | Acento/links/texto interactivo en dark |
| `blue-300` | `#A5C6FF` | Detalles, gráficos |
| `emerald-700` | `#047857` | Éxito/ahorro en claro |
| `emerald-600` | `#0E9F6E` | Gradiente, éxito en claro |
| `emerald-500` | `#10B981` | Acentos |
| `emerald-400` | `#34D399` | Éxito/ahorro/ingreso en dark |
| `amber-700` | `#B45309` | Advertencia en claro |
| `amber-500` | `#F59E0B` | Detalles de advertencia |
| `amber-400` | `#FBBF24` | Advertencia en dark |
| `red-600` | `#DC2626` | Error/destructivo en claro |
| `red-400` | `#F87171` | Error/destructivo en dark |
| `graphite-700/500/400/300` | `#334155` / `#64748B` / `#94A3B8` / `#CBD5E1` | Gasto/neutro, texto secundario, bordes |

### 3.3 Semánticos — verificados WCAG AA

Contraste calculado con luminancia relativa WCAG 2.x (script de verificación, 2026-09-23). Umbral texto ≥ 4.5:1; no-texto ≥ 3:1.

**Tema oscuro** (sobre `bg-base #0A1626` / `bg-surface #102138` / `bg-elevated #17304D`):

| Token | Valor | base | surface | elevated |
|---|---|---|---|---|
| `text-primary` | `#E8EFFA` | 15.71 | 14.00 | 11.59 |
| `text-secondary` | `#A9BCD6` | 9.39 | 8.37 | 6.93 |
| `text-muted` | `#8AA0C4` | 6.84 | 6.10 | 5.05 |
| `accent` | `#6EA8FF` | 7.54 | 6.72 | 5.56 |
| `success` / `money-in` | `#34D399` | 9.45 | 8.42 | 6.97 |
| `warning` | `#FBBF24` | 10.89 | 9.70 | 8.03 |
| `danger` | `#F87171` | 6.57 | 5.85 | 4.85 |
| `money-out` | `#94A3B8` | 7.09 | 6.32 | 5.23 |
| Botón | blanco sobre `#2563EB` | 5.17 | — | — |

**Tema claro** (sobre `bg-base #F4F7FC` / `bg-surface #FFFFFF`):

| Token | Valor | base | surface |
|---|---|---|---|
| `text-primary` | `#0A1626` | 16.92 | 18.17 |
| `text-secondary` | `#475569` | 7.06 | 7.58 |
| `text-muted` | `#5B6B80` | 5.07 | 5.44 |
| `accent` / `action` | `#1D4ED8` | 6.24 | 6.70 |
| `success` / `money-in` | `#047857` | 5.11 | 5.48 |
| `warning` | `#B45309` | 4.68 | 5.02 |
| `danger` | `#DC2626` | 4.50 | 4.83 |
| `money-out` | `#5B6B80` | 5.07 | 5.44 |
| Botón | blanco sobre `#1D4ED8` | 6.70 | — |

> `--text-muted` no debe usarse para texto de lectura continua: es para hints y metadatos.

### 3.4 Colores de categoría (9 canónicas + Otros)

Un color por categoría, consistente entre chat (gráficos PNG), dashboard y badges. Contraste ≥ 3:1 sobre el fondo correspondiente (mínimo medido: dark 3.82, light 3.56 — todos cumplen no-texto).

| Categoría (display, código y datos) | Dark | Light |
|---|---|---|
| Servicios | `#6EA8FF` | `#2563EB` |
| Comida | `#F97316` | `#EA580C` |
| Transporte | `#22D3EE` | `#0891B2` |
| Ocio | `#A78BFA` | `#7C3AED` |
| Vivienda | `#818CF8` | `#4F46E5` |
| Salud | `#2DD4BF` | `#0D9488` |
| Educación | `#A3E635` | `#4D7C0F` |
| Ropa | `#F472B6` | `#DB2777` |
| Ingresos | `#34D399` | `#059669` |
| Otros (bucket de gráficos) | `#64748B` | `#64748B` |

**Regla de nombres (D3.6, aprobada 2026-09-23):** la categoría canónica se unifica **con tildes** en display, código y almacenamiento («Educación»). Requiere migración: renombrar semillas y taxonomía (`onboarding_finalization.py:19-29`), tests, y filas existentes (`Educacion` → `Educación`) — ver §9.

### 3.5 Reglas de uso del color

- Superficies: máximo 3 niveles (base/surface/elevated). Nada de gradientes de fondo salvo el hero.
- Estados interactivos: hover = subir un paso el azul; focus = borde `--accent` + halo `--shadow-glow`; disabled = `text-muted` + 40 % opacidad.
- Glassmorphism vigente: `--bg-glass` + borde `--border` sobre superficies elevadas; no usarlo en tablas de datos.
- El color nunca es la única señal de estado: siempre acompañar con texto/ícono (accesibilidad para daltonismo).

---

## 4. Tipografía y jerarquía de escaneo

### 4.1 Familias

| Rol | Familia | Fallbacks | Estado |
|---|---|---|---|
| **Display** (encabezados de marca, landing, títulos de sección) | **Space Grotesk** (500/700) | Inter, system-ui | Nueva; agregar a Google Fonts al construir landing |
| **UI / datos** (cuerpo, números, tablas, chat) | **Inter** (400/500/600/700/800) | system-ui, `-apple-system`, Segoe UI | Ya en uso |
| **Mono** (código, comandos del bot) | **JetBrains Mono** (400/600) | Fira Code, monospace | Ya en uso |

La UI del producto no cambia de familia: Inter ya cumple legibilidad y tiene cifras tabulares. Space Grotesk se reserva a display para no re-tematizar toda la interfaz.

### 4.2 Escala

| Token | Tamaño/Peso | Uso |
|---|---|---|
| `display-lg` | 32px / 700 / -0.02em | Título de landing/hero |
| `display-md` | 24px / 700 | Título de página |
| `heading-lg` | 20px / 700 | Título de sección/card |
| `heading-md` | 17px / 600 | Subtítulo |
| `body-lg` | 16px / 400 | Cuerpo principal |
| `body-md` | 14px / 400 | UI estándar |
| `body-sm` | 13px / 400 | Metadatos |
| `caption` | 12px / 500 | Labels, badges |
| `data` | 14px / 600 + `tnum` | Montos, tablas, KPIs |

### 4.3 Números y datos

- **Siempre cifras tabulares** (`font-variant-numeric: tabular-nums` / clase `.tabular`) para que los balances no bailen entre renders: montos, KPIs, tablas, ejes de gráficos.
- Formato es-AR: `$12.500` (miles con punto, sin decimales si son cero); decimales con coma cuando existan.
- Unidades: `%` para porcentajes, `ARS`/`USD` explícitas en contexto ambiguo.
- Alineación: montos a la derecha en tablas; KPIs con dígitos alineados en la misma columna.

---

## 5. Iconografía

- **Estilo:** line-style, grilla 24×24, trazo 1.75–2 px, esquinas y extremos redondeados, sin relleno. Reutilizar el set existente del frontend (`app/templates/components/icons/`, ~30 SVG) como base oficial de UI.
- **Iconos de acción del chat:** la semántica visual de reacción de WhatsApp se documenta como sistema: `⏳` en proceso (STK-180, implementado) → `✅` éxito / `❌` error (STK-222, roadmap).
- **Categorías:** cada una de las 9 canónicas debe tener un ícono lineal propio, legible a 16 px en móvil, coloreado con `--cat-*`.
- **Prohibido:** emojis como iconografía de UI (se usan solo en texto del chat, `02-identidad-verbal.md` §4.4); iconos rellenos mezclados con lineales; íconos de más de 2 trazos conceptuales.

---

## 6. Componentes

### 6.1 Web (dashboard/onboarding)

| Componente | Especificación |
|---|---|
| Card / sección | `bg-surface`, radio `--radius-lg`, borde `--border`, `--shadow-card`; padding `--space-6` |
| Stat card / KPI | Label `caption` + valor `display-md` `.tabular`; badge de estado con color semántico |
| Chip | `--radius-full`, fondo `--bg-glass`, texto `caption`; «Próximamente» en `text-muted` |
| Barra de presupuesto | Riel `bg-elevated`; progreso: `action` normal, `warning` ≥ 80 %, `danger` excedido; siempre con % y monto textuales |
| Botón primario | Fondo `--action`, texto `--on-action`, radio `--radius-md`, hover `--action-hover`, focus con `--shadow-glow` |
| Botón secundario | Fondo transparente, borde `--border-strong`, texto `--text-primary` |
| Input | Fondo `bg-elevated`, borde `--border`, focus borde `--accent`; label siempre visible |
| Tabla / lista de movimientos | Filas 44 px mínimo, monto `.tabular` a la derecha, egreso en `money-out`, ingreso en `money-in`, fecha `text-secondary` |
| Empty state | Ícono lineal + frase útil («Enviá gastos a LUKA por WhatsApp para verlos acá.») + CTA |
| Alert | Fondo del tinte semántico al 12 %, borde al 30 %, ícono+texto; nunca solo color |

### 6.2 Chat (WhatsApp)

| Componente | Especificación |
|---|---|
| Confirmación | ✅ + una línea: `✅ Registré tu egreso: nafta por $5000 ARS.` |
| Alerta de límite | ⚠️ + categoría en negrita + montos; máximo 4 líneas |
| Sugerencia | 💡 + propuesta + botones («Sí, avisame» / «No, gracias») |
| Lista | 📌 + ítems con guion; máximo 10 antes de paginar |
| Gráfico | PNG 2× con paleta categórica, fondo `--bg-surface` (oscuro) o blanco (claro), sin mezclar monedas |
| Estados de reacción | ⏳ procesando · ✅ listo · ❌ error |

---

## 7. Gráficos y datos

- **Paleta de datos:** la tabla §3.4 en el orden canónico; «Otros» siempre grafito; máximo 6 elementos por gráfico (5 categorías + Otros), regla ya vigente (`docs/movement-charts.md`).
- **Torta:** etiquetas con nombre + %; nunca más de 6 porciones; ingreso vs egreso no se mezcla en una torta.
- **Barras:** orden descendente por monto; grilla sutil (`--border`), sin 3D ni sombras.
- **Evolución mensual:** línea/área con relleno al 12 %; máx. 24 meses.
- **Accesibilidad:** cada serie con etiqueta textual (leyenda o etiqueta directa); no depender solo del color.
- **Consistencia chat↔web:** mismo color por categoría en PNG de WhatsApp y dashboard (fuente: tokens).

---

## 8. Design Tokens

| Archivo | Rol |
|---|---|
| `tokens/design-tokens.json` | Fuente de verdad (W3C-style `$type`/`$value`), versionada |
| `tokens/tokens.css` | Implementación lista para copiar: `:root` (oscuro) + `[data-theme="light"]` |

Cobertura: color (primitivo/semántico/categórico/gradientes), tipografía, espaciado, radios, sombras, movimiento. Regla de gobernanza: **ningún valor de diseño se escribe hardcodeado en componentes**; todo sale de tokens (ver `05-gobernanza-manual-vivo.md` §4).

---

## 9. Migración desde el estado actual (sin tocar código en esta fase)

| Actual | Valor | Destino |
|---|---|---|
| `--accent-primary` | `#6366f1` | `--action` `#2563EB` |
| `--accent-violet` | `#8b5cf6` | Retirar como «violeta de marca»; usar `--cat-ocio`/`--cat-vivienda` según contexto |
| `--accent-pink` | `#ec4899` | `--cat-ropa` |
| `--accent-teal` | `#14b8a6` | `--cat-salud` |
| `--accent-amber` | `#f59e0b` | `--warning` o `--cat-comida` según uso |
| Texto `#f1f5f9` / `#94a3b8` / `#475569` | — | `#E8EFFA` / `#A9BCD6` / `#8AA0C4` |
| Rojo `#f87171` en montos negativos y barras | — | `--money-out` grafito; rojo solo en error/exceso crítico |
| Gráficos `PALETTE = #3066BE, #087F8C, #7A5195, #BB5A24, #A33757, #58752D` (`luka/app/services/movement_chart.py:22`) | — | Paleta categórica §3.4 |
| Logo gradiente `#6366f1 → #a855f7` | — | Gradiente de marca `#2563EB → #0E9F6E` |
| Categorías del dashboard: 8 entradas con «Entretenimiento», «Hogar», «Otro» (`app/dashboard.py:23-32`) | — | 9 canónicas + Otros §3.4 |
| Categoría `Educacion` sin tilde (código, semillas y filas existentes) | — | «Educación» con tilde en todo el sistema: migración de datos (`UPDATE categorias`), semillas, taxonomía y tests (§3.4) |
| Isotipo K provisional e isotipo «A» del frontend | — | Isotipo definitivo (§2.1–2.2); assets K eliminados |
| Inter cargada, sin Space Grotesk | — | Sumar Space Grotesk (solo display) |
| Sin favicon | — | `assets/favicon.svg` + PNG (`favicon-32`, `favicon-512`, `apple-touch-icon`) en `luka_frontend/public/` |

**Alcance:** esta fase documenta; la aplicación de tokens al código se planifica aparte (tarea técnica con sus tests de UI). Prioridad sugerida: (1) tokens semánticos de color, (2) categorías, (3) gráficos, (4) logo/favicon, (5) tipografía display.

---

## 10. Decisiones de esta fase

| # | Decisión | Estado |
|---|---|---|
| D3.1 | Paleta navy + azul `#2563EB` + esmeralda `#0E9F6E`, semánticos verificados AA | ✅ Aprobado 2026-09-23 |
| D3.2 | Rojo prohibido para gastos; grafito para egreso | ✅ Aprobado 2026-09-23 |
| D3.3 | Símbolo nuevo para el isotipo (fluidez/diálogo/balance); K y A deprecados | ✅ Cumplido 2026-09-23 — isotipo definitivo en `public/` y `docs/marca/assets/` |
| D3.4 | Space Grotesk (display) + Inter (UI/datos, tabular) + JetBrains Mono | ✅ Aprobado 2026-09-23 |
| D3.5 | Design tokens versionados en `docs/marca/tokens/` como fuente de verdad | ✅ Aprobado 2026-09-23 |
| D3.6 | Categorías unificadas con tildes (display, código y datos) + color oficial en ambos temas | ✅ Aprobado — migración pendiente |

---

## 11. Anexo · Valores RGB

Conversión estándar de los HEX del sistema (sRGB 8-bit). Los semánticos que reutilizan primitivos no se repiten.

**Primitivos**

| Token | HEX | RGB |
|---|---|---|
| `navy-950` | `#06101F` | 6, 16, 31 |
| `navy-900` | `#0A1626` | 10, 22, 38 |
| `navy-800` | `#102138` | 16, 33, 56 |
| `navy-700` | `#17304D` | 23, 48, 77 |
| `navy-600` | `#1F4166` | 31, 65, 102 |
| `blue-700` | `#1D4ED8` | 29, 78, 216 |
| `blue-600` | `#2563EB` | 37, 99, 235 |
| `blue-500` | `#3B82F6` | 59, 130, 246 |
| `blue-400` | `#6EA8FF` | 110, 168, 255 |
| `blue-300` | `#A5C6FF` | 165, 198, 255 |
| `emerald-700` | `#047857` | 4, 120, 87 |
| `emerald-600` | `#0E9F6E` | 14, 159, 110 |
| `emerald-500` | `#10B981` | 16, 185, 129 |
| `emerald-400` | `#34D399` | 52, 211, 153 |
| `amber-700` | `#B45309` | 180, 83, 9 |
| `amber-500` | `#F59E0B` | 245, 158, 11 |
| `amber-400` | `#FBBF24` | 251, 191, 36 |
| `red-600` | `#DC2626` | 220, 38, 38 |
| `red-400` | `#F87171` | 248, 113, 113 |
| `graphite-700` | `#334155` | 51, 65, 85 |
| `graphite-500` | `#64748B` | 100, 116, 139 |
| `graphite-400` | `#94A3B8` | 148, 163, 184 |
| `graphite-300` | `#CBD5E1` | 203, 213, 225 |

**Semánticos propios (sin primitivo equivalente)**

| Token | HEX | RGB |
|---|---|---|
| `text-primary` (dark) | `#E8EFFA` | 232, 239, 250 |
| `text-secondary` (dark) | `#A9BCD6` | 169, 188, 214 |
| `text-muted` (dark) | `#8AA0C4` | 138, 160, 196 |
| `bg-base` (light) | `#F4F7FC` | 244, 247, 252 |
| `text-secondary` (light) | `#475569` | 71, 85, 105 |
| `text-muted` / `money-out` (light) | `#5B6B80` | 91, 107, 128 |

**Categorías**

| Categoría | HEX | RGB |
|---|---|---|
| Servicios (dark) | `#6EA8FF` | 110, 168, 255 |
| Comida (dark) | `#F97316` | 249, 115, 22 |
| Transporte (dark) | `#22D3EE` | 34, 211, 238 |
| Ocio (dark) | `#A78BFA` | 167, 139, 250 |
| Vivienda (dark) | `#818CF8` | 129, 140, 248 |
| Salud (dark) | `#2DD4BF` | 45, 212, 191 |
| Educación (dark) | `#A3E635` | 163, 230, 53 |
| Ropa (dark) | `#F472B6` | 244, 114, 182 |
| Ingresos (dark) | `#34D399` | 52, 211, 153 |
| Otros (ambos temas) | `#64748B` | 100, 116, 139 |
| Servicios (light) | `#2563EB` | 37, 99, 235 |
| Comida (light) | `#EA580C` | 234, 88, 12 |
| Transporte (light) | `#0891B2` | 8, 145, 178 |
| Ocio (light) | `#7C3AED` | 124, 58, 237 |
| Vivienda (light) | `#4F46E5` | 79, 70, 229 |
| Salud (light) | `#0D9488` | 13, 148, 136 |
| Educación (light) | `#4D7C0F` | 77, 124, 15 |
| Ropa (light) | `#DB2777` | 219, 39, 119 |
| Ingresos (light) | `#059669` | 5, 150, 105 |

---

## 12. Fuentes

- `luka_frontend/static/css/style.css`, `registro.css`, `admin_flows.css`, `app/templates/**`, `app/dashboard.py`
- `luka/app/services/movement_chart.py`, `luka/docs/movement-charts.md`, `luka/public/*`, `luka/testing/.streamlit/config.toml`
- Verificación de contraste: script de luminancia WCAG ejecutado 2026-09-23 (resultados en §3.3–3.4)
- Norman, D. *Emotional Design* (nivel visceral); Neumeier, M. *The Brand Gap* (originalidad/epidemias visuales).
