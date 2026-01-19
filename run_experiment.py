#!/usr/bin/env python3
"""
Digital Red Queen - Experiment Runner

Run Core War evolution experiments with various LLMs.

Usage:
    # Single LLM experiment
    python run_experiment.py --llm openai --model gpt-4 --rounds 10
    
    # Compare multiple LLMs
    python run_experiment.py --compare --llms openai,anthropic,ollama --rounds 5
    
    # Quick demo run
    python run_experiment.py --demo
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from corewar.redcode import Warrior, parse_warrior, WARRIORS
from corewar.battle import Battle
from drq import DigitalRedQueen, DRQConfig
from visualize import (
    plot_fitness_curves, 
    plot_battle_comparison,
    analyze_drq_run,
    BattleVisualizer,
)


def get_llm_provider(provider_name: str, model: str = None):
    """
    Get an LLM provider by name.
    
    Args:
        provider_name: One of 'openai', 'anthropic', 'ollama'
        model: Optional model name
        
    Returns:
        LLMProvider instance
    """
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        from llm_interface import OpenAIProvider
        model = model or "gpt-4"
        return OpenAIProvider(model=model)
        
    elif provider_name == "anthropic":
        from llm_interface import AnthropicProvider
        model = model or "claude-3-sonnet-20240229"
        return AnthropicProvider(model=model)
        
    elif provider_name == "ollama":
        from llm_interface import OllamaProvider
        model = model or "llama3"
        return OllamaProvider(model=model)
        
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def run_demo():
    """Run a quick demo battle between classic warriors."""
    print("\n" + "="*60)
    print("CORE WAR DEMO - Classic Warriors Battle")
    print("="*60 + "\n")
    
    # Parse classic warriors
    warriors = [
        parse_warrior(WARRIORS["imp"]),
        parse_warrior(WARRIORS["dwarf"]),
    ]
    
    print(f"Warriors: {', '.join(w.name for w in warriors)}")
    print()
    
    # Run battle
    battle = Battle(core_size=8000, max_cycles=80000, num_rounds=10)
    result = battle.run(warriors)
    
    print(f"Winner: {result.get_winner_name()}")
    print(f"Cycles: {result.cycles}")
    print()
    
    # Show behavioral metrics
    for wid, metrics in result.metrics.items():
        name = result.warrior_names[wid]
        print(f"{name}:")
        print(f"  Memory coverage: {metrics.get('memory_coverage', 0):.2%}")
        print(f"  Threads spawned: {metrics.get('threads_spawned', 0)}")
        print(f"  Instructions executed: {metrics.get('instructions_executed', 0)}")
    
    print("\n" + "="*60)
    print("Demo complete! To run a full DRQ evolution:")
    print("  python run_experiment.py --llm openai --model gpt-4 --rounds 5")
    print("="*60 + "\n")


def run_single_experiment(
    provider_name: str,
    model: str,
    num_rounds: int,
    generations: int,
    output_dir: str,
    verbose: bool = True,
):
    """
    Run a single DRQ experiment with one LLM.
    
    Args:
        provider_name: LLM provider name
        model: Model name
        num_rounds: Number of DRQ rounds
        generations: Generations per round
        output_dir: Output directory
        verbose: Whether to print progress
    """
    print("\n" + "="*60)
    print(f"Digital Red Queen Experiment")
    print(f"LLM: {provider_name}/{model}")
    print(f"Rounds: {num_rounds}, Generations: {generations}")
    print("="*60 + "\n")
    
    # Get LLM provider
    try:
        llm = get_llm_provider(provider_name, model)
        print(f"✓ Initialized {llm.name}")
    except Exception as e:
        print(f"✗ Failed to initialize LLM: {e}")
        print("\nMake sure you have the required API key set:")
        print("  export OPENAI_API_KEY='your-key'")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("Or for Ollama, make sure it's running: ollama serve")
        return
    
    # Configure DRQ
    config = DRQConfig(
        num_rounds=num_rounds,
        generations_per_round=generations,
        output_dir=output_dir,
        verbose=verbose,
    )
    
    # Run evolution
    drq = DigitalRedQueen(llm, config)
    champions = drq.run()
    
    print(f"\n✓ Evolution complete!")
    print(f"  Champions: {len(champions)}")
    print(f"  Output: {drq.output_dir / f'run_{drq.run_id}'}")
    
    # Generate visualizations
    try:
        fitness_curves = drq.get_fitness_curves()
        plot_path = drq.output_dir / f"run_{drq.run_id}" / "fitness_curves.png"
        plot_fitness_curves(fitness_curves, save_path=str(plot_path))
        print(f"  Fitness plot: {plot_path}")
    except Exception as e:
        print(f"  (Skipped visualization: {e})")
    
    return drq


def run_comparison(
    providers: list,
    num_rounds: int,
    generations: int,
    output_dir: str,
):
    """
    Compare multiple LLMs in DRQ experiments.
    
    Args:
        providers: List of (provider_name, model) tuples
        num_rounds: Number of DRQ rounds
        generations: Generations per round
        output_dir: Base output directory
    """
    print("\n" + "="*60)
    print("Digital Red Queen - LLM Comparison")
    print(f"Providers: {len(providers)}")
    print(f"Rounds: {num_rounds}, Generations: {generations}")
    print("="*60 + "\n")
    
    results = {}
    
    for provider_name, model in providers:
        print(f"\n>>> Running with {provider_name}/{model}")
        
        llm_output = os.path.join(output_dir, f"{provider_name}_{model}")
        
        try:
            drq = run_single_experiment(
                provider_name=provider_name,
                model=model,
                num_rounds=num_rounds,
                generations=generations,
                output_dir=llm_output,
                verbose=True,
            )
            
            if drq:
                results[f"{provider_name}/{model}"] = {
                    "champions": len(drq.champions),
                    "final_fitness": drq.round_results[-1].champion_fitness if drq.round_results else 0,
                    "output_dir": llm_output,
                }
        except Exception as e:
            print(f"✗ Failed: {e}")
            results[f"{provider_name}/{model}"] = {"error": str(e)}
    
    # Print summary
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    for llm_name, res in results.items():
        if "error" in res:
            print(f"  {llm_name}: FAILED - {res['error']}")
        else:
            print(f"  {llm_name}: {res['champions']} champions, final fitness {res['final_fitness']:.4f}")
    
    print("="*60 + "\n")
    
    return results


def run_tournament(warriors_dir: str, num_battles: int = 10):
    """
    Run a tournament between warriors in a directory.
    
    Args:
        warriors_dir: Directory containing .red files
        num_battles: Battles per matchup
    """
    warriors_path = Path(warriors_dir)
    
    # Load warriors
    warriors = []
    for red_file in warriors_path.glob("*.red"):
        try:
            with open(red_file) as f:
                warrior = parse_warrior(f.read())
                warriors.append(warrior)
                print(f"Loaded: {warrior.name}")
        except Exception as e:
            print(f"Failed to load {red_file}: {e}")
    
    if len(warriors) < 2:
        print("Need at least 2 warriors for a tournament")
        return
    
    print(f"\nRunning tournament with {len(warriors)} warriors...")
    
    battle = Battle(core_size=8000, max_cycles=80000, num_rounds=num_battles)
    stats = battle.run_tournament(warriors)
    
    # Print results
    print("\n" + "="*60)
    print("TOURNAMENT RESULTS")
    print("="*60)
    
    # Sort by points
    sorted_stats = sorted(
        [(warriors[i].name, s) for i, s in stats.items()],
        key=lambda x: x[1]["points"],
        reverse=True,
    )
    
    for rank, (name, s) in enumerate(sorted_stats, 1):
        print(f"{rank}. {name}: {s['points']:.0f} pts (W:{s['wins']} D:{s['draws']} L:{s['losses']})")
    
    print("="*60 + "\n")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Digital Red Queen - Core War LLM Evolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_experiment.py --demo
  python run_experiment.py --llm openai --model gpt-4 --rounds 10
  python run_experiment.py --compare --llms openai:gpt-4,anthropic:claude-3-sonnet-20240229
  python run_experiment.py --tournament ./warriors
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a quick demo battle",
    )
    
    parser.add_argument(
        "--llm",
        type=str,
        choices=["openai", "anthropic", "ollama"],
        help="LLM provider to use",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Model name (e.g., gpt-4, claude-3-sonnet-20240229, llama3)",
    )
    
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="Number of DRQ rounds (default: 5)",
    )
    
    parser.add_argument(
        "--generations",
        type=int,
        default=30,
        help="Generations per round (default: 30)",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="./drq_output",
        help="Output directory (default: ./drq_output)",
    )
    
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare multiple LLMs",
    )
    
    parser.add_argument(
        "--llms",
        type=str,
        help="Comma-separated LLMs for comparison (e.g., openai:gpt-4,anthropic:claude-3-sonnet-20240229)",
    )
    
    parser.add_argument(
        "--tournament",
        type=str,
        help="Run tournament with warriors from directory",
    )
    
    args = parser.parse_args()
    
    # Handle different modes
    if args.demo:
        run_demo()
        
    elif args.tournament:
        run_tournament(args.tournament)
        
    elif args.compare and args.llms:
        # Parse LLM specs
        providers = []
        for spec in args.llms.split(","):
            if ":" in spec:
                provider, model = spec.split(":", 1)
            else:
                provider = spec
                model = None
            providers.append((provider.strip(), model))
        
        run_comparison(
            providers=providers,
            num_rounds=args.rounds,
            generations=args.generations,
            output_dir=args.output,
        )
        
    elif args.llm:
        run_single_experiment(
            provider_name=args.llm,
            model=args.model,
            num_rounds=args.rounds,
            generations=args.generations,
            output_dir=args.output,
        )
        
    else:
        parser.print_help()
        print("\nQuick start: python run_experiment.py --demo")


if __name__ == "__main__":
    main()
