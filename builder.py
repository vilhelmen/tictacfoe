#!/usr/bin/env python3

import itertools
import math
import sys

import progressbar
from py2neo import Node, Graph, Relationship, Subgraph, cypher_escape, cypher_repr

# Maybe just use the raw neo4j library?


"""
docker run --publish=7474:7474 --publish=7687:7687 neo4j
"""

# We need to deduplicate nodes, but not edges. Edges will always be unique.
graph_nodes = {}
graph_edges = []
# Turn implies a single move, let's go with round
graph_rounds = []


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

    state_itr = map(lambda x: (x, 9 - x.count(' '), *check_wins(x)), state_itr)

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

        # Idea: marking all leaves as End nodes. Then another label for Win/Loss/Tie.
        #  Easier search than where exists(n.winner). It doesn't HURT to have it, right?
        #  Also mark intermediary nodes. The root board is marked intermediary, and that technically isn't correct
        if wins == 0:
            if level == 9:
                total_ties += 1
                new_node['winner'] = 'N'
                new_node.add_label("Tie")
                new_node.add_label("End")
            else:
                new_node.add_label("Intermediary")
        else:
            winner = next(iter(winner))
            if winner == 'U':
                total_wins += 1
                new_node.add_label("Win")
            else:
                total_losses += 1
                new_node.add_label("Loss")
            new_node['winner'] = winner
            new_node.add_label("End")

        graph_nodes[state] = new_node

    # Ugh, either I fix it here or add another if to the generator that is only used once :/
    # I think i changed my mind. I like nodes being either intermediary or end states, I think.
    # Having Start doesn't hurt, I guess.
    # graph_nodes['         '].remove_label("Intermediary")
    graph_nodes['         '].add_label("Start")

    return total_wins, total_losses, total_ties, total_invalid, total_states


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
                    graph_edges.append(Relationship(current_state_node, "Move", next_node, who=move, where=new_move))

    # Second layer connectivity, compound moves
    # This enforces turn ordering by combining us/them move pairs into a single edge
    # Single move rounds are always our move
    print("Building rounds...")
    for current_state, current_state_node in progressbar.progressbar(graph_nodes.items()):
        # Look at all moves from this node, and add valid moves

        # If we have at least two moves, go through all permutations
        # Rounds are always Us and then Them, unless there is only one empty space, in which it is always us.
        move_list = [i for i, ltr in enumerate(current_state) if ltr == ' ']
        if len(move_list) == 1:
            next_node = graph_nodes.get(current_state[0:move_list[0]] + 'U' + current_state[move_list[0] + 1:])
            if next_node:
                graph_rounds.append(Relationship(current_state_node, "Round", next_node, where=move_list))
        else:
            single_move_blacklist = set()
            for move_pair in itertools.permutations(move_list, 2):
                move_one_state = current_state[0:move_pair[0]] + 'U' + current_state[move_pair[0] + 1:]
                move_one_node = graph_nodes.get(move_one_state)

                move_two_state = move_one_state[0:move_pair[1]] + 'T' + move_one_state[move_pair[1] + 1:]
                move_two_node = graph_nodes.get(move_two_state)
                # If the double move node isn't valid, we need to check the single node move
                if move_two_node:
                    # Turn is valid
                    graph_rounds.append(Relationship(current_state_node, "Round", move_two_node, where=list(move_pair)))
                elif move_one_node and move_pair[0] not in single_move_blacklist:
                    # Only one move is valid, and we haven't done it yet
                    graph_rounds.append(Relationship(current_state_node, "Round", move_one_node, where=[move_pair[0]]))
                    single_move_blacklist.add(move_pair[0])

    print("Done processing!")
    print(len(graph_nodes), "nodes,", len(graph_edges), "edges,", len(graph_rounds), "rounds. Woooo")


def grouper(iterable, n):
    """Groups iterable into chunks of size n (does not pad on poor division)"""
    it = iter(iterable)
    group = tuple(itertools.islice(it, n))
    while group:
        yield group
        group = tuple(itertools.islice(it, n))


