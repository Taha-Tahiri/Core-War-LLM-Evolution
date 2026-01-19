"""
MAP-Elites Algorithm for Quality-Diversity Optimization

This module implements the MAP-Elites algorithm used in DRQ
to maintain behavioral diversity while optimizing warrior fitness.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Any
import numpy as np
import random
from copy import deepcopy


@dataclass
class BehaviorDescriptor:
    """
    Defines the behavioral space for MAP-Elites.
    
    The DRQ paper uses two axes:
    1. Memory coverage (fraction of core addresses accessed)
    2. Threads spawned (via SPL instruction)
    """
    
    # Axis definitions: (name, min_value, max_value, num_bins)
    axes: List[Tuple[str, float, float, int]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.axes:
            # Default axes from DRQ paper
            self.axes = [
                ("memory_coverage", 0.0, 1.0, 10),  # 10 bins for coverage
                ("threads_spawned", 0, 100, 10),    # 10 bins for threads
            ]
    
    def get_cell_index(self, metrics: Dict[str, float]) -> Tuple[int, ...]:
        """
        Map behavioral metrics to a cell index in the archive.
        
        Args:
            metrics: Dict of metric name -> value
            
        Returns:
            Tuple of bin indices for each axis
        """
        indices = []
        for name, min_val, max_val, num_bins in self.axes:
            value = metrics.get(name, min_val)
            
            # Clamp to range
            value = max(min_val, min(max_val, value))
            
            # Convert to bin index
            if max_val > min_val:
                normalized = (value - min_val) / (max_val - min_val)
                bin_idx = int(normalized * (num_bins - 1))
                bin_idx = min(bin_idx, num_bins - 1)
            else:
                bin_idx = 0
            
            indices.append(bin_idx)
        
        return tuple(indices)
    
    def get_archive_shape(self) -> Tuple[int, ...]:
        """Get the shape of the archive grid."""
        return tuple(axis[3] for axis in self.axes)


@dataclass
class EliteCell:
    """A single cell in the MAP-Elites archive."""
    solution: Any  # The warrior or solution
    fitness: float
    metrics: Dict[str, float]
    generation: int = 0


class MAPElites:
    """
    MAP-Elites Quality-Diversity Algorithm.
    
    Maintains an archive of elite solutions, one per behavioral niche.
    This prevents diversity collapse during evolution.
    """
    
    def __init__(
        self,
        behavior_descriptor: Optional[BehaviorDescriptor] = None,
        initial_population_size: int = 100,
        batch_size: int = 20,
    ):
        """
        Initialize MAP-Elites.
        
        Args:
            behavior_descriptor: Defines the behavioral space
            initial_population_size: Size of initial random population
            batch_size: Number of solutions to generate per iteration
        """
        self.descriptor = behavior_descriptor or BehaviorDescriptor()
        self.initial_population_size = initial_population_size
        self.batch_size = batch_size
        
        # Initialize archive
        self.archive: Dict[Tuple[int, ...], EliteCell] = {}
        self.generation = 0
        
        # Statistics
        self.stats = {
            "total_evaluations": 0,
            "archive_updates": 0,
            "best_fitness": 0.0,
            "archive_size": 0,
        }
    
    def initialize(
        self,
        generate_fn: Callable[[], Any],
        evaluate_fn: Callable[[Any], Tuple[float, Dict[str, float]]],
    ):
        """
        Initialize the archive with random solutions.
        
        Args:
            generate_fn: Function that generates a random solution
            evaluate_fn: Function that returns (fitness, metrics) for a solution
        """
        for _ in range(self.initial_population_size):
            solution = generate_fn()
            fitness, metrics = evaluate_fn(solution)
            self._try_add(solution, fitness, metrics)
    
    def _try_add(
        self, 
        solution: Any, 
        fitness: float, 
        metrics: Dict[str, float]
    ) -> bool:
        """
        Try to add a solution to the archive.
        
        Returns:
            True if the solution was added/updated
        """
        cell_idx = self.descriptor.get_cell_index(metrics)
        
        self.stats["total_evaluations"] += 1
        
        # Check if cell is empty or new solution is better
        if cell_idx not in self.archive:
            self.archive[cell_idx] = EliteCell(
                solution=solution,
                fitness=fitness,
                metrics=metrics,
                generation=self.generation,
            )
            self.stats["archive_updates"] += 1
            self.stats["archive_size"] = len(self.archive)
            if fitness > self.stats["best_fitness"]:
                self.stats["best_fitness"] = fitness
            return True
        
        elif fitness > self.archive[cell_idx].fitness:
            self.archive[cell_idx] = EliteCell(
                solution=solution,
                fitness=fitness,
                metrics=metrics,
                generation=self.generation,
            )
            self.stats["archive_updates"] += 1
            if fitness > self.stats["best_fitness"]:
                self.stats["best_fitness"] = fitness
            return True
        
        return False
    
    def sample_elite(self) -> Optional[EliteCell]:
        """Sample a random elite from the archive."""
        if not self.archive:
            return None
        return random.choice(list(self.archive.values()))
    
    def sample_elites(self, n: int) -> List[EliteCell]:
        """Sample n random elites from the archive."""
        if not self.archive:
            return []
        return random.choices(list(self.archive.values()), k=min(n, len(self.archive)))
    
    def get_best(self) -> Optional[EliteCell]:
        """Get the elite with highest fitness."""
        if not self.archive:
            return None
        return max(self.archive.values(), key=lambda e: e.fitness)
    
    def step(
        self,
        mutate_fn: Callable[[Any], Any],
        evaluate_fn: Callable[[Any], Tuple[float, Dict[str, float]]],
    ) -> int:
        """
        Run one iteration of MAP-Elites.
        
        Args:
            mutate_fn: Function to mutate a solution
            evaluate_fn: Function to evaluate a solution
            
        Returns:
            Number of archive updates
        """
        self.generation += 1
        updates = 0
        
        for _ in range(self.batch_size):
            # Sample a parent
            parent = self.sample_elite()
            if parent is None:
                continue
            
            # Generate offspring
            offspring = mutate_fn(parent.solution)
            
            # Evaluate
            fitness, metrics = evaluate_fn(offspring)
            
            # Try to add to archive
            if self._try_add(offspring, fitness, metrics):
                updates += 1
        
        return updates
    
    def run(
        self,
        generate_fn: Callable[[], Any],
        mutate_fn: Callable[[Any], Any],
        evaluate_fn: Callable[[Any], Tuple[float, Dict[str, float]]],
        num_generations: int = 100,
        verbose: bool = True,
    ) -> EliteCell:
        """
        Run the full MAP-Elites algorithm.
        
        Args:
            generate_fn: Function to generate random solutions
            mutate_fn: Function to mutate solutions
            evaluate_fn: Function to evaluate solutions
            num_generations: Number of generations to run
            verbose: Whether to print progress
            
        Returns:
            The best elite found
        """
        # Initialize
        if not self.archive:
            if verbose:
                print("Initializing archive...")
            self.initialize(generate_fn, evaluate_fn)
            if verbose:
                print(f"  Archive size: {len(self.archive)}")
        
        # Evolution loop
        for gen in range(num_generations):
            updates = self.step(mutate_fn, evaluate_fn)
            
            if verbose and (gen + 1) % 10 == 0:
                best = self.get_best()
                print(
                    f"Gen {gen + 1}: archive={len(self.archive)}, "
                    f"updates={updates}, best_fitness={best.fitness:.4f}"
                )
        
        return self.get_best()
    
    def get_archive_grid(self) -> np.ndarray:
        """
        Get the archive as a 2D fitness grid (for visualization).
        
        Only works for 2-axis behavioral descriptors.
        """
        shape = self.descriptor.get_archive_shape()
        if len(shape) != 2:
            raise ValueError("get_archive_grid only works for 2D archives")
        
        grid = np.full(shape, np.nan)
        for cell_idx, elite in self.archive.items():
            grid[cell_idx] = elite.fitness
        
        return grid
    
    def get_all_elites(self) -> List[EliteCell]:
        """Get all elites in the archive."""
        return list(self.archive.values())
    
    def clear(self):
        """Clear the archive."""
        self.archive = {}
        self.generation = 0
        self.stats = {
            "total_evaluations": 0,
            "archive_updates": 0,
            "best_fitness": 0.0,
            "archive_size": 0,
        }
