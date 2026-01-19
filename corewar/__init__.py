"""
Core War Simulator - A complete Redcode/MARS implementation.

This module provides a full Core War virtual machine for running
warrior battles in the Digital Red Queen evolution system.
"""

from .redcode import (
    Instruction,
    OpCode,
    Modifier,
    AddressMode,
    parse_warrior,
    warrior_to_string,
)
from .mars import MARS, Process
from .battle import Battle, BattleResult

__all__ = [
    "Instruction",
    "OpCode", 
    "Modifier",
    "AddressMode",
    "parse_warrior",
    "warrior_to_string",
    "MARS",
    "Process",
    "Battle",
    "BattleResult",
]