def db_feed(bolt_url=None):
    if bolt_url:
        g = Graph(bolt_url)
    else:
        g = Graph('bolt://neo4j:neo4j@localhost:7687')

        # Just let me use the default docker credentials. Come on.
        g.run("CALL dbms.changePassword('new password')")

        g = Graph('bolt://neo4j:new password@localhost:7687')

    print('Tossing old data...')
    g.delete_all()

    # Ok, so the push of the full graph takes 12 minutes(!)
    # But doing parts individually takes FOREVER
    # But if we chunk the parts... Hehehe
    # WHAT THE HELL PUSHING THESE CHUNKS TAKES SECONDS. I'm even on my cell connection. I'm so mad.
    print('Pushing nodes...')
    tx = g.begin()
    for chunk in progressbar.progressbar(grouper(graph_nodes.values(), math.ceil(len(graph_nodes) / 10)), max_value=10):
        subg = Subgraph(nodes=chunk)
        tx.create(subg)
    print('Commit.')
    tx.commit()

    print('Pushing edges...')
    tx = g.begin()
    for chunk in progressbar.progressbar(grouper(graph_edges, math.ceil(len(graph_edges) / 20)), max_value=20):
        subg = Subgraph(relationships=chunk)
        tx.create(subg)
    print('Commit.')
    tx.commit()

    print('Pushing rounds...')
    tx = g.begin()
    for chunk in progressbar.progressbar(grouper(graph_rounds, math.ceil(len(graph_rounds) / 40)), max_value=40):
        subg = Subgraph(relationships=chunk)
        tx.create(subg)
    print('Commit.')
    tx.commit()

    # nodes and edges are now bound to their server copies, probably.

    s = g.schema

    print('Building constraints...')
    # Constraint implies an index, BUT an indexed term cannot have a constraint created
    # So this has to go first
    for x in {"state"} - {x[0] for x in s.get_uniqueness_constraints("Board")}:
        s.create_uniqueness_constraint("Board", x)

    # Technically we're just scheduling them
    print('Building indices...')
    for x in {"winner", "level"} - {x[0] for x in s.get_indexes("Board")}:
        s.create_index("Board", x)

    # Indices for Intermediary, Win, Loss, Tie, End, Start???? EHHH??
    # Rounds?

    # I can't imagine these are useful but why not
    for x in {"who", "where"} - {x[0] for x in s.get_indexes("Move")}:
        s.create_index("Move", x)

    print('Checking totals...')
    server_nodes = g.run('MATCH (n:Board) RETURN count(n)').evaluate()
    server_edges = g.run('MATCH (:Board)-[r:Move]->(:Board) RETURN count(r)').evaluate()
    server_rounds = g.run('MATCH (:Board)-[r:Round]->(:Board) RETURN count(r)').evaluate()
    print("Server has", server_nodes, "nodes,", server_edges, "edges, and", server_rounds, "rounds.")

    print('Done!')
    return


def db_post_process(bolt_url=None):
    if bolt_url:
        g = Graph(bolt_url)
    else:
        g = Graph('bolt://neo4j:new password@localhost:7687')

    # Data more easily computed by the db than us (ideally...)

    # Ideas:
    # move vector at each node pointing towards best move(s) (most wins, shortest path, fewer losses??)
    #  maximize win/loss ratio shortest path? Just ratio?
    # Count win nodes user current node. Same with loss?

    # I think I like gathering potential of descendants, ordering by potential, and selecting from that list
    # Hard could be first third, medium, middle third, easy, last third.
    # Easy might just be actively bad, though

    # This could be done during DFS but that's so slow
    # Potential
    # Is a tie a win or a loss? Ignore it?
    # a tie is better than a loss, but not something we should aim for.
    # Seems like a last resort kind of thing, like if potential is zero.
    # peggy_hill_hoo_yeah.wav works first time

    # TODO: make better, ignoring for now
    '''
    print('Computing node round potential...')
    tx = g.begin()

    for level_no in progressbar.progressbar([8, 7, 6, 5, 4, 3, 2, 1, 0]):
        # Attempt at a bottom-up build for faster computation
        # {{ to escape for format()
        # An intermediary MUST lead to some sort of end state or else the graph is busted
        tx.run("""
            MATCH (n:Board:Intermediary {{level: {level_no}}})-[:Round*]->(m:Board:End)
            WITH n, COLLECT(DISTINCT m) as m
            WITH n, SIZE(FILTER(x IN m WHERE x:Win)) as winner_children, 
                SIZE(FILTER(x IN m WHERE x:Loss)) as loser_children,
                SIZE(FILTER(x IN m WHERE x:Tie)) as tie_total
            SET n.potential = CASE loser_children WHEN 0 THEN 9999.99 ELSE toFloat(winner_children)/loser_children END,
                n.desperation = CASE loser_children WHEN 0 THEN 9999.99 ELSE (toFloat(winner_children)+tie_total)/loser_children END
            """.format(level_no=cypher_repr(level_no)))

    print('Commit.')
    tx.commit()

    s = g.schema
    print('Building potential index...')
    for x in {"potential"} - {x[0] for x in s.get_indexes("Board")}:
        s.create_index("Board", x)
    '''

    # More analysis, flag nodes with a direct T move to a Loss as critical
    # critical nodes have only one acceptable move, a block

    # Mark nodes with >1 direct Ts to Loss as some sort of fail state
    # Remove Rounds to them? We never want to go there.

    # So, we can't really have an if count(r) == 1 set n:critical elif count(r) > 1...
    # but you can fake it with foreach and list tricks
    print('Computing node criticality...')
    sizes = g.run("""
                MATCH (n:Board:Intermediary)-[r:Round]->(m:Board:Loss)
                WITH n, count(r) AS total
                WITH COLLECT([n, total]) as pairs
                WITH [x IN pairs WHERE x[1] = 1 | x[0]] AS criticals, [x IN pairs WHERE x[1] > 1 | x[0]] AS doomed
                FOREACH (n IN criticals | SET n:Critical)
                FOREACH (n IN doomed | SET n:Doomed)
                RETURN [SIZE(criticals), SIZE(doomed)]
            """).evaluate()
    print(sizes[0], "critical nodes,", sizes[1], "doomed nodes.")

    print('Computing node imminence...')
    sizes = g.run("""
                MATCH (n:Board:Intermediary)-[r:Round]->(m:Board:Win)
                SET n:Imminent
                RETURN COUNT(n)
            """).evaluate()
    print(sizes[0], "imminent nodes")

    # Hopefully the final edge type, ApprovedRound
    # These are the ones actually approved for use
    # Imminent states should only move to win states. Anything else is dumb.
    # Critical states should only have blocking moves. Anything else is dumb.
    # General round constraints:
    #   No moves to doomed states. (Another criticality thing?)
    #   No moves to critical states unless they can still lead to victory(?)
    #   Only moves to imminent states if possible??
    #  These are treating it like we control both moves, though. This may result in gaps in logic.
    print('Creating approved rounds...')

    print('Approving imminent rounds...')
    total = g.run("""
                MATCH (n:Board:Imminent)-[r:Round]->(m:Board:Win)
                CREATE (n)-[:ApprovedRound PROPERTIES(r)]->(m)
                RETURN COUNT(r)
            """).evaluate()
    print(total, "Imminent approved rounds")

    print('Approving critical block rounds')
    # Find moves to Loss nodes. these moves should all share the same T move
    # Take the T move, make it a U move, and generate all valid moves out (but not doomed, etc??)
    # This is getting complicated. Maybe it's easier to just duplicate all rounds and prune bad ones
    total = g.run("""
                MATCH (n:Board:Critical)-[r:Round]->(m:Board:Loss)
                collect distinct U/T moves(?)
                unwind them
                CREATE (n)-[:ApprovedRound where: [block, other]]->(m)
                RETURN COUNT(??)
            """).evaluate()
    # No rounds going to Doomed or Loss nodes. Skip critical nodes (for now, needs more processing).
    # Skip connections to nodes that only lead to nodes with no Win/Tie children
    # Only move to criticals if the critical can be redeemed
    g.run("""
            MATCH (n:Board:Intermediary)-[r:Round]->(m:Board)
            WHERE NOT m:Doomed AND NOT m:Loss AND NOT n:Critical
        """)

    # may need to pull all critical nodes and process them locally

    print('Done!')
    return


