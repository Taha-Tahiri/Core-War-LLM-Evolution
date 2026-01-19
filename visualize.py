"""
Visualization Tools for Core War and DRQ

Provides tools for visualizing:
- Battle replays
- MAP-Elites archives
- Fitness curves
- Behavioral analysis
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from pathlib import Path
import json

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.animation import FuncAnimation
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

from corewar.redcode import Warrior, parse_warrior
from corewar.mars import MARS
from corewar.battle import Battle


def plot_fitness_curves(
    fitness_curves: Dict[int, List[float]],
    title: str = "DRQ Fitness Evolution",
    save_path: Optional[str] = None,
):
    """
    Plot fitness curves from DRQ rounds.
    
    Args:
        fitness_curves: Dict mapping round number to fitness values
        title: Plot title
        save_path: Optional path to save the figure
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for visualization")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color palette
    colors = plt.cm.viridis(np.linspace(0, 1, len(fitness_curves)))
    
    for (round_num, curve), color in zip(sorted(fitness_curves.items()), colors):
        ax.plot(curve, label=f"Round {round_num + 1}", color=color, linewidth=2)
    
    ax.set_xlabel("Generation", fontsize=12)
    ax.set_ylabel("Best Fitness", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_archive_heatmap(
    archive_grid: np.ndarray,
    x_label: str = "Memory Coverage",
    y_label: str = "Threads Spawned",
    title: str = "MAP-Elites Archive",
    save_path: Optional[str] = None,
):
    """
    Plot MAP-Elites archive as a heatmap.
    
    Args:
        archive_grid: 2D numpy array of fitness values
        x_label: Label for x-axis
        y_label: Label for y-axis
        title: Plot title
        save_path: Optional path to save the figure
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for visualization")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create heatmap
    im = ax.imshow(
        archive_grid.T,
        origin="lower",
        aspect="auto",
        cmap="viridis",
        vmin=0,
        vmax=1,
    )
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Fitness", fontsize=12)
    
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(title, fontsize=14)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_generality_progression(
    generality_scores: List[float],
    round_labels: Optional[List[str]] = None,
    title: str = "Generality Over DRQ Rounds",
    save_path: Optional[str] = None,
):
    """
    Plot how generality improves over DRQ rounds.
    
    Args:
        generality_scores: List of generality scores per round
        round_labels: Optional labels for each round
        title: Plot title
        save_path: Optional path to save the figure
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for visualization")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    rounds = range(1, len(generality_scores) + 1)
    
    ax.plot(rounds, generality_scores, 'o-', linewidth=2, markersize=8, color='#2ecc71')
    ax.fill_between(rounds, generality_scores, alpha=0.3, color='#2ecc71')
    
    ax.set_xlabel("DRQ Round", fontsize=12)
    ax.set_ylabel("Generality Score", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    
    if round_labels:
        ax.set_xticks(rounds)
        ax.set_xticklabels(round_labels, rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_battle_comparison(
    warriors: List[Warrior],
    core_size: int = 8000,
    max_cycles: int = 80000,
    num_battles: int = 10,
    save_path: Optional[str] = None,
):
    """
    Create a head-to-head comparison matrix of warriors.
    
    Args:
        warriors: List of warriors to compare
        core_size: Core size for battles
        max_cycles: Max cycles per battle
        num_battles: Battles per matchup
        save_path: Optional path to save the figure
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for visualization")
        return
    
    n = len(warriors)
    win_matrix = np.zeros((n, n))
    
    battle = Battle(
        core_size=core_size,
        max_cycles=max_cycles,
        num_rounds=num_battles,
    )
    
    # Run all matchups
    for i in range(n):
        for j in range(n):
            if i == j:
                win_matrix[i, j] = 0.5
            else:
                result = battle.run([warriors[i], warriors[j]])
                if result.winner_id == 0:
                    win_matrix[i, j] = 1.0
                elif result.winner_id is None:
                    win_matrix[i, j] = 0.5
                else:
                    win_matrix[i, j] = 0.0
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(win_matrix, cmap="RdYlGn", vmin=0, vmax=1)
    
    # Labels
    names = [w.name[:15] for w in warriors]  # Truncate long names
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_yticklabels(names)
    
    # Add text annotations
    for i in range(n):
        for j in range(n):
            val = win_matrix[i, j]
            color = 'white' if val < 0.3 or val > 0.7 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color)
    
    ax.set_xlabel("Opponent", fontsize=12)
    ax.set_ylabel("Warrior", fontsize=12)
    ax.set_title("Head-to-Head Win Rates", fontsize=14)
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Win Rate", fontsize=12)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    else:
        plt.show()
    
    plt.close()


class BattleVisualizer:
    """
    Visualizes Core War battles in real-time.
    """
    
    def __init__(self, core_size: int = 8000):
        """
        Initialize the visualizer.
        
        Args:
            core_size: Size of the core
        """
        self.core_size = core_size
        self.grid_size = int(np.ceil(np.sqrt(core_size)))
    
    def _ownership_to_image(self, ownership: List[int]) -> np.ndarray:
        """Convert ownership array to image."""
        # Pad to square
        padded = ownership + [-1] * (self.grid_size**2 - len(ownership))
        img = np.array(padded).reshape(self.grid_size, self.grid_size)
        return img
    
    def visualize_final_state(
        self,
        warriors: List[Warrior],
        max_cycles: int = 80000,
        save_path: Optional[str] = None,
    ):
        """
        Visualize the final state of a battle.
        
        Args:
            warriors: Warriors to battle
            max_cycles: Maximum cycles
            save_path: Optional path to save figure
        """
        if not HAS_MATPLOTLIB:
            print("matplotlib required for visualization")
            return
        
        # Run battle
        mars = MARS(core_size=self.core_size, max_cycles=max_cycles)
        
        spacing = self.core_size // len(warriors)
        for i, w in enumerate(warriors):
            mars.load_warrior(w, i * spacing, i)
        
        mars.run()
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 10))
        
        img = self._ownership_to_image(mars.ownership)
        
        # Custom colormap: unowned=black, warrior colors
        cmap = plt.cm.get_cmap('tab10', len(warriors) + 1)
        colors = ['#1a1a2e']  # Dark background for unowned
        for i in range(len(warriors)):
            colors.append(cmap(i))
        
        from matplotlib.colors import ListedColormap
        custom_cmap = ListedColormap(colors)
        
        im = ax.imshow(img + 1, cmap=custom_cmap, vmin=0, vmax=len(warriors))
        
        # Legend
        patches = [
            mpatches.Patch(color=colors[0], label='Unowned'),
        ]
        for i, w in enumerate(warriors):
            patches.append(mpatches.Patch(color=colors[i + 1], label=w.name[:20]))
        ax.legend(handles=patches, loc='upper right')
        
        ax.set_title(f"Core State after {mars.cycle} cycles", fontsize=14)
        ax.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Saved to {save_path}")
        else:
            plt.show()
        
        plt.close()


def analyze_drq_run(output_dir: str) -> Dict:
    """
    Analyze a completed DRQ run from saved files.
    
    Args:
        output_dir: Path to DRQ output directory
        
    Returns:
        Analysis results
    """
    output_path = Path(output_dir)
    
    # Find latest run
    runs = sorted(output_path.glob("run_*"))
    if not runs:
        raise ValueError(f"No runs found in {output_dir}")
    
    latest_run = runs[-1]
    
    # Load summary
    summary_path = latest_run / "summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
    else:
        summary = {}
    
    # Load round metrics
    round_metrics = []
    for round_dir in sorted(latest_run.glob("round_*")):
        metrics_path = round_dir / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                round_metrics.append(json.load(f))
    
    # Compute statistics
    if round_metrics:
        fitness_values = [r["fitness"] for r in round_metrics]
        analysis = {
            "num_rounds": len(round_metrics),
            "final_fitness": fitness_values[-1],
            "mean_fitness": np.mean(fitness_values),
            "fitness_improvement": fitness_values[-1] - fitness_values[0] if len(fitness_values) > 1 else 0,
            "summary": summary,
            "round_metrics": round_metrics,
        }
    else:
        analysis = {"summary": summary, "round_metrics": []}
    
    return analysis


def compare_llm_runs(output_dirs: List[str]) -> Dict:
    """
    Compare multiple DRQ runs with different LLMs.
    
    Args:
        output_dirs: List of output directories to compare
        
    Returns:
        Comparison results
    """
    results = {}
    
    for output_dir in output_dirs:
        try:
            analysis = analyze_drq_run(output_dir)
            llm_name = analysis.get("summary", {}).get("llm", Path(output_dir).name)
            results[llm_name] = analysis
        except Exception as e:
            print(f"Error analyzing {output_dir}: {e}")
    
    return results
