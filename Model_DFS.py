'PERMAINAN DOMINO DENGAN MODEL DFS'

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