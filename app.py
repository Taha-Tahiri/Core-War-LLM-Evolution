#!/usr/bin/env python3
"""
Digital Red Queen - Interactive Web Interface

A beautiful web-based UI for running Core War LLM evolution experiments.
"""

import sys
import os
import json
import threading
import time
from pathlib import Path
from datetime import datetime

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

from flask import Flask, render_template_string, jsonify, request
from corewar.redcode import Warrior, parse_warrior, warrior_to_string, WARRIORS
from corewar.battle import Battle

app = Flask(__name__)

# Global state for tracking experiments
current_experiment = {
    "running": False,
    "progress": 0,
    "status": "idle",
    "logs": [],
    "results": None,
    "fitness_history": [],
    "round_champions": [],
    "round_curves": {},  # Store fitness curves per round
    "all_warriors": [],  # Track all warriors' performance
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Red Queen - Core War LLM Evolution</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-hover: #1a1a25;
            --accent: #00ff88;
            --accent-dim: #00cc6a;
            --accent-glow: rgba(0, 255, 136, 0.15);
            --text: #e0e0e0;
            --text-dim: #888;
            --border: #2a2a35;
            --danger: #ff4757;
            --warning: #ffa502;
            --success: #00ff88;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at top, rgba(0, 255, 136, 0.03) 0%, transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(100, 100, 255, 0.03) 0%, transparent 50%);
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
        
        header { text-align: center; margin-bottom: 1.5rem; padding: 1rem 0; }
        
        h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent) 0%, #00ccff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.3rem;
        }
        
        .subtitle { color: var(--text-dim); font-size: 1rem; }
        
        .top-section {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        @media (max-width: 1000px) {
            .top-section { grid-template-columns: 1fr; }
        }
        
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
        }
        
        .card:hover {
            border-color: var(--accent-dim);
            box-shadow: 0 0 30px var(--accent-glow);
        }
        
        .card h2 {
            font-size: 1rem;
            margin-bottom: 1rem;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .card h2::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent);
        }
        
        label { display: block; margin-bottom: 0.3rem; color: var(--text-dim); font-size: 0.8rem; }
        
        select, input[type="number"] {
            width: 100%;
            padding: 0.5rem 0.7rem;
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-bottom: 0.7rem;
            transition: all 0.2s ease;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 15px var(--accent-glow);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.7rem 1rem;
            border: none;
            border-radius: 8px;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            width: 100%;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%);
            color: var(--bg-dark);
        }
        
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px var(--accent-glow); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        .btn-secondary {
            background: var(--bg-hover);
            color: var(--text);
            border: 1px solid var(--border);
            font-size: 0.8rem;
            padding: 0.5rem;
        }
        
        .btn-secondary:hover { border-color: var(--accent); }
        
        .status-bar {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.75rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        
        .status-indicator { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--text-dim);
        }
        
        .status-dot.running { background: var(--warning); animation: pulse 1.5s infinite; }
        .status-dot.complete { background: var(--success); }
        .status-dot.error { background: var(--danger); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--warning); }
            50% { opacity: 0.5; box-shadow: none; }
        }
        
        .progress-wrapper { flex: 1; }
        
        .progress-bar {
            height: 8px;
            background: var(--bg-dark);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent) 0%, #00ccff 100%);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .main-chart {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            height: 400px;
        }
        
        .main-chart h3 {
            font-size: 1rem;
            color: var(--accent);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .chart-wrapper {
            height: calc(100% - 2rem);
            position: relative;
        }
        
        .charts-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        @media (max-width: 900px) {
            .charts-row { grid-template-columns: 1fr; }
        }
        
        .small-chart {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            height: 280px;
        }
        
        .small-chart h3 {
            font-size: 0.95rem;
            color: var(--accent);
            margin-bottom: 0.75rem;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }
        
        .result-card {
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.6rem;
            text-align: center;
        }
        
        .result-value {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--accent);
            font-family: 'JetBrains Mono', monospace;
        }
        
        .result-label { color: var(--text-dim); font-size: 0.7rem; margin-top: 0.1rem; }
        
        .log-container {
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.6rem;
            max-height: 150px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
        }
        
        .log-line { padding: 0.15rem 0; border-bottom: 1px solid var(--border); }
        .log-line:last-child { border-bottom: none; }
        .log-time { color: var(--text-dim); margin-right: 0.5rem; }
        
        .quick-actions { display: flex; gap: 0.5rem; margin-top: 0.6rem; }
        .quick-actions .btn { flex: 1; }
        
        .bottom-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        
        @media (max-width: 900px) {
            .bottom-grid { grid-template-columns: 1fr; }
        }
        
        .warrior-code {
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            white-space: pre-wrap;
            overflow-x: auto;
            max-height: 250px;
            overflow-y: auto;
        }
        
        footer {
            text-align: center;
            padding: 1.5rem;
            color: var(--text-dim);
            font-size: 0.85rem;
        }
        
        footer a { color: var(--accent); text-decoration: none; }
        footer a:hover { text-decoration: underline; }
        
        .legend-item {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            margin-right: 1rem;
            font-size: 0.8rem;
        }
        
        .legend-color {
            width: 12px;
            height: 3px;
            border-radius: 2px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔴 Digital Red Queen</h1>
            <p class="subtitle">Evolve Core War warriors using LLMs</p>
        </header>
        
        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Ready</span>
            </div>
            <div class="progress-wrapper">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                </div>
            </div>
            <span id="progressText" style="font-family: 'JetBrains Mono', monospace; min-width: 45px; font-size: 0.9rem;">0%</span>
            <span id="runtimeText" style="color: var(--text-dim); font-size: 0.85rem; min-width: 50px;">--:--</span>
        </div>
        
        <!-- Main Chart - DRQ Fitness Evolution -->
        <div class="main-chart">
            <h3>📈 DRQ Fitness Evolution (All Rounds)</h3>
            <div class="chart-wrapper">
                <canvas id="mainFitnessChart"></canvas>
            </div>
        </div>
        
        <!-- Secondary Charts Row -->
        <div class="charts-row" style="margin-top: 1.5rem;">
            <div class="small-chart">
                <h3>🏆 Champion Fitness per Round</h3>
                <div class="chart-wrapper">
                    <canvas id="championChart"></canvas>
                </div>
            </div>
            <div class="small-chart">
                <h3>📊 Archive Coverage</h3>
                <div class="chart-wrapper">
                    <canvas id="archiveChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="top-section">
            <!-- Configuration Card -->
            <div class="card">
                <h2>Configuration</h2>
                
                <label for="provider">LLM Provider</label>
                <select id="provider">
                    <option value="gemini">Google Gemini</option>
                    <option value="openai">OpenAI GPT</option>
                    <option value="anthropic">Anthropic Claude</option>
                    <option value="ollama">Ollama (Local)</option>
                </select>
                
                <label for="model">Model</label>
                <select id="model">
                    <option value="gemini-1.5-flash">gemini-1.5-flash (Fast)</option>
                    <option value="gemini-1.5-pro">gemini-1.5-pro (Powerful)</option>
                </select>
                
                <label for="rounds">DRQ Rounds</label>
                <input type="number" id="rounds" value="3" min="1" max="20">
                
                <label for="generations">Generations per Round</label>
                <input type="number" id="generations" value="10" min="5" max="100">
                
                <button class="btn btn-primary" id="startBtn" onclick="startExperiment()">
                    ▶ Start Evolution
                </button>
                
                <div class="quick-actions">
                    <button class="btn btn-secondary" onclick="runDemo()">🎮 Demo</button>
                    <button class="btn btn-secondary" onclick="runTournament()">🏆 Tournament</button>
                </div>
            </div>
            
            <!-- Results Card -->
            <div class="card" style="display: flex; flex-direction: column;">
                <h2>Results</h2>
                
                <div class="results-grid">
                    <div class="result-card">
                        <div class="result-value" id="championsCount">-</div>
                        <div class="result-label">Champions</div>
                    </div>
                    <div class="result-card">
                        <div class="result-value" id="bestFitness">-</div>
                        <div class="result-label">Best Fitness</div>
                    </div>
                    <div class="result-card">
                        <div class="result-value" id="archiveSize">-</div>
                        <div class="result-label">Archive Size</div>
                    </div>
                    <div class="result-card">
                        <div class="result-value" id="improvement">-</div>
                        <div class="result-label">Improvement</div>
                    </div>
                </div>
                
                <div class="log-container" id="logContainer" style="flex: 1;">
                    <div class="log-line">
                        <span class="log-time">[--:--:--]</span>
                        <span>Waiting to start...</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Bottom Section -->
        <div class="bottom-grid">
            <div class="card">
                <h2>🏅 Best Champion Code</h2>
                <div class="warrior-code" id="warriorCode">; No champion yet...
; Run an evolution experiment to see the evolved warrior code here.</div>
            </div>
            <div class="card">
                <h2>📋 Round Summary</h2>
                <div class="warrior-code" id="roundSummary">Waiting for evolution to start...

Each round will evolve a new champion that must defeat
all previous champions (Red Queen dynamics).</div>
            </div>
        </div>
        
        <footer>
            Based on <a href="https://pub.sakana.ai/drq/" target="_blank">Digital Red Queen</a> by Sakana AI
        </footer>
    </div>
    
    <script>
        let pollInterval = null;
        let startTime = null;
        let mainFitnessChart = null;
        let championChart = null;
        let archiveChart = null;
        
        // Color palette for rounds
        const roundColors = [
            '#8b5cf6', // Purple
            '#f59e0b', // Amber  
            '#10b981', // Emerald
            '#ef4444', // Red
            '#3b82f6', // Blue
            '#ec4899', // Pink
            '#14b8a6', // Teal
            '#f97316', // Orange
            '#8b5cf6', // Purple
            '#06b6d4', // Cyan
        ];
        
        // Initialize charts
        function initCharts() {
            const commonOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#888',
                            font: { size: 11 },
                            boxWidth: 20,
                            padding: 15,
                        }
                    },
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#888', font: { size: 10 } },
                        title: { display: true, text: 'Generation', color: '#888' }
                    },
                    y: {
                        min: 0,
                        max: 1,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#888', font: { size: 10 } },
                        title: { display: true, text: 'Best Fitness', color: '#888' }
                    }
                }
            };
            
            // Main fitness chart - shows all rounds
            mainFitnessChart = new Chart(document.getElementById('mainFitnessChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    ...commonOptions,
                    plugins: {
                        ...commonOptions.plugins,
                        title: {
                            display: false,
                        }
                    }
                }
            });
            
            // Champion bar chart
            championChart = new Chart(document.getElementById('championChart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Champion Fitness',
                        data: [],
                        backgroundColor: roundColors.map(c => c + 'cc'),
                        borderColor: roundColors,
                        borderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        },
                        y: {
                            min: 0,
                            max: 1,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        }
                    }
                }
            });
            
            // Archive size chart
            archiveChart = new Chart(document.getElementById('archiveChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Archive Size',
                        data: [],
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        fill: true,
                        tension: 0.3,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        },
                        y: {
                            min: 0,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#888' }
                        }
                    }
                }
            });
        }
        
        initCharts();
        
        // Update model options based on provider
        document.getElementById('provider').addEventListener('change', function() {
            const modelSelect = document.getElementById('model');
            const models = {
                gemini: [
                    {value: 'gemini-1.5-flash', text: 'gemini-1.5-flash (Fast)'},
                    {value: 'gemini-1.5-pro', text: 'gemini-1.5-pro (Powerful)'},
                ],
                openai: [
                    {value: 'gpt-4', text: 'gpt-4'},
                    {value: 'gpt-4-turbo', text: 'gpt-4-turbo'},
                    {value: 'gpt-3.5-turbo', text: 'gpt-3.5-turbo'},
                ],
                anthropic: [
                    {value: 'claude-3-sonnet-20240229', text: 'claude-3-sonnet'},
                    {value: 'claude-3-opus-20240229', text: 'claude-3-opus'},
                    {value: 'claude-3-haiku-20240307', text: 'claude-3-haiku'},
                ],
                ollama: [
                    {value: 'llama3', text: 'llama3'},
                    {value: 'codellama', text: 'codellama'},
                    {value: 'mistral', text: 'mistral'},
                ],
            };
            
            modelSelect.innerHTML = '';
            models[this.value].forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.value;
                opt.textContent = m.text;
                modelSelect.appendChild(opt);
            });
        });
        
        function addLog(message) {
            const container = document.getElementById('logContainer');
            const time = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'log-line';
            line.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
            container.appendChild(line);
            container.scrollTop = container.scrollHeight;
        }
        
        function updateStatus(status, progress) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            dot.className = 'status-dot ' + (status === 'running' ? 'running' : status === 'complete' ? 'complete' : status === 'error' ? 'error' : '');
            text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            progressFill.style.width = progress + '%';
            progressText.textContent = Math.round(progress) + '%';
            
            if (startTime) {
                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById('runtimeText').textContent = formatTime(elapsed);
            }
        }
        
        function formatTime(seconds) {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}:${s.toString().padStart(2, '0')}`;
        }
        
        function updateCharts(data) {
            // Update main fitness chart with per-round curves
            if (data.round_curves && Object.keys(data.round_curves).length > 0) {
                const datasets = [];
                let maxLen = 0;
                
                Object.keys(data.round_curves).sort((a, b) => parseInt(a) - parseInt(b)).forEach((roundNum, idx) => {
                    const curve = data.round_curves[roundNum];
                    if (curve.length > maxLen) maxLen = curve.length;
                    
                    datasets.push({
                        label: `Round ${parseInt(roundNum) + 1}`,
                        data: curve,
                        borderColor: roundColors[idx % roundColors.length],
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 1,
                    });
                });
                
                mainFitnessChart.data.labels = Array.from({length: maxLen}, (_, i) => i);
                mainFitnessChart.data.datasets = datasets;
                mainFitnessChart.update('none');
            }
            
            // Update champion chart
            if (data.round_champions && data.round_champions.length > 0) {
                championChart.data.labels = data.round_champions.map((_, i) => `Round ${i + 1}`);
                championChart.data.datasets[0].data = data.round_champions;
                championChart.data.datasets[0].backgroundColor = data.round_champions.map((_, i) => roundColors[i % roundColors.length] + 'cc');
                championChart.data.datasets[0].borderColor = data.round_champions.map((_, i) => roundColors[i % roundColors.length]);
                championChart.update('none');
            }
            
            // Update archive chart
            if (data.archive_history && data.archive_history.length > 0) {
                archiveChart.data.labels = data.archive_history.map((_, i) => `R${i + 1}`);
                archiveChart.data.datasets[0].data = data.archive_history;
                archiveChart.update('none');
            }
        }
        
        async function startExperiment() {
            const provider = document.getElementById('provider').value;
            const model = document.getElementById('model').value;
            const rounds = document.getElementById('rounds').value;
            const generations = document.getElementById('generations').value;
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('logContainer').innerHTML = '';
            document.getElementById('roundSummary').textContent = '';
            startTime = Date.now();
            
            // Reset charts
            mainFitnessChart.data.labels = [];
            mainFitnessChart.data.datasets = [];
            mainFitnessChart.update('none');
            championChart.data.labels = [];
            championChart.data.datasets[0].data = [];
            championChart.update('none');
            archiveChart.data.labels = [];
            archiveChart.data.datasets[0].data = [];
            archiveChart.update('none');
            
            addLog('Starting evolution experiment...');
            updateStatus('running', 0);
            
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider, model, rounds, generations})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog(`LLM: ${provider}/${model}`);
                    addLog(`Rounds: ${rounds}, Generations: ${generations}`);
                    pollInterval = setInterval(pollStatus, 500);
                } else {
                    addLog('Error: ' + data.error);
                    updateStatus('error', 0);
                    document.getElementById('startBtn').disabled = false;
                }
            } catch (e) {
                addLog('Error: ' + e.message);
                updateStatus('error', 0);
                document.getElementById('startBtn').disabled = false;
            }
        }
        
        async function pollStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                updateStatus(data.status, data.progress);
                updateCharts(data);
                
                // Add new logs
                const logContainer = document.getElementById('logContainer');
                const existingLogs = logContainer.querySelectorAll('.log-line').length;
                if (data.logs.length > existingLogs - 1) {
                    data.logs.slice(Math.max(0, existingLogs - 1)).forEach(log => {
                        if (!log.includes('undefined')) addLog(log);
                    });
                }
                
                // Update round summary
                if (data.round_summary) {
                    document.getElementById('roundSummary').textContent = data.round_summary;
                }
                
                if (data.status === 'complete' || data.status === 'error') {
                    clearInterval(pollInterval);
                    document.getElementById('startBtn').disabled = false;
                    
                    if (data.results) {
                        showResults(data.results);
                    }
                }
            } catch (e) {
                console.error('Poll error:', e);
            }
        }
        
        function showResults(results) {
            document.getElementById('championsCount').textContent = results.champions || '-';
            document.getElementById('bestFitness').textContent = results.best_fitness ? results.best_fitness.toFixed(3) : '-';
            document.getElementById('archiveSize').textContent = results.archive_size || '-';
            
            if (results.improvement !== undefined) {
                const sign = results.improvement >= 0 ? '+' : '';
                document.getElementById('improvement').textContent = sign + (results.improvement * 100).toFixed(1) + '%';
            }
            
            if (results.champion_code) {
                document.getElementById('warriorCode').textContent = results.champion_code;
            }
        }
        
        async function runDemo() {
            document.getElementById('logContainer').innerHTML = '';
            addLog('Running demo battle...');
            
            try {
                const response = await fetch('/api/demo');
                const data = await response.json();
                
                addLog(`Warriors: ${data.warriors.join(' vs ')}`);
                addLog(`Winner: ${data.winner}`);
                addLog(`Cycles: ${data.cycles}`);
                
                data.metrics.forEach((m, i) => {
                    addLog(`${data.warriors[i]}: coverage=${(m.memory_coverage * 100).toFixed(1)}%`);
                });
                
                updateStatus('complete', 100);
            } catch (e) {
                addLog('Error: ' + e.message);
            }
        }
        
        async function runTournament() {
            document.getElementById('logContainer').innerHTML = '';
            addLog('Running tournament...');
            
            try {
                const response = await fetch('/api/tournament');
                const data = await response.json();
                
                addLog(`${data.warriors} warriors competing`);
                addLog('---');
                data.rankings.forEach((r, i) => {
                    addLog(`${i + 1}. ${r.name}: ${r.points} pts`);
                });
                
                // Update champion chart with tournament results
                championChart.data.labels = data.rankings.map(r => r.name.substring(0, 10));
                championChart.data.datasets[0].data = data.rankings.map(r => r.points);
                championChart.data.datasets[0].backgroundColor = data.rankings.map((_, i) => roundColors[i % roundColors.length] + 'cc');
                championChart.data.datasets[0].borderColor = data.rankings.map((_, i) => roundColors[i % roundColors.length]);
                championChart.options.scales.y.max = Math.max(...data.rankings.map(r => r.points)) + 2;
                championChart.update();
                
                updateStatus('complete', 100);
            } catch (e) {
                addLog('Error: ' + e.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/demo')
def api_demo():
    """Run a quick demo battle."""
    warriors = [
        parse_warrior(WARRIORS["imp"]),
        parse_warrior(WARRIORS["dwarf"]),
    ]
    
    battle = Battle(core_size=8000, max_cycles=80000, num_rounds=10)
    result = battle.run(warriors)
    
    return jsonify({
        "warriors": [w.name for w in warriors],
        "winner": result.get_winner_name(),
        "cycles": result.cycles,
        "metrics": [result.metrics.get(i, {}) for i in range(len(warriors))],
    })

@app.route('/api/tournament')
def api_tournament():
    """Run a tournament between example warriors."""
    warriors_dir = Path(PROJECT_ROOT) / "warriors"
    warriors = []
    
    for red_file in warriors_dir.glob("*.red"):
        try:
            with open(red_file) as f:
                warrior = parse_warrior(f.read())
                warriors.append(warrior)
        except Exception:
            pass
    
    if len(warriors) < 2:
        return jsonify({"error": "Not enough warriors"}), 400
    
    battle = Battle(core_size=8000, max_cycles=80000, num_rounds=5)
    stats = battle.run_tournament(warriors)
    
    rankings = sorted(
        [{"name": warriors[i].name, **s} for i, s in stats.items()],
        key=lambda x: x["points"],
        reverse=True
    )
    
    return jsonify({
        "warriors": len(warriors),
        "rankings": rankings,
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start a DRQ experiment."""
    global current_experiment
    
    if current_experiment["running"]:
        return jsonify({"success": False, "error": "Experiment already running"})
    
    data = request.json
    provider = data.get("provider", "gemini")
    model = data.get("model", "gemini-1.5-flash")
    rounds = int(data.get("rounds", 3))
    generations = int(data.get("generations", 10))
    
    current_experiment = {
        "running": True,
        "progress": 0,
        "status": "running",
        "logs": [],
        "results": None,
        "fitness_history": [],
        "round_champions": [],
        "round_curves": {},
        "archive_history": [],
        "round_summary": "",
    }
    
    def run_experiment():
        global current_experiment
        try:
            from drq import DigitalRedQueen, DRQConfig
            
            # Get LLM provider
            if provider == "gemini":
                from llm_interface import GeminiProvider
                llm = GeminiProvider(model=model)
            elif provider == "openai":
                from llm_interface import OpenAIProvider
                llm = OpenAIProvider(model=model)
            elif provider == "anthropic":
                from llm_interface import AnthropicProvider
                llm = AnthropicProvider(model=model)
            else:
                from llm_interface import OllamaProvider
                llm = OllamaProvider(model=model)
            
            current_experiment["logs"].append(f"Initialized {llm.name}")
            
            config = DRQConfig(
                num_rounds=rounds,
                generations_per_round=generations,
                verbose=False,
            )
            
            drq = DigitalRedQueen(llm, config)
            
            initial_fitness = None
            round_summary_lines = []
            
            for round_num in range(rounds):
                current_experiment["logs"].append(f"Round {round_num + 1}/{rounds} starting...")
                current_experiment["progress"] = ((round_num) / rounds) * 100
                
                result = drq._run_round(round_num)
                drq.round_results.append(result)
                drq.champions.append(result.champion)
                
                # Store fitness curve for this round
                current_experiment["round_curves"][str(round_num)] = result.best_fitness_curve.copy()
                current_experiment["round_champions"].append(result.champion_fitness)
                current_experiment["archive_history"].append(result.archive_size)
                
                if initial_fitness is None and result.best_fitness_curve:
                    initial_fitness = result.best_fitness_curve[0]
                
                # Update round summary
                summary_line = f"Round {round_num + 1}: {result.champion.name}\n  Fitness: {result.champion_fitness:.4f} | Archive: {result.archive_size}"
                round_summary_lines.append(summary_line)
                current_experiment["round_summary"] = "\n\n".join(round_summary_lines)
                
                current_experiment["logs"].append(
                    f"Round {round_num + 1} complete: {result.champion.name} (fitness: {result.champion_fitness:.4f})"
                )
            
            current_experiment["progress"] = 100
            current_experiment["status"] = "complete"
            
            final_fitness = current_experiment["round_champions"][-1] if current_experiment["round_champions"] else 0
            improvement = final_fitness - initial_fitness if initial_fitness else 0
            
            current_experiment["results"] = {
                "champions": len(drq.champions),
                "best_fitness": final_fitness,
                "archive_size": drq.round_results[-1].archive_size if drq.round_results else 0,
                "champion_code": warrior_to_string(drq.champions[-1]) if drq.champions else "",
                "improvement": improvement,
            }
            
            current_experiment["logs"].append(f"Evolution complete! Final fitness: {final_fitness:.4f}")
            
        except Exception as e:
            current_experiment["status"] = "error"
            current_experiment["logs"].append(f"Error: {str(e)}")
            import traceback
            current_experiment["logs"].append(traceback.format_exc())
        finally:
            current_experiment["running"] = False
    
    thread = threading.Thread(target=run_experiment)
    thread.start()
    
    return jsonify({"success": True})

@app.route('/api/status')
def api_status():
    """Get current experiment status."""
    return jsonify(current_experiment)

if __name__ == '__main__':
    port = 8080
    print("\n" + "="*50)
    print("🔴 Digital Red Queen - Web Interface")
    print("="*50)
    print(f"\nOpen in your browser: http://localhost:{port}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
