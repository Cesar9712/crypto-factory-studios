# CryptoQuest RPG — Sistema Visual V31 “Modo Dios”

## Alcance y frontera de seguridad

V31 es una reconstrucción exclusivamente visual. No modifica mecánicas, estadísticas, balance, energía, progreso, inventario, combate, pagos, persistencia, backend ni APIs. La dirección artística cubre el juego web móvil completo y mantiene las cuatro clases del lanzamiento: Guerrero, Mago, Arquero y Asesino. Nigromante queda fuera de esta versión.

Los recursos se producen en 4K/8K como fuente maestra y se exportan al runtime en tamaños móviles optimizados. No se deben cargar texturas 8K directamente en el navegador móvil.

## Dirección artística maestra

- Fantasía oscura premium: obsidiana tallada, carbón, hierro ennegrecido, bronce y oro envejecido.
- Profundidad mediante cuatro capas: fondo atmosférico, superficie, bisel metálico y contenido.
- Luz principal cálida y tenue desde arriba; luz ambiental fría, nunca saturada.
- Contraste controlado: el oro identifica jerarquía y selección; no se usa como relleno general.
- Superficies densas, táctiles y legibles. Ningún panel debe parecer una tarjeta web genérica.
- Ornamentación funcional: runas, remaches y esquinas guían la mirada sin cubrir texto ni controles.

## Tokens visuales

| Función | Valor maestro |
|---|---|
| Vacío | `#020202` |
| Obsidiana | `#0A0908` |
| Carbón elevado | `#191611` |
| Bronce profundo | `#3F2B17` |
| Bronce | `#7C572D` |
| Oro | `#D2A457` |
| Oro iluminado | `#F4DFAD` |
| Texto | `#F1E9DA` |
| Texto secundario | `#A79B87` |
| Vida | `#A61924` → `#E04A50` |
| Maná | `#2458AE` → `#66A0FF` |
| Arcano/EXP | `#7E3FB0` |
| Éxito | `#5DA36E` |
| Peligro | `#D55A59` |

Tipografía: Cinzel para títulos, nombres, botones y cifras heroicas; Inter para lectura, descripciones y datos densos. Títulos en mayúsculas moderadas, tracking amplio; textos corridos sin mayúsculas forzadas.

## Rediseño por sección

### 1. Inicio y HUD

- Cabecera compacta con avatar en medallón, nivel visible, identidad y recursos sin solapamientos.
- Recursos en celdas grabadas con aura cromática diferenciada.
- Escenario del héroe convertido en cámara cinematográfica con viñeta, profundidad, runas y luz de suelo.
- Barras HP/MP/EXP con volumen, brillo contenido y lectura numérica estable.
- Misión principal tratada como pergamino oscuro quemado, con recompensas inmediatamente visibles.
- CTA de aventura con bisel de bronce y respuesta táctil.

### 2. Navegación superior e inferior

- Dock inferior de juego móvil con estado activo iluminado y línea de energía dorada.
- Iconos normalizados dentro de medallones; tamaño y contraste idénticos en todas las pestañas.
- Objetivos táctiles mínimos de 44 px, estados `focus-visible`, pulsado y deshabilitado.
- Safe areas para Android/iOS y densidad ajustada a 360×800, 390×844 y 412×915.

### 3. Personaje, equipo, sets y estadísticas

- Retrato sobre cámara de obsidiana con iluminación cálida inferior.
- Slots biselados por rareza sin depender solo del color: borde, aura y contraste cambian juntos.
- Estadísticas en filas metálicas compactas con numeración tabular.
- Sets activos con resplandor bajo y efectos únicos separados visualmente de estadísticas normales.

### 4. Inventario y detalle de objetos

- Tarjetas de dos columnas con cabecera, arte, metadatos y pie claramente separados.
- Iconos de objeto sobre pedestal cromático de rareza.
- Filtros horizontales compactos y estados activos coherentes con la navegación.
- Hoja de detalle inferior con material vinculado a rareza, comparación positiva/negativa y botones seguros.

