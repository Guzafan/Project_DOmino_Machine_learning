import random
import time
import json
import os

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading

from modelling_search import BFSBot, AStarBot, DFSBot
from modelling_ensemble import RandomForestBot, XGBBot

# ==========================================
# 1. GAME LOGIC ENGINE
# ==========================================
class DominoEngine:
    def __init__(self):
        self.boneyard = []
        self.player_hand = []
        self.bot_hand = []
        self.board = []
        self.left_end = None
        self.right_end = None
        self.reset_game()

    def reset_game(self):
        self.boneyard = [(i, j) for i in range(7) for j in range(i, 7)]
        random.shuffle(self.boneyard)
        self.player_hand = [self.boneyard.pop() for _ in range(7)]
        self.bot_hand = [self.boneyard.pop() for _ in range(7)]
        self.board = []
        self.left_end = None
        self.right_end = None

        self.player_last_pass = (-1, -1)
        self.bot_last_pass = (-1, -1)

    def get_valid_moves(self, hand):
        if not self.board:
            return [(tile, 'first') for tile in hand]
        
        valid_moves = []
        for tile in hand:
            if self.left_end in tile:
                valid_moves.append((tile, 'left'))
            # FIXED: Removed restriction that blocked right-side placement if left-side matched
            if self.right_end in tile:
                valid_moves.append((tile, 'right'))
        return valid_moves

    def play_tile(self, hand, move):
        tile, side = move
        hand.remove(tile)
        
        if side == 'first':
            self.board.append(tile)
            self.left_end, self.right_end = tile
        else:
            if side == 'left':
                if tile[1] == self.left_end:
                    self.board.insert(0, tile)
                    self.left_end = tile[0]
                else:
                    self.board.insert(0, (tile[1], tile[0]))
                    self.left_end = tile[1]
            elif side == 'right':
                if tile[0] == self.right_end:
                    self.board.append(tile)
                    self.right_end = tile[1]
                else:
                    self.board.append((tile[1], tile[0]))
                    self.right_end = tile[0]

    def draw_tile(self, hand):
        if self.boneyard:
            hand.append(self.boneyard.pop())
            return True
        return False

    def calculate_score(self, hand):
        return sum(tile[0] + tile[1] for tile in hand)

