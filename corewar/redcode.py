"""
Redcode Parser and Instruction Set

Implements the ICWS'94 Redcode standard for Core War warriors.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import re


class OpCode(Enum):
    """Redcode operation codes."""
    DAT = auto()  # Data - kills process if executed
    MOV = auto()  # Move - copy from A to B
    ADD = auto()  # Add - add A to B
    SUB = auto()  # Subtract - subtract A from B
    MUL = auto()  # Multiply - multiply B by A
    DIV = auto()  # Divide - divide B by A
    MOD = auto()  # Modulo - B modulo A
    JMP = auto()  # Jump - transfer execution to A
    JMZ = auto()  # Jump if Zero - jump to A if B is zero
    JMN = auto()  # Jump if Not Zero - jump to A if B is not zero
    DJN = auto()  # Decrement and Jump if Not Zero
    SPL = auto()  # Split - spawn new process at A
    CMP = auto()  # Compare - skip next if A equals B (alias for SEQ)
    SEQ = auto()  # Skip if Equal
    SNE = auto()  # Skip if Not Equal
    SLT = auto()  # Skip if Less Than
    LDP = auto()  # Load from P-space
    STP = auto()  # Store to P-space
    NOP = auto()  # No Operation


class Modifier(Enum):
    """Instruction modifiers that specify how operands interact."""
    A = auto()   # A-field to A-field
    B = auto()   # B-field to B-field
    AB = auto()  # A-field to B-field
    BA = auto()  # B-field to A-field
    F = auto()   # Both fields (A to A, B to B)
    X = auto()   # Both fields crossed (A to B, B to A)
    I = auto()   # Entire instruction


class AddressMode(Enum):
    """Addressing modes for operands."""
    IMMEDIATE = "#"      # Immediate value
    DIRECT = "$"         # Direct address (default)
    A_INDIRECT = "*"     # A-field indirect
    B_INDIRECT = "@"     # B-field indirect
    A_PREDEC = "{"       # A-field pre-decrement indirect
    B_PREDEC = "<"       # B-field pre-decrement indirect
    A_POSTINC = "}"      # A-field post-increment indirect
    B_POSTINC = ">"      # B-field post-increment indirect


@dataclass
class Instruction:
    """A single Redcode instruction."""
    opcode: OpCode = OpCode.DAT
    modifier: Modifier = Modifier.F
    a_mode: AddressMode = AddressMode.DIRECT
    a_value: int = 0
    b_mode: AddressMode = AddressMode.DIRECT
    b_value: int = 0
    
    def copy(self) -> "Instruction":
        """Create a deep copy of this instruction."""
        return Instruction(
            opcode=self.opcode,
            modifier=self.modifier,
            a_mode=self.a_mode,
            a_value=self.a_value,
            b_mode=self.b_mode,
            b_value=self.b_value,
        )
    
    def __str__(self) -> str:
        """Convert instruction to Redcode string."""
        a_mode_str = self.a_mode.value if self.a_mode != AddressMode.DIRECT else ""
        b_mode_str = self.b_mode.value if self.b_mode != AddressMode.DIRECT else ""
        
        return (
            f"{self.opcode.name}.{self.modifier.name} "
            f"{a_mode_str}{self.a_value}, {b_mode_str}{self.b_value}"
        )


@dataclass  
class Warrior:
    """A Core War warrior program."""
    name: str = "Unknown"
    author: str = "Unknown"
    instructions: List[Instruction] = field(default_factory=list)
    start_offset: int = 0  # Offset from first instruction to start execution
    
    def __len__(self) -> int:
        return len(self.instructions)


def _parse_address_mode(char: str) -> AddressMode:
    """Parse an address mode character."""
    mode_map = {
        "#": AddressMode.IMMEDIATE,
        "$": AddressMode.DIRECT,
        "*": AddressMode.A_INDIRECT,
        "@": AddressMode.B_INDIRECT,
        "{": AddressMode.A_PREDEC,
        "<": AddressMode.B_PREDEC,
        "}": AddressMode.A_POSTINC,
        ">": AddressMode.B_POSTINC,
    }
    return mode_map.get(char, AddressMode.DIRECT)


def _parse_operand(operand: str) -> Tuple[AddressMode, int]:
    """Parse an operand string into mode and value."""
    operand = operand.strip()
    if not operand:
        return AddressMode.DIRECT, 0
    
    # Check for address mode prefix
    if operand[0] in "#$*@{<}>":
        mode = _parse_address_mode(operand[0])
        value_str = operand[1:].strip()
    else:
        mode = AddressMode.DIRECT
        value_str = operand
    
    # Parse the value
    try:
        value = int(value_str) if value_str else 0
    except ValueError:
        value = 0
    
    return mode, value


def _get_default_modifier(opcode: OpCode, a_mode: AddressMode, b_mode: AddressMode) -> Modifier:
    """Get the default modifier for an opcode based on ICWS'94 rules."""
    if opcode == OpCode.DAT:
        return Modifier.F
    elif opcode in (OpCode.MOV, OpCode.SEQ, OpCode.SNE, OpCode.CMP):
        if a_mode == AddressMode.IMMEDIATE:
            return Modifier.AB
        elif b_mode == AddressMode.IMMEDIATE:
            return Modifier.B
        else:
            return Modifier.I
    elif opcode in (OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD):
        if a_mode == AddressMode.IMMEDIATE:
            return Modifier.AB
        elif b_mode == AddressMode.IMMEDIATE:
            return Modifier.B
        else:
            return Modifier.F
    elif opcode == OpCode.SLT:
        if a_mode == AddressMode.IMMEDIATE:
            return Modifier.AB
        else:
            return Modifier.B
    elif opcode in (OpCode.JMP, OpCode.JMZ, OpCode.JMN, OpCode.DJN, OpCode.SPL):
        return Modifier.B
    elif opcode == OpCode.NOP:
        return Modifier.F
    else:
        return Modifier.F


