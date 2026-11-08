# Auditoría del agente — 2026-11-07

Se revisaron el cliente HTTP, los contratos de datos, las recetas del sello,
el parser de auditoría, la CLI, los ejemplos, la presentación y la documentación.
La revisión incluyó una segunda lectura independiente de los cambios.

El resultado mejora las comprobaciones locales y elimina garantías que el
repositorio no podía sostener. No certifica la exactitud del motor remoto.

## Fallos corregidos

| Problema | Cambio y comprobación |
|---|---|
| El cliente convertía respuestas anidadas a tipos declarados sin validarlas | Valida objetos, listas, tipos, rangos y estados de éxito antes de devolver datos |
| NaN, infinito, booleanos como números y claves JSON duplicadas podían entrar como datos | Rechaza valores no finitos, desbordamientos y JSON ambiguo; pruebas con entradas malformadas |
| Una respuesta de otro activo podía atribuirse a la consulta | Comprueba los IDs proporcionados y exige identidad para señales de batch disponibles |
| Contadores y disponibilidad del batch podían contradecir sus filas | Comprueba cantidades, duplicados y ausencia de señales en filas explícitamente indisponibles |
| Los importes podían perder precisión si se convirtieran a float | Conserva las cadenas decimales originales, valida con Decimal y prueba precisión exacta |
| Una versión desconocida podía obtener un sello verificado usando una receta anterior | Solo verifica algoritmos y versiones conocidos; versiones nuevas quedan sin comprobar |
| Entradas malformadas del sello podían verificarse o romper el verificador | Valida estructura, ocho campos cubiertos, números finitos y formato SHA-256 |
| Campos desconocidos de auditoría se presentaban como controlados por Python | Los muestra sin interpretación confirmada; las correcciones se atribuyen a la API |
| Faltaban datos y la pantalla inventaba neutralidad, ausencia de anomalía o confianza cero | Los valores ausentes se muestran como desconocidos o no disponibles |
| Un hash coincidente se confundía con exactitud de todo el análisis | La salida y el README especifican cobertura, exclusiones y ausencia de autenticación |
| Las fuentes aparecían como verificadas sin consultar sus contenidos | Se identifican como referencias reportadas por la API |
| Un sello incorrecto no hacía fallar la salida JSON y podía disparar alertas | JSON sale con código 1; watch descarta esa lectura para las alertas y conserva la anterior |
| El redondeo podía mostrar 1.00 aunque proximidad o evidencia fueran menores que 1 | Muestra <1.00 cuando el redondeo cruzaría ese límite |
| Fechas futuras o extremas podían aparentar frescura o causar desbordamiento | Señala reloj adelantado y trata fechas ilegibles como no disponibles; muestra fechas por activo |
| Texto de la API podía alterar estilos o simular mensajes en terminal | Escapa markup y limpia controles, incluidos caracteres bidireccionales |
| README y recursos visuales prometían verdad matemática no demostrada | Documentación abreviada y ajustada al alcance comprobado; pantalla regenerada del fixture |

Se agregó `--require-verified-seal` para exigir una receta compatible y un digest
coincidente. En una consulta normal o JSON, la ausencia de un sello verificable
sale con código 1. En watch, esa lectura no modifica las alertas. El modo
estricto comprueba el sello; no transforma el informe en evidencia verificada.

```bash
python agent.py coin bitcoin --require-verified-seal
python agent.py coin bitcoin --json --require-verified-seal
```

## Comprobaciones realizadas

- Python 3.14.0: **314 pruebas aprobadas** contra fixtures y HTTP simulado.
- mypy: sin errores en 31 archivos fuente.
- Ruff: sin errores.
- Las recetas publicadas reproducen los sellos históricos de Radar de las
  versiones 2.1.0, 2.2.0 y 2.4.0.
- Pruebas que cambian narrativa, confianza, ancho de bandas, fuentes y fechas
  demuestran que esos cambios pueden conservar un sello válido.

Comandos de verificación usados en Windows, con temporales dentro del proyecto:

```powershell
python -m pytest tests/ -q -p no:cacheprovider --basetemp .tmp/pytest-final
python -m mypy . --cache-dir .tmp/mypy-final
python -m ruff check . --no-cache
git diff --check
```

No se ejecutaron consultas en vivo ni se consumió una cuota de API. Los tests
locales no equivalen a una comprobación del servicio desplegado.

## Qué falta para comprobar los cálculos

Este repositorio no contiene la implementación que calcula Z-Score, Bollinger,
regímenes, confianza o filtros léxicos. Tampoco incluye las series completas
de precios que dieron lugar a cada respuesta. Los números recibidos siguen
siendo afirmaciones del servicio.

Para auditar esas fórmulas hacen falta el código de la versión desplegada, las
velas originales y sus timestamps, la definición de cada ventana y retorno,
las reglas de desviación estándar, umbrales y redondeo, y vectores de referencia
calculados de manera independiente. Sin ellos no se puede afirmar que el agente
calcule «perfecto» ni que detecte todas las alucinaciones.

El process seal cubre `algorithm_id`, `engine_version`, `z_score`,
`market_regime`, `sentiment`, `sentiment_override`, `filters_applied` y
`fields_overridden`. Excluye el texto, confianza, ancho de bandas, fuentes,
fechas y otros diagnósticos. Es un hash sin clave: quien cambia datos puede
recalcularlo. Verificarlo no demuestra que el pipeline haya ejecutado los
pasos que declara ni quién lo emitió.