# ==========================================
# 2. GUI INTEGRATION
# ==========================================
class DominoGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎲 High Roller Dominoes: Player vs AI 🎲")
        self.root.state('zoomed')
        
        self.engine = DominoEngine()
        self.bot = None 
        self.player_turn = True
        self.consecutive_passes = 0
        
        # Timer & Pause Variables
        self.start_time = 0
        self.accumulated_time = 0 
        self.game_active = False
        self.is_paused = False
        self.timer_running = False
        self.timer_id = None
        
        self.final_time_str = ""
        self.final_time_seconds = 0

        # Leaderboard
        self.leaderboard_file = "leaderboard.json"
        self.leaderboard = self.load_leaderboard()
        
        self.TILE_W = 80
        self.TILE_H = 40

        self.tile_images = {}
        self.hand_coords = []
        
        # Tracking variables for drag & drop selection
        self.left_end_cx = 0
        self.left_end_cy = 0
        self.right_end_cx = 0
        self.right_end_cy = 0
        self.press_x = 0
        self.press_y = 0
        self.clicked_tile = None

        self.load_tile_assets()
        self.setup_casino_style()
        self.setup_login()
        self.setup_gui()
        self.show_login()

    def load_tile_assets(self):
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        if not os.path.exists(assets_dir):
            print(f"Warning: Assets folder not found at {assets_dir}")
            return

        self.base_pil_images = {}
        self.scaled_images_cache = {}

        for i in range(7):
            for j in range(i, 7):
                fname = f"{i} {j}.png"
                path = os.path.join(assets_dir, fname)
                if os.path.exists(path):
                    orig = Image.open(path).convert('RGBA')
                    
                    if orig.width > orig.height:
                        orig = orig.transpose(Image.ROTATE_270)
                    
                    base_v = orig.resize((self.TILE_H, self.TILE_W), Image.Resampling.LANCZOS)
                    
                    img_N = base_v                                  
                    img_E = base_v.transpose(Image.ROTATE_90)       
                    img_S = base_v.transpose(Image.ROTATE_180)      
                    img_W = base_v.transpose(Image.ROTATE_270)      
                    
                    # Store raw PIL images for dynamic scaling
                    self.base_pil_images[f"{i}_{j}_N"] = img_N
                    self.base_pil_images[f"{i}_{j}_E"] = img_E
                    self.base_pil_images[f"{i}_{j}_S"] = img_S
                    self.base_pil_images[f"{i}_{j}_W"] = img_W
                    
                    # Store standard 1.0x Tkinter images
                    self.tile_images[f"{i}_{j}_N"] = ImageTk.PhotoImage(img_N)
                    self.tile_images[f"{i}_{j}_E"] = ImageTk.PhotoImage(img_E)
                    self.tile_images[f"{i}_{j}_S"] = ImageTk.PhotoImage(img_S)
                    self.tile_images[f"{i}_{j}_W"] = ImageTk.PhotoImage(img_W)
                    
                    if i != j:
                        self.base_pil_images[f"{j}_{i}_N"] = img_S
                        self.base_pil_images[f"{j}_{i}_E"] = img_W
                        self.base_pil_images[f"{j}_{i}_S"] = img_N
                        self.base_pil_images[f"{j}_{i}_W"] = img_E
                        
                        self.tile_images[f"{j}_{i}_N"] = ImageTk.PhotoImage(img_S)
                        self.tile_images[f"{j}_{i}_E"] = ImageTk.PhotoImage(img_W)
                        self.tile_images[f"{j}_{i}_S"] = ImageTk.PhotoImage(img_N)
                        self.tile_images[f"{j}_{i}_W"] = ImageTk.PhotoImage(img_E)

    def load_leaderboard(self):
        default_bots = ["BFS (Search)", "DFS (Search)", "A* (Search)", "Random Forest (Ensemble)", "XGBoost (Ensemble)"]
        try:
            with open(self.leaderboard_file, "r") as f:
                data = json.load(f)
                for bot in default_bots:
                    if bot not in data or not isinstance(data[bot], dict):
                        data[bot] = {}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {bot: {} for bot in default_bots}

    def save_leaderboard(self):
        with open(self.leaderboard_file, "w") as f:
            json.dump(self.leaderboard, f, indent=4)

    def setup_casino_style(self):
        self.bg_color = "#1a1614"
        self.panel_bg = "#26201e"
        self.copper_accent = "#b87333"
        self.neon_aether = "#00e5ff"
        self.text_color = "#e8d8c8"
        
        self.root.configure(bg=self.bg_color)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(".", background=self.bg_color, foreground=self.text_color)
        style.configure("TFrame", background=self.panel_bg, borderwidth=0, relief="flat")
        
        style.configure("TButton", background=self.panel_bg, foreground=self.neon_aether, borderwidth=2, bordercolor=self.copper_accent, font=("Helvetica", 12, "bold"))
        style.map("TButton", background=[("active", self.copper_accent), ("disabled", self.bg_color)], foreground=[("active", "#1a1614"), ("disabled", "#555555")], bordercolor=[("disabled", "#333333")])
        
        style.configure("TLabel", background=self.panel_bg, foreground=self.copper_accent, font=("Helvetica", 14))

        style.configure("TCombobox", fieldbackground=self.panel_bg, background=self.panel_bg, foreground=self.neon_aether, arrowcolor=self.copper_accent)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", self.panel_bg), ("disabled", self.bg_color)], 
                  selectbackground=[("readonly", self.copper_accent)], 
                  selectforeground=[("readonly", "#1a1614")]
        )

        style.configure("Treeview", background=self.panel_bg, fieldbackground=self.panel_bg, foreground=self.text_color, borderwidth=0, rowheight=25)
        style.map("Treeview", background=[("selected", self.copper_accent)], foreground=[("selected", self.bg_color)])
        style.configure("Treeview.Heading", background=self.bg_color, foreground=self.copper_accent, font=("Helvetica", 11, "bold"), relief="flat")
        style.map("Treeview.Heading", background=[('active', self.panel_bg)])

    def setup_login(self):
        self.login_frame = tk.Frame(self.root, bg="#0d0b0a")
        self.login_box = tk.Frame(self.login_frame, bg=self.bg_color, highlightbackground="#0033FF", highlightthickness=2, relief="flat", padx=25, pady=25)
        self.login_box.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(self.login_box, text="♠ HIGH ROLLERS DOMINOES ♠", font=("Helvetica", 28, "bold"), bg=self.bg_color, fg="#FFD700").pack(pady=(30, 40))
        tk.Label(self.login_box, text="Enter Nickname:", font=("Helvetica", 14), bg=self.bg_color, fg=self.copper_accent).pack(pady=(10, 5))

        self.player_name_var = tk.StringVar(value="HighRoller")
        tk.Entry(self.login_box, textvariable=self.player_name_var, font=("Helvetica", 16),
                 bg=self.panel_bg, fg=self.neon_aether, insertbackground=self.neon_aether,
                 relief="solid", highlightthickness=1, highlightbackground=self.copper_accent, justify="center").pack(ipady=5, ipadx=10, pady=(0, 20))

        tk.Label(self.login_box, text="Select Opponent:", font=("Helvetica", 14), bg=self.bg_color, fg=self.copper_accent).pack(pady=(10, 5))
        self.bot_var = tk.StringVar(value="BFS (Search)")
        self.bot_dropdown = ttk.Combobox(self.login_box, textvariable=self.bot_var, values=["BFS (Search)", "DFS (Search)", "A* (Search)", "Random Forest (Ensemble)", "XGBoost (Ensemble)"], state="readonly", font=("Helvetica", 14), width=25)
        self.bot_dropdown.pack(pady=(0, 30), ipady=5)

        ttk.Button(self.login_box, text="VIEW LEADERBOARD", command=self.show_leaderboard).pack(ipadx=20, ipady=10, pady=(0, 10))
        ttk.Button(self.login_box, text="ENTER CASINO", command=self.show_game).pack(ipadx=20, ipady=10, pady=(0, 20))

    def show_leaderboard(self):
        top = tk.Toplevel(self.root)
        top.title("Casino Records")
        top.geometry("600x450")
        top.configure(bg=self.panel_bg)
        
        tk.Label(top, text="🏆 GLOBAL LEADERBOARDS 🏆", font=("Helvetica", 18, "bold"), 
                 bg=self.panel_bg, fg="#FFD700").pack(pady=15)
        
        filter_frame = tk.Frame(top, bg=self.panel_bg)
        filter_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(filter_frame, text="Select Model:", bg=self.panel_bg, fg=self.copper_accent).pack(side=tk.LEFT)
        
        bot_models = sorted(list(self.leaderboard.keys()))
        if not bot_models:
             bot_models = ["BFS (Search)", "DFS (Search)", "A* (Search)", "Random Forest (Ensemble)", "XGBoost (Ensemble)"]

        model_var = tk.StringVar(value=bot_models[0] if bot_models else "")
        model_dropdown = ttk.Combobox(filter_frame, textvariable=model_var, values=bot_models, state="readonly")
        model_dropdown.pack(side=tk.LEFT, padx=10)

        columns = ("username", "time", "wins")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=10)
        tree.heading("username", text="Username")
        tree.heading("time", text="Fastest Time (s)")
        tree.heading("wins", text="Total Wins")
        
        tree.column("username", anchor=tk.CENTER, width=150)
        tree.column("time", anchor=tk.CENTER, width=120)
        tree.column("wins", anchor=tk.CENTER, width=100)
        tree.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        def update_table(*args):
            for item in tree.get_children():
                tree.delete(item)
            
            selected = model_var.get()
            data = self.leaderboard.get(selected, {})
            
            if isinstance(data, dict):
                sorted_users = sorted(data.items(), key=lambda x: x[1].get('wins', 0) if isinstance(x[1], dict) else 0, reverse=True)
                
                for user, stats in sorted_users:
                    if isinstance(stats, dict):
                        f_time = stats.get("fastest_time", "N/A")
                        if isinstance(f_time, (int, float)): f_time = f"{f_time:.2f}"
                        tree.insert("", tk.END, values=(user, f_time, stats.get("wins", 0)))

        model_dropdown.bind("<<ComboboxSelected>>", update_table)
        update_table()
        
        ttk.Button(top, text="Close", command=top.destroy).pack(pady=15)

    def show_login(self):
        self.game_active = False
        self.is_paused = False
        self.timer_running = False
        self.engine.reset_game()
        self.bot = None
        
        self.current_status_msg = "Awaiting System Initialization..."
        if hasattr(self, 'status_var'):
            self.status_var.set("Place your bets and press 'Start Game' to deal!")
            self.timer_var.set("Time: 00:00")
            
        for widget in self.root.winfo_children():
            if not isinstance(widget, tk.Toplevel): widget.pack_forget()
        self.login_frame.place(x=0, y=0, relwidth=1, relheight=1)

    def show_game(self):
        self.in_game_bot_var.set(self.bot_var.get())
        self.login_frame.place_forget()
        self.main_wrapper.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.board_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.update_ui()
        self.root.update_idletasks()
        self.draw_screen()

    def setup_gui(self):
        self.main_wrapper = tk.Frame(self.root, bg="#2E2E2E")
        self.control_frame = ttk.LabelFrame(self.main_wrapper, text=" 🎰 Controls ", padding=(15, 15))

        self.timer_var = tk.StringVar(value="Time: 00:00")
        ttk.Label(self.control_frame, textvariable=self.timer_var, font=("Courier", 16, "bold"), foreground="#00FF00").pack(anchor=tk.W, pady=(0, 15))

        ttk.Label(self.control_frame, text="Opponent Model:", font=("Helvetica", 10), foreground=self.copper_accent).pack(anchor=tk.W, pady=(0, 2))
        self.in_game_bot_var = tk.StringVar()
        self.in_game_bot_dropdown = ttk.Combobox(self.control_frame, textvariable=self.in_game_bot_var,
                     values=["BFS (Search)", "DFS (Search)", "A* (Search)", "Random Forest (Ensemble)", "XGBoost (Ensemble)"],
                     state="readonly", font=("Helvetica", 10))
        self.in_game_bot_dropdown.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(self.control_frame, text="Start Game", command=self.start_game)
        self.start_btn.pack(fill=tk.X, pady=5)
        self.pause_btn = ttk.Button(self.control_frame, text="Pause Game", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(fill=tk.X, pady=5)
        
        self.leaderboard_btn = ttk.Button(self.control_frame, text="Leaderboard", command=self.show_leaderboard)
        self.leaderboard_btn.pack(fill=tk.X, pady=5)
        
        ttk.Button(self.control_frame, text="Log Out", command=self.show_login).pack(fill=tk.X, pady=5)
        ttk.Separator(self.control_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        self.draw_btn = ttk.Button(self.control_frame, text="Draw Tile", command=self.player_draw, state=tk.DISABLED)
        self.draw_btn.pack(fill=tk.X, pady=5)
        self.pass_btn = ttk.Button(self.control_frame, text="Pass Turn", command=self.player_pass, state=tk.DISABLED)
        self.pass_btn.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="Place your bets and press 'Start Game' to deal!")
        ttk.Label(self.control_frame, textvariable=self.status_var, wraplength=180, foreground="#FFD700", font=("Helvetica", 10, "italic")).pack(side=tk.BOTTOM, pady=10)

        self.board_frame = ttk.LabelFrame(self.main_wrapper, text=" Casino Felt ", padding=(10, 10))
        self.canvas = tk.Canvas(self.board_frame, bg="#1a6e3e", highlightthickness=0, highlightbackground="#FFD700", borderwidth=0)
        
        # Bound split events for press tracking and release destination checks
        self.canvas.bind("<Button-1>", self.handle_press)
        self.canvas.bind("<Double-Button-1>", self.handle_double_click)
        self.canvas.bind("<B1-Motion>", self.handle_drag)
        self.canvas.bind("<ButtonRelease-1>", self.handle_release)
        self.canvas.bind("<Configure>", lambda e: self.draw_screen())

    def toggle_pause(self):
        if not self.game_active: return
        self.is_paused = not self.is_paused
        self.pause_btn.config(text="Resume Game" if self.is_paused else "Pause Game")
        self.update_status("Game Paused." if self.is_paused else "Game Resumed.")
        self.update_ui()
        if not self.is_paused:
            if not self.player_turn: self.bot_turn()

    def update_timer(self):
        if not getattr(self, 'timer_running', False): 
            return
        if self.game_active and not self.is_paused:
            self.accumulated_time += 1
            mins, secs = divmod(self.accumulated_time, 60)
            self.timer_var.set(f"Time: {int(mins):02d}:{int(secs):02d}")
        
        self.timer_id = self.root.after(1000, self.update_timer)

    def start_game(self):
        self.bot_var.set(self.in_game_bot_var.get())
        selection = self.bot_var.get()
        if selection == "XGBoost (Ensemble)": self.bot = XGBBot()
        elif selection == "Random Forest (Ensemble)": self.bot = RandomForestBot()
        elif selection == "BFS (Search)": self.bot = BFSBot()
        elif selection == "DFS (Search)": self.bot = DFSBot()
        elif selection == "A* (Search)": self.bot = AStarBot()

        self.engine.reset_game()
        self.player_turn = True
        self.is_paused = False
        self.start_btn.config(text="Restart Game")
        self.pause_btn.config(state=tk.NORMAL, text="Pause Game")
        
        if hasattr(self, 'timer_id') and self.timer_id:
            self.root.after_cancel(self.timer_id)
        
        self.accumulated_time = 0
        self.timer_var.set("Time: 00:00")
        self.timer_running = True
        self.game_active = True
        self.update_timer()
        self.player_turn = random.choice([True, False])

        if self.player_turn:
            self.update_status(f"Game started vs {self.bot.name}! You go first.")
            self.update_ui()
        else:
            self.update_status(f"Game started vs {self.bot.name}! Bot goes first.")
            self.update_ui()
            self.root.after(500, self.bot_turn)

    def update_ui(self):
        self.draw_screen()
        
        if not self.game_active or self.is_paused:
            self.in_game_bot_dropdown.config(state="readonly")
            self.leaderboard_btn.config(state=tk.NORMAL)
        else:
            self.in_game_bot_dropdown.config(state=tk.DISABLED)
            self.leaderboard_btn.config(state=tk.DISABLED)
            
        if not self.game_active or self.is_paused:
            self.draw_btn.config(state=tk.DISABLED)
            self.pass_btn.config(state=tk.DISABLED)
            return

        valid_moves = self.engine.get_valid_moves(self.engine.player_hand)
        if self.player_turn:
            if not valid_moves:
                if self.engine.boneyard:
                    self.draw_btn.config(state=tk.NORMAL)
                    self.pass_btn.config(state=tk.DISABLED)
                else:
                    self.draw_btn.config(state=tk.DISABLED)
                    self.pass_btn.config(state=tk.NORMAL)
            else:
                self.draw_btn.config(state=tk.DISABLED)
                self.pass_btn.config(state=tk.DISABLED)

    def draw_screen(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: cw, ch = 800, 600
        cx, cy = cw / 2, ch / 2

        self.canvas.create_oval(cx - 380, cy - 280, cx + 380, cy + 280, outline="#b87333", width=8)
        
        status_text = getattr(self, 'current_status_msg', "Awaiting System Initialization...")
        self.canvas.create_text(cx, 40, text=status_text, font=("Helvetica", 20, "bold"), fill="#FFD700", tags="status_text")

        if not self.game_active:
            self.canvas.create_text(cx, cy, text="Place your bets and press 'Start Game' to deal!", font=("Helvetica", 20, "bold"), fill="#FFD700")
            return
        
        bot_text_str = f"{self.bot.name if self.bot else 'Bot'} Tiles: {len(self.engine.bot_hand)}"
        self.canvas.create_text(cx, cy - 230, text=bot_text_str, font=("Helvetica", 16, "bold"), fill="#FFD700")

        boneyard_text_str = f"Boneyard: {len(self.engine.boneyard)} tiles"
        self.canvas.create_text(cx, cy - 195, text=boneyard_text_str, font=("Helvetica", 12, "bold"), fill="#FFD700")

        layout = []
        if self.engine.board:
            joint_x, joint_y = 0, 0
            state = 'GOING_EAST'
            dir_vec = (1, 0)
            
            tiles_in_current_dir = 0
            MAX_H = 9  
            MAX_V = 2  
            
            for i, tile in enumerate(self.engine.board):
                val1, val2 = tile
                is_double = (val1 == val2)
                
                if dir_vec[0] != 0:
                    orient = 'N' if is_double else ('E' if dir_vec[0] > 0 else 'W')
                    L_along = 40 if is_double else 80
                else: 
                    orient = 'E' if is_double else ('N' if dir_vec[1] > 0 else 'S')
                    L_along = 40 if is_double else 80

                if tiles_in_current_dir == 0 and i > 0:
                    prev_dir = layout[-1]['dir']
                    if prev_dir[0] != 0 and dir_vec[1] != 0: 
                        joint_x -= prev_dir[0] * 20 
                    elif prev_dir[1] != 0 and dir_vec[0] != 0: 
                        joint_y -= prev_dir[1] * 20

                half_L = L_along / 2
                center_x = joint_x + dir_vec[0] * half_L
                center_y = joint_y + dir_vec[1] * half_L
                
                layout.append({'tile': (val1, val2), 'cx': center_x, 'cy': center_y, 'orient': orient, 'dir': dir_vec})
                
                joint_x += dir_vec[0] * L_along
                joint_y += dir_vec[1] * L_along
                tiles_in_current_dir += 1
                
                current_limit = MAX_H if dir_vec[0] != 0 else MAX_V
                if tiles_in_current_dir >= current_limit:
                    tiles_in_current_dir = 0
                    if state == 'GOING_EAST':
                        state, dir_vec = 'GOING_SOUTH_1', (0, 1)
                    elif state == 'GOING_SOUTH_1':
                        state, dir_vec = 'GOING_WEST', (-1, 0)
                    elif state == 'GOING_WEST':
                        state, dir_vec = 'GOING_SOUTH_2', (0, 1)
                    elif state == 'GOING_SOUTH_2':
                        state, dir_vec = 'GOING_EAST', (1, 0)

            min_x = min(i['cx'] for i in layout)
            max_x = max(i['cx'] for i in layout)
            min_y = min(i['cy'] for i in layout)
            max_y = max(i['cy'] for i in layout)
            
            layout_w = max_x - min_x + 80
            layout_h = max_y - min_y + 80
            
            safe_w = cw - 60   
            safe_h = ch - 380 
            
            scale_x = safe_w / layout_w if layout_w > safe_w else 1.0
            scale_y = safe_h / layout_h if layout_h > safe_h else 1.0
            scale = min(scale_x, scale_y, 1.0)
            
            offset_x = (cw / 2) - ((min_x + max_x) / 2) * scale
            offset_y = (cy - 30) - ((min_y + max_y) / 2) * scale
            
            # FIXED: Save true layout end coordinates for distance analysis
            if layout:
                self.left_end_cx = layout[0]['cx'] * scale + offset_x
                self.left_end_cy = layout[0]['cy'] * scale + offset_y
                self.right_end_cx = layout[-1]['cx'] * scale + offset_x
                self.right_end_cy = layout[-1]['cy'] * scale + offset_y
            
            for item in layout:
                img_key = f"{item['tile'][0]}_{item['tile'][1]}_{item['orient']}"
                
                if scale < 1.0:
                    cache_key = (img_key, round(scale, 2))
                    if cache_key not in self.scaled_images_cache:
                        orig_img = self.base_pil_images[img_key]
                        new_size = (int(orig_img.width * scale), int(orig_img.height * scale))
                        resized = orig_img.resize(new_size, Image.Resampling.LANCZOS)
                        self.scaled_images_cache[cache_key] = ImageTk.PhotoImage(resized)
                    img = self.scaled_images_cache[cache_key]
                else:
                    img = self.tile_images.get(img_key)
                
                if img:
                    draw_x = item['cx'] * scale + offset_x
                    draw_y = item['cy'] * scale + offset_y
                    self.canvas.create_image(draw_x, draw_y, image=img, anchor=tk.CENTER, tags="board")

        if self.is_paused:
            self.canvas.create_rectangle(cx - 175, cy - 70, cx + 175, cy + 70, fill="black", outline="#FFD700", width=4)
            self.canvas.create_text(cx, cy, text="PAUSED", font=("Helvetica", 30, "bold"), fill="red")
            return

        # Player Hand
        self.hand_coords = []
        hand_count = len(self.engine.player_hand)
        start_x = (cw - (hand_count * (self.TILE_H + 15))) // 2
        for i, tile in enumerate(self.engine.player_hand):
            tx, ty = start_x + i * (self.TILE_H + 15), ch - 150 
            img = self.tile_images.get(f"{tile[0]}_{tile[1]}_N")
            if img:
                tag = f"hand_tile_{i}"
                self.canvas.create_image(tx, ty, image=img, anchor="nw", tags=("tile", tag))
                self.hand_coords.append((tx, tx + self.TILE_H, ty, ty + self.TILE_W, tile, tag))

    # FIXED: Split click detection into handle_press and handle_release
    def handle_press(self, event):
        if not self.player_turn or not self.game_active or self.is_paused: return

        self.clicked_tile = None
        self.drag_item = None
        
        # Loop includes the tag to find the specific image element
        for x1, x2, y1, y2, tile, tag in self.hand_coords:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.clicked_tile = tile
                self.press_x = event.x
                self.press_y = event.y
                self.last_x = event.x
                self.last_y = event.y
                
                # Grab the actual canvas item to move it
                items = self.canvas.find_withtag(tag)
                if items:
                    self.drag_item = items[0]
                    self.canvas.tag_raise(self.drag_item)
                    coords = self.canvas.coords(self.drag_item)
                    self.drag_start_x = coords[0]
                    self.drag_start_y = coords[1]
                break

    def handle_double_click(self, event):
        """Double-clicking a hand tile plays it automatically (smart side selection)."""
        if not self.player_turn or not self.game_active or self.is_paused:
            return

        tile = None
        for x1, x2, y1, y2, t, tag in self.hand_coords:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                tile = t
                break

        if tile is None:
            return

        valid_moves = self.engine.get_valid_moves(self.engine.player_hand)
        possible_moves = [m for m in valid_moves if m[0] == tile]

        if not possible_moves:
            self.update_status("That tile doesn't match either end!")
            return

        # When both sides are valid, prefer the closer board end
        if len(possible_moves) > 1:
            dist_left  = (event.x - self.left_end_cx)**2  + (event.y - self.left_end_cy)**2
            dist_right = (event.x - self.right_end_cx)**2 + (event.y - self.right_end_cy)**2
            move_to_make = next((m for m in possible_moves if m[1] == ('left' if dist_left <= dist_right else 'right')), possible_moves[0])
        else:
            move_to_make = possible_moves[0]

        self.engine.play_tile(self.engine.player_hand, move_to_make)
        self.consecutive_passes = 0
        self.check_win_condition()
        if self.game_active:
            self.player_turn = False
            self.update_ui()
            self.root.after(1000, self.bot_turn)


    def handle_drag(self, event):
        if not getattr(self, 'drag_item', None): return
        
        # Move the tile visually across the screen
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        self.canvas.move(self.drag_item, dx, dy)
        
        self.last_x = event.x
        self.last_y = event.y

    def handle_release(self, event):
        if not getattr(self, 'drag_item', None) or not getattr(self, 'clicked_tile', None): 
            return

        tile = self.clicked_tile
        item = self.drag_item
        
        # Reset references
        self.clicked_tile = None
        self.drag_item = None

        # --- Drag-cancel: if dropped back over any tile in the player's hand, snap back ---
        for x1, x2, y1, y2, _t, _tag in self.hand_coords:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.canvas.coords(item, self.drag_start_x, self.drag_start_y)
                self.update_status("Move cancelled — tile returned to hand.")
                return

        valid_moves = self.engine.get_valid_moves(self.engine.player_hand)
        possible_moves = [m for m in valid_moves if m[0] == tile]
        
        if not possible_moves:
            self.update_status("Invalid move! Doesn't match either end.")
            self.canvas.coords(item, self.drag_start_x, self.drag_start_y)
            return

        # Calculate placement based on where the mouse was released
        drop_x, drop_y = event.x, event.y
        move_to_make = None

        if len(possible_moves) > 1:
            # Tile matches both sides, check distance
            if hasattr(self, 'left_end_cx') and hasattr(self, 'right_end_cx'):
                dist_left = (drop_x - self.left_end_cx)**2 + (drop_y - self.left_end_cy)**2
                dist_right = (drop_x - self.right_end_cx)**2 + (drop_y - self.right_end_cy)**2
                
                if dist_left < dist_right:
                    move_to_make = next((m for m in possible_moves if m[1] == 'left'), possible_moves[0])
                else:
                    move_to_make = next((m for m in possible_moves if m[1] == 'right'), possible_moves[0])
            else:
                move_to_make = possible_moves[0]
        else:
            move_to_make = possible_moves[0]
            
        if move_to_make:
            self.engine.play_tile(self.engine.player_hand, move_to_make)
            self.consecutive_passes = 0
            self.check_win_condition()
            if self.game_active: 
                self.player_turn = False
                self.update_ui()
                self.root.after(1000, self.bot_turn)
        else:
            # If for some reason it fails, snap the tile back to the hand
            self.canvas.coords(item, self.drag_start_x, self.drag_start_y)

    def player_draw(self):
        if self.engine.draw_tile(self.engine.player_hand):
            self.draw_screen()
            self.update_status("You drew a tile.")
            self.update_ui()

    def player_pass(self):
        self.consecutive_passes += 1
        self.update_status("You passed your turn.")
        if self.consecutive_passes >= 2:
            self.handle_blocked_game()
        else:
            self.player_turn = False
            self.update_ui()
            self.root.after(1000, self.bot_turn)

    def bot_turn(self):
        if not self.engine.bot_hand or not self.game_active or self.is_paused: return
        self.update_status(f"{self.bot.name} is calculating odds...")

        def get_move():
            time.sleep(1)
            self.root.update()
            move = self.bot.choose_move(self.engine)
            self.root.after(0, self.execute_bot_move, move)

        threading.Thread(target=get_move, daemon=True).start()
    
    def execute_bot_move(self, move):
        if not self.game_active or self.is_paused: return

        if move:
            self.engine.play_tile(self.engine.bot_hand, move)
            self.consecutive_passes = 0 
            self.update_status(f"{self.bot.name} played [{move[0][0]}|{move[0][1]}].")
        else:
            if len(self.engine.boneyard) > 0:
                self.engine.draw_tile(self.engine.bot_hand)
                self.draw_screen()
                self.update_status(f"{self.bot.name} had to draw a tile. Still their turn...")
                self.root.after(1000, self.bot_turn) 
                return
            else:
                self.consecutive_passes += 1
                self.update_status(f"{self.bot.name} passed. Your turn!")

        if self.consecutive_passes >= 2:
            self.handle_blocked_game()
        else:
            self.check_win_condition()
            if self.game_active:
                self.player_turn = True
                self.update_ui()

    def handle_blocked_game(self):
        self.game_active = False
        self.pause_btn.config(state=tk.DISABLED)
        p_score, b_score = self.engine.calculate_score(self.engine.player_hand), self.engine.calculate_score(self.engine.bot_hand)
        
        if p_score < b_score: 
            self.trigger_end_game(won=True, reason="blocked")
        elif b_score < p_score: 
            self.trigger_end_game(won=False, reason="blocked")
        else: 
            messagebox.showinfo("Tie Game", "A tie? Try again!")
            self.bot_dropdown.config(state="readonly")
            self.in_game_bot_dropdown.config(state="readonly")
            
    def check_win_condition(self):
        if not self.engine.player_hand:
            self.game_active = False
            self.root.update_idletasks()
            self.root.after(500, lambda: self.trigger_end_game(won=True, reason="empty"))
            
        elif not self.engine.bot_hand:
            self.game_active = False
            self.root.update_idletasks()
            self.root.after(500, lambda: self.trigger_end_game(won=False, reason="empty"))

    def trigger_end_game(self, won, reason):
        bot_model = self.bot_var.get()
        player_name = self.player_name_var.get()
        
        if bot_model not in self.leaderboard:
            self.leaderboard[bot_model] = {}
        
        if player_name not in self.leaderboard[bot_model]:
            self.leaderboard[bot_model][player_name] = {"wins": 0, "fastest_time": float('inf')}
            
        if won:
            stats = self.leaderboard[bot_model][player_name]
            stats["wins"] = stats.get("wins", 0) + 1
            current_time = self.accumulated_time
            best_time = stats.get("fastest_time", float('inf'))
            
            if isinstance(best_time, str): best_time = float('inf')
            if current_time < best_time:
                stats["fastest_time"] = current_time
            
        self.save_leaderboard()
        self.root.update()
        
        mins, secs = divmod(self.accumulated_time, 60)
        time_display_str = f"{int(mins):02d}:{int(secs):02d}"
        
        if won:
            messagebox.showinfo("Winner!", f"You won against {bot_model} in {time_display_str}!")
        else:
            messagebox.showerror("Lost!", f"You lost against {bot_model} in {time_display_str}.")
            
        # Re-enable model selection after the game ends
        self.bot_dropdown.config(state="readonly")
        self.in_game_bot_dropdown.config(state="readonly")
        
    def update_status(self, msg):
        self.status_var.set(msg)
        self.current_status_msg = msg 
        if hasattr(self, 'canvas') and self.canvas.find_withtag("status_text"):
            self.canvas.itemconfig("status_text", text=msg)
            self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = DominoGameGUI(root)
    root.mainloop()