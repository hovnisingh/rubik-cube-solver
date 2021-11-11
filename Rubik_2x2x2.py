from os import stat
import random
import copy
import sys
import time
from typing import runtime_checkable

global verbose
global solution
global count
global failures
# ============================================================================
# get_arg() returns command line arguments.
# ============================================================================


def get_arg(index, default=None):
    '''Returns the command-line argument, or the default if not provided'''
    return sys.argv[index] if len(sys.argv) > index else default


# ============================================================================
# List of possible moves
# https://ruwix.com/online-puzzle-simulators/2x2x2-pocket-cube-simulator.php
#
# Each move permutes the tiles in the current state to produce the new state
# ============================================================================

RULES = {
    "U": [2,  0,  3,  1,   20, 21,  6,  7,    4,  5, 10, 11,
          12, 13, 14, 15,    8,  9, 18, 19,   16, 17, 22, 23],
    "U'": [1,  3,  0,  2,    8,  9,  6,  7,   16, 17, 10, 11,
           12, 13, 14, 15,   20, 21, 18, 19,    4,  5, 22, 23],
    "R":  [0,  9,  2, 11,    6,  4,  7,  5,    8, 13, 10, 15,
           12, 22, 14, 20,   16, 17, 18, 19,    3, 21,  1, 23],
    "R'": [0, 22,  2, 20,    5,  7,  4,  6,    8,  1, 10,  3,
           12, 9, 14, 11,    16, 17, 18, 19,   15, 21, 13, 23],
    "F":  [0,  1, 19, 17,    2,  5,  3,  7,   10,  8, 11,  9,
           6,  4, 14, 15,   16, 12, 18, 13,   20, 21, 22, 23],
    "F'": [0,  1,  4,  6,   13,  5, 12,  7,    9, 11,  8, 10,
           17, 19, 14, 15,   16,  3, 18,  2,   20, 21, 22, 23],
    "D":  [0,  1,  2,  3,    4,  5, 10, 11,    8,  9, 18, 19,
           14, 12, 15, 13,   16, 17, 22, 23,   20, 21,  6,  7],
    "D'": [0,  1,  2,  3,    4,  5, 22, 23,    8,  9,  6,  7,
           13, 15, 12, 14,   16, 17, 10, 11,   20, 21, 18, 19],
    "L":  [23,  1, 21,  3,    4,  5,  6,  7,    0,  9,  2, 11,
           8, 13, 10, 15,   18, 16, 19, 17,   20, 14, 22, 12],
    "L'": [8,  1, 10,  3,    4,  5,  6,  7,   12,  9, 14, 11,
           23, 13, 21, 15,   17, 19, 16, 18,   20,  2, 22,  0],
    "B":  [5,  7,  2,  3,    4, 15,  6, 14,    8,  9, 10, 11,
           12, 13, 16, 18,    1, 17,  0, 19,   22, 20, 23, 21],
    "B'": [18, 16,  2,  3,    4,  0,  6,  1,    8,  9, 10, 11,
           12, 13,  7,  5,   14, 17, 15, 19,   21, 23, 20, 22]
}


'''
sticker indices:

        0  1
        2  3
16 17   8  9   4  5  20 21
18 19  10 11   6  7  22 23
       12 13
       14 15

face colors:

    0
  4 2 1 5
    3

rules:
[ U , U', R , R', F , F', D , D', L , L', B , B']
'''


