"""
Fitness Evaluation for Core War Warriors

Provides fitness evaluation functions for the DRQ evolution loop.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corewar.redcode import Warrior, parse_warrior
from corewar.battle import Battle, evaluate_fitness


@dataclass
class FitnessConfig:
    """Configuration for fitness evaluation."""
    core_size: int = 8000
    max_cycles: int = 80000
    battles_per_opponent: int = 5
    
    # Scoring weights
    win_score: float = 3.0
    draw_score: float = 1.0
    loss_score: float = 0.0


class FitnessEvaluator:
    """
    Evaluates warrior fitness for DRQ evolution.
    
    Handles:
    - Single opponent evaluation
    - Multi-opponent (historical) evaluation
    - Generality evaluation against held-out warriors
    """
    
    def __init__(self, config: Optional[FitnessConfig] = None):
        """
        Initialize the fitness evaluator.
        
        Args:
            config: Fitness evaluation configuration
        """
        self.config = config or FitnessConfig()
        
        # Statistics
        self.total_evaluations = 0
        self.cache_hits = 0
        
        # Optional caching (disabled by default due to stochasticity)
        self._cache: Dict[str, Tuple[float, Dict]] = {}
        self.use_cache = False
    
    def evaluate(
        self,
        warrior: Warrior,
        opponents: List[Warrior],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate a warrior against a set of opponents.
        
        This is the main fitness function for DRQ.
        
        Args:
            warrior: The warrior to evaluate
            opponents: List of opponent warriors
            
        Returns:
            Tuple of (fitness score in [0,1], behavioral metrics)
        """
        if not opponents:
            return 0.0, {}
        
        self.total_evaluations += 1
        
        battle = Battle(
            core_size=self.config.core_size,
            max_cycles=self.config.max_cycles,
            num_rounds=self.config.battles_per_opponent,
        )
        
        total_score = 0.0
        all_metrics = []
        
        for opponent in opponents:
            result = battle.run([warrior, opponent])
            
            # Scoring
            if result.winner_id == 0:
                total_score += self.config.win_score
            elif result.winner_id is None:
                total_score += self.config.draw_score
            else:
                total_score += self.config.loss_score
            
            # Collect behavioral metrics
            if 0 in result.metrics:
                all_metrics.append(result.metrics[0])
        
        # Normalize fitness
        max_score = self.config.win_score * len(opponents)
        fitness = total_score / max_score if max_score > 0 else 0.0
        
        # Average behavioral metrics
        avg_metrics = {}
        if all_metrics:
            for key in all_metrics[0].keys():
                avg_metrics[key] = sum(m.get(key, 0) for m in all_metrics) / len(all_metrics)
        
        return fitness, avg_metrics
    
    def evaluate_generality(
        self,
        warrior: Warrior,
        test_warriors: List[Warrior],
    ) -> Dict[str, float]:
        """
        Evaluate a warrior's generality against a held-out test set.
        
        Used to measure how well warriors perform against unseen opponents.
        
        Args:
            warrior: The warrior to evaluate
            test_warriors: List of held-out test warriors
            
        Returns:
            Dict with generality metrics
        """
        if not test_warriors:
            return {"generality": 0.0, "wins": 0, "draws": 0, "losses": 0}
        
        battle = Battle(
            core_size=self.config.core_size,
            max_cycles=self.config.max_cycles,
            num_rounds=self.config.battles_per_opponent,
        )
        
        wins = 0
        draws = 0
        losses = 0
        
        for test_warrior in test_warriors:
            result = battle.run([warrior, test_warrior])
            
            if result.winner_id == 0:
                wins += 1
            elif result.winner_id is None:
                draws += 1
            else:
                losses += 1
        
        total = len(test_warriors)
        
        return {
            "generality": (wins + 0.5 * draws) / total,
            "win_rate": wins / total,
            "draw_rate": draws / total,
            "loss_rate": losses / total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
        }
    
    def head_to_head(
        self,
        warrior1: Warrior,
        warrior2: Warrior,
        num_battles: int = 10,
    ) -> Dict[str, float]:
        """
        Run head-to-head battles between two warriors.
        
        Args:
            warrior1: First warrior
            warrior2: Second warrior
            num_battles: Number of battles to run
            
        Returns:
            Dict with battle results
        """
        battle = Battle(
            core_size=self.config.core_size,
            max_cycles=self.config.max_cycles,
            num_rounds=num_battles,
        )
        
        result = battle.run([warrior1, warrior2])
        
        # Detailed breakdown would require running individual battles
        # For now, just return the aggregate winner
        if result.winner_id == 0:
            return {
                "winner": "warrior1",
                "warrior1_win_rate": 1.0,
                "warrior2_win_rate": 0.0,
            }
        elif result.winner_id == 1:
            return {
                "winner": "warrior2",
                "warrior1_win_rate": 0.0,
                "warrior2_win_rate": 1.0,
            }
        else:
            return {
                "winner": "draw",
                "warrior1_win_rate": 0.5,
                "warrior2_win_rate": 0.5,
            }


def create_evaluator_for_opponents(
    opponents: List[Warrior],
    config: Optional[FitnessConfig] = None,
):
    """
    Create a fitness evaluation function for a fixed set of opponents.
    
    This is useful for MAP-Elites which expects a function signature of:
    evaluate(solution) -> (fitness, metrics)
    
    Args:
        opponents: List of opponent warriors
        config: Optional fitness configuration
        
    Returns:
        A callable that evaluates warriors
    """
    evaluator = FitnessEvaluator(config)
    
    def evaluate(warrior: Warrior) -> Tuple[float, Dict[str, float]]:
        return evaluator.evaluate(warrior, opponents)
    
    return evaluate
