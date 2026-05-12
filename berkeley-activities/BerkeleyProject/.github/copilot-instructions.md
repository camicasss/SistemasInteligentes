# Copilot Instructions for AI Coding Agents

## Project Overview
This codebase implements search algorithms and agent-based logic for AI coursework, including Pacman and Eight Puzzle environments. The main files are:
- `search.py`: Core search algorithms (DFS, BFS, UCS, A*).
- `searchAgents.py`: Pacman agent strategies using search.
- `eightpuzzle.py`: Eight Puzzle environment and agent logic.
- `pacman.py`: Game engine for Pacman.
- `game.py`: General game framework.
- `util.py`: Utility functions (priority queue, etc).

## Architecture & Data Flow
- **Agents** interact with environments via search algorithms.
- **Search algorithms** are implemented in `search.py` and used by agents in `searchAgents.py` and `eightpuzzle.py`.
- **Game logic** is handled in `pacman.py` and `game.py`.
- **Graphics**: `graphicsDisplay.py`, `graphicsUtils.py`, `textDisplay.py`.
- **Layouts**: Maze and puzzle layouts are stored in `layouts/`.

## Developer Workflows
- **Testing**: Run `python3 autograder.py -q qN` (where N is question number) to test solutions. Test cases are in `test_cases/`.
- **Debugging**: Use `python3 pacman.py` with agent and layout options for manual runs.
- **No build step**: Pure Python, no compilation required.

## Project-Specific Conventions
- **Search algorithms** must return a list of actions (e.g., ['North', 'East', ...]).
- **State representation**: States are often tuples (e.g., position, visited corners).
- **Agent classes** inherit from base agent classes in `game.py` or `searchAgents.py`.
- **Testing**: Solutions are validated against `.solution` files in `test_cases/`.
- **Graphics**: Use text or graphical display modules as needed.

## Integration Points
- **External dependencies**: None required; all code is self-contained.
- **Cross-component communication**: Agents call search functions, which operate on environment state.

## Examples
- To implement a new search algorithm, add it to `search.py` and reference it in `searchAgents.py`.
- To debug Pacman, run: `python3 pacman.py --layout tinyMaze --pacman SearchAgent`.

## Key Files
- `search.py`, `searchAgents.py`, `eightpuzzle.py`, `pacman.py`, `game.py`, `util.py`, `layouts/`, `test_cases/`

---

**Update this file if project structure or conventions change.**
