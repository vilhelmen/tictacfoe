from py2neo import Node, Graph, Relationship
# Maybe just use the raw neo4j library?


"""
docker run --publish=7474:7474 --publish=7687:7687 neo4j
"""

# We need to deduplicate nodes, but not edges. Edges will always be unique.
graph_nodes = {}
graph_edges = []

# Alternatively, we can load it directly into the db.
# But we'll avoid the hassle of talking back and forth with the db doing it this way


# Strings are immutable, so woo hoo.
# Replace elements with text[:1] + 'Z' + text[2:]
def recurse_board(current_state, move, previous_state_node):
    # Validate
    # Check all win states, panic if we have more than one win and return

    # 012
    # 345
    # 678

    # I had 8 ifs but I forgot to account for blank spaces. I guess it's still 8 ifs.
    # This should make it a little better, minor optimization. So much for across, down, and diagonal blocks.
    # WHOOPS, need to know what side won if it's just one
    wins = 0
    winner_set = set()
    if current_state[0] in {'U', 'T'}:
        # 3 states
        # *--
        # |\
        # | \
        cat_wins = 0
        if current_state[0] == current_state[4] and current_state[0] == current_state[8]:
            cat_wins += 1
        if current_state[0] == current_state[3] and current_state[0] == current_state[6]:
            cat_wins += 1
        if current_state[0] == current_state[1] and current_state[0] == current_state[2]:
            cat_wins += 1
        if cat_wins:
            wins += cat_wins
            winner_set.add(current_state[4])
    if current_state[4] in {'U', 'T'}:
        # The two diagonals could go here but I'm not sure that's better?
        # It would make the branches more unbalanced.
        # Generated states with multiple win states are less likely than others^[citation needed]
        # Mmmmm I can't tell what that implies at 2:30 AM.
        # Spreading it out more evenly... UHHHHH??????
        # 2 states
        #  |
        # -*-
        #  |
        cat_wins = 0
        if current_state[3] == current_state[4] and current_state[3] == current_state[5]:
            cat_wins += 1
        if current_state[1] == current_state[4] and current_state[1] == current_state[7]:
            cat_wins += 1
        if cat_wins:
            wins += cat_wins
            winner_set.add(current_state[4])
    if current_state[4] in {'U', 'T'}:
        # 3 states
        # \ |
        #  \|
        # --*
        cat_wins = 0
        if current_state[6] == current_state[7] and current_state[6] == current_state[8]:
            cat_wins += 1
        if current_state[2] == current_state[5] and current_state[2] == current_state[8]:
            cat_wins += 1
        if current_state[6] == current_state[4] and current_state[6] == current_state[2]:
            cat_wins += 1
        if cat_wins:
            wins += cat_wins
            winner_set.add(current_state[4])

    # NO >:C
    if wins > 1:
        return
    elif wins == 1:
        winner = next(iter(winner_set))
    else:
        winner = None

    # At this point, we have our board, and we know it's valid.
    # We also know if it's a winner.
    # If it's a winner, we should insert it and end.
    # If it's not, we should insert our current state, plan our next moves, and iterate on them.

    # Add to the node pile
    if current_state not in graph_nodes:
        graph_nodes[current_state] = Node("BoardState")
    current_state_node = graph_nodes[current_state]
    graph_edges.append(Relationship(previous_state_node, "Move", current_state_node, move=move))

    if winner:
        # Properties can be added after the fact without messing up relationships, I checked!
        current_state_node['victory'] = winner
        return

    # Get indices of empty spaces. this could be passed in. We'd have to watch for edits, or just use slices!
    # We could also just iterate through this, but I'd rather just have a list for clarity
    next_moves = [i for i, ltr in enumerate(current_state) if ltr == ' ']

    # Iterate through them, changing each piece to U, T and then back to ' ' and move to the next spot
    # (num of empty spaces also happens to be the inverse of piece total)


def recurse_generate():
    # Need a converter, board->id and back

    # Reduce across columns and rows for each, etc, etc.
    # Oh hell, I forgot about diagonals.
    # It's only like 8 directions, why bother with numpy

    # we need and US and a THEM maybe? Victory and loss nodes?
    # make the board even UvT instead of XvO to drive it home maybe?

    # Ok, I wanted to use ID for the board layout, but apparently that's an internal thing we shouldn't do that

    # So, each node has a state, which is just a string "U TUTT TU"
    # How do we mark victory/loss nodes. victory = true? he property just needs to exist, it doesn't need a value
    # Idea, let's add a property that is the piece total. Could be used for hierarchical layout.

    # Edges have a character/string marking whose turn it is

    # we can only recurse like 9 levels, so recursion should totally be safe. Super easy.

    # Curious... Can we dedpue half the boards by somehow changing which is which?
    # That seems like query complexity will be string hell
    # Unless each board position is a property...?????????????????????

    # So, we have the string "         " and loop though placing pieces, tracking what piece and the predecessor
    # But that seems wasteful for some reason(?)
    # We can use itertools to loop through generating all 8 character strings of " UT"
    # Then we just need to skip invalid ones. But then we have to reverse engineer connections.
    # That seems like an edit distance problem, though.
    # The generator is so easy though...

    board_start = "        "

    recurse_board()


if __name__ == '__main__':
    recurse_generate()
