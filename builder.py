#!/usr/bin/env python3

from py2neo import Node, Graph, Relationship
import itertools
import progressbar
# Maybe just use the raw neo4j library?


"""
docker run --publish=7474:7474 --publish=7687:7687 neo4j
"""

# We need to deduplicate nodes, but not edges. Edges will always be unique.
graph_nodes = {}
graph_edges = []

# Alternatively, we can load it directly into the db.
# But we'll avoid the hassle of talking back and forth with the db doing it this way


def check_wins(current_state):
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

    return wins, winner_set


# Strings are immutable, so woo hoo.
# Replace elements with text[:1] + 'Z' + text[2:]
def DFS_recurse_board(current_state, move, previous_state_node, init=False):
    # Validate
    # Check all win states, panic if we have more than one win and return

    # 012
    # 345
    # 678

    # I had 8 ifs but I forgot to account for blank spaces. I guess it's still 8 ifs.
    # This should make it a little better, minor optimization. So much for across, down, and diagonal blocks.
    # WHOOPS, need to know what side won if it's just one
    wins, winner_set = check_wins(current_state)

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
        graph_nodes[current_state] = Node("Board", state=current_state)
        if not len(graph_nodes) % 100:
            print(len(graph_nodes), 'nodes!')
    current_state_node = graph_nodes[current_state]
    # If we're not the first board, we have a parent board.
    if not init:
        graph_edges.append(Relationship(previous_state_node, "Move", current_state_node, who=move))

    if winner:
        # Properties can be added after the fact without messing up relationships, I checked!
        current_state_node['winner'] = winner
        return

    # Get indices of empty spaces. this could be passed in. We'd have to watch for edits, or just use slices!
    # We could also just iterate through this, but I'd rather just have a list for clarity
    move_list = [i for i, ltr in enumerate(current_state) if ltr == ' ']

    # Iterate through them, changing each piece to U, T and then back to ' ' and move to the next spot
    # (num of empty spaces also happens to be the inverse of piece total)
    for new_move in move_list:
        # new_move in the index of a space to modify
        # We need to generate len(next_moves)*2 new boards and send them to the next level of processing
        for x in ['U', 'T']:
            # Thread these if init (But they'd probably have to be processes and uggghhhhh)
            DFS_recurse_board(current_state[0:new_move] + x + current_state[new_move+1:], x, current_state)
    else:
        # We didn't actually have any moves left, the board is full. No one wins.
        current_state_node['winner'] = 'N'

    # I'm curious. We could make the DB compute this, but this is easier for everyone involved.
    current_state_node['level'] = 9 - len(move_list)

    return


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

    # Curious... Can we dedupe half the boards by somehow changing which is which?
    # That seems like query complexity will be string hell
    # Unless each board position is a property...?????????????????????

    # So, we have the string "         " and loop though placing pieces, tracking what piece and the predecessor
    # But that seems wasteful for some reason(?)
    # We can use itertools to loop through generating all 8 character strings of " UT"
    # Then we just need to skip invalid ones. But then we have to reverse engineer connections.
    # That seems like an edit distance problem, though.
    # The generator is so easy though...

    print("Launching DFS build!")

    DFS_recurse_board("         ", "???", "?????????", True)

    print("Done processing! (??)")
    print(len(graph_nodes), "nodes and", len(graph_edges), "edges. Woooo")


def stat_check():
    # Run through all states as a sanity check
    states = itertools.product(' UT', repeat=9)
    total_wins, total_losses, total_ties, total_invalid, total = (0, 0, 0, 0, 3**9)
    for current_state in states:
        wins, winner_set = check_wins(current_state)

        if wins == 0:
            if ' ' not in current_state:
                total_ties += 1
        elif wins == 1:
            if 'U' in winner_set:
                total_wins += 1
            else:
                total_losses += 1
        else:
            total_invalid += 1

    print(total_wins, total_losses, total_ties, total_invalid, total)
    return total_wins, total_losses, total_ties, total_invalid, total


def node_generate():
    # node generation method.
    # Instead of running DFS from the root, this generates all nodes and all moves out from them
    # Should be no faster, but avoids large gaps of no visible progress.
    # So it's really just a placebo
    print("Computing move space...")

    # progress bar 1 init here
    # 0 to 3**9
    for current_state in progressbar.progressbar(itertools.product(' UT', repeat=9), max_value=3 ** 9):
        wins, winner_set = check_wins(current_state)

        # NO >:C
        if wins > 1:
            continue
        elif wins == 1:
            winner = next(iter(winner_set))
        else:
            winner = None

        # At this point, we have our board, and we know it's valid.
        # We also know if it's a winner.
        # If it's a winner, we should insert it and end.
        # If it's not, we should insert our current state, plan our next moves, and iterate on them.

        # No duplicate nodes this time!
        # Anything that made it here is valid

        # RIGHT, current_state when iterated this way is a tuple of strings. WHOOPS.
        # It can be used for keying the dict, but it makes things annoying later
        # That's fine for 90% of this
        state_str = ''.join(current_state)
        current_state_node = Node("Board", state=state_str)

        if winner:
            # Properties can be added after the fact without messing up relationships, I checked!
            current_state_node['winner'] = winner

        graph_nodes[state_str] = current_state_node

    print("Connecting nodes...")
    # new progress bar, new total, uhhh 17335!
    for current_state, current_state_node in progressbar.progressbar(graph_nodes.items()):
        # Look at all moves from this node, and add valid moves

        # Get indices of empty spaces.
        # Iterate through them, changing each piece to U or T
        # (num of empty spaces also happens to be the inverse of piece total, which is the level depth)
        move_list = [i for i, ltr in enumerate(current_state) if ltr == ' ']
        for new_move in move_list:
            # new_move in the index of a space to modify
            # We need to generate len(next_moves)*2 new boards and check validity
            # if it's valid, make a connection
            for move in ['U', 'T']:
                next_node = graph_nodes[current_state[0:new_move] + move + current_state[new_move + 1:]]
                if check_wins(next_node)[0] <= 1:
                    # state is valid, add to edges
                    graph_edges.append(Relationship(current_state_node, "Move", next_node, who=move))

        else:
            # Take this moment to detect ties, since this tells us that
            # We didn't actually have any moves left, the board is full. No one wins.
            current_state_node['winner'] = 'N'

        # I'm curious. We could make the DB compute this, but this is easier for everyone involved.
        current_state_node['level'] = 9 - len(move_list)

    print("Done processing!")
    print(len(graph_nodes), "nodes and", len(graph_edges), "edges. Woooo")


if __name__ == '__main__':
    #DFS_recurse_generate()
    stat_check()
