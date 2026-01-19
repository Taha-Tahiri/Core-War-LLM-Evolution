"""
Digital Red Queen - Main Evolution Algorithm

Implements the DRQ self-play algorithm for evolving Core War warriors
using LLMs and quality-diversity optimization.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
import json
import os
from datetime import datetime
from pathlib import Path

from corewar.redcode import Warrior, parse_warrior, warrior_to_string, WARRIORS
from corewar.battle import Battle, evaluate_fitness
from evolution.map_elites import MAPElites, BehaviorDescriptor, EliteCell
from evolution.fitness import FitnessEvaluator, FitnessConfig
from llm_interface.base import LLMProvider, WarriorGenerator, GenerationConfig


@dataclass
class DRQConfig:
    """Configuration for Digital Red Queen algorithm."""
    
    # Evolution parameters
    num_rounds: int = 10                    # Number of DRQ rounds
    generations_per_round: int = 50         # Generations of MAP-Elites per round
    initial_population_size: int = 50       # Initial random warriors per round
    batch_size: int = 10                    # Warriors to generate per generation
    
    # History parameters
    history_length: int = -1                # -1 = full history, >0 = last K champions
    
    # Battle configuration
    core_size: int = 8000
    max_cycles: int = 80000
    battles_per_evaluation: int = 5
    
    # MAP-Elites behavior space
    memory_coverage_bins: int = 10
    threads_spawned_bins: int = 10
    max_threads_expected: int = 100
    
    # LLM generation
    temperature: float = 0.8
    max_warrior_length: int = 50
    
    # Output
    output_dir: str = "./drq_output"
    save_checkpoints: bool = True
    verbose: bool = True


@dataclass
class RoundResult:
    """Results from a single DRQ round."""
    round_number: int
    champion: Warrior
    champion_fitness: float
    champion_metrics: Dict[str, float]
    
    # Evolution statistics
    archive_size: int
    total_evaluations: int
    best_fitness_curve: List[float] = field(default_factory=list)
    
    # Performance vs history
    vs_history: Dict[str, float] = field(default_factory=dict)


class DigitalRedQueen:
    """
    Digital Red Queen Evolution Algorithm.
    
    Evolves Core War warriors through adversarial self-play:
    1. Start with initial warrior(s)
    2. Each round, use MAP-Elites to evolve a new champion
    3. New champion must defeat all previous champions
    4. Repeat for multiple rounds
    
    Based on: "Digital Red Queen: Adversarial Program Evolution in Core War with LLMs"
    https://pub.sakana.ai/drq/
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        config: Optional[DRQConfig] = None,
        initial_warriors: Optional[List[Warrior]] = None,
    ):
        """
        Initialize DRQ.
        
        Args:
            llm_provider: LLM provider for warrior generation
            config: Algorithm configuration
            initial_warriors: Optional list of starting warriors
        """
        self.config = config or DRQConfig()
        self.llm = llm_provider
        
        # Initialize warrior generator
        gen_config = GenerationConfig(
            temperature=self.config.temperature,
            max_warrior_length=self.config.max_warrior_length,
        )
        self.generator = WarriorGenerator(llm_provider, gen_config)
        
        # Initialize fitness evaluator
        fitness_config = FitnessConfig(
            core_size=self.config.core_size,
            max_cycles=self.config.max_cycles,
            battles_per_opponent=self.config.battles_per_evaluation,
        )
        self.evaluator = FitnessEvaluator(fitness_config)
        
        # Champion history
        self.champions: List[Warrior] = []
        self.round_results: List[RoundResult] = []
        
        # Initialize with starting warriors
        if initial_warriors:
            self.champions = initial_warriors.copy()
        else:
            # Start with classic warriors
            self.champions = [
                parse_warrior(WARRIORS["imp"]),
                parse_warrior(WARRIORS["dwarf"]),
            ]
        
        # Create output directory
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run ID for this experiment
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_opponents(self) -> List[Warrior]:
        """Get the list of opponents for the current round."""
        if self.config.history_length < 0:
            # Full history
            return self.champions.copy()
        elif self.config.history_length == 0:
            # Only the last champion
            return [self.champions[-1]] if self.champions else []
        else:
            # Last K champions
            return self.champions[-self.config.history_length:]
    
    def _create_behavior_descriptor(self) -> BehaviorDescriptor:
        """Create the behavioral descriptor for MAP-Elites."""
        return BehaviorDescriptor(axes=[
            ("memory_coverage", 0.0, 1.0, self.config.memory_coverage_bins),
            ("threads_spawned", 0, self.config.max_threads_expected, 
             self.config.threads_spawned_bins),
        ])
    
    def _run_round(self, round_num: int) -> RoundResult:
        """
        Run a single DRQ round.
        
        Args:
            round_num: The round number (0-indexed)
            
        Returns:
            RoundResult with the champion and statistics
        """
        if self.config.verbose:
            print(f"\n{'='*60}")
            print(f"DRQ Round {round_num + 1}/{self.config.num_rounds}")
            print(f"{'='*60}")
            print(f"Opponents: {len(self._get_opponents())} champions in history")
        
        opponents = self._get_opponents()
        
        # Create evaluation function for this round
        def evaluate(warrior: Warrior) -> Tuple[float, Dict[str, float]]:
            return self.evaluator.evaluate(warrior, opponents)
        
        # Create MAP-Elites instance
        map_elites = MAPElites(
            behavior_descriptor=self._create_behavior_descriptor(),
            initial_population_size=self.config.initial_population_size,
            batch_size=self.config.batch_size,
        )
        
        # Generation function
        def generate() -> Warrior:
            return self.generator.generate_random()
        
        # Mutation function
        def mutate(warrior: Warrior) -> Warrior:
            return self.generator.mutate(warrior)
        
        # Track fitness curve
        fitness_curve = []
        
        # Initialize archive
        if self.config.verbose:
            print("\nInitializing archive...")
        
        map_elites.initialize(generate, evaluate)
        
        best = map_elites.get_best()
        if best:
            fitness_curve.append(best.fitness)
        
        # Evolution loop
        for gen in range(self.config.generations_per_round):
            updates = map_elites.step(mutate, evaluate)
            
            best = map_elites.get_best()
            if best:
                fitness_curve.append(best.fitness)
            
            if self.config.verbose and (gen + 1) % 10 == 0:
                print(
                    f"  Gen {gen + 1}: archive={len(map_elites.archive)}, "
                    f"updates={updates}, best={best.fitness:.4f if best else 0:.4f}"
                )
        
        # Get the champion
        champion_cell = map_elites.get_best()
        
        if champion_cell is None:
            # Fallback if no warriors evolved
            champion = parse_warrior(WARRIORS["dwarf"])
            champion.name = f"Fallback_Round{round_num}"
            champion_fitness = 0.0
            champion_metrics = {}
        else:
            champion = champion_cell.solution
            champion.name = f"{champion.name}_R{round_num}"
            champion_fitness = champion_cell.fitness
            champion_metrics = champion_cell.metrics
        
        # Create result
        result = RoundResult(
            round_number=round_num,
            champion=champion,
            champion_fitness=champion_fitness,
            champion_metrics=champion_metrics,
            archive_size=len(map_elites.archive),
            total_evaluations=map_elites.stats["total_evaluations"],
            best_fitness_curve=fitness_curve,
        )
        
        # Evaluate vs each opponent individually
        for i, opp in enumerate(opponents):
            h2h = self.evaluator.head_to_head(champion, opp)
            result.vs_history[f"vs_{opp.name}"] = h2h.get("warrior1_win_rate", 0.5)
        
        if self.config.verbose:
            print(f"\nRound {round_num + 1} Complete!")
            print(f"  Champion: {champion.name}")
            print(f"  Fitness: {champion_fitness:.4f}")
            print(f"  Archive size: {result.archive_size}")
        
        return result
    
    def run(self) -> List[Warrior]:
        """
        Run the full DRQ evolution.
        
        Returns:
            List of champion warriors from each round
        """
        print(f"\n{'#'*60}")
        print(f"# Digital Red Queen - Core War LLM Evolution")
        print(f"# LLM: {self.llm.name}")
        print(f"# Rounds: {self.config.num_rounds}")
        print(f"# Generations per round: {self.config.generations_per_round}")
        print(f"{'#'*60}")
        
        evolved_champions = []
        
        for round_num in range(self.config.num_rounds):
            # Run round
            result = self._run_round(round_num)
            self.round_results.append(result)
            
            # Add champion to history
            self.champions.append(result.champion)
            evolved_champions.append(result.champion)
            
            # Save checkpoint
            if self.config.save_checkpoints:
                self._save_checkpoint(round_num, result)
        
        # Save final results
        self._save_final_results()
        
        return evolved_champions
    
    def _save_checkpoint(self, round_num: int, result: RoundResult):
        """Save a checkpoint after each round."""
        round_dir = self.output_dir / f"run_{self.run_id}" / f"round_{round_num:03d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        
        # Save champion source
        champion_path = round_dir / "champion.red"
        with open(champion_path, "w") as f:
            f.write(warrior_to_string(result.champion))
        
        # Save metrics
        metrics_path = round_dir / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump({
                "round": round_num,
                "champion_name": result.champion.name,
                "fitness": result.champion_fitness,
                "metrics": result.champion_metrics,
                "archive_size": result.archive_size,
                "total_evaluations": result.total_evaluations,
                "fitness_curve": result.best_fitness_curve,
                "vs_history": result.vs_history,
            }, f, indent=2)
    
    def _save_final_results(self):
        """Save final experiment results."""
        run_dir = self.output_dir / f"run_{self.run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save all champions
        champions_dir = run_dir / "champions"
        champions_dir.mkdir(exist_ok=True)
        
        for i, champion in enumerate(self.champions):
            path = champions_dir / f"champion_{i:03d}.red"
            with open(path, "w") as f:
                f.write(warrior_to_string(champion))
        
        # Save summary
        summary = {
            "run_id": self.run_id,
            "llm": self.llm.name,
            "config": {
                "num_rounds": self.config.num_rounds,
                "generations_per_round": self.config.generations_per_round,
                "history_length": self.config.history_length,
                "core_size": self.config.core_size,
                "max_cycles": self.config.max_cycles,
            },
            "results": [
                {
                    "round": r.round_number,
                    "champion": r.champion.name,
                    "fitness": r.champion_fitness,
                    "archive_size": r.archive_size,
                }
                for r in self.round_results
            ],
            "generator_stats": self.generator.get_stats(),
        }
        
        with open(run_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nResults saved to: {run_dir}")
    
    def evaluate_generality(
        self,
        test_warriors: List[Warrior],
        champion_idx: int = -1,
    ) -> Dict[str, float]:
        """
        Evaluate a champion's generality against held-out warriors.
        
        Args:
            test_warriors: List of test warriors
            champion_idx: Index of champion to test (-1 for latest)
            
        Returns:
            Generality metrics
        """
        champion = self.champions[champion_idx]
        return self.evaluator.evaluate_generality(champion, test_warriors)
    
    def get_fitness_curves(self) -> Dict[int, List[float]]:
        """Get fitness curves from all rounds."""
        return {
            r.round_number: r.best_fitness_curve
            for r in self.round_results
        }
    
    def get_champions(self) -> List[Warrior]:
        """Get all champions."""
        return self.champions.copy()


def run_drq_experiment(
    llm_provider: LLMProvider,
    num_rounds: int = 10,
    generations_per_round: int = 50,
    output_dir: str = "./drq_output",
    verbose: bool = True,
) -> List[Warrior]:
    """
    Convenience function to run a DRQ experiment.
    
    Args:
        llm_provider: The LLM provider to use
        num_rounds: Number of DRQ rounds
        generations_per_round: Generations of MAP-Elites per round
        output_dir: Output directory for results
        verbose: Whether to print progress
        
    Returns:
        List of evolved champion warriors
    """
    config = DRQConfig(
        num_rounds=num_rounds,
        generations_per_round=generations_per_round,
        output_dir=output_dir,
        verbose=verbose,
    )
    
    drq = DigitalRedQueen(llm_provider, config)
    return drq.run()
