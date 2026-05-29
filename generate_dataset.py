import random
import csv
import time
import os

import pandas as pd

from modelling_search import BFSBot, AStarBot
from gui_code import DominoEngine

def extract_features(engine, current_hand, opponent_hand, move, opp_pass_l=-1, opp_pass_r=-1):
    tile, side = move
    l_end = engine.left_end if engine.left_end is not None else -1
    r_end = engine.right_end if engine.right_end is not None else -1
    
    # --- 1. Base Features ---
    my_hand_size = len(current_hand)
    opp_hand_size = len(opponent_hand)
    boneyard_size = len(engine.boneyard)
    is_double = 1 if tile[0] == tile[1] else 0
    pip_count = sum([t[0] + t[1] for t in current_hand])
    
    suit_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
    for t in current_hand:
        suit_counts[t[0]] += 1
        if t[0] != t[1]: suit_counts[t[1]] += 1
            
    # --- 2. NEW: Unplayed Tile Counts (Card Counting) ---
    unplayed = {0:7, 1:7, 2:7, 3:7, 4:7, 5:7, 6:7} # 7 of each suit exist
    # Subtract what we see in our hand
    for t in current_hand:
        unplayed[t[0]] -= 1
        if t[0] != t[1]: unplayed[t[1]] -= 1
    # Subtract what we see on the board
    for t in engine.board:
        unplayed[t[0]] -= 1
        if t[0] != t[1]: unplayed[t[1]] -= 1

    # --- 3. NEW: Is Opponent Vulnerable ---
    # Determine what the board ends WILL be after this move
    new_l, new_r = l_end, r_end
    if side == 'first':
        new_l, new_r = tile[0], tile[1]
    elif side == 'left':
        new_l = tile[0] if tile[1] == l_end else tile[1]
    elif side == 'right':
        new_r = tile[1] if tile[0] == r_end else tile[0]
        
    # If this move forces a board end to be a suit the opponent just passed on, they are vulnerable!
    is_vuln = 0
    if ((new_l == opp_pass_l or new_l == opp_pass_r) and new_l != -1) or \
       ((new_r == opp_pass_l or new_r == opp_pass_r) and new_r != -1):
        is_vuln = 1
    
    return {
        "Left_End": l_end, "Right_End": r_end, "Tile_A": tile[0], "Tile_B": tile[1],
        "My_Hand_Size": my_hand_size, "Opp_Hand_Size": opp_hand_size, "Boneyard_Size": boneyard_size,
        "Is_Double": is_double, "Pip_Count": pip_count,
        "Count_0": suit_counts[0], "Count_1": suit_counts[1], "Count_2": suit_counts[2],
        "Count_3": suit_counts[3], "Count_4": suit_counts[4], "Count_5": suit_counts[5], "Count_6": suit_counts[6],
        "Unplayed_0": unplayed[0], "Unplayed_1": unplayed[1], "Unplayed_2": unplayed[2], # <-- ADDED
        "Unplayed_3": unplayed[3], "Unplayed_4": unplayed[4], "Unplayed_5": unplayed[5], "Unplayed_6": unplayed[6],
        "Is_Opponent_Vulnerable": is_vuln # <-- ADDED (Passed features removed)
    }

def simulate_games(num_games=1000, save_path="generated_dataset.csv"):
    engine = DominoEngine()
    bot_bfs = BFSBot()
    bot_astar = AStarBot()
    dataset = []
    
    for game_idx in range(num_games):
        engine.reset_game()
        hand_bfs, hand_astar = engine.bot_hand, engine.player_hand
        bfs_last_pass, astar_last_pass = (-1, -1), (-1, -1)
        turn = random.choice(['BFS', 'ASTAR']) 
        consecutive_passes = 0
        
        while consecutive_passes < 2 and len(hand_bfs) > 0 and len(hand_astar) > 0:
            if turn == 'BFS':
                current_bot, engine.bot_hand, engine.player_hand = bot_bfs, hand_bfs, hand_astar
                opp_passed = astar_last_pass
            else:
                current_bot, engine.bot_hand, engine.player_hand = bot_astar, hand_astar, hand_bfs
                opp_passed = bfs_last_pass
                
            valid_moves = engine.get_valid_moves(engine.bot_hand)
            if valid_moves:
                consecutive_passes = 0
                best_move = current_bot.choose_move(engine)
                
                # Label the best move as 1, others as 0
                for move in valid_moves:
                    row = extract_features(engine, engine.bot_hand, engine.player_hand, move, opp_passed[0], opp_passed[1])
                    row["Label"] = 1 if move == best_move else 0 
                    dataset.append(row)
                    
                engine.play_tile(engine.bot_hand, best_move)
                
            else:
                # Track what they passed on
                current_l = engine.left_end if engine.left_end is not None else -1
                current_r = engine.right_end if engine.right_end is not None else -1
                if turn == 'BFS': bfs_last_pass = (current_l, current_r)
                else: astar_last_pass = (current_l, current_r)

                if len(engine.boneyard) > 0:
                    engine.draw_tile(engine.bot_hand)
                    consecutive_passes = 0 
                else:
                    consecutive_passes += 1
            
            if turn == 'BFS':
                hand_bfs, hand_astar, turn = engine.bot_hand, engine.player_hand, 'ASTAR'
            else:
                hand_astar, hand_bfs, turn = engine.bot_hand, engine.player_hand, 'BFS'
            
        if (game_idx + 1) % 100 == 0:
            print(f"Finished {game_idx + 1} / {num_games} games...")

    df = pd.DataFrame(dataset)
    df.to_csv(save_path, index=False)

if __name__ == "__main__":
    simulate_games(num_games=140000)