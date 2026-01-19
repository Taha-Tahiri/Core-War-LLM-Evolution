"""
MARS - Memory Array Redcode Simulator

The virtual machine that executes Core War battles.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple
from collections import deque
import copy

from .redcode import Instruction, OpCode, Modifier, AddressMode, Warrior


@dataclass
class Process:
    """A single execution thread in the MARS."""
    program_counter: int = 0
    warrior_id: int = 0


@dataclass
class WarriorState:
    """Runtime state for a warrior in battle."""
    warrior_id: int
    name: str
    processes: deque  # deque of program counters
    is_alive: bool = True
    
    # Behavioral metrics for MAP-Elites
    memory_accessed: Set[int] = field(default_factory=set)
    threads_spawned: int = 0
    instructions_executed: int = 0
    memory_writes: int = 0


class MARS:
    """
    Memory Array Redcode Simulator - the Core War virtual machine.
    
    Implements ICWS'94 standard with support for multiple warriors
    and process queues.
    """
    
    def __init__(
        self,
        core_size: int = 8000,
        max_cycles: int = 80000,
        max_processes: int = 8000,
        max_length: int = 100,
        min_distance: int = 100,
    ):
        """
        Initialize the MARS.
        
        Args:
            core_size: Number of memory addresses (default 8000)
            max_cycles: Maximum cycles before draw (default 80000)
            max_processes: Max processes per warrior (default 8000)
            max_length: Max warrior length (default 100)
            min_distance: Min distance between warriors (default 100)
        """
        self.core_size = core_size
        self.max_cycles = max_cycles
        self.max_processes = max_processes
        self.max_length = max_length
        self.min_distance = min_distance
        
        # Initialize core memory with DAT 0, 0
        self.core: List[Instruction] = [
            Instruction() for _ in range(core_size)
        ]
        
        # Track which warrior owns each cell (for visualization)
        self.ownership: List[int] = [-1] * core_size
        
        # Warrior states
        self.warriors: Dict[int, WarriorState] = {}
        self.warrior_order: List[int] = []  # Round-robin order
        self.current_warrior_idx: int = 0
        
        # Simulation state
        self.cycle: int = 0
        self.running: bool = False
        
    def _normalize(self, address: int) -> int:
        """Normalize an address to be within core bounds."""
        return address % self.core_size
    
    def _read(self, address: int) -> Instruction:
        """Read an instruction from core memory."""
        addr = self._normalize(address)
        return self.core[addr]
    
    def _write(self, address: int, instruction: Instruction, warrior_id: int):
        """Write an instruction to core memory."""
        addr = self._normalize(address)
        self.core[addr] = instruction.copy()
        self.ownership[addr] = warrior_id
        
        # Track behavioral metrics
        if warrior_id in self.warriors:
            self.warriors[warrior_id].memory_writes += 1
            self.warriors[warrior_id].memory_accessed.add(addr)
    
    def _resolve_address(
        self, 
        base_pc: int,
        mode: AddressMode, 
        value: int,
        is_a_field: bool,
        warrior_id: int,
    ) -> Tuple[int, int]:
        """
        Resolve an address based on addressing mode.
        
        Returns:
            Tuple of (pointer to instruction, field value to use)
        """
        base_addr = self._normalize(base_pc + value)
        
        if mode == AddressMode.IMMEDIATE:
            # Value is the operand itself
            return base_pc, value
            
        elif mode == AddressMode.DIRECT:
            # Direct reference to address
            return base_addr, value
            
        elif mode == AddressMode.A_INDIRECT:
            # Indirect through A-field
            target = self._read(base_addr)
            return self._normalize(base_addr + target.a_value), target.a_value
            
        elif mode == AddressMode.B_INDIRECT:
            # Indirect through B-field
            target = self._read(base_addr)
            return self._normalize(base_addr + target.b_value), target.b_value
            
        elif mode == AddressMode.A_PREDEC:
            # Pre-decrement A-field, then indirect
            target = self._read(base_addr)
            target.a_value = (target.a_value - 1) % self.core_size
            self._write(base_addr, target, warrior_id)
            return self._normalize(base_addr + target.a_value), target.a_value
            
        elif mode == AddressMode.B_PREDEC:
            # Pre-decrement B-field, then indirect
            target = self._read(base_addr)
            target.b_value = (target.b_value - 1) % self.core_size
            self._write(base_addr, target, warrior_id)
            return self._normalize(base_addr + target.b_value), target.b_value
            
        elif mode == AddressMode.A_POSTINC:
            # Indirect through A-field, then post-increment
            target = self._read(base_addr)
            result_addr = self._normalize(base_addr + target.a_value)
            result_val = target.a_value
            target.a_value = (target.a_value + 1) % self.core_size
            self._write(base_addr, target, warrior_id)
            return result_addr, result_val
            
        elif mode == AddressMode.B_POSTINC:
            # Indirect through B-field, then post-increment
            target = self._read(base_addr)
            result_addr = self._normalize(base_addr + target.b_value)
            result_val = target.b_value
            target.b_value = (target.b_value + 1) % self.core_size
            self._write(base_addr, target, warrior_id)
            return result_addr, result_val
            
        return base_addr, value
    
    def load_warrior(self, warrior: Warrior, position: int, warrior_id: int) -> bool:
        """
        Load a warrior into core memory at the specified position.
        
        Args:
            warrior: The Warrior to load
            position: Starting address in core
            warrior_id: Unique ID for this warrior
            
        Returns:
            True if loaded successfully
        """
        if len(warrior.instructions) > self.max_length:
            return False
        
        # Copy instructions to core
        for i, instr in enumerate(warrior.instructions):
            addr = self._normalize(position + i)
            self.core[addr] = instr.copy()
            self.ownership[addr] = warrior_id
        
        # Create warrior state
        start_pc = self._normalize(position + warrior.start_offset)
        self.warriors[warrior_id] = WarriorState(
            warrior_id=warrior_id,
            name=warrior.name,
            processes=deque([start_pc]),
        )
        self.warrior_order.append(warrior_id)
        
        return True
    
    def _execute_one(self, warrior_state: WarriorState) -> bool:
        """
        Execute one instruction for a warrior.
        
        Returns:
            True if the warrior is still alive
        """
        if not warrior_state.processes:
            warrior_state.is_alive = False
            return False
        
        # Get current process
        pc = warrior_state.processes.popleft()
        warrior_id = warrior_state.warrior_id
        
        # Track metrics
        warrior_state.instructions_executed += 1
        warrior_state.memory_accessed.add(pc)
        
        # Fetch instruction
        instr = self._read(pc)
        next_pc = self._normalize(pc + 1)
        
        # Resolve operand addresses
        a_addr, a_val = self._resolve_address(pc, instr.a_mode, instr.a_value, True, warrior_id)
        b_addr, b_val = self._resolve_address(pc, instr.b_mode, instr.b_value, False, warrior_id)
        
        # Get source and destination instructions
        src = self._read(a_addr)
        dst = self._read(b_addr)
        
        # Execute based on opcode
        if instr.opcode == OpCode.DAT:
            # DAT kills the process - don't add next_pc back
            pass
            
        elif instr.opcode == OpCode.MOV:
            self._execute_mov(instr.modifier, src, dst, a_addr, b_addr, warrior_id)
            warrior_state.processes.append(next_pc)
            
        elif instr.opcode == OpCode.ADD:
            self._execute_add(instr.modifier, src, dst, b_addr, warrior_id)
            warrior_state.processes.append(next_pc)
            
        elif instr.opcode == OpCode.SUB:
            self._execute_sub(instr.modifier, src, dst, b_addr, warrior_id)
            warrior_state.processes.append(next_pc)
            
        elif instr.opcode == OpCode.MUL:
            self._execute_mul(instr.modifier, src, dst, b_addr, warrior_id)
            warrior_state.processes.append(next_pc)
            
        elif instr.opcode == OpCode.DIV:
            if not self._execute_div(instr.modifier, src, dst, b_addr, warrior_id):
                pass  # Division by zero kills process
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.MOD:
            if not self._execute_mod(instr.modifier, src, dst, b_addr, warrior_id):
                pass  # Modulo by zero kills process
            else:
                warrior_state.processes.append(next_pc)
            
        elif instr.opcode == OpCode.JMP:
            warrior_state.processes.append(a_addr)
            
        elif instr.opcode == OpCode.JMZ:
            if self._is_zero(instr.modifier, dst):
                warrior_state.processes.append(a_addr)
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.JMN:
            if not self._is_zero(instr.modifier, dst):
                warrior_state.processes.append(a_addr)
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.DJN:
            # Decrement first
            new_dst = dst.copy()
            if instr.modifier in (Modifier.A, Modifier.BA):
                new_dst.a_value = (new_dst.a_value - 1) % self.core_size
            elif instr.modifier in (Modifier.B, Modifier.AB):
                new_dst.b_value = (new_dst.b_value - 1) % self.core_size
            else:  # F, X, I
                new_dst.a_value = (new_dst.a_value - 1) % self.core_size
                new_dst.b_value = (new_dst.b_value - 1) % self.core_size
            self._write(b_addr, new_dst, warrior_id)
            
            # Then jump if not zero
            if not self._is_zero(instr.modifier, new_dst):
                warrior_state.processes.append(a_addr)
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.SPL:
            # Split: add new process at A, continue at next instruction
            if len(warrior_state.processes) < self.max_processes - 1:
                warrior_state.processes.append(a_addr)
                warrior_state.threads_spawned += 1
            warrior_state.processes.append(next_pc)
            
        elif instr.opcode in (OpCode.CMP, OpCode.SEQ):
            if self._compare_equal(instr.modifier, src, dst):
                warrior_state.processes.append(self._normalize(next_pc + 1))
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.SNE:
            if not self._compare_equal(instr.modifier, src, dst):
                warrior_state.processes.append(self._normalize(next_pc + 1))
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.SLT:
            if self._compare_less_than(instr.modifier, src, dst):
                warrior_state.processes.append(self._normalize(next_pc + 1))
            else:
                warrior_state.processes.append(next_pc)
                
        elif instr.opcode == OpCode.NOP:
            warrior_state.processes.append(next_pc)
            
        else:
            # Unknown opcode - treat as NOP
            warrior_state.processes.append(next_pc)
        
        # Check if warrior is still alive
        warrior_state.is_alive = len(warrior_state.processes) > 0
        return warrior_state.is_alive
    
    def _execute_mov(self, modifier: Modifier, src: Instruction, dst: Instruction, 
                     a_addr: int, b_addr: int, warrior_id: int):
        """Execute MOV instruction."""
        new_dst = dst.copy()
        
        if modifier == Modifier.A:
            new_dst.a_value = src.a_value
        elif modifier == Modifier.B:
            new_dst.b_value = src.b_value
        elif modifier == Modifier.AB:
            new_dst.b_value = src.a_value
        elif modifier == Modifier.BA:
            new_dst.a_value = src.b_value
        elif modifier == Modifier.F:
            new_dst.a_value = src.a_value
            new_dst.b_value = src.b_value
        elif modifier == Modifier.X:
            new_dst.a_value = src.b_value
            new_dst.b_value = src.a_value
        elif modifier == Modifier.I:
            new_dst = src.copy()
        
        self._write(b_addr, new_dst, warrior_id)
    
    def _execute_add(self, modifier: Modifier, src: Instruction, dst: Instruction,
                     b_addr: int, warrior_id: int):
        """Execute ADD instruction."""
        new_dst = dst.copy()
        
        if modifier == Modifier.A:
            new_dst.a_value = (new_dst.a_value + src.a_value) % self.core_size
        elif modifier == Modifier.B:
            new_dst.b_value = (new_dst.b_value + src.b_value) % self.core_size
        elif modifier == Modifier.AB:
            new_dst.b_value = (new_dst.b_value + src.a_value) % self.core_size
        elif modifier == Modifier.BA:
            new_dst.a_value = (new_dst.a_value + src.b_value) % self.core_size
        elif modifier in (Modifier.F, Modifier.I):
            new_dst.a_value = (new_dst.a_value + src.a_value) % self.core_size
            new_dst.b_value = (new_dst.b_value + src.b_value) % self.core_size
        elif modifier == Modifier.X:
            new_dst.a_value = (new_dst.a_value + src.b_value) % self.core_size
            new_dst.b_value = (new_dst.b_value + src.a_value) % self.core_size
        
        self._write(b_addr, new_dst, warrior_id)
    
    def _execute_sub(self, modifier: Modifier, src: Instruction, dst: Instruction,
                     b_addr: int, warrior_id: int):
        """Execute SUB instruction."""
        new_dst = dst.copy()
        
        if modifier == Modifier.A:
            new_dst.a_value = (new_dst.a_value - src.a_value) % self.core_size
        elif modifier == Modifier.B:
            new_dst.b_value = (new_dst.b_value - src.b_value) % self.core_size
        elif modifier == Modifier.AB:
            new_dst.b_value = (new_dst.b_value - src.a_value) % self.core_size
        elif modifier == Modifier.BA:
            new_dst.a_value = (new_dst.a_value - src.b_value) % self.core_size
        elif modifier in (Modifier.F, Modifier.I):
            new_dst.a_value = (new_dst.a_value - src.a_value) % self.core_size
            new_dst.b_value = (new_dst.b_value - src.b_value) % self.core_size
        elif modifier == Modifier.X:
            new_dst.a_value = (new_dst.a_value - src.b_value) % self.core_size
            new_dst.b_value = (new_dst.b_value - src.a_value) % self.core_size
        
        self._write(b_addr, new_dst, warrior_id)
    
    def _execute_mul(self, modifier: Modifier, src: Instruction, dst: Instruction,
                     b_addr: int, warrior_id: int):
        """Execute MUL instruction."""
        new_dst = dst.copy()
        
        if modifier == Modifier.A:
            new_dst.a_value = (new_dst.a_value * src.a_value) % self.core_size
        elif modifier == Modifier.B:
            new_dst.b_value = (new_dst.b_value * src.b_value) % self.core_size
        elif modifier == Modifier.AB:
            new_dst.b_value = (new_dst.b_value * src.a_value) % self.core_size
        elif modifier == Modifier.BA:
            new_dst.a_value = (new_dst.a_value * src.b_value) % self.core_size
        elif modifier in (Modifier.F, Modifier.I):
            new_dst.a_value = (new_dst.a_value * src.a_value) % self.core_size
            new_dst.b_value = (new_dst.b_value * src.b_value) % self.core_size
        elif modifier == Modifier.X:
            new_dst.a_value = (new_dst.a_value * src.b_value) % self.core_size
            new_dst.b_value = (new_dst.b_value * src.a_value) % self.core_size
        
        self._write(b_addr, new_dst, warrior_id)
    
    def _execute_div(self, modifier: Modifier, src: Instruction, dst: Instruction,
                     b_addr: int, warrior_id: int) -> bool:
        """Execute DIV instruction. Returns False if division by zero."""
        new_dst = dst.copy()
        
        try:
            if modifier == Modifier.A:
                if src.a_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value // src.a_value
            elif modifier == Modifier.B:
                if src.b_value == 0:
                    return False
                new_dst.b_value = new_dst.b_value // src.b_value
            elif modifier == Modifier.AB:
                if src.a_value == 0:
                    return False
                new_dst.b_value = new_dst.b_value // src.a_value
            elif modifier == Modifier.BA:
                if src.b_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value // src.b_value
            elif modifier in (Modifier.F, Modifier.I):
                if src.a_value == 0 or src.b_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value // src.a_value
                new_dst.b_value = new_dst.b_value // src.b_value
            elif modifier == Modifier.X:
                if src.b_value == 0 or src.a_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value // src.b_value
                new_dst.b_value = new_dst.b_value // src.a_value
        except ZeroDivisionError:
            return False
        
        self._write(b_addr, new_dst, warrior_id)
        return True
    
    def _execute_mod(self, modifier: Modifier, src: Instruction, dst: Instruction,
                     b_addr: int, warrior_id: int) -> bool:
        """Execute MOD instruction. Returns False if modulo by zero."""
        new_dst = dst.copy()
        
        try:
            if modifier == Modifier.A:
                if src.a_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value % src.a_value
            elif modifier == Modifier.B:
                if src.b_value == 0:
                    return False
                new_dst.b_value = new_dst.b_value % src.b_value
            elif modifier == Modifier.AB:
                if src.a_value == 0:
                    return False
                new_dst.b_value = new_dst.b_value % src.a_value
            elif modifier == Modifier.BA:
                if src.b_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value % src.b_value
            elif modifier in (Modifier.F, Modifier.I):
                if src.a_value == 0 or src.b_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value % src.a_value
                new_dst.b_value = new_dst.b_value % src.b_value
            elif modifier == Modifier.X:
                if src.b_value == 0 or src.a_value == 0:
                    return False
                new_dst.a_value = new_dst.a_value % src.b_value
                new_dst.b_value = new_dst.b_value % src.a_value
        except ZeroDivisionError:
            return False
        
        self._write(b_addr, new_dst, warrior_id)
        return True
    
    def _is_zero(self, modifier: Modifier, instr: Instruction) -> bool:
        """Check if the relevant field(s) are zero."""
        if modifier in (Modifier.A, Modifier.BA):
            return instr.a_value == 0
        elif modifier in (Modifier.B, Modifier.AB):
            return instr.b_value == 0
        else:  # F, X, I
            return instr.a_value == 0 and instr.b_value == 0
    
    def _compare_equal(self, modifier: Modifier, src: Instruction, dst: Instruction) -> bool:
        """Compare instructions for equality based on modifier."""
        if modifier == Modifier.A:
            return src.a_value == dst.a_value
        elif modifier == Modifier.B:
            return src.b_value == dst.b_value
        elif modifier == Modifier.AB:
            return src.a_value == dst.b_value
        elif modifier == Modifier.BA:
            return src.b_value == dst.a_value
        elif modifier == Modifier.F:
            return src.a_value == dst.a_value and src.b_value == dst.b_value
        elif modifier == Modifier.X:
            return src.a_value == dst.b_value and src.b_value == dst.a_value
        elif modifier == Modifier.I:
            return (src.opcode == dst.opcode and 
                    src.modifier == dst.modifier and
                    src.a_mode == dst.a_mode and
                    src.a_value == dst.a_value and
                    src.b_mode == dst.b_mode and
                    src.b_value == dst.b_value)
        return False
    
    def _compare_less_than(self, modifier: Modifier, src: Instruction, dst: Instruction) -> bool:
        """Compare if src is less than dst based on modifier."""
        if modifier == Modifier.A:
            return src.a_value < dst.a_value
        elif modifier == Modifier.B:
            return src.b_value < dst.b_value
        elif modifier == Modifier.AB:
            return src.a_value < dst.b_value
        elif modifier == Modifier.BA:
            return src.b_value < dst.a_value
        else:  # F, X, I
            return src.a_value < dst.a_value and src.b_value < dst.b_value
    
    def step(self) -> bool:
        """
        Execute one step (one instruction from one warrior).
        
        Returns:
            True if the simulation should continue
        """
        if self.cycle >= self.max_cycles:
            return False
        
        # Count living warriors
        alive_warriors = [w for w in self.warriors.values() if w.is_alive]
        if len(alive_warriors) <= 1:
            return False
        
        # Get current warrior
        while True:
            warrior_id = self.warrior_order[self.current_warrior_idx]
            warrior_state = self.warriors[warrior_id]
            
            if warrior_state.is_alive:
                break
            
            self.current_warrior_idx = (self.current_warrior_idx + 1) % len(self.warrior_order)
        
        # Execute one instruction
        self._execute_one(warrior_state)
        
        # Move to next warrior
        self.current_warrior_idx = (self.current_warrior_idx + 1) % len(self.warrior_order)
        self.cycle += 1
        
        return True
    
    def run(self) -> Optional[int]:
        """
        Run the simulation until completion.
        
        Returns:
            The winner's warrior_id, or None for a draw
        """
        self.running = True
        
        while self.step():
            pass
        
        self.running = False
        
        # Determine winner
        alive = [w for w in self.warriors.values() if w.is_alive]
        if len(alive) == 1:
            return alive[0].warrior_id
        return None
    
    def get_behavioral_metrics(self, warrior_id: int) -> Dict[str, float]:
        """Get behavioral metrics for a warrior (for MAP-Elites)."""
        if warrior_id not in self.warriors:
            return {}
        
        state = self.warriors[warrior_id]
        return {
            "memory_coverage": len(state.memory_accessed) / self.core_size,
            "threads_spawned": state.threads_spawned,
            "instructions_executed": state.instructions_executed,
            "memory_writes": state.memory_writes,
        }
    
    def reset(self):
        """Reset the MARS to initial state."""
        self.core = [Instruction() for _ in range(self.core_size)]
        self.ownership = [-1] * self.core_size
        self.warriors = {}
        self.warrior_order = []
        self.current_warrior_idx = 0
        self.cycle = 0
        self.running = False
