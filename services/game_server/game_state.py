class GameState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turn_id = 1
        self.story_history = []       # [{turn,text}]
        self.players = {}             # name -> ws (bot ma ws=None)
        self.actions = {}             # name -> action str
        # Single player
        self.single_player = False
        self.bot_name = None
        self.bot_persona = None
        # Story mode
        self.metrics = {"time": 20, "suspicion": 0, "reputation": 0}
        self.casefile = {"clues": [], "suspects": []}
        self.inventory = {"pistol_loaded": False, "ammo": 0, "cigarettes": 0, "matches": 0}
        self.location = "office"
        self.relations = {}  # name -> {mood:int, trust:int, fear:int} (0..100)
        self.case_graph = {"nodes": [], "edges": []}

    def _clamp(self, v, lo=0, hi=100): 
        return max(lo, min(hi, int(v)))

    def _rel_get(self, name: str):
        r = self.relations.get(name)
        if not r:
            r = {"mood":50, "trust":50, "fear":50}
            self.relations[name] = r
        return r

    def _cg_merge(self, delta: dict):
        nodes = delta.get("nodes_add", []) or []
        edges = delta.get("edges_add", []) or []
        # proste łączenie, bez usuwania duplikatów (MVP dopuszcza duplikaty wg id – lepiej filtr)
        seen = {n["id"] for n in self.case_graph["nodes"]}
        for n in nodes:
            if n["id"] not in seen:
                self.case_graph["nodes"].append(n)
                seen.add(n["id"])
        self.case_graph["edges"].extend(edges)

    def add_player(self, name, ws): self.players[name] = ws
    def replace_player_ws(self, name, ws): self.players[name] = ws
    def record_action(self, player, action):
        self.actions[player] = action
        return len(self.players) >= 2 and len(self.actions) == len(self.players)

    def to_json(self):
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "history": self.story_history,
            "players": list(self.players.keys()),
            "actions": self.actions,
            "metrics": self.metrics,
            "casefile": self.casefile,
            "inventory": getattr(self, "inventory", {"pistol_loaded": False, "ammo": 0, "cigarettes": 0, "matches": 0}),
            "location": getattr(self, "location", "office"),
            "relations": self.relations,
            "case_graph": self.case_graph
        }

    def apply_narration(self, text):
        self.story_history.append({"turn": self.turn_id, "text": text})

    def apply_storystep(self, story: dict):
        # metrics
        delta = story.get("state_diff", {}).get("metrics_delta", {}) or story.get("metrics_delta", {})
        for k, v in delta.items():
            if k in self.metrics and isinstance(v, int):
                self.metrics[k] += v
        # location
        new_loc = story.get("state_diff", {}).get("location")
        if isinstance(new_loc, str) and new_loc:
            self.location = new_loc
        # inventory
        inv = story.get("state_diff", {}).get("inventory", {})
        if inv:
            if "pistol_loaded" in inv:
                self.inventory["pistol_loaded"] = bool(inv["pistol_loaded"])
            if "ammo_delta" in inv:
                self.inventory["ammo"] = max(0, int(self.inventory.get("ammo",0)) + int(inv["ammo_delta"]))
            if "cigarettes_delta" in inv:
                self.inventory["cigarettes"] = max(0, int(self.inventory.get("cigarettes",0)) + int(inv["cigarettes_delta"]))
        # casefile
        for c in story.get("state_diff", {}).get("casefile", {}).get("clues_add", []):
            self.casefile["clues"].append(c)
        for s in story.get("state_diff", {}).get("casefile", {}).get("suspects_upd", []):
            self.casefile["suspects"].append(s)
        # relations
        for rd in story.get("relations_delta", []):
            name = rd.get("name")
            if not name: continue
            r = self._rel_get(name)
            r["mood"]  = self._clamp(r["mood"]  + int(rd.get("mood_delta",0)))
            r["trust"] = self._clamp(r["trust"] + int(rd.get("trust_delta",0)))
            r["fear"]  = self._clamp(r["fear"]  + int(rd.get("fear_delta",0)))
        
        # case graph
        if story.get("graph_delta"):
            self._cg_merge(story["graph_delta"])

    def next_turn(self):
        self.turn_id += 1
        self.actions = {}