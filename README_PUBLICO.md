# Porra Mundial 2026 - versión pública y de solo lectura

Esta versión de la app:
- usa una fuente de datos fija (Google Sheets / Drive)
- elimina controles de edición para visitantes
- mejora el diseño visual
- muestra ranking, podium y tabla de puntos por equipo

## Cambio principal
El enlace de datos está fijado dentro de `app.py` en la constante `SOURCE_URL`.
Los visitantes no pueden cambiarlo desde la interfaz.

## Cómo actualizar la web
Solo tienes que actualizar la hoja origen. La app volverá a leer los datos automáticamente.