class Cube:

    def __init__(self, config="WWWW RRRR GGGG YYYY OOOO BBBB"):

        # ============================================================================
        # tiles is a string without spaces in it that corresponds to config
        # ============================================================================
        self.config = config
        self.tiles = config.replace(" ", "")

        self.depth = 0
        self.rule = ""
        self.parent = None

    def __str__(self):
        # ============================================================================
        # separates tiles into chunks of size 4 and inserts a space between them
        # for readability
        # ============================================================================
        chunks = [self.tiles[i:i+4] +
                  " " for i in range(0, len(self.tiles), 4)]
        return "".join(chunks)

    def __eq__(self, state):
        return (self.tiles == state.tiles) or (self.config == state.config)

    def toGrid(self):
        # ============================================================================
        # produces a string portraying the cube in flattened display form, i.e.,
        #
        #	   RW
        #	   GG
        #	BR WO YO GY
        #	WW OO YG RR
        #	   BB
        #	   BY
        # ============================================================================
        def part(face, portion):
            # ============================================================================
            # This routine converts the string corresponding to a single face to a
            # 2x2 grid
            #    face is in [0..5] if it exists, -1 if not
            #    portion is either TOP (=0) or BOTTOM (=1)
            # Example:
            # If state.config is "RWGG YOYG WOOO BBBY BRWW GYRR".
            #   part(0,TOP) is GW , part(0,BOTTOM) is WR, ...
            #   part(5,TOP) is BR , part(5,BOTTOM) is BB
            # ============================================================================

            result = "   "
            if face >= 0:
                offset = 4*face + 2*portion
                result = self.tiles[offset] + self.tiles[offset+1] + " "
            return result

        TOP = 0
        BOTTOM = 1

        str = ""
        for row in [TOP, BOTTOM]:
            str += part(-1, row) + part(0, row) + \
                part(-1, row) + part(-1, row) + "\n"

        for row in [TOP, BOTTOM]:
            str += part(4, row) + part(2, row) + \
                part(1, row) + part(5, row) + "\n"

        for row in [TOP, BOTTOM]:
            str += part(-1, row) + part(3, row) + \
                part(-1, row) + part(-1, row) + "\n"

        return str

    def applicablerules(self):
        return list(RULES.keys())
    
    # Takes in a rule 
    # Changes the state’s tiles and configuration based on the rule key’s indexes
    def applyrule(self, rule):
        rules = RULES.get(rule)
        new_tiles = [None] * len(rules)
        x = []
        i = 0
        for num in rules:
            new_tiles[i] = self.tiles[num]
            i = i + 1
        index = 0
        while (index+4 <= 24):
            x.append(new_tiles[index:index+4])
            index = index + 4
        self.config = [None] * len(x)
        i = 0
        for each in x:
            self.config[i] = "".join(each)
            i = i+1
        
        self.tiles = "".join(self.config)
        self.config = " ".join(self.config)

        return self
    
    # Returns true if each face in a state’s configuration of tiles has the same-colored tiles
    def goal(self):
        sides = ["WWWW", "RRRR", "OOOO", "GGGG", "BBBB", "YYYY"]
        face = self.config.split()
        for i in face:
            if i not in sides:
                return False
        return True


#--------------------------------------------------------------------
# GRAPHSEARCH:
#--------------------------------------------------------------------
# Takes in a list of states and which heuristic graph search is supposed to used
# Has an OPEN list and CLOSED list for states
# Generated but not expanded (OPEN)
# States that have been generated and expanded (CLOSED)
# Keeps track of each state's parent and each state's rule
# OUTPUT: The shortest path solution to a fully solved Rubik Cube
#-------------------------------------------------------------------
def graphsearch(statelist, heuristic):
    nodes_generated = 0
    nodes_expanded = 0
    timer = time.time()
    path = []
    tilespath = []
    closed = []
    openstates = [statelist]
    while (len(openstates) != 0):
        openstates = heuristic(openstates)
        state = openstates.pop(0)
        closed.append(copy.deepcopy(state))
        nodes_expanded = nodes_expanded +1
        if state.goal():
            finalstate = copy.deepcopy(state)
            while (state.parent is not None):
                tilespath.append(state)
                path.append(state.rule)
                state = state.parent
            print("Time: ", time.time() - timer, "seconds")
            tilespath.reverse()
            path.reverse()
            for i in range(len(tilespath)):
                print("Move", path[i], "produced state:", tilespath[i])
            print("Final State:")
            print(finalstate.toGrid())
            print("Nodes Generated:", nodes_generated)
            print("Nodes Expanded:", nodes_expanded)
            return path
        for rule in state.applicablerules():
            state2 = copy.deepcopy(state)
            newstate = state2.applyrule(rule)
            if (newstate not in (openstates+closed)):
                newstate.parent = state
                newstate.depth = state.depth + 1
                newstate.rule = rule
                nodes_generated = nodes_generated +1
                openstates.append(newstate)
            elif newstate in openstates:
                newstate.parent = [state, newstate.parent][argmin(state,newstate)]
                if newstate.parent.depth == state.depth:
                    newstate.rule = rule
                newstate.depth = newstate.parent.depth + 1
            elif newstate in closed:
                newstate.parent = [state, newstate.parent][argmin(state,newstate)]
                newstate.depth = newstate.parent.depth + 1
                for d in descendants(state,closed):
                    d.depth = d.parent.depth + 1