### 5. Talentos y habilidades

- Bosque de talentos en tres ramas con conectores metálicos y progreso legible.
- Nodo disponible: pulso dorado discreto. Aprendido: brillo verde contenido. Bloqueado: carbón desaturado.
- Capstones con doble borde y aura mayor.
- Habilidades de combate, clase y efectos comparten la misma gramática de iconos.

### 6. Campaña, mundo, misiones y mazmorras

- Camino vertical con línea de bronce y nodos con estado completado, disponible, bloqueado o jefe.
- Banners de zona con relieve, icono de bioma y lectura clara de nivel/recompensa.
- Jefes y némesis usan hierro teñido de sangre; eventos usan bronce/ámbar.
- Mazmorras, torre, arena y endgame reciben cámaras atmosféricas propias sin cambiar contenido.

### 7. Combate

- Fondo de arena en capas con viñeta, cuadrícula rúnica mínima y suelo oscuro.
- Nombre, vida e intención del enemigo con jerarquía inmediata.
- Aura del enemigo animada con opacidad/transform, sin canvas ni WebGL pesado.
- Botones de ataque, habilidades y utilidades comparten bisel, iconografía y feedback táctil.
- Telegrafías de jefe con pulso rojo; log de combate legible y contenido.

### 8. Bastión y pantallas secundarias

- Bastión con núcleo luminoso y servicios presentados como placas de herrería.
- Misiones, builds, compañeros, colecciones, facciones, crafting, contratos, expediciones, bestiario, logros y buzón usan la misma superficie, espaciado y jerarquía.
- Estados vacíos tratados como placas grabadas, no como cajas web.

### 9. Creación, carga, resultados y modales

- Pantalla de carga con sello CQ animado, círculos rúnicos y fondo de obsidiana.
- Selección de clase con tarjetas de cámara, borde activo dorado y silueta central.
- Modales con desenfoque controlado, panel forjado y acciones consistentes.
- Victoria usa oro cálido; derrota, hierro ensangrentado. Botín conserva color de rareza.

### 10. VFX, movimiento y optimización

- Partículas ambientales ligeras inyectadas como 12 elementos sin interacción.
- Entradas de panel de 280 ms; presión táctil de 140 ms; barras con transición de 320 ms.
- Brillos en `opacity` y `transform` para evitar repaints costosos.
- `prefers-reduced-motion` desactiva partículas y animaciones decorativas.
- Sin overlays WebGL, video de fondo ni texturas gigantes en el runtime.

## Prompts maestros de arte 4K/8K

Todos los prompts deben añadir: `no text, no watermark, no logo, no UI mockup, isolated asset when requested, production game asset, consistent CryptoQuest RPG visual language`.

### Kit completo de interfaz

```text
Create an 8K dark-fantasy mobile RPG UI asset kit for CryptoQuest RPG. Forged black obsidian, charcoal iron, aged bronze, restrained antique gold, micro-scratches, engraved runes, beveled metallic relief, deep shadows, soft warm top light, cold ambient rim light, premium AAA game production quality. Include modular HUD frames, character header, resource cells, HP/MP/EXP bar frames, quest panel, inventory frame, talent frame, modal frame, bottom navigation dock, tactile buttons, corner ornaments, dividers and empty states. Orthographic front view, transparent background, modular nine-slice construction, consistent material scale, no text, no icons inside frames, no watermark, 8192x8192 source sheet.
```

### Marcos y paneles nine-slice

```text
8K modular nine-slice frame sheet for a premium dark fantasy mobile RPG, carved obsidian center, blackened iron bevel, aged bronze corners, subtle antique-gold inner line, tiny runic engraving, controlled wear and micro-scratches, symmetrical geometry, clean transparent background, front orthographic view, thin and dense mobile proportions, no text, no symbols, no watermark.
```

### HUD de recursos

```text
4K mobile RPG resource HUD components, three matching forged-obsidian cells with aged bronze separators, subtle internal glow wells for crimson energy crystal, embossed gold coin and violet premium gem, tactile metallic depth, soft top lighting, transparent background, isolated modular components, no numbers, no labels, no watermark.
```

