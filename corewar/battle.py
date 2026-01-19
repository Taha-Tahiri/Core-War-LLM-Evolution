"""
Battle Module - Manages Core War battles between warriors.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

from .redcode import Warrior, parse_warrior
from .mars import MARS


@dataclass
class BattleResult:
    """Result of a Core War battle."""
    winner_id: Optional[int]  # None for draw
    warrior_ids: List[int]
    warrior_names: Dict[int, str]
    cycles: int
    
    # Detailed metrics per warrior
    metrics: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    # Survival time for each warrior
    survival_cycles: Dict[int, int] = field(default_factory=dict)
    
    def is_draw(self) -> bool:
        return self.winner_id is None
    
    def get_winner_name(self) -> str:
        if self.winner_id is None:
            return "Draw"
        return self.warrior_names.get(self.winner_id, "Unknown")


class Battle:
    """
    Manages Core War battles between warriors.
    
    Supports 2+ warriors in a single battle with configurable
    core size and cycle limits.
    """
    
    def __init__(
        self,
        core_size: int = 8000,
        max_cycles: int = 80000,
        max_processes: int = 8000,
        max_length: int = 100,
        min_distance: int = 100,
        num_rounds: int = 1,  # Number of rounds per battle (for averaging)
    ):
        """
        Initialize battle configuration.
        
        Args:
            core_size: Size of core memory
            max_cycles: Maximum cycles before draw
            max_processes: Max processes per warrior
            max_length: Max warrior length
            min_distance: Minimum distance between warriors
            num_rounds: Number of rounds to run (for statistical averaging)
        """
        self.core_size = core_size
        self.max_cycles = max_cycles
        self.max_processes = max_processes
        self.max_length = max_length
        self.min_distance = min_distance
        self.num_rounds = num_rounds
    
    def _generate_positions(self, num_warriors: int, lengths: List[int]) -> List[int]:
        """Generate random starting positions for warriors."""
        positions = []
        attempts = 0
        max_attempts = 1000
        
        while len(positions) < num_warriors and attempts < max_attempts:
            # Pick a random position
            pos = random.randint(0, self.core_size - 1)
            
            # Check if it's far enough from other warriors
            valid = True
            for i, other_pos in enumerate(positions):
                # Check distance in both directions (core is circular)
                dist1 = abs(pos - other_pos)
                dist2 = self.core_size - dist1
                min_dist = min(dist1, dist2)
                
                # Need enough space for the warrior plus minimum distance
                required_dist = max(lengths[i], lengths[len(positions)]) + self.min_distance
                if min_dist < required_dist:
                    valid = False
                    break
            
            if valid:
                positions.append(pos)
            
            attempts += 1
        
        if len(positions) < num_warriors:
            # Fallback: evenly space warriors
            spacing = self.core_size // num_warriors
            positions = [i * spacing for i in range(num_warriors)]
        
        return positions
    
    def run(self, warriors: List[Warrior]) -> BattleResult:
        """
        Run a battle between warriors.
        
        Args:
            warriors: List of Warrior objects to battle
            
        Returns:
            BattleResult with winner and metrics
        """
        if len(warriors) < 2:
            raise ValueError("Need at least 2 warriors for a battle")
        
        # Run multiple rounds and aggregate
        wins = {i: 0 for i in range(len(warriors))}
        draws = 0
        all_metrics: Dict[int, Dict[str, List[float]]] = {
            i: {"memory_coverage": [], "threads_spawned": [], 
                "instructions_executed": [], "memory_writes": []}
            for i in range(len(warriors))
        }
        total_cycles = 0
        
        for _ in range(self.num_rounds):
            # Create fresh MARS
            mars = MARS(
                core_size=self.core_size,
                max_cycles=self.max_cycles,
                max_processes=self.max_processes,
                max_length=self.max_length,
                min_distance=self.min_distance,
            )
            
            # Generate random positions
            lengths = [len(w) for w in warriors]
            positions = self._generate_positions(len(warriors), lengths)
            
            # Load warriors
            for i, (warrior, pos) in enumerate(zip(warriors, positions)):
                mars.load_warrior(warrior, pos, i)
            
            # Run battle
            winner = mars.run()
            total_cycles += mars.cycle
            
            # Track results
            if winner is not None:
                wins[winner] += 1
            else:
                draws += 1
            
            # Collect metrics
            for i in range(len(warriors)):
                metrics = mars.get_behavioral_metrics(i)
                for key, value in metrics.items():
                    if key in all_metrics[i]:
                        all_metrics[i][key].append(value)
        
        # Determine overall winner (most wins, or draw if tied)
        max_wins = max(wins.values())
        winners = [i for i, w in wins.items() if w == max_wins]
        
        if len(winners) == 1 and max_wins > draws:
            final_winner = winners[0]
        else:
            final_winner = None
        
        # Average metrics
        avg_metrics = {}
        for i, metrics_dict in all_metrics.items():
            avg_metrics[i] = {
                key: sum(values) / len(values) if values else 0.0
                for key, values in metrics_dict.items()
            }
        
        return BattleResult(
            winner_id=final_winner,
            warrior_ids=list(range(len(warriors))),
            warrior_names={i: w.name for i, w in enumerate(warriors)},
            cycles=total_cycles // self.num_rounds,
            metrics=avg_metrics,
        )
    
    def run_tournament(
        self, 
        warriors: List[Warrior],
        rounds_per_match: int = 10,
    ) -> Dict[int, Dict[str, float]]:
        """
        Run a round-robin tournament between all warriors.
        
        Args:
            warriors: List of warriors to compete
            rounds_per_match: Rounds per head-to-head match
            
        Returns:
            Dict mapping warrior index to tournament statistics
        """
        n = len(warriors)
        stats = {
            i: {"wins": 0, "losses": 0, "draws": 0, "points": 0.0}
            for i in range(n)
        }
        
        # Each pair fights
        for i in range(n):
            for j in range(i + 1, n):
                # Run match
                original_rounds = self.num_rounds
                self.num_rounds = rounds_per_match
                
                result = self.run([warriors[i], warriors[j]])
                
                self.num_rounds = original_rounds
                
                # Update stats
                if result.winner_id == 0:
                    stats[i]["wins"] += 1
                    stats[j]["losses"] += 1
                    stats[i]["points"] += 3.0
                elif result.winner_id == 1:
                    stats[j]["wins"] += 1
                    stats[i]["losses"] += 1
                    stats[j]["points"] += 3.0
                else:
                    stats[i]["draws"] += 1
                    stats[j]["draws"] += 1
                    stats[i]["points"] += 1.0
                    stats[j]["points"] += 1.0
        
        return stats


def evaluate_fitness(
    challenger: Warrior,
    opponents: List[Warrior],
    battle_config: Optional[Dict] = None,
    num_battles: int = 5,
) -> Tuple[float, Dict[str, float]]:
    """
    Evaluate a challenger's fitness against a set of opponents.
    
    This is the main fitness function for the DRQ evolution loop.
    
    Args:
        challenger: The warrior to evaluate
        opponents: List of opponent warriors
        battle_config: Optional battle configuration
        num_battles: Number of battles per opponent
        
    Returns:
        Tuple of (fitness score, behavioral metrics)
    """
    if not opponents:
        return 0.0, {}
    
    config = battle_config or {}
    battle = Battle(
        core_size=config.get("core_size", 8000),
        max_cycles=config.get("max_cycles", 80000),
        num_rounds=num_battles,
    )
    
    total_score = 0.0
    all_metrics = []
    
    for opponent in opponents:
        result = battle.run([challenger, opponent])
        
        # Score: 3 for win, 1 for draw, 0 for loss
        if result.winner_id == 0:
            total_score += 3.0
        elif result.winner_id is None:
            total_score += 1.0
        # else: loss, 0 points
        
        # Collect metrics for the challenger (index 0)
        if 0 in result.metrics:
            all_metrics.append(result.metrics[0])
    
    # Normalize fitness to [0, 1]
    max_possible = 3.0 * len(opponents)
    fitness = total_score / max_possible if max_possible > 0 else 0.0
    
    # Average behavioral metrics
    avg_metrics = {}
    if all_metrics:
        for key in all_metrics[0].keys():
            avg_metrics[key] = sum(m.get(key, 0) for m in all_metrics) / len(all_metrics)
    
    return fitness, avg_metrics
