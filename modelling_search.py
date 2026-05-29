import random

class DFSBot:
    def __init__(self):
        self.name = "Depth-First Search"    
        self.max_depth = 3  # Menentukan seberapa jauh model dapat membayangkan langkah kedepannya

    def choose_move(self, engine):
        valid_moves = engine.get_valid_moves(engine.bot_hand)   # Mengambil kartu yang dimiliki oleh pemain untuk dilempar/ dimainkan
        if not valid_moves: # Kondisi jika tidak ada kartu yang bisa di lempar, maka akan 'None'
            return None

        best_move = None    # 'None' disini dibuat sebagai tempat awal untuk kemudian dipakai menyimpan langkah yang dianggap sebagai terbaik
        best_score = -float('inf')  # '- float' disini sebagai nilai tak terhingga untuk dijadikan sebagai pembanding nilai awal

        for move in valid_moves:
            tile, side = move
            remaining_hand = [t for t in engine.bot_hand if t != tile]  # Daftar sisa kartu yang dimiliki pemain
            
            new_left, new_right = self.simulate_board(engine.left_end, engine.right_end, move)  # Memprediksi kemungkinan menjalankan kartu yang dimiliki tanpa mengubah susunan kartu yang sedang dimainkan 

            score = self.dfs(remaining_hand, new_left, new_right, depth=1)  # Menjalankan simulasi dengan DFS untuk memprediksi apakah memiliki peluang untung/sebaliknya

            if score > best_score:  # Hasil yang dinyatakan lebih baik dari simulasi sebelumnya, akan disimpan sebagai 'best score'
                best_score = score
                best_move = move

        return best_move if best_move else random.choice(valid_moves)   # Mengembalikan langkah terbaik/memilih secara acak jika terdapat semua skor sama

    def simulate_board(self, left, right, move):    # Fungsi untuk menghitung angka pada ujung kartu tanpa mengubah kartu yang aslinya
        tile, side = move
        if side == 'first': # Jika sebagai kartu pertama
            return tile[0], tile[1]
        
        if side == 'left':  # Jika dipasang di bagian kiri, kemudian cari angka kartu yang akan menghadap keluar
            new_left = tile[0] if tile[1] == left else tile[1]
            return new_left, right
        else:   # Jika di pasang di bagian kanan, kemudian cari angka kartu yang akan menghadap keluar
            new_right = tile[1] if tile[0] == right else tile[0]
            return left, new_right

    def dfs(self, hand, left, right, depth):    # Fungsi rekrusif untuk menelusuri kemungkinan langkah         
        if depth >= self.max_depth or not hand:
            return len(self.get_simulated_valid_moves(hand, left, right))   # Pemberian skor berdasarkan berapa banyak pilihan langkah yang masih terbuka
        valid_moves = self.get_simulated_valid_moves(hand, left, right)  # Cari kartu mana saja di tangan simulasi yang bisa dipasang        
        if not valid_moves: # Diberikan skor neatif sebagai penanda bahwa langkah kartu buntu
            return -1 
        max_path_score = -float('inf')
        
        for move in valid_moves:    # Menelusuri tiap kemungkinan langkah yang dimiliki
            tile, side = move
            new_hand = [t for t in hand if t != tile]   # Kurangi kartu di tangan simulasi

            new_l, new_r = self.simulate_board(left, right, move)   # Update kondisi papan simulasi
            
            score = self.dfs(new_hand, new_l, new_r, depth + 1) # REKURSI: Panggil DFS lagi dengan menambah kedalaman (depth + 1)
            max_path_score = max(max_path_score, score)  # Mengambil skor tertinggi dari semua jalur yang mungkin

        return max_path_score

    def get_simulated_valid_moves(self, hand, left, right): # Mengecek kartu di tangan simulasi yang cocok dengan ujung papan simulasi
        moves = []
        for tile in hand:
            if left in tile: 
                moves.append((tile, 'left'))
            if right in tile: 
                moves.append((tile, 'right'))
        return moves

class BFSBot:
    def __init__(self):
        self.name = "Breadth-First Search"

    def choose_move(self, engine):
        valid_moves = engine.get_valid_moves(engine.bot_hand)
        if not valid_moves:
            return None

        best_move = None
        max_future_moves = -1

        # BFS Logic: Look one "level" deep (1-ply search). 
        # Which current move will leave me with the most options on my NEXT turn?
        for move in valid_moves:
            tile, side = move
            
            # Simulate what the board ends would look like if we make this move
            simulated_left = engine.left_end
            simulated_right = engine.right_end
            
            if side == 'first':
                simulated_left, simulated_right = tile
            elif side == 'left':
                simulated_left = tile[0] if tile[1] == simulated_left else tile[1]
            elif side == 'right':
                simulated_right = tile[1] if tile[0] == simulated_right else tile[0]

            # Count how many of our remaining tiles would match these new simulated ends
            remaining_hand = [t for t in engine.bot_hand if t != tile]
            future_options = 0
            for future_tile in remaining_hand:
                if simulated_left in future_tile or simulated_right in future_tile:
                    future_options += 1

            if future_options > max_future_moves:
                max_future_moves = future_options
                best_move = move

        # Fallback if all moves lead to 0 future options
        if best_move is None:
            best_move = random.choice(valid_moves)

        return best_move


class AStarBot:
    def __init__(self):
        self.name = "A* Search"

    def choose_move(self, engine):
        valid_moves = engine.get_valid_moves(engine.bot_hand)
        if not valid_moves:
            return None

        best_move = None
        lowest_cost = float('inf')

        # A* Logic: Evaluate f(n) = g(n) + h(n)
        # We want to MINIMIZE the cost function f(n).
        for move in valid_moves:
            tile, side = move
            
            # g(n): The immediate cost. In dominoes, we want to dump heavy tiles.
            # So, playing a heavy tile has a "lower" cost penalty than playing a light tile.
            # Max tile weight is 12 (6|6).
            g = 12 - (tile[0] + tile[1]) 

            # h(n): The heuristic (guess) of future difficulty.
            # Let's count how many "unplayable" heavy tiles are left in our hand 
            # if we make this move.
            simulated_left = engine.left_end
            simulated_right = engine.right_end
            
            if side == 'first':
                simulated_left, simulated_right = tile
            elif side == 'left':
                simulated_left = tile[0] if tile[1] == simulated_left else tile[1]
            elif side == 'right':
                simulated_right = tile[1] if tile[0] == simulated_right else tile[0]

            remaining_hand = [t for t in engine.bot_hand if t != tile]
            
            # Heuristic penalty for every tile we hold that DOESN'T match the new board
            h = 0
            for future_tile in remaining_hand:
                if simulated_left not in future_tile and simulated_right not in future_tile:
                    h += (future_tile[0] + future_tile[1]) # Add its weight to the penalty

            # Total cost evaluation
            f = g + h

            if f < lowest_cost:
                lowest_cost = f
                best_move = move

        if best_move is None:
            best_move = random.choice(valid_moves)

        return best_move