### Barras HP/MP/EXP

```text
4K dark fantasy RPG status bar asset set, narrow cinematic mobile proportions, black obsidian tracks, blackened iron and aged bronze frame, liquid crimson health, deep sapphire mana, restrained violet experience energy, glass highlight only on upper edge, readable at small scale, transparent background, empty and full variants, no text, no watermark.
```

### Iconografía universal

```text
8K sprite sheet of 64 premium dark fantasy RPG icons, unified silhouette language, centered object, three-quarter view, forged metal and magical materials, deep charcoal background removed, antique gold edge light, crisp readable silhouette at 48 pixels, consistent camera and lighting, transparent background, equal padding, no frames, no text, no watermark. Categories: attributes, currencies, navigation, crafting, quests, achievements, bestiary, factions and utility.
```

### Iconos de habilidades — Guerrero

```text
8K sprite sheet, 24 Warrior skill icons for CryptoQuest RPG, brutal forged steel, cracked shields, heavy sword arcs, blood-red impact energy, dust and sparks, dark fantasy AAA style, readable silhouettes at 64 pixels, consistent three-quarter camera, antique-gold rim light, transparent background, no frames, no text, no watermark.
```

### Iconos de habilidades — Mago

```text
8K sprite sheet, 24 Mage skill icons for CryptoQuest RPG, arcane sigils, blue flame, lightning, frost, deep violet mana, controlled magical particles, dark fantasy AAA style, readable silhouettes at 64 pixels, consistent lighting and scale, transparent background, no frames, no text, no watermark.
```

### Iconos de habilidades — Arquero

```text
8K sprite sheet, 24 Archer skill icons for CryptoQuest RPG, recurved bows, spectral arrows, piercing volleys, traps, wind trails, emerald and amber accents, dark fantasy AAA style, readable silhouettes at 64 pixels, consistent lighting and scale, transparent background, no frames, no text, no watermark.
```

### Iconos de habilidades — Asesino

```text
8K sprite sheet, 24 Assassin skill icons for CryptoQuest RPG, twin daggers, shadow steps, poison, bleeding marks, smoke, violet-black energy and restrained crimson accents, dark fantasy AAA style, readable silhouettes at 64 pixels, consistent lighting and scale, transparent background, no frames, no text, no watermark.
```

### Objetos, equipo y rarezas

```text
8K RPG inventory icon atlas, 80 isolated dark fantasy items: swords, daggers, bows, staves, shields, helmets, armor, gloves, boots, rings, amulets, relics, potions and crafting materials. Consistent three-quarter camera, centered silhouette, physically plausible metal/leather/wood/gem materials, soft warm key light and cold rim light, transparent background, equal padding. Produce neutral lighting masters suitable for common gray, uncommon green, rare blue, epic violet, legendary gold and mythic crimson rarity glows. No frames, no text, no watermark.
```

### Héroes de las cuatro clases

```text
8K full-body static class hero key art for CryptoQuest RPG: [WARRIOR / MAGE / ARCHER / ASSASSIN]. Premium dark fantasy realism, black obsidian and aged-bronze equipment language, battle-worn materials, restrained class-color magic, confident neutral standing pose, no animation pose requirement, centered full silhouette, cinematic warm top light and cold rim light, dark transparent or separable background, strong readability on a mobile hero stage, no text, no logo, no watermark.
```

Generar una imagen separada por clase, manteniendo lente, cámara, escala, contraste y dirección de luz idénticos.

### Bastión

```text
8K vertical mobile background, Bastion of Aether for CryptoQuest RPG, monumental black-stone citadel interior, ancient bronze machinery, distant forge light, worn obsidian floor, suspended runes, soft fog layers, dark fantasy cinematic atmosphere, center kept readable for UI, darker edges for overlays, no characters, no text, no watermark, 9:16 composition.
```

### Mapa y campaña

