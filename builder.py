#!/usr/bin/env python3

from py2neo import Node, Graph, Relationship, Subgraph
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
    # 012
    # 345
    # 678
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
            winner_set.add(current_state[0])
    if current_state[4] in {'U', 'T'}:
        # 3 states
        #  |/
        # -*-
        # /|
        cat_wins = 0
        if current_state[4] == current_state[3] and current_state[4] == current_state[5]:
            cat_wins += 1
        if current_state[4] == current_state[1] and current_state[4] == current_state[7]:
            cat_wins += 1
        if current_state[4] == current_state[6] and current_state[4] == current_state[2]:
            cat_wins += 1
        if cat_wins:
            wins += cat_wins
            winner_set.add(current_state[4])
    if current_state[8] in {'U', 'T'}:
        # 2 states
        #   |
        #   |
        # --*
        cat_wins = 0
        if current_state[8] == current_state[7] and current_state[8] == current_state[6]:
            cat_wins += 1
        if current_state[8] == current_state[2] and current_state[8] == current_state[5]:
            cat_wins += 1
        if cat_wins:
            wins += cat_wins
            winner_set.add(current_state[8])

    return wins, winner_set


def prime_node_set(str_key=True):
    # prepopulate node set
    state_itr = itertools.product(' UT', repeat=9)

    if str_key:
        state_itr = map(lambda x: ''.join(x), state_itr)

    state_itr = map(lambda x: (x, 9-x.count(' '), *check_wins(x)), state_itr)

    total_wins, total_losses, total_ties, total_invalid, total_states = (0, 0, 0, 0, 3 ** 9)

    # We could filter invalid nodes from the iterator, but it would mess with progress counts
    for state, level, wins, winner in progressbar.progressbar(state_itr, max_value=3 ** 9):
        # Invalid!
        # Lol whoops, I wasn't respecting turn ordering. This threw out an additional 9000 states
        if wins > 1 or abs(state.count('U') - state.count('T')) > 1:
            total_invalid += 1
            continue

        new_node = Node("Board", state=state, level=level)

        # 0 wins and not level 9 (or 0) indicates intermediary node, may be of use to know?
        if wins == 0:
            if level == 9:
                total_ties += 1
                new_node['winner'] = 'N'
        else:
            winner = next(iter(winner))
            if winner == 'U':
                total_wins += 1
            else:
                total_losses += 1
            new_node['winner'] = winner

        graph_nodes[state] = new_node

    return total_wins, total_losses, total_ties, total_invalid, total_states


# Strings are immutable, so woo hoo.
# Replace elements with text[:1] + 'Z' + text[2:]
def DFS_recurse_board(current_state, move, previous_state_node, init=False):
    # Validate
    # Check all win states, panic if we have more than one win and return

    # 012
    # 345
    # 678

    # the node set has already been primed, and we validated before calling. Load node and plot next moves
    current_state_node = graph_nodes[current_state]

    # If we're not the first board, we have a parent board.
    if not init:
        graph_edges.append(Relationship(previous_state_node, "Move", current_state_node, who=move))

    # we're good, move on to another path
    if 'winner' in current_state_node:
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
            new_state = current_state[0:new_move] + x + current_state[new_move+1:]
            # This prevents unnecessary recursions. A boon to the 95 minute runtime.
            if new_state in graph_nodes:
                DFS_recurse_board(new_state, x, current_state)

    return


def DFS_recurse_generate():
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

    print("Priming node cache")
    prime_node_set()

    print("Launching DFS build!")

    DFS_recurse_board("         ", "???", "?????????", True)

    print("Done processing! (??)")
    print(len(graph_nodes), "nodes and", len(graph_edges), "edges. Woooo")


def BFS_recurse_board(node_layer):
    # extremely gentler on recursion depth than DFS
    new_layer = {}
    for n in progressbar.progressbar(node_layer):
        current_state = n['state']
        move_list = [i for i, ltr in enumerate(current_state) if ltr == ' ']

        # Iterate through them, changing each piece to U, T and then back to ' ' and move to the next spot
        # (num of empty spaces also happens to be the inverse of piece total)
        for new_move in move_list:
            # if the next node is good, add it to the next layer and build a link
            for x in ['U', 'T']:
                next_state = current_state[0:new_move] + x + current_state[new_move + 1:]
                if next_state in graph_nodes:
                    next_node = graph_nodes[next_state]
                    graph_edges.append(Relationship(n, "Move", next_node, who=x))
                    new_layer[next_state] = next_node

    if new_layer:
        print('Recursing...')
        return BFS_recurse_board(new_layer.values())


def BFS_recurse_generate():
    print("Priming node cache")
    prime_node_set()

    print("Launching BFS build!")

    BFS_recurse_board([graph_nodes['         ']])

    print("Done processing! (??)")
    print(len(graph_nodes), "nodes and", len(graph_edges), "edges. Woooo")


def stat_check():
    # Run through all states as a sanity check
    print(prime_node_set())


def node_generate():
    # node generation method.
    # Instead of running DFS from the root, this generates all nodes and all moves out from them
    print("Computing move space...")

    prime_node_set()

    print("Connecting nodes...")
    # new progress bar, new total, uhhh 17361!
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
                next_node = graph_nodes.get(current_state[0:new_move] + move + current_state[new_move + 1:])
                if next_node:
                    # state is valid, add to edges
                    graph_edges.append(Relationship(current_state_node, "Move", next_node, who=move))

    print("Done processing!")
    print(len(graph_nodes), "nodes and", len(graph_edges), "edges. Woooo")


def db_feed():
    g = Graph('bolt://neo4j:neo4j@localhost:7687')

    # Just let me use the default docker credentials. Come on.
    g.run("CALL dbms.changePassword('new password')")

    g = Graph('bolt://neo4j:new password@localhost:7687')

    graph = Subgraph(nodes=graph_nodes.items(), relationships=graph_edges)

    g.create(graph)


def debug_dump():
    with open('state_edges.txt', 'w') as se, open('full_edges.txt', 'w') as fe:
        for edge in graph_edges:
            se.write(edge.start_node['state'] + '->' + edge.end_node['state'] + '\n')
            fe.write(str(edge) + '\n')


if __name__ == '__main__':
    DFS_recurse_generate()
    #BFS_recurse_generate()
    #node_generate()
    #stat_check()
    #prime_node_set()
    debug_dump()
    #db_feed()
