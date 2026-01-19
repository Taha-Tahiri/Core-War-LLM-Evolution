# Digital Red Queen - Core War LLM Evolution

A Python implementation inspired by ["Digital Red Queen: Adversarial Program Evolution in Core War with LLMs"](https://pub.sakana.ai/drq/) by Sakana AI.

## Overview

This project implements a self-play evolutionary algorithm that uses Large Language Models (LLMs) to evolve "warriors" - assembly-like programs that compete for control of a virtual machine in the classic programming game **Core War**.

### What is Core War?

Core War is a programming game where small assembly programs ("warriors") written in **Redcode** compete in a shared memory space. Warriors try to:
- Survive as long as possible
- Crash opponent programs by overwriting their code
- Replicate themselves to increase survival chances

### What is Digital Red Queen (DRQ)?

DRQ is a self-play algorithm that:
1. Starts with an initial warrior
2. Uses an LLM to evolve a new warrior that defeats the previous one
3. In each subsequent round, evolves a warrior to defeat ALL previous champions
4. This creates "Red Queen dynamics" - continuous adaptation pressure

## Features

- **Multiple LLM Support**: Google Gemini, OpenAI (GPT-4), Anthropic (Claude), and local models via Ollama
- **MAP-Elites Algorithm**: Preserves behavioral diversity during evolution
- **Complete Core War Simulator**: Full Redcode-94 implementation with threading support
- **Visualization Tools**: Battle replays, fitness curves, and behavioral analysis
- **Configurable Experiments**: Adjust history length, generations, population size

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### Step 1: Add your API key to `config.env`

Open the `config.env` file in the project folder and add your API key:

```bash
# For Google Gemini (recommended)
GEMINI_API_KEY=your-gemini-api-key-here

# Or for OpenAI
OPENAI_API_KEY=your-openai-api-key-here

# Or for Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

> **Note**: Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Step 2: Run the experiment

```bash
python run_experiment.py --llm gemini --rounds 5
```

## Quick Start

### Demo (no API key needed)

```bash
python run_experiment.py --demo
```

### Run Tournament Between Example Warriors

```bash
python run_experiment.py --tournament ./warriors
```

### Run DRQ Evolution with Gemini

```bash
# Quick run (5 rounds, ~10 min)
python run_experiment.py --llm gemini --model gemini-1.5-flash --rounds 5

# Full run (10 rounds, ~30 min)
python run_experiment.py --llm gemini --model gemini-1.5-pro --rounds 10

# Custom settings
python run_experiment.py --llm gemini --rounds 10 --generations 50
```

### Python API

```python
from drq import DigitalRedQueen, DRQConfig
from llm_interface import GeminiProvider

# Initialize with Gemini
llm = GeminiProvider(model="gemini-1.5-flash")

# Configure the experiment
config = DRQConfig(
    num_rounds=10,
    generations_per_round=50,
    initial_population_size=50,
)

# Create DRQ instance and run
drq = DigitalRedQueen(llm, config)
champions = drq.run()

# Analyze results
print(f"Evolved {len(champions)} champions")
```

## Supported LLM Providers

| Provider | Models | API Key Variable |
|----------|--------|------------------|
| **Gemini** | `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-pro` | `GEMINI_API_KEY` |
| **OpenAI** | `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo` | `OPENAI_API_KEY` |
| **Anthropic** | `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku` | `ANTHROPIC_API_KEY` |
| **Ollama** | `llama3`, `codellama`, `mistral` | (local, no key needed) |

### Compare Multiple LLMs

```bash
python run_experiment.py --compare --llms gemini:gemini-1.5-flash,openai:gpt-4 --rounds 5
```

## Project Structure

```
cor wars/
├── config.env              # Your API keys (not committed to git)
├── config.env.example      # Template for API keys
├── requirements.txt        # Python dependencies
├── run_experiment.py       # CLI experiment runner
├── drq.py                  # Main DRQ algorithm
├── visualize.py            # Visualization tools
├── corewar/                # Core War simulator
│   ├── redcode.py          # Redcode parser & instruction set
│   ├── mars.py             # MARS virtual machine
│   └── battle.py           # Battle simulation
├── evolution/              # Evolution algorithms
│   ├── map_elites.py       # Quality-diversity algorithm
│   └── fitness.py          # Fitness evaluation
├── llm_interface/          # LLM providers
│   ├── gemini_provider.py  # Google Gemini
│   ├── openai_provider.py  # OpenAI GPT
│   ├── anthropic_provider.py # Anthropic Claude
│   └── ollama_provider.py  # Local models
└── warriors/               # Example warriors
    ├── imp.red             # Simple self-copying warrior
    ├── dwarf.red           # Classic bomber
    ├── mice.red            # Self-replicator
    ├── scanner.red         # Enemy scanner
    ├── vampire.red         # Trap planter
    └── replicator.red      # Multi-threaded paper
```

## How DRQ Works

```
Round 0: Start with seed warriors (Imp, Dwarf)
    │
    ▼
Round 1: Use LLM + MAP-Elites to evolve warrior that beats Round 0 champions
    │
    ▼
Round 2: Evolve warrior that beats ALL previous champions (Round 0 + 1)
    │
    ▼
Round N: Each new champion must defeat the entire history
    │
    ▼
Result: Warriors become increasingly general and robust
```

## Redcode Reference

| Opcode | Description |
|--------|-------------|
| `DAT` | Data (kills process if executed) |
| `MOV` | Move (copy data) |
| `ADD` | Add |
| `SUB` | Subtract |
| `JMP` | Jump |
| `JMZ` | Jump if zero |
| `JMN` | Jump if not zero |
| `DJN` | Decrement and jump if not zero |
| `SPL` | Split (spawn new thread) |
| `CMP`/`SEQ` | Compare/Skip if equal |
| `SNE` | Skip if not equal |
| `SLT` | Skip if less than |
| `NOP` | No operation |

## Output

Results are saved to `./drq_output/run_YYYYMMDD_HHMMSS/`:
- `champions/` - Evolved warrior source code
- `round_XXX/champion.red` - Champion from each round
- `round_XXX/metrics.json` - Fitness and behavioral metrics
- `summary.json` - Experiment summary
- `fitness_curves.png` - Visualization of evolution

## References

- [Digital Red Queen Paper](https://pub.sakana.ai/drq/) - Original research by Sakana AI
- [Core War Wikipedia](https://en.wikipedia.org/wiki/Core_War)
- [Redcode Standard (ICWS'94)](http://corewar.co.uk/icws94.txt)

## License

MIT License