# BFS HEURISTIC
# Takes in a list of states and returns the sorted list of sates based on the depth of each state

def bfs_heuristic(states):
    newstatelist = sorted(states, key=lambda x: x.depth)
    return newstatelist

# BEST FIRST HEURISTIC
# For each face, calculates the number of misplaced tiles
# Sorts the list of states based on the list of misplaced tiles

def heursitic(states):
    states = bfs_heuristic(states)
    outOfPlace = []
    for state in states:
        tileOutofPlace = 0
        faces = state.config.split(" ")
        for each in faces:
            if not checking_faces(each):
                tileOutofPlace = tileOutofPlace +1
        outOfPlace.append(tileOutofPlace)
    assert(len(outOfPlace) == len(states))
    states_sorted = [state for op, state in sorted(zip(outOfPlace, states), key=lambda x: x[0])]
    return states_sorted


# Returns true is each tile in a face (input) is the same color
def checking_faces(tiles):
    if (tiles[0] == tiles[1] == tiles[2] == tiles[3]):
        return True
    return False


#--------------------------------------------------------------------
# ITERATIVE DEEPENING:
#--------------------------------------------------------------------
# Calls backtrack and if path returned is a failure
# Increase the depthbound and recall backtrack
# Returns the path to the solution
#--------------------------------------------------------------------
def iterative_deepening(statelist, depthbound):
    timer = time.time()
    n = depthbound
    while True:
        path = backtrack([statelist], n)
        if (path != "FAILURE"):
            break;
        else:
            n+=1
    print("Time: ", time.time() - timer, "seconds")
    return path


# def dfs(statelist, depthbound):
#     nodes_generated = 0
#     nodes_expanded = 0
#     timer = time.time()
#     path = []
#     tilespath = []
#     closed = []
#     openstates = [statelist]
#     while (len(openstates) != 0):
#         state = openstates.pop(0)
#         closed.append(copy.deepcopy(state))
#         nodes_expanded = nodes_expanded +1
#         if state.goal():
#             finalstate = copy.deepcopy(state)
#             while (state.parent is not None):
#                 tilespath.append(state)
#                 path.append(state.rule)
#                 state = state.parent
#             print("Time: ", time.time() - timer, "seconds")
#             tilespath.reverse()
#             path.reverse()
#             for i in range(len(tilespath)):
#                 print("Move", path[i], "produced state:", tilespath[i])
#             print("Final State:")
#             print(finalstate.toGrid())
#             print("Nodes Generated:", nodes_generated)
#             print("Nodes Expanded:", nodes_expanded)
#             return path
#         if (len(closed) > depthbound):
#             return "FAILURE"
#         for rule in state.applicablerules():
#             state2 = copy.deepcopy(state)
#             newstate = state2.applyrule(rule)
#             if (newstate not in (openstates+closed)):
#                 newstate.parent = state
#                 newstate.depth = state.depth + 1
#                 newstate.rule = rule
#                 nodes_generated = nodes_generated +1
#                 openstates.insert(0,newstate)
#             elif newstate in openstates:
#                 newstate.parent = [state, newstate.parent][argmin(state,newstate)]
#                 if newstate.parent.depth == state.depth:
#                     newstate.rule = rule
#                 newstate.depth = newstate.parent.depth + 1
#             elif newstate in closed:
#                 newstate.parent = [state, newstate.parent][argmin(state,newstate)]
#                 newstate.depth = newstate.parent.depth + 1
#                 for d in descendants(state,closed):
#                     d.depth = d.parent.depth + 1
    


#--------------------------------------------------------------------
# BACKTRACK:
#--------------------------------------------------------------------
# Initializes state to first element in statelist
# Checks if state is in the rest of the statelist, if it reaches the deadend condition,
# if the amount of states in statelist is greater than depthbound 
# If backtrack doesn’t return a failure, append the state and the rule to solution and return
#--------------------------------------------------------------------
      
