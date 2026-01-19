"""
Base LLM Interface

Defines the abstract interface for LLM providers and warrior generation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import random
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corewar.redcode import Warrior, parse_warrior, warrior_to_string, WARRIORS


# Redcode specification for LLM prompts
REDCODE_SPEC = """
# Redcode-94 Specification for Core War

## Overview
Redcode is an assembly-like language for Core War warriors.
Warriors compete in a shared memory space (the "core"), trying to crash opponents while surviving.

## Opcodes

| Opcode | Description |
|--------|-------------|
| DAT | Data - kills process if executed |
| MOV | Move - copy from source to destination |
| ADD | Add source to destination |
| SUB | Subtract source from destination |
| MUL | Multiply destination by source |
| DIV | Divide destination by source (kills on /0) |
| MOD | Modulo destination by source (kills on %0) |
| JMP | Jump to address |
| JMZ | Jump if zero |
| JMN | Jump if not zero |
| DJN | Decrement and jump if not zero |
| SPL | Split - spawn new process at address |
| CMP/SEQ | Compare - skip next if equal |
| SNE | Skip if not equal |
| SLT | Skip if less than |
| NOP | No operation |

## Modifiers

| Modifier | Meaning |
|----------|---------|
| .A | A-field to A-field |
| .B | B-field to B-field |
| .AB | A-field to B-field |
| .BA | B-field to A-field |
| .F | Both fields (A→A, B→B) |
| .X | Crossed (A→B, B→A) |
| .I | Entire instruction |

## Addressing Modes

| Mode | Symbol | Meaning |
|------|--------|---------|
| Immediate | # | Use value directly |
| Direct | $ | Address relative to current (default) |
| A-Indirect | * | Use A-field of target as address |
| B-Indirect | @ | Use B-field of target as address |
| A-Pre-decrement | { | Decrement A-field, then indirect |
| B-Pre-decrement | < | Decrement B-field, then indirect |
| A-Post-increment | } | Indirect, then increment A-field |
| B-Post-increment | > | Indirect, then increment B-field |

## Example Warriors

### Imp (simplest warrior - copies itself forward)
```
MOV.I 0, 1
```

### Dwarf (bomber - writes DAT instructions at regular intervals)
```
ADD.AB #4, 3
MOV.I  2, @2
JMP    -2
DAT    #0, #0
```

### Simple Replicator
```
SPL    0, 0
MOV.I  -1, 1
```

## Common Strategies

1. **Bomber**: Write DAT instructions to random addresses to crash opponents
2. **Replicator**: Copy self to new locations for redundancy
3. **Scanner**: Search for enemy code, then attack
4. **Paper**: Create many copies via SPL (threading)
5. **Stone**: Powerful bomber that bombs at regular intervals
6. **Scissors**: Fast scanner that hunts bombers

## Tips for Strong Warriors

- Use SPL to create multiple threads (harder to kill)
- Combine strategies (e.g., replicating bomber)
- Cover memory efficiently
- Use relative addressing for position-independent code
- Keep warriors compact (100 instructions max)
"""


@dataclass
class GenerationConfig:
    """Configuration for warrior generation."""
    temperature: float = 0.8
    max_tokens: int = 1024
    max_warrior_length: int = 50
    strategy_hint: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider/model name."""
        pass


class WarriorGenerator:
    """
    Generates and mutates Core War warriors using an LLM.
    
    This is the core component that connects LLMs to the evolution loop.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        config: Optional[GenerationConfig] = None,
    ):
        """
        Initialize the warrior generator.
        
        Args:
            llm_provider: The LLM provider to use
            config: Generation configuration
        """
        self.llm = llm_provider
        self.config = config or GenerationConfig()
        
        # Track generation stats
        self.generations = 0
        self.mutations = 0
        self.parse_failures = 0
    
    def _extract_code(self, response: str) -> str:
        """Extract Redcode from LLM response (handles markdown code blocks)."""
        # Try to find code block
        code_pattern = r"```(?:redcode|asm|assembly|)?\n?(.*?)```"
        matches = re.findall(code_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # If no code block, try to extract lines that look like Redcode
        lines = []
        for line in response.split("\n"):
            line = line.strip()
            # Check if line starts with a known opcode
            if any(line.upper().startswith(op) for op in 
                   ["DAT", "MOV", "ADD", "SUB", "MUL", "DIV", "MOD", 
                    "JMP", "JMZ", "JMN", "DJN", "SPL", "CMP", "SEQ", "SNE", "SLT", "NOP"]):
                lines.append(line)
            elif line.startswith(";"):
                lines.append(line)
        
        return "\n".join(lines) if lines else response
    
    def generate_random(self) -> Warrior:
        """
        Generate a random warrior using the LLM.
        
        Returns:
            A new Warrior object
        """
        self.generations += 1
        
        strategies = [
            "a bomber that writes DAT instructions at various memory locations",
            "a replicator that copies itself to spread across memory",
            "a scanner that searches for enemy code and attacks it",
            "a paper warrior that uses SPL to create many threads",
            "a quick-scanning attacker that finds and destroys enemies fast",
            "a hybrid bomber-replicator for robustness",
            "a stealthy warrior that hides and attacks unexpectedly",
            "a multi-threaded bomber that attacks from multiple locations",
        ]
        
        strategy = self.config.strategy_hint or random.choice(strategies)
        
        prompt = f"""Generate a Core War warrior in Redcode.

Strategy: Create {strategy}

Requirements:
- Maximum {self.config.max_warrior_length} instructions
- Use valid Redcode-94 syntax
- Include comments explaining the strategy
- Give the warrior a creative name

