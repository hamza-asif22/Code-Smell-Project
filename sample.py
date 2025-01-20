def print_solution(board):
    for row in board:
        print(" ".join("Q" if cell else "." for cell in row))
    print("\n")

def is_safe(board, row, col, n):
    for i in range(row):
        if board[i][col]:
            return False
    for i, j in zip(range(row, -1, -1), range(col, -1, -1)):
        if board[i][j]:
            return False
    for i, j in zip(range(row, -1, -1), range(col, n)):
        if board[i][j]:
            return False
    return True

def solve_n_queens_util(board, row, n):
    if row >= n:
        print_solution(board)
        return True  # Prints one solution
    res = False
    for col in range(n):
        if is_safe(board, row, col, n):
            board[row][col] = 1  # Place queen
            res = solve_n_queens_util(board, row + 1, n) or res
            board[row][col] = 0  # Backtrack and remove queen
    return res

def solve_n_queens(n):
    board = [[0 for _ in range(n)] for _ in range(n)]
    if not solve_n_queens_util(board, 0, n):
        print("No solution exists")
    else:
        print("Solution(s) found!")
solve_n_queens(4)