def parse_instruction(line: str) -> Optional[Instruction]:
    """Parse a single Redcode instruction line."""
    # Remove comments
    if ";" in line:
        line = line[:line.index(";")]
    
    line = line.strip().upper()
    if not line:
        return None
    
    # Match instruction pattern
    # Format: OPCODE[.MODIFIER] A_OPERAND [, B_OPERAND]
    pattern = r"^(\w+)(?:\.(\w+))?\s+([^,]+)(?:,\s*(.+))?$"
    match = re.match(pattern, line)
    
    if not match:
        return None
    
    opcode_str, modifier_str, a_operand, b_operand = match.groups()
    
    # Parse opcode
    try:
        opcode = OpCode[opcode_str]
    except KeyError:
        return None
    
    # Parse operands
    a_mode, a_value = _parse_operand(a_operand)
    b_mode, b_value = _parse_operand(b_operand) if b_operand else (AddressMode.DIRECT, 0)
    
    # Parse or infer modifier
    if modifier_str:
        try:
            modifier = Modifier[modifier_str]
        except KeyError:
            modifier = _get_default_modifier(opcode, a_mode, b_mode)
    else:
        modifier = _get_default_modifier(opcode, a_mode, b_mode)
    
    return Instruction(
        opcode=opcode,
        modifier=modifier,
        a_mode=a_mode,
        a_value=a_value,
        b_mode=b_mode,
        b_value=b_value,
    )


def parse_warrior(source: str) -> Warrior:
    """Parse a complete Redcode warrior program."""
    warrior = Warrior()
    labels: dict[str, int] = {}
    
    lines = source.strip().split("\n")
    
    # First pass: collect metadata and labels
    for line in lines:
        line_stripped = line.strip()
        
        # Parse metadata
        if line_stripped.lower().startswith(";name"):
            warrior.name = line_stripped[5:].strip()
        elif line_stripped.lower().startswith(";author"):
            warrior.author = line_stripped[7:].strip()
        elif line_stripped.lower().startswith(";redcode"):
            continue
        elif line_stripped.lower().startswith("org"):
            # ORG directive - set start offset
            parts = line_stripped.split()
            if len(parts) > 1:
                try:
                    warrior.start_offset = int(parts[1])
                except ValueError:
                    # Could be a label reference
                    pass
    
    # Second pass: parse instructions
    for line in lines:
        # Skip metadata and empty lines
        if line.strip().startswith(";") or not line.strip():
            continue
        if line.strip().lower().startswith(("org", "end")):
            continue
        
        # Try to parse as instruction
        instruction = parse_instruction(line)
        if instruction:
            warrior.instructions.append(instruction)
    
    return warrior


def warrior_to_string(warrior: Warrior) -> str:
    """Convert a Warrior back to Redcode source code."""
    lines = [
        f";redcode-94",
        f";name {warrior.name}",
        f";author {warrior.author}",
        "",
    ]
    
    for instr in warrior.instructions:
        lines.append(str(instr))
    
    if warrior.start_offset != 0:
        lines.append(f"ORG {warrior.start_offset}")
    
    return "\n".join(lines)


# Classic warrior examples
WARRIORS = {
    "imp": """;redcode-94
;name Imp
;author A.K. Dewdney
;strategy The simplest warrior - copies itself forward

MOV.I 0, 1
""",
    
    "dwarf": """;redcode-94
;name Dwarf
;author A.K. Dewdney
;strategy Bombs memory at regular intervals

ADD.AB #4, 3
MOV.I  2, @2
JMP    -2
DAT    #0, #0
""",
    
    "mice": """;redcode-94
;name Mice
;author Chip Wendell
;strategy Self-replicating bomber

        SPL    0, 0        ; spawn thread
        MOV.I  12, <15     ; copy backwards
        DJN    -1, -3      ; loop
        SPL    @14, 0      ; spawn at target
        ADD.AB #653, 13    ; next target
        JMZ    -5, -7      ; check if done
        MOV.I  10, <11     ; clear behind
        DJN    -1, -3      ; loop
        SPL    2, 0        ; new generation
        JMP    -9, 0       ; restart
        DAT    #0, #833    ; bomb
        DAT    #0, #0      ; pointer
        DAT    #0, #0      ; counter
        DAT    #0, #0      ; target
        DAT    #0, #0      ; scratch
""",
    
    "scanner": """;redcode-94
;name Scanner
;author Unknown
;strategy Scans for enemies then bombs them

scan    ADD.AB bomb, ptr
        MOV.I  @ptr, copy
        SNE.I  copy, empty
        JMP    scan
        SUB.AB #5, ptr
attack  MOV.I  bomb, @ptr
        ADD.AB #1, ptr
        DJN    attack, count
        JMP    scan
bomb    DAT    #0, #0
ptr     DAT    #0, #15
copy    DAT    #0, #0
empty   DAT    #0, #0
count   DAT    #0, #5
""",
}
