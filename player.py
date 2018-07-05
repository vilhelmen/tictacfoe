#!/usr/bin/env python3

from py2neo import Graph, cypher_escape, cypher_repr
import random
import sys
import itertools

graph = Graph(sys.argv[1] if len(sys.argv) > 1 else 'bolt://neo4j:new password@localhost:7687')


def play():

    while True:
        who = input("Who first, (C)PU or (P)layer? ").upper().strip()
        if who == 'C':
            play_cycle = itertools.cycle(['U', 'T'])
        elif who == 'P':
            play_cycle = itertools.cycle(['T', 'U'])
        else:
            print("why tho")
            continue
        break

    while True:
        level = input("CPU level: 0,1,2? ").upper().strip()
        if level in {'0','1','2'}:
            difficulty_offset = int(level)
            break
        print("why tho")

    board_state = "         "

    player_str_map = str.maketrans('UT', 'XO')

    def state_to_str(state):
        return "{}|{}|{}\n-----\n{}|{}|{}\n-----\n{}|{}|{}".format(*state.translate(player_str_map))

    for turn in play_cycle:
        current_node = graph.nodes.match("Board", state=board_state).first()

        print('\n' + state_to_str(board_state) + '\n')
        print("DBG:", current_node)

        if current_node.has_label("End"):
            print("Game over!")
            if current_node.has_label("Win"):
                print("Womp womp")
            elif current_node.has_label("Loss"):
                print("YOU DEFEATED")
            else:
                print("Tie :/")
            return

        print("Odds are {}in your favor...".format("" if current_node['potential'] < 1 else "not "))

        if turn == 'U':
            # Check for a direct win
            # I can't find a nice way to use the object API for this without jumping through hoops

            if current_node['potential'] == 9999.99:
                print("Victory eminent(?)")
            if current_node['potential'] == 0:
                print('Doom! (but also potential is bugged right now)')

            win_move = graph.evaluate(
                "MATCH (n {{state: {board_state}}})-[r:Move {{who: 'U'}}]->(m:Win) RETURN r".format(
                    board_state=cypher_repr(board_state)))
            if win_move:
                print("Direct victory")
                board_state = board_state[0:win_move['where']] + 'U' + board_state[win_move['where'] + 1:]
                continue

            block_move = graph.evaluate(
                "MATCH (n {{state: {board_state}}})-[r:Move {{who: 'U'}}]->(m:Intermediary)-[s:Move {{who: 'T'}}]->(o:Loss) RETURN s".format(
                    board_state=cypher_repr(board_state)))
            if block_move:
                print("OH BEANS")
                board_state = board_state[0:block_move['where']] + 'U' + board_state[block_move['where'] + 1:]
                continue

            """
            tie_move = graph.evaluate(
                "MATCH (n {{state: {board_state}}})-[r:Move {{who: 'U'}}]->(m:Tie) RETURN r".format(
                    board_state=cypher_repr(board_state)))
            if tie_move:
                print("I guess this will have to do.")
                board_state = board_state[0:tie_move['where']] + 'U' + board_state[tie_move['where'] + 1:]
                continue
            """

            move = graph.evaluate("""
match (n:Board {{state: {board_state}}})-[r:Move {{who: 'U'}}]->(m:Board:Intermediary) where m.potential > 0
with r
order by m.potential DESC
with collect(r) as moves, count(r) as total, count(r)/3.0 as chunk_size
with moves, total, chunk_size, rand() as sel, {difficulty} as offset
with moves, total, toInteger((chunk_size*offset)+(chunk_size*sel)) as idx

return moves[idx]
""".format(board_state=cypher_repr(board_state), difficulty=cypher_repr(difficulty_offset)))
            print("DBG:", move)
            board_state = board_state[0:move['where']] + 'U' + board_state[move['where'] + 1:]

        else:
            while True:
                move = input("O to ? ").upper().strip()
                try:
                    move = int(move)
                    if board_state[move] == ' ':
                        break
                except:
                    pass
                print("why tho")
            board_state = board_state[0:move] + 'T' + board_state[move+1:]

    return


"""
match (n:Board {{state: {}}})-[r:Move {who: 'U'}]->(m:Board:Intermediary)
with r
order by m.potential DESC
with collect(r) as moves, count(r) as total, count(r)/3.0 as chunk_size
with moves, total, chunk_size, rand() as sel, {difficulty} as offset
with moves, total, toInteger((chunk_size*offset)+(chunk_size*sel)) as idx

return moves[idx], idx, total
"""


if __name__ == '__main__':
    play()