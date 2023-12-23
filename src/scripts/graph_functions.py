import networkx as nx
import sys

#Functions for indirect graph processing, nodes - "utig1-234"
def remove_large_tangles(G, MAX_LEN, MAX_SHORT_COMPONENT):
    shorts = set()
    for node in G.nodes():
        if G.nodes[node]['length'] < MAX_LEN:
            shorts.add(node)
    sh_G = G.subgraph(shorts)
    nodes_deleted = 0
    components_deleted = 0
    to_delete = []
    for comp in nx.connected_components(sh_G):
        if len(comp) > MAX_SHORT_COMPONENT:
            components_deleted += 1
            for e in comp:
                nodes_deleted += 1
                to_delete.append(e)
    G.remove_nodes_from(to_delete)
    sys.stderr.write(f'Removed {components_deleted} short nodes components and {nodes_deleted} short nodes. New '
                     f'number of nodes {G.number_of_nodes()}\n')
    return set(to_delete)

def nodes_in_tangles(G, MAX_LEN, MIN_TANGLE_SIZE):
    shorts = set()
    for node in G.nodes():
        if G.nodes[node]['length'] < MAX_LEN:
            shorts.add(node)
    res = set()
    sh_G = G.subgraph(shorts)
    for comp in nx.connected_components(sh_G):
        if len(comp) > MIN_TANGLE_SIZE:
            for n in comp:
                res.add(n)
    return res


def load_indirect_graph(gfa_file, G):

    for line in open(gfa_file, 'r'):
        if "#" in line:
            continue
        line = line.strip().split()

        if line[0] == "S":
            #noseq graphs
            ls = len(line[2])
            cov = 0
            for i in range(3, len(line)):
                spl_tag = line[i].split(":")
                if spl_tag[0] == "LN":
                    ls = int(spl_tag[2])
                if spl_tag[0] == "ll":
                    cov = float(spl_tag[2])                           
            G.add_node(line[1], length=int(ls), coverage=float(cov))
            
    #L and S lines can be mixed
    for line in open(gfa_file, 'r'):
        if "#" in line:
            continue
        line = line.strip().split()       
        if line[0] == "L":
            if line[1] not in G or line[3] not in G:
                sys.stderr.write("Error while graph loading; link between nodes not in graph:%s" % (line))
                sys.exit(1)
            G.add_edge(line[1], line[3])
