#!/usr/bin/env python3
"""
LLM Battle - Compare different LLMs in Core War evolution.

This script runs DRQ evolution with multiple LLMs in parallel,
then pits their evolved warriors against each other to determine
which LLM produces the best warriors.

Usage:
    python llm_battle.py --llms gemini,openai,anthropic --rounds 3
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
def load_env():
    env_file = os.path.join(PROJECT_ROOT, "config.env")
    if os.path.exists(env_file):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if value.strip() and not value.strip().startswith("your-"):
                            os.environ[key.strip()] = value.strip().strip('"')

load_env()

from corewar.redcode import Warrior, parse_warrior, warrior_to_string
from corewar.battle import Battle
from drq import DigitalRedQueen, DRQConfig


def get_llm_provider(provider_name: str, model: str = None):
    """Get an LLM provider by name."""
    provider_name = provider_name.lower()
    
    if provider_name == "gemini":
        from llm_interface import GeminiProvider
        model = model or "gemini-1.5-flash"
        return GeminiProvider(model=model)
    elif provider_name == "openai":
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


def evolve_with_llm(llm_spec: str, rounds: int, generations: int) -> dict:
    """
    Run DRQ evolution with a specific LLM.
    
    Args:
        llm_spec: LLM specification (e.g., "gemini:gemini-1.5-flash")
        rounds: Number of DRQ rounds
        generations: Generations per round
        
    Returns:
        Dict with LLM name, champions, and final fitness
    """
    # Parse LLM spec
    if ":" in llm_spec:
        provider, model = llm_spec.split(":", 1)
    else:
        provider = llm_spec
        model = None
    
    try:
        llm = get_llm_provider(provider, model)
        llm_name = llm.name
        
        print(f"\n{'='*50}")
        print(f"🤖 Starting evolution with {llm_name}")
        print(f"{'='*50}")
        
        config = DRQConfig(
            num_rounds=rounds,
            generations_per_round=generations,
            verbose=True,
            output_dir=f"./drq_output/llm_battle/{provider}",
        )
        
        drq = DigitalRedQueen(llm, config)
        champions = drq.run()
        
        # Get the best champion (last one, as it beats all previous)
        best_champion = champions[-1] if champions else None
        final_fitness = drq.round_results[-1].champion_fitness if drq.round_results else 0
        
        return {
            "llm_name": llm_name,
            "provider": provider,
            "model": model,
            "champions": champions,
            "best_champion": best_champion,
            "final_fitness": final_fitness,
            "success": True,
        }
        
    except Exception as e:
        print(f"❌ Error with {llm_spec}: {e}")
        return {
            "llm_name": llm_spec,
            "provider": provider,
            "model": model,
            "champions": [],
            "best_champion": None,
            "final_fitness": 0,
            "success": False,
            "error": str(e),
        }


def run_llm_tournament(llm_results: list, battles_per_match: int = 10) -> dict:
    """
    Run a tournament between warriors evolved by different LLMs.
    
    Args:
        llm_results: List of evolution results from different LLMs
        battles_per_match: Number of battles per matchup
        
    Returns:
        Tournament results
    """
    print("\n" + "="*60)
    print("🏆 LLM TOURNAMENT - Warriors Battle!")
    print("="*60)
    
    # Filter successful evolutions with champions
    valid_results = [r for r in llm_results if r["success"] and r["best_champion"]]
    
    if len(valid_results) < 2:
        print("❌ Need at least 2 successful evolutions for a tournament")
        return {"error": "Not enough participants"}
    
    # Create battle instance
    battle = Battle(core_size=8000, max_cycles=80000, num_rounds=battles_per_match)
    
    # Initialize scores
    scores = {r["llm_name"]: {"wins": 0, "losses": 0, "draws": 0, "points": 0} 
              for r in valid_results}
    
    # Head-to-head matches
    match_results = []
    
    for i, result1 in enumerate(valid_results):
        for j, result2 in enumerate(valid_results):
            if i >= j:
                continue
            
            llm1 = result1["llm_name"]
            llm2 = result2["llm_name"]
            warrior1 = result1["best_champion"]
            warrior2 = result2["best_champion"]
            
            print(f"\n⚔️  {llm1} vs {llm2}")
            print(f"   {warrior1.name} vs {warrior2.name}")
            
            # Run battle
            battle_result = battle.run([warrior1, warrior2])
            
            if battle_result.winner_id == 0:
                winner = llm1
                scores[llm1]["wins"] += 1
                scores[llm1]["points"] += 3
                scores[llm2]["losses"] += 1
                print(f"   Winner: {llm1} 🏆")
            elif battle_result.winner_id == 1:
                winner = llm2
                scores[llm2]["wins"] += 1
                scores[llm2]["points"] += 3
                scores[llm1]["losses"] += 1
                print(f"   Winner: {llm2} 🏆")
            else:
                winner = "Draw"
                scores[llm1]["draws"] += 1
                scores[llm1]["points"] += 1
                scores[llm2]["draws"] += 1
                scores[llm2]["points"] += 1
                print(f"   Result: Draw 🤝")
            
            match_results.append({
                "llm1": llm1,
                "llm2": llm2,
                "warrior1": warrior1.name,
                "warrior2": warrior2.name,
                "winner": winner,
                "cycles": battle_result.cycles,
            })
    
    # Sort by points
    rankings = sorted(
        [(llm, s) for llm, s in scores.items()],
        key=lambda x: (x[1]["points"], x[1]["wins"]),
        reverse=True
    )
    
    return {
        "rankings": rankings,
        "scores": scores,
        "matches": match_results,
    }


def print_final_results(tournament_results: dict, llm_results: list):
    """Print the final tournament results."""
    print("\n" + "="*60)
    print("🏆 FINAL RESULTS - LLM BATTLE")
    print("="*60)
    
    rankings = tournament_results.get("rankings", [])
    
    if not rankings:
        print("No results available")
        return
    
    # Print podium
    medals = ["🥇", "🥈", "🥉"]
    
    print("\n📊 LEADERBOARD:\n")
    for i, (llm_name, scores) in enumerate(rankings):
        medal = medals[i] if i < 3 else "  "
        print(f"{medal} {i+1}. {llm_name}")
        print(f"      Points: {scores['points']} | Wins: {scores['wins']} | Draws: {scores['draws']} | Losses: {scores['losses']}")
    
    # Print evolution stats
    print("\n📈 EVOLUTION STATS:\n")
    for result in llm_results:
        if result["success"]:
            print(f"   {result['llm_name']}:")
            print(f"      Final Fitness: {result['final_fitness']:.4f}")
            print(f"      Champions Evolved: {len(result['champions'])}")
            if result["best_champion"]:
                print(f"      Best Warrior: {result['best_champion'].name}")
    
    # Declare winner
    if rankings:
        winner_name, winner_scores = rankings[0]
        print("\n" + "="*60)
        print(f"🎉 WINNER: {winner_name}")
        print(f"   with {winner_scores['points']} points!")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Battle - Compare different LLMs in Core War evolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Battle between Gemini and OpenAI
    python llm_battle.py --llms gemini,openai --rounds 3
    
    # Battle with specific models
    python llm_battle.py --llms gemini:gemini-1.5-flash,openai:gpt-4 --rounds 5
    
    # Three-way battle
    python llm_battle.py --llms gemini,openai,anthropic --rounds 3
    
    # Quick test
    python llm_battle.py --llms gemini,ollama:llama3 --rounds 2 --generations 5
        """
    )
    
    parser.add_argument(
        "--llms",
        type=str,
        required=True,
        help="Comma-separated list of LLMs (e.g., gemini,openai,anthropic or gemini:gemini-1.5-flash,openai:gpt-4)",
    )
    
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of DRQ evolution rounds per LLM (default: 3)",
    )
    
    parser.add_argument(
        "--generations",
        type=int,
        default=10,
        help="Generations per round (default: 10)",
    )
    
    parser.add_argument(
        "--battles",
        type=int,
        default=10,
        help="Battles per tournament match (default: 10)",
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run evolutions in parallel (faster but uses more API calls)",
    )
    
    args = parser.parse_args()
    
    # Parse LLM list
    llm_specs = [s.strip() for s in args.llms.split(",")]
    
    print("\n" + "#"*60)
    print("# 🔴 LLM BATTLE - Core War Evolution Competition")
    print("#"*60)
    print(f"\nCompetitors: {', '.join(llm_specs)}")
    print(f"Rounds per LLM: {args.rounds}")
    print(f"Generations per round: {args.generations}")
    print(f"Battles per match: {args.battles}")
    
    # Run evolution for each LLM
    llm_results = []
    
    if args.parallel and len(llm_specs) > 1:
        print("\n🚀 Running evolutions in parallel...")
        with ThreadPoolExecutor(max_workers=len(llm_specs)) as executor:
            futures = {
                executor.submit(evolve_with_llm, spec, args.rounds, args.generations): spec 
                for spec in llm_specs
            }
            for future in as_completed(futures):
                result = future.result()
                llm_results.append(result)
    else:
        print("\n🔄 Running evolutions sequentially...")
        for spec in llm_specs:
            result = evolve_with_llm(spec, args.rounds, args.generations)
            llm_results.append(result)
    
    # Run tournament
    tournament_results = run_llm_tournament(llm_results, args.battles)
    
    # Print final results
    print_final_results(tournament_results, llm_results)
    
    # Save results
    output_dir = Path("./drq_output/llm_battle")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"battle_{timestamp}.json"
    
    save_data = {
        "timestamp": timestamp,
        "llm_specs": llm_specs,
        "config": {
            "rounds": args.rounds,
            "generations": args.generations,
            "battles_per_match": args.battles,
        },
        "evolution_results": [
            {
                "llm_name": r["llm_name"],
                "provider": r["provider"],
                "final_fitness": r["final_fitness"],
                "success": r["success"],
                "champion_name": r["best_champion"].name if r["best_champion"] else None,
            }
            for r in llm_results
        ],
        "tournament": {
            "rankings": [(name, scores) for name, scores in tournament_results.get("rankings", [])],
            "matches": tournament_results.get("matches", []),
        },
    }
    
    with open(results_file, "w") as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n📁 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
