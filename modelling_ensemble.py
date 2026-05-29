import pandas as pd

import os
import random
import joblib

class XGBBot:
    def __init__(self, model_path="./models/domino_bot_xgb.joblib"): #domino_bot_rf.joblib
        self.model_path = model_path
        self.name = 'Extreme Gradient Boosting'
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Successfully loaded pre-trained model from {self.model_path}")
        else:
            print(f"Warning: {self.model_path} not found. Bot will play completely randomly.")
            self.model = None

    def choose_move(self, engine):
        valid_moves = engine.get_valid_moves(engine.bot_hand)
        #self.model = None

        if not valid_moves: 
            return None
        if self.model is None: 
            return random.choice(valid_moves)

        best_move = None
        highest_prob = -1

        for move in valid_moves:
            tile, side = move
            l_end = engine.left_end if engine.left_end is not None else -1
            r_end = engine.right_end if engine.right_end is not None else -1
            
            my_hand_size = len(engine.bot_hand)
            opp_hand_size = len(engine.player_hand)
            boneyard_size = len(engine.boneyard)
            
            is_double = 1 if tile[0] == tile[1] else 0
            pip_count = sum([t[0] + t[1] for t in engine.bot_hand])

            suit_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
            for t in engine.bot_hand:
                suit_counts[t[0]] += 1
                if t[0] != t[1]: suit_counts[t[1]] += 1
                
            # --- NEW: Unplayed counts ---
            unplayed = {0:7, 1:7, 2:7, 3:7, 4:7, 5:7, 6:7}
            for t in engine.bot_hand:
                unplayed[t[0]] -= 1
                if t[0] != t[1]: unplayed[t[1]] -= 1
            for t in engine.board:
                unplayed[t[0]] -= 1
                if t[0] != t[1]: unplayed[t[1]] -= 1

            # --- NEW: Vulnerability Check ---
            opp_pass_l = engine.player_last_pass[0] if hasattr(engine, 'player_last_pass') else -1
            opp_pass_r = engine.player_last_pass[1] if hasattr(engine, 'player_last_pass') else -1
            
            new_l, new_r = l_end, r_end
            if side == 'first':
                new_l, new_r = tile[0], tile[1]
            elif side == 'left':
                new_l = tile[0] if tile[1] == l_end else tile[1]
            elif side == 'right':
                new_r = tile[1] if tile[0] == r_end else tile[0]
                
            is_vuln = 0
            if ((new_l == opp_pass_l or new_l == opp_pass_r) and new_l != -1) or \
               ((new_r == opp_pass_l or new_r == opp_pass_r) and new_r != -1):
                is_vuln = 1

            # --- UPDATE FEATURE NAMES & VALUES ---
            feature_names = [
                "Left_End", "Right_End", "Tile_A", "Tile_B", "My_Hand_Size", 
                "Opp_Hand_Size", "Boneyard_Size", "Is_Double", "Pip_Count",
                "Count_0", "Count_1", "Count_2", "Count_3", "Count_4", "Count_5", "Count_6",
                "Unplayed_0", "Unplayed_1", "Unplayed_2", "Unplayed_3", "Unplayed_4", "Unplayed_5", "Unplayed_6",
                "Is_Opponent_Vulnerable"
            ]

            feature_values = [[
                l_end, r_end, tile[0], tile[1], my_hand_size, opp_hand_size, boneyard_size, 
                is_double, pip_count, suit_counts[0], suit_counts[1], suit_counts[2], 
                suit_counts[3], suit_counts[4], suit_counts[5], suit_counts[6],
                unplayed[0], unplayed[1], unplayed[2], unplayed[3], unplayed[4], unplayed[5], unplayed[6],
                is_vuln
            ]]

            features = pd.DataFrame(feature_values, columns=feature_names)
            
            prob = self.model.predict_proba(features)[0][1] 
            if prob > highest_prob:
                highest_prob = prob
                best_move = move

        if best_move is None:
            best_move = random.choice(valid_moves)
        return best_move

