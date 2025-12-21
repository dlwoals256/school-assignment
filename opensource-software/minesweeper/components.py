"""
Core game logic for Minesweeper.

This module contains pure domain logic without any pygame or pixel-level
concerns. It defines:
- CellState: the state of a single cell
- Cell: a cell positioned by (col,row) with an attached CellState
- Board: grid management, mine placement, adjacency computation, reveal/flag

The Board exposes imperative methods that the presentation layer (run.py)
can call in response to user inputs, and does not know anything about
rendering, timing, or input devices.
"""

import random
from typing import List, Tuple
import json

class CellState:
    """Mutable state of a single cell.

    Attributes:
        is_mine: Whether this cell contains a mine.
        is_revealed: Whether the cell has been revealed to the player.
        is_flagged: Whether the player flagged this cell as a mine.
        adjacent: Number of adjacent mines in the 8 neighboring cells.
    """

    def __init__(self, is_mine: bool = False, is_revealed: bool = False, is_flagged: bool = False, adjacent: int = 0):
        self.is_mine = is_mine
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.adjacent = adjacent


class Cell:
    """Logical cell positioned on the board by column and row."""

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.state = CellState()


class Board:
    """Minesweeper board state and rules.

    Responsibilities:
    - Generate and place mines with first-click safety
    - Compute adjacency counts for every cell
    - Reveal cells (iterative flood fill when adjacent == 0)
    - Toggle flags, check win/lose conditions
    """

    def __init__(self, cols: int, rows: int, mines: int):
        self.cols = cols
        self.rows = rows
        self.num_mines = mines
        self.cells: List[Cell] = [Cell(c, r) for r in range(rows) for c in range(cols)]
        self._mines_placed = False
        self.revealed_count = 0
        self.game_over = False
        self.win = False

    def index(self, col: int, row: int) -> int:
        """Return the flat list index for (col,row)."""
        return row * self.cols + col

    def is_inbounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows
    
    # Modified
    def neighbors(self, col: int, row: int) -> List[Tuple[int, int]]:
        """Return a flat list of valid (col, row) neighbors."""
        result = []
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue  # 자기 자신은 제외
                n_c, n_r = col + j, row + i
                if self.is_inbounds(n_c, n_r):
                    result.append((n_c, n_r))
        return result

    def place_mines(self, safe_col: int, safe_row: int) -> None:
        all_positions = [(c, r) for r in range(self.rows) for c in range(self.cols)]
        forbidden = {(safe_col, safe_row)} | set(self.neighbors(safe_col, safe_row))
        pool = [p for p in all_positions if p not in forbidden]
        random.shuffle(pool)

        # Place mines
        mine_pos = pool[:self.num_mines]
        for c, r in mine_pos:
            self.cells[self.index(c, r)].state.is_mine = True
        
        # Compute adjacency counts
        for cell in self.cells:
            if cell.state.is_mine:
                continue
            c, r = cell.col, cell.row
            adjacent_mines = 0
            for n_c, n_r in self.neighbors(c, r):
                if self.is_inbounds(n_c, n_r) and self.cells[self.index(n_c, n_r)].state.is_mine:
                    adjacent_mines += 1
            cell.state.adjacent = adjacent_mines

        self._mines_placed = True

    def reveal(self, col: int, row: int) -> None:
        if not self.is_inbounds(col, row):
            return
        
        if not self._mines_placed:
            self.place_mines(col, row)
        
        cell = self.cells[self.index(col, row)]

        if cell.state.is_revealed or cell.state.is_flagged:
            return
        
        cell.state.is_revealed = True
        self.revealed_count += 1

        if cell.state.is_mine:
            self.game_over = True
            self._reveal_all_mines()
            return
        
        if cell.state.adjacent == 0:
            for n_c, n_r in self.neighbors(col, row):
                if self.is_inbounds(n_c, n_r):
                    self.reveal(n_c, n_r)

        self._check_win()

    def toggle_flag(self, col: int, row: int) -> None:
        if not self.is_inbounds(col, row):
            return
        
        cell = self.cells[self.index(col, row)]

        if cell.state.is_revealed:
            return
        
        cell.state.is_flagged = not cell.state.is_flagged

    def flagged_count(self) -> int:
        return sum(1 for cell in self.cells if cell.state.is_flagged)

    def _reveal_all_mines(self) -> None:
        """Reveal all mines; called on game over."""
        for cell in self.cells:
            if cell.state.is_mine:
                cell.state.is_revealed = True

    def _check_win(self) -> None:
        """Set win=True when all non-mine cells have been revealed."""
        total_cells = self.cols * self.rows
        if self.revealed_count == total_cells - self.num_mines and not self.game_over:
            self.win = True
            for cell in self.cells:
                if not cell.state.is_revealed and not cell.state.is_mine:
                    cell.state.is_revealed = True
    def to_dict(self):
        """현재 보드 상태를 딕셔너리로 변환"""
        return {
            "cols": self.cols,
            "rows": self.rows,
            "num_mines": self.num_mines,
            "mines_placed": self._mines_placed,
            "revealed_count": self.revealed_count,
            "game_over": self.game_over,
            "win": self.win,
            "cells": [
                {
                    "col": c.col,
                    "row": c.row,
                    "is_mine": c.state.is_mine,
                    "is_revealed": c.state.is_revealed,
                    "is_flagged": c.state.is_flagged,
                    "adjacent": c.state.adjacent
                } for c in self.cells
            ]
        }
    def from_dict(self, data):
        """딕셔너리 데이터를 읽어와서 보드 상태 복구"""
        self.cols = data["cols"]
        self.rows = data["rows"]
        self.num_mines = data["num_mines"]
        self._mines_placed = data["mines_placed"]
        self.revealed_count = data["revealed_count"]
        self.game_over = data["game_over"]
        self.win = data["win"]
        
        self.cells = []
        for c_data in data["cells"]:
            cell = Cell(c_data["col"], c_data["row"])
            cell.state.is_mine = c_data["is_mine"]
            cell.state.is_revealed = c_data["is_revealed"]
            cell.state.is_flagged = c_data["is_flagged"]
            cell.state.adjacent = c_data["adjacent"]
            self.cells.append(cell)

    def save_to_file(self, filename="savegame.json"):
        """보드 상태를 JSON 파일로 저장 (오류 수정 버전)"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # self.to_dict()가 반환하는 딕셔너리를 파일 f에 기록
                json.dump(self.to_dict(), f, indent=4)
            print(f"Game saved to {filename}")
        except Exception as e:
            print(f"Save failed: {e}")
    @classmethod
    def load_from_file(cls, filename="savegame.json"):
        """JSON 파일로부터 보드 객체 생성 및 복구"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            board = cls(data["cols"], data["rows"], data["num_mines"])
            board.from_dict(data)
            return board
        except FileNotFoundError:
            return None
        