def backtrack(statelist, depthbound):
    path = []
    visited = []
    global count
    global failures
    state = statelist[0]
    if (statelist.count(state)>1):
        return "FAILURE"
    if (len(statelist) > depthbound):
        return "FAILURE"
    if state.goal():
        print("!!!!!!")
        return None
    ruleset = (state.applicablerules())
    if (len(ruleset)==0):
        return "FAILURE"
    for rule in ruleset:
        newstate = state.applyrule(rule)
        if newstate.goal():
            solution.append([newstate,rule])
            return solution
        if newstate.config not in visited:
            visited.append(str(newstate.config))
            count += 1
            newstatelist = [newstate] + statelist
            path = backtrack(newstatelist, depthbound)
            if (path!="FAILURE"):
                solution.append([newstate,rule])
                return solution
            else:
                failures+=1
    return "FAILURE"

 
# Return list of rules that haven’t been applied to the given state
def deadend(state):
    for rule in list(RULES.keys()):
        if state.parent is not None:
            if state.parent.rule == rule:
                return True
    return False


# Add all the generated states from applying each rule that hasn’t been applied for into a new list
# Return list of descendants of a given state

def descendants(state, closed):
    descendants = []
    for rule in state.applicablerules():
        for each in closed:
            if rule != each.rule:
                descendedstate = state.applyrule(rule)
                descendants.append(descendedstate)
    return descendants


# Takes in a state and a newly generated state and decides whether or not the parent of the newstate should change to state 
def argmin(state, newstate):
    array = [state.depth,newstate.parent.depth]
    return array.index(min(array))
    

    # --------------------------------------------------------------------------------
    #  MAIN PROGRAM
    # --------------------------------------------------------------------------------
if __name__ == '__main__':

    # ============================================================================
    # Read input from command line:
    #   python3 <this program>.py STATE VERBOSE
    # where
    # STATE is a string prescribing an initial state
    #  (if empty, generate a problem to solve by applying a sequence of random
    #   rules to the default state.)
    # VERBOSE specifies to enter VERBOSE mode for detailed algorithm tracing.
    # ============================================================================
    CONFIG = get_arg(1)

    VERBOSE = get_arg(2)
    VERBOSE = (VERBOSE == "verbose" or VERBOSE == "v")
    if VERBOSE:
        verbose = True
        print("Verbose mode:")

    random.seed()  # use clock to randomize RNG

    # ============================================================================
    # Print list of all rules.
    # ============================================================================
    print("All Rules:\n_________")
    for m in RULES.keys():
        print("  " + str(m) + ": " + str(RULES[m]))

    # ============================================================================
    # Test case: default state is a goal state
    # ============================================================================
    state = Cube()
    print(state)

    if state.goal():
        print("SOLVED!")
    else:
        print("NOT SOLVED.")

    # ============================================================================
    # Test case: This state is one move from a goal.
    # Applying the "R" rule should solve the puzzle.
    # ============================================================================
    state = Cube("GRGR YYYY OGOG BOBO WWWW BRBR")
    print(state.toGrid())
    newState = state.applyrule("R")
    print(newState.toGrid())
    if newState.goal():
        print("SOLVED!")
    else:
        print("NOT SOLVED.")
        
    
    # ============================================================================
    # Breadth-First
    # ============================================================================
    state = Cube("GRGR YYYY OGOG BOBO WWWW BRBR")
    states = Cube("BBOG WOGY GRYY RRGO RYWB WWBO")
    
    print("BFS")
    graphsearch(state, bfs_heuristic)
 
    print("\n")
    
    # ============================================================================
    # Best-First
    # ============================================================================
    print("BEST FIRST")
    graphsearch(state, heursitic)
    
    # ============================================================================
    # Iterative-Deepening
    # ============================================================================
    print("\n")
    count = 0
    failures = 0
    solution = []
    
    state = Cube("GRGR YYYY OGOG BOBO WWWW BRBR")
    
    print("ITERATIVE-DEEPENING")
    path = iterative_deepening(state,20)
    if (path != "FAILURE"):
        for x in path:
            print("Move", x[1], "produced state:", x[0]) 
    else:
        print(path)
    print("NUMBER OF FAILURES:", failures)
    print("NUMBER OF CALLS TO BACKTRACK:", count)
    

 
    