class RandomForestBot:
    def __init__(self, model_path="./models/domino_bot_rf.joblib"): #domino_bot_rf.joblib
        self.model_path = model_path
        self.name = 'Random Forest'
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Successfully loaded pre-trained model from {self.model_path}")
        else:
            print(f"Warning: {self.model_path} not found. Bot will play completely randomly.")
            self.model = None

    def choose_move(self, engine):
        valid_moves = engine.get_valid_moves(engine.bot_hand)

        if not valid_moves: 
            return None
        if self.model is None: 
            return random.choice(valid_moves)

        best_move = None
        highest_prob = -1

        for move in valid_moves:
            tile, side = move
            l_end = engine.left_end if engine.left_end is not None else -1
            r_end = engine.right_end if engine.right_end is not None else -1
            
            my_hand_size = len(engine.bot_hand)
            opp_hand_size = len(engine.player_hand)
            boneyard_size = len(engine.boneyard)
            
            is_double = 1 if tile[0] == tile[1] else 0
            pip_count = sum([t[0] + t[1] for t in engine.bot_hand])

            suit_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
            for t in engine.bot_hand:
                suit_counts[t[0]] += 1
                if t[0] != t[1]: suit_counts[t[1]] += 1
                
            # --- NEW: Unplayed counts ---
            unplayed = {0:7, 1:7, 2:7, 3:7, 4:7, 5:7, 6:7}
            for t in engine.bot_hand:
                unplayed[t[0]] -= 1
                if t[0] != t[1]: unplayed[t[1]] -= 1
            for t in engine.board:
                unplayed[t[0]] -= 1
                if t[0] != t[1]: unplayed[t[1]] -= 1

            # --- NEW: Vulnerability Check ---
            opp_pass_l = engine.player_last_pass[0] if hasattr(engine, 'player_last_pass') else -1
            opp_pass_r = engine.player_last_pass[1] if hasattr(engine, 'player_last_pass') else -1
            
            new_l, new_r = l_end, r_end
            if side == 'first':
                new_l, new_r = tile[0], tile[1]
            elif side == 'left':
                new_l = tile[0] if tile[1] == l_end else tile[1]
            elif side == 'right':
                new_r = tile[1] if tile[0] == r_end else tile[0]
                
            is_vuln = 0
            if ((new_l == opp_pass_l or new_l == opp_pass_r) and new_l != -1) or \
               ((new_r == opp_pass_l or new_r == opp_pass_r) and new_r != -1):
                is_vuln = 1

            # --- UPDATE FEATURE NAMES & VALUES ---
            feature_names = [
                "Left_End", "Right_End", "Tile_A", "Tile_B", "My_Hand_Size", 
                "Opp_Hand_Size", "Boneyard_Size", "Is_Double", "Pip_Count",
                "Count_0", "Count_1", "Count_2", "Count_3", "Count_4", "Count_5", "Count_6",
                "Unplayed_0", "Unplayed_1", "Unplayed_2", "Unplayed_3", "Unplayed_4", "Unplayed_5", "Unplayed_6",
                "Is_Opponent_Vulnerable"
            ]

            feature_values = [[
                l_end, r_end, tile[0], tile[1], my_hand_size, opp_hand_size, boneyard_size, 
                is_double, pip_count, suit_counts[0], suit_counts[1], suit_counts[2], 
                suit_counts[3], suit_counts[4], suit_counts[5], suit_counts[6],
                unplayed[0], unplayed[1], unplayed[2], unplayed[3], unplayed[4], unplayed[5], unplayed[6],
                is_vuln
            ]]

            features = pd.DataFrame(feature_values, columns=feature_names)
                        
            prob = self.model.predict_proba(features)[0][1] 
            if prob > highest_prob:
                highest_prob = prob
                best_move = move

        if best_move is None:
            best_move = random.choice(valid_moves)
        return best_move