Return ONLY the Redcode, starting with ;name and ;author comments.
"""

        system_prompt = f"""You are an expert Core War programmer. 
Generate valid Redcode-94 warriors for the Core War game.

{REDCODE_SPEC}

Always output valid Redcode that can be parsed. Use proper opcodes, modifiers, and addressing modes."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            code = self._extract_code(response)
            warrior = parse_warrior(code)
            
            # Validate
            if not warrior.instructions:
                raise ValueError("Empty warrior")
            
            return warrior
            
        except Exception as e:
            self.parse_failures += 1
            # Fallback to a simple random warrior
            return self._generate_fallback()
    
    def mutate(self, warrior: Warrior) -> Warrior:
        """
        Mutate a warrior using the LLM.
        
        Args:
            warrior: The warrior to mutate
            
        Returns:
            A mutated Warrior object
        """
        self.mutations += 1
        
        source = warrior_to_string(warrior)
        
        mutation_types = [
            "Improve the bombing pattern to cover more memory",
            "Add more threading with SPL instructions",
            "Make it more defensive by adding self-checks",
            "Increase attack speed",
            "Add a secondary attack strategy",
            "Optimize instruction count",
            "Add decoy code to confuse scanners",
            "Improve replication efficiency",
            "Change addressing modes for better performance",
            "Add a scanning component to find enemies",
        ]
        
        mutation = random.choice(mutation_types)
        
        prompt = f"""Mutate this Core War warrior to improve it.

Current warrior:
```
{source}
```

Mutation goal: {mutation}

Requirements:
- Keep the core strategy but improve it
- Maximum {self.config.max_warrior_length} instructions
- Maintain valid Redcode-94 syntax
- Make meaningful changes, not just cosmetic

Return ONLY the improved Redcode.
"""

        system_prompt = f"""You are an expert Core War programmer.
Improve warriors while maintaining valid Redcode-94 syntax.

{REDCODE_SPEC}

Focus on making warriors stronger against diverse opponents."""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            code = self._extract_code(response)
            mutated = parse_warrior(code)
            
            # Validate
            if not mutated.instructions:
                raise ValueError("Empty warrior")
            
            return mutated
            
        except Exception as e:
            self.parse_failures += 1
            # Fallback: return slightly modified original
            return self._mutate_fallback(warrior)
    
    def _generate_fallback(self) -> Warrior:
        """Generate a fallback warrior when LLM fails."""
        # Pick a random classic warrior and slightly modify it
        template = random.choice(list(WARRIORS.values()))
        warrior = parse_warrior(template)
        warrior.name = f"Fallback_{self.generations}"
        return warrior
    
    def _mutate_fallback(self, warrior: Warrior) -> Warrior:
        """Simple mutation when LLM fails."""
        from corewar.redcode import Instruction, OpCode, AddressMode
        
        mutated = Warrior(
            name=f"{warrior.name}_mut",
            author=warrior.author,
            instructions=[instr.copy() for instr in warrior.instructions],
            start_offset=warrior.start_offset,
        )
        
        if mutated.instructions:
            # Pick random instruction and modify its values
            idx = random.randint(0, len(mutated.instructions) - 1)
            instr = mutated.instructions[idx]
            
            # Randomly modify A or B value
            if random.random() < 0.5:
                instr.a_value = (instr.a_value + random.randint(-5, 5)) % 8000
            else:
                instr.b_value = (instr.b_value + random.randint(-5, 5)) % 8000
        
        return mutated
    
    def crossover(self, parent1: Warrior, parent2: Warrior) -> Warrior:
        """
        Create offspring by combining two warriors.
        
        Args:
            parent1: First parent warrior
            parent2: Second parent warrior
            
        Returns:
            A new Warrior combining elements of both parents
        """
        source1 = warrior_to_string(parent1)
        source2 = warrior_to_string(parent2)
        
        prompt = f"""Combine these two Core War warriors into a new hybrid warrior.

Parent 1:
```
{source1}
```

Parent 2:
```
{source2}
```

Requirements:
- Combine the best strategies from both parents
- Maximum {self.config.max_warrior_length} instructions
- Create something new, not just concatenation
- Maintain valid Redcode-94 syntax

Return ONLY the new hybrid Redcode.
"""

        system_prompt = f"""You are an expert Core War programmer.
Create hybrid warriors by intelligently combining strategies.

{REDCODE_SPEC}"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            code = self._extract_code(response)
            offspring = parse_warrior(code)
            
            if not offspring.instructions:
                raise ValueError("Empty warrior")
            
            return offspring
            
        except Exception:
            self.parse_failures += 1
            # Fallback: simple crossover
            return self._crossover_fallback(parent1, parent2)
    
    def _crossover_fallback(self, parent1: Warrior, parent2: Warrior) -> Warrior:
        """Simple crossover when LLM fails."""
        # Take first half of parent1 and second half of parent2
        mid1 = len(parent1.instructions) // 2
        mid2 = len(parent2.instructions) // 2
        
        instructions = (
            [i.copy() for i in parent1.instructions[:mid1]] +
            [i.copy() for i in parent2.instructions[mid2:]]
        )
        
        return Warrior(
            name=f"{parent1.name}x{parent2.name}",
            author="Crossover",
            instructions=instructions[:self.config.max_warrior_length],
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get generation statistics."""
        return {
            "generations": self.generations,
            "mutations": self.mutations,
            "parse_failures": self.parse_failures,
            "success_rate": (
                (self.generations + self.mutations - self.parse_failures) /
                max(1, self.generations + self.mutations)
            ),
        }
