# tools/test_shot_planner.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'ai_orchestrator'))

# Set local config paths for testing
os.environ['SHOTS_CONFIG_PATH'] = os.path.join(os.path.dirname(__file__), '..', 'config', 'shots.json')
os.environ['ANCHORS_CONFIG_PATH'] = os.path.join(os.path.dirname(__file__), '..', 'config', 'anchors.json')

from shot_planner import plan_shot

cases = [
    {"tags":{"location":"alley","action":"investigate","mood":"tense","motif":"red_neon","subject":"detective"}},
    {"tags":{"location":"office","action":"connect","mood":"melancholic","motif":"red_file","subject":"detective"}},
    {"tags":{"location":"bar","action":"interrogate","mood":"tense","motif":"red_lipstick","subject":"witness"}},
]

for c in cases:
    p = plan_shot(c["tags"])
    print(c["tags"], "->", p["shot"], "| vision:", p["vision_query"], "| prompt:", p["provider_prompt"][:80], "…")
