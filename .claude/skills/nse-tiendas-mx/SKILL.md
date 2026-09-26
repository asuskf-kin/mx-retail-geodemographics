---
name: nse-tiendas-mx
description: >
  Replica para cualquier ciudad o zona metropolitana de México el pipeline de perfil socioeconómico
  de hogares (tamaño, edad del menor, edad del jefe, NSE AMAI 2024) por AGEB y por área de
  influencia de tiendas DENUE (supermercados 462111, minisupers 462112, abarrotes 461110), separando
  canal Moderno y Tradicional. Usar cuando pidan "haz lo mismo para Monterrey/Guadalajara/…",
  "NSE por AGEB", "hogares alrededor de las tiendas", "DENUE 462111 462112", "perfil demográfico de
  tiendas", "índice Nielsen por tienda", o actualizar el análisis de Mérida con datos nuevos.
argument-hint: "[ciudad o zona metropolitana]"
---

# Replicar NSE × tiendas en otra ciudad

El pipeline ya existe y funciona en este repo. **No lo reescribas**: se reutiliza cambiando solo `src/config.py`.
Primero lee `.claude/CLAUDE.md`. Los detalles técnicos (códigos del Censo, tabla AMAI, URLs, trampas) están en
[reference.md](reference.md).

## Pasos

1. **Identificar el estado y la zona.** Obtén la clave INEGI de entidad (`ENT`) y los municipios de la zona
   metropolitana según la delimitación SEDATU-CONAPO-INEGI *Metrópolis de México 2020*.
   Confirma la lista con el usuario si hay duda, porque cambia todo el universo.
2. **Editar `src/config.py`**, bloque "Estado / ciudad":
   - `ENT`, `NOM_ENT`, `ABREV_MICRO` (tabla en reference.md) y `MG_SLUG` (nombre del zip del Marco Geoestadístico).
   - `ZM_NOMBRE` y `ZM_MUNICIPIOS` (`{clave_mun_3dig: nombre}`).
   - `REGION_NIELSEN` (tabla en reference.md).
   - `ENIGH_ESTADOS`: el estado más sus vecinos de la misma región. La ENIGH es chica por estado y conviene tener 5k+ hogares.
3. **Verificar las URLs antes de correr.** Haz un `HEAD` o un GET pequeño a cada `C.URLS`. Si INEGI devuelve
   `text/html`, el nombre del archivo está mal: `descargar()` lanza un error explícito en ese caso.
   El `MG_SLUG` es el que más falla (acentos y espacios: "ciudad_de_mexico", "nuevo_leon", "michoacan_de_ocampo").
4. **Renombrar si se quiere** (opcional). Los notebooks se llaman `*_merida` pero no dependen del nombre.
   Si cambias el nombre, ajusta también los nombres de los xlsx de salida.
5. **Regenerar y correr** 01 → 02 → 03 con nbclient (el comando está en CLAUDE.md).
6. **Validar** antes de entregar:
   - Tabla "Validacion ENIGH": diferencia ≤ ~2 pp por nivel. Si es mayor, amplía `ENIGH_ESTADOS`.
   - Hoja "Ajuste microsim": diferencias ≤ ~5% en `autom`, `inter`, `pc` y `p18pb`.
     `cua1` puede salir peor porque tiene muchas celdas confidenciales.
   - "Validacion ZM": la suma de AGEB debe parecerse a la estimación directa de la muestra (±2–3 pp).
   - Notebook 02: revisa la celda "cadenas detectadas dentro de abarrotes" para detectar falsos positivos del regex.
     **Agrega las cadenas locales** de la ciudad (en Mérida fueron Dunosusa, Willys, Aki, Go Mart, Farahon, Waldo's…).
     Para encontrarlas, lista los `nom_estab` más repetidos que quedaron como "Independiente".
7. **Entregar**: los xlsx de `outputs/` y un resumen con los supuestos (sección "Supuestos" de reference.md).

## Decisiones que NO debes asumir; pregúntalas
- La lista de municipios de la ZM, si el usuario solo nombra la ciudad.
- La referencia del índice (ZM o estado).
- Si el canal Tradicional incluye abarrotes 461110 (en Mérida sí se incluyeron).
- Cómo clasificar franquicias de tiendas de barrio (Six, Modelorama, Tiendas Extra): en Mérida, Six quedó como Tradicional.
- Radios de influencia: `RADIOS_M` en el notebook 03 (default 500 m y 1 km).