def db_stats(bolt_url=None):
    if bolt_url:
        g = Graph(bolt_url)
    else:
        g = Graph('bolt://neo4j:new password@localhost:7687')

    print('Counting levels...')
    print(g.run("""
        UNWIND [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] AS level_no
        MATCH (n:Board {level: level_no})
        WITH level_no, COLLECT(n) as n
        RETURN level_no, SIZE(n) as total,
            SIZE(FILTER(x IN n WHERE x:Intermediary)) as intermediary,
            SIZE(FILTER(x IN n WHERE x:End)) as end,
            SIZE(FILTER(x IN n WHERE x:Win)) as win,
            SIZE(FILTER(x IN n WHERE x:Loss)) as loss,
            SIZE(FILTER(x IN n WHERE x:Tie)) as tie
            ORDER BY level_no ASC
        """).to_table())

    print('Evaluating potential...')
    # Change to accumulate 9999s to a separate list and count them
    print(g.run("""
    UNWIND [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] AS level_no
    MATCH (n:Board:Intermediary {level: level_no})
    WITH level_no, COLLECT(n) AS n
    WITH level_no,
        FILTER(x IN n WHERE x.potential <> 9999.99) AS risky_list,
        FILTER(x IN n WHERE x.potential = 9999.99) AS inevitable
    UNWIND risky_list AS risky
    RETURN level_no, SIZE(inevitable), min(risky.potential), avg(risky.potential), max(risky.potential),
        min(risky.desperation), avg(risky.desperation), max(risky.desperation) ORDER BY level_no ASC
    """).to_table())

    print('Done!')
    return


def debug_dump():
    with open('state_edges.txt', 'w') as se, open('full_edges.txt', 'w') as fe:
        for edge in graph_edges:
            se.write(edge.start_node['state'] + '->' + edge.end_node['state'] + '\n')
            fe.write(str(edge) + '\n')


if __name__ == '__main__':
    node_generate()
    # stat_check()
    # prime_node_set()
    # debug_dump()

    db_feed(sys.argv[1] if len(sys.argv) > 1 else None)

    db_post_process(sys.argv[1] if len(sys.argv) > 1 else None)

    db_stats(sys.argv[1] if len(sys.argv) > 1 else None)