```text
8K vertical dark fantasy campaign map background, weathered black parchment fused with carved obsidian, aged bronze route ornaments, mountains, ruins, crypts and corrupted forests drawn with premium etched detail, central route area uncluttered, dark edges, subtle ember glow, no labels, no icons, no text, no watermark, 9:16.
```

### Arena de combate

```text
8K vertical mobile battle arena background for CryptoQuest RPG, ruined obsidian cathedral courtyard, cracked stone floor, bronze braziers, distant arches, controlled fog, subtle runic geometry, cinematic depth, center stage reserved for enemy silhouette, lower region dark for combat HUD, no characters, no UI, no text, no watermark, 9:16.
```

### Mazmorra y jefe

```text
8K vertical dark fantasy boss chamber, colossal blackened-iron gate, obsidian pillars, restrained blood-red fissures, ancient bronze seals, volumetric fog, deep cinematic shadows, central boss stage empty, mobile 9:16 composition, no creature, no UI, no text, no watermark.
```

### Pantallas de carga

```text
8K vertical loading-screen artwork for CryptoQuest RPG, solitary [WARRIOR / MAGE / ARCHER / ASSASSIN] overlooking the Bastion of Aether, premium dark fantasy cinematic composition, obsidian architecture, aged bronze highlights, deep charcoal atmosphere, soft particles, lower quarter kept dark and quiet for progress indicator, no text, no logo, no watermark, 9:16.
```

### Atlas VFX

```text
8K transparent VFX sprite atlas for a dark fantasy mobile RPG: embers, gold dust motes, smoke wisps, blood impact, blue mana sparks, violet arcane pulse, green poison cloud, frost shards, lightning arcs, shield flash and loot rarity bursts. Physically coherent lighting, restrained bloom, isolated effects, even cell spacing, black-free alpha, no text, no watermark.
```

## Variantes opcionales

1. **Obsidiana Forjada** — predeterminada. Bronce y oro envejecido; equilibrada para todo el juego.
2. **Hierro de Sangre** — solo jefes, derrota, némesis y alertas. Hierro oscuro, rojo profundo y humo.
3. **Ruina Esmeralda** — bosques, veneno y facciones antiguas. Obsidiana musgosa, bronce verdoso y luz esmeralda tenue.

Las variantes cambian acentos y atmósfera, nunca geometría, espaciado, jerarquía, tipografía ni tamaños de interacción.

## Reglas obligatorias de coherencia

1. Un mismo componente conserva forma, padding, borde y comportamiento en todas las pantallas.
2. Oro significa selección, progreso importante o acción primaria; no decoración indiscriminada.
3. Rojo significa vida, daño, peligro o jefe. Azul significa maná. Violeta significa arcano/EXP/premium.
4. Cada icono usa una silueta central, el mismo ángulo de cámara y un margen interno mínimo del 12%.
5. Ningún texto debe integrarse dentro de imágenes generadas.
6. Todos los controles táctiles deben medir al menos 44×44 px cuando la estructura existente lo permita.
7. La animación nunca debe retrasar una acción ni ocultar información funcional.
8. Máximo un brillo dominante por componente y dos fuentes de luz por escena.
9. Sombras externas dan elevación; sombras internas dan profundidad. No mezclar ambas sin jerarquía.
10. Validar siempre 360×800, 390×844 y 412×915, modo reducido de movimiento y textos largos.

## Exportación y rendimiento

- Fuentes maestras: PNG/TIFF 4096–8192 px, perfil sRGB.
- Runtime: WebP/AVIF; iconos 128–256 px, fondos 1080×1920 o 1440×2560, marcos nine-slice 512–1024 px.
- Atlases separados por función para evitar descargas innecesarias.
- Mantener transparencia limpia, sin halos negros.
- Presupuesto recomendado por pantalla: fondo ≤ 500 KB, atlas visible ≤ 600 KB, VFX visible ≤ 250 KB.
- Comprobar contraste, recorte, safe areas y nitidez a escala 1× antes de aprobar un recurso.


