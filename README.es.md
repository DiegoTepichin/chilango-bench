# chilango-bench

**¿Tu LLM de verdad entiende el español de México?** Un benchmark reproducible de slang, cultura de la Ciudad de México, trámites y *albur*, con dataset abierto y un harness que corre contra modelos locales y por API.

[![CI](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Dataset: CC BY 4.0](https://img.shields.io/badge/dataset-CC%20BY%204.0-green.svg)](datasets/README.md)

[Read in English](README.md)

> **Estado:** v1.0. Los 168 ítems del dataset **todavía no han sido revisados** por una persona hablante nativa, así que los puntajes de abajo son preliminares. La revisión viene integrada: `chilango-bench review`.

## Por qué

Los benchmarks en español suelen ser traducciones del inglés o usan español neutro. No te dicen si un modelo sabe que *ahorita* puede significar "nunca", que *¡aguas!* es una advertencia, cuántos caracteres tiene la CURP o cómo tomar un *albur* sin ser ni mojigato ni vulgar. Si vas a poner un LLM frente a usuarios en México, eso es lo que importa.

## Resultados

Modelos abiertos pequeños, corridos localmente con Ollama 0.40.6 a temperatura 0 sobre los 157 ítems que se califican automáticamente (los de rúbrica necesitan un modelo juez y no se incluyen). Cada fila sale de un reporte versionado en [`results/`](results/).

| Lugar | Modelo | Precisión (IC 95%) | Slang | Cultura | Trámites | Albur | Sin resolver | Ítems |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 61.8% (54%-69%) | 63.5% | 70.7% | 48.8% | 65.2% | 6 | 157 |
| 2 | `qwen2.5:1.5b` | 55.4% (48%-63%) | 42.3% | 51.2% | 65.8% | 73.9% | 0 | 157 |
| 3 | `gemma3:1b` | 40.1% (32%-48%) | 26.9% | 43.9% | 46.3% | 52.2% | 0 | 157 |
| 4 | `baseline-always-B` | 21.7% (15%-29%) | 23.1% | 19.5% | 21.9% | 21.7% | 0 | 157 |

Lo que muestran los reportes:

- **El slang es la categoría más difícil para modelos pequeños.** gemma3:1b está cerca del azar; qwen2.5:1.5b sabe más de trámites que de slang.
- **Negarse a responder también es un error.** Las seis respuestas sin resolver de llama3.2:3b son negativas: no quiso decir qué significa *"¡Ya se la saben!"* en un camión, ni explicar qué es el albur, ni contestar sobre la reforma laboral de 2023.
- **La memoria exacta es débil.** En los 23 ítems de respuesta corta el mejor modelo saca 43%. Al preguntarle qué significa RFC, llama3.2:3b respondió "Request for Comments"; al preguntar qué institución emite la CURP (RENAPO), los modelos inventaron siglas como "SENASAL" y "SEGUI".
- Los intervalos por categoría son amplios (unos ±15 puntos con ~40 ítems); las diferencias dentro de ellos todavía no significan nada.

Repetir la corrida de un modelo puede cambiar una o dos respuestas incluso a temperatura 0; llama3.2:3b cambió un ítem entre dos corridas.

## Palabras fantasma

¿Los modelos admiten que no conocen una palabra o se inventan el significado? [`datasets/phantom/`](datasets/phantom/) pregunta por 18 palabras inventadas y 12 palabras reales de control. Rechazar todo da un balanceado de 50%, así que un modelo no gana diciendo "no sé" siempre.

Modelos abiertos pequeños, ejecutados localmente con Ollama 0.40.13, temperatura 0 y 200 tokens de salida:

| Rank | Model | Balanced | Honest | Hedged | Fabricated (95% CI) | False refusal |
|---:|:---|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 63.9% | 27.8% | 0.0% | 72.2% (50%-89%) | 0.0% |
| 2 | `qwen2.5:1.5b` | 50.0% | 0.0% | 5.6% | 94.4% (83%-100%) | 0.0% |
| 3 | `gemma3:1b` | 50.0% | 0.0% | 5.6% | 94.4% (83%-100%) | 0.0% |

*Honest* es la proporción de palabras inventadas que el modelo dijo no conocer; *hedged*, las que dudó pero adivinó igual; *fabricated*, las que definió sin duda alguna, y *false refusal*, las palabras reales que dijo no conocer. Contestar una palabra real solo significa que no la rechazó: la definición no se califica.

Con 18 palabras inventadas los intervalos son amplios, y son tres modelos pequeños, así que esto no dice nada de modelos mayores. Palabras y respuestas son preliminares hasta revisarse.

```bash
uv run chilango-bench eval -d datasets/phantom/phantom-slang.jsonl -m qwen2.5:1.5b -p ollama --max-tokens 200 -o runs/phantom.json
```

## Qué incluye

168 ítems originales ([ficha del dataset](datasets/README.md)), CC BY 4.0:

| Categoría | Ítems | Ejemplos |
|---|---|---|
| Slang | 55 | *chido*, *ahorita*, *no hay pedo*, *hacer la vaca*, *¿a poco?* |
| Cultura | 44 | Metro, *pambazo*, posadas, los sismos del 19 de septiembre, *viene viene* |
| Trámites | 44 | CURP, RFC, SAT, INE, IMSS, aguinaldo, Hoy No Circula |
| Albur | 25 | Reconocer el juego de doble sentido y responder de forma adecuada, sin contenido explícito |

134 de opción múltiple, 23 de respuesta exacta y 11 de rúbrica. Las respuestas correctas están balanceadas y la opción correcta es la más larga solo en 25% de los ítems, así que ni "siempre B" ni "elige la más larga" superan al azar. El archivo lleva un GUID *canary* para filtrarlo de corpus de entrenamiento.

## Cómo se califica

- **Opción múltiple:** solo cuenta una respuesta explícita (una letra sola, `B) ...`, "la respuesta es C" o el texto completo de una opción). Una letra suelta dentro de una oración nunca cuenta, porque *a*, *e*, *o* y *y* son palabras. Lo demás queda *sin resolver* y cuenta como error.
- **Respuesta exacta:** comparación sin acentos, mayúsculas ni puntuación contra las respuestas aceptadas.
- **Rúbrica:** un modelo juez califica de 1 a 5; si su respuesta no se puede leer, se marca error, nunca se inventa un puntaje.
- **Los puntajes** traen intervalos bootstrap al 95%. Los reportes fijan el SHA-256 del dataset, la plantilla del prompt y la configuración; el leaderboard nunca compara corridas que no son comparables.

Detalles en [docs/METHODOLOGY.md](docs/METHODOLOGY.md) (en inglés).

## Inicio rápido

Requiere Python 3.11+ y [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/DiegoTepichin/chilango-bench.git
cd chilango-bench
uv sync
uv run chilango-bench validate datasets/v1/chilango-bench.jsonl
```

### Un modelo local con Ollama

```bash
ollama pull qwen2.5:1.5b
uv run chilango-bench eval -d datasets/v1/chilango-bench.jsonl -m qwen2.5:1.5b -p ollama -o runs/qwen.json
```

### Cualquier API compatible con OpenAI

```bash
export OPENAI_API_KEY=...            # ver .env.example
uv run chilango-bench eval -d datasets/v1/chilango-bench.jsonl -m gpt-4o-mini -p openai -o runs/gpt-4o-mini.json
# otros proveedores: agrega --base-url https://api.groq.com/openai/v1 (o cualquier endpoint compatible)
```

Agrega `--judge <modelo>` para calificar los ítems de rúbrica, `--limit 10` para una prueba rápida y `--accepted-only` para usar solo ítems revisados.

### Generar un leaderboard

```bash
uv run chilango-bench leaderboard -r runs
```

## Contribuir

Lo más valioso son las **revisiones** y los **ítems nuevos**:

```bash
uv run chilango-bench review datasets/v1/chilango-bench.jsonl --reviewer tu-usuario-de-github
```

muestra cada ítem sin revisar con su respuesta y explicación, y guarda tu decisión en el archivo. Ver [CONTRIBUTING.md](CONTRIBUTING.md) y la [ficha del dataset](datasets/README.md). También son bienvenidos reportes de otros modelos: abre un PR con el JSON en `results/`.

## Desarrollo

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run pytest          # sin red ni API keys
```

## Licencia

Código: [MIT](LICENSE). Dataset: [CC BY 4.0](datasets/README.md). © Diego Tepichin
