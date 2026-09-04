# Reactivar los juegos preservados de Crypto Factory Studios

## Estado actual

CryptoQuest RPG y Crypto Factory Game están **preservados pero temporalmente desactivados y ocultos**. No se eliminaron carpetas, assets, datos, tablas, productos, historial ni lógica de juego.

La fuente de verdad es la tabla `platform_feature_flags` y los controles del panel de administración de Prompt Factory.

Flags actuales:

- `cryptoquest_enabled = false`
- `crypto_factory_game_enabled = false`

Mientras una flag está en `false`, el Worker público devuelve 404 + `noindex` para las rutas específicas del juego y elimina esos títulos/productos de los catálogos públicos.

## Reactivación desde Admin

1. Entrar con una cuenta `admin` o `platform_owner`.
2. Abrir `/prompt-factory/admin`.
3. En **Feature flags de plataforma**, cambiar a `ON` el juego deseado.
4. El edge vuelve a consultar las flags automáticamente. El caché de flags dura como máximo unos segundos.
5. Verificar primero las rutas públicas antes de volver a promocionar el juego.

También puede utilizarse la API administrativa:

- `PUT /api/v1/admin/platform/features/cryptoquest_enabled`
- `PUT /api/v1/admin/platform/features/crypto_factory_game_enabled`

Body: `{ "enabled": true }`.

## Workflows de CryptoQuest congelados explícitamente

Mientras CryptoQuest está oculto, estos workflows están configurados como `workflow_dispatch` únicamente para que CFS y Prompt Factory no dependan del juego:

- `.github/workflows/cryptoquest-v19-production.yml`
- `.github/workflows/cryptoquest-v20-production.yml`
- `.github/workflows/cryptoquest-production.yml`
- `.github/workflows/cryptoquest-production-smoke.yml`

Sus jobs se conservaron. Para restaurar automatización, recuperar únicamente sus bloques `on:` anteriores desde el historial Git y volver a habilitar los triggers deseados después de poner `cryptoquest_enabled=true`.

Los demás workflows históricos de CryptoQuest permanecen preservados y están limitados a cambios en archivos del juego o ejecución manual. No modificar la carpeta congelada mientras el juego siga desactivado.

## Recursos preservados

No requieren restauración:

- `frontend/games/cryptoquest/**`
- capas V19/V20/V21/V31 y datos empaquetados
- APIs y sistemas de save/build/publicación existentes
- registros de `games`, `game_builds`, `game_saves`
- productos y entitlements de Battle Pass
- almacenamiento y datos históricos
- commits y branches
- analítica histórica

Crypto Factory Game se trata igual: sus registros/recursos permanecen almacenados aunque el edge no lo exponga públicamente.

## Checklist antes de volver a activar

1. Confirmar que CFS QA y PostgreSQL están verdes.
2. Activar **un solo juego a la vez**.
3. Verificar `/api/v1/platform/features`.
4. Ejecutar manualmente el workflow de producción correspondiente.
5. Verificar rutas, móvil, auth, save/load y pagos específicos del juego.
6. Restaurar triggers automáticos solo cuando el smoke manual pase.
7. Reincorporar enlaces de navegación y SEO en un cambio separado.
8. Ejecutar Cloudflare deploy y production smoke de CFS.

## Rollback rápido

Si una reactivación causa cualquier regresión, volver la flag a `OFF`. El Worker volverá a ocultar el juego sin borrar ni migrar sus datos.
