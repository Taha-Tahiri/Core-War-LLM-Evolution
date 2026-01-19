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

- **Multiple LLM Support**: Works with OpenAI (GPT-4), Anthropic (Claude), and local models via Ollama
- **MAP-Elites Algorithm**: Preserves behavioral diversity during evolution
- **Complete Core War Simulator**: Full Redcode implementation with threading support
- **Visualization Tools**: Battle replays, fitness curves, and behavioral analysis
- **Configurable Experiments**: Adjust history length, generations, population size

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set up your API keys:

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

For local models, ensure Ollama is running:
```bash
ollama serve
```

## Quick Start

```python
from drq import DigitalRedQueen
from llm_interface import OpenAIProvider

# Initialize with your preferred LLM
llm = OpenAIProvider(model="gpt-4")

# Create DRQ instance
drq = DigitalRedQueen(
    llm_provider=llm,
    num_rounds=10,
    generations_per_round=50,
    population_size=100
)

# Run evolution
champions = drq.run()

# Analyze results
drq.visualize_evolution()
```

## Running Experiments

### Single LLM Evolution
```bash
python run_experiment.py --llm openai --model gpt-4 --rounds 10
```

### Compare Multiple LLMs
```bash
python run_experiment.py --compare --llms openai,anthropic,ollama --rounds 10
```

## Project Structure

```
cor wars/
├── README.md
├── requirements.txt
├── corewar/
│   ├── __init__.py
│   ├── redcode.py      # Redcode instruction set
│   ├── mars.py         # MARS virtual machine
│   └── battle.py       # Battle simulation
├── evolution/
│   ├── __init__.py
│   ├── map_elites.py   # Quality-diversity algorithm
│   └── fitness.py      # Fitness evaluation
├── llm_interface/
│   ├── __init__.py
│   ├── base.py         # Base LLM interface
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── ollama_provider.py
├── drq.py              # Main DRQ algorithm
├── run_experiment.py   # CLI experiment runner
├── visualize.py        # Visualization tools
└── warriors/           # Example warriors
    ├── imp.red
    ├── dwarf.red
    └── mice.red
```

## Redcode Reference

Basic opcodes:
- `DAT`: Data (kills process if executed)
- `MOV`: Move (copy data)
- `ADD`: Add
- `SUB`: Subtract
- `JMP`: Jump
- `JMZ`: Jump if zero
- `JMN`: Jump if not zero
- `DJN`: Decrement and jump if not zero
- `SPL`: Split (spawn new thread)
- `CMP`/`SEQ`: Compare/Skip if equal
- `SNE`: Skip if not equal
- `SLT`: Skip if less than
- `NOP`: No operation

## References

- [Digital Red Queen Paper](https://pub.sakana.ai/drq/)
- [Core War Wikipedia](https://en.wikipedia.org/wiki/Core_War)
- [Redcode Standard](http://corewar.co.uk/icws94.txt)

## License

MIT License
