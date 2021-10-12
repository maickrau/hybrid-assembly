#!/usr/bin/python

import sys

# gfa from stdin
# gfa to stdout

def getone(s):
	assert len(s) == 1
	for n in s:
		return n

def revcomp(s):
	comp = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N'}
	return "".join(comp[c] for c in s[::-1])

def revnode(n):
	return (">" if n[0] == "<" else "<") + n[1:]

def start_unitig(startpos, unitigs, belongs_to_unitig, edges):
	assert startpos[1:] not in belongs_to_unitig
	new_unitig = [startpos]
	belongs_to_unitig.add(startpos[1:])
	while len(edges[new_unitig[-1]]) == 1 and getone(edges[new_unitig[-1]])[1:] != new_unitig[-1][1:]:
		new_pos = getone(edges[new_unitig[-1]])
		if len(edges[revnode(new_pos)]) != 1: break
		assert new_pos[1:] not in belongs_to_unitig
		new_unitig.append(new_pos)
		belongs_to_unitig.add(new_pos[1:])
	unitigs.append(new_unitig)

def start_circular_unitig(startpos, unitigs, belongs_to_unitig, edges):
	assert startpos[1:] not in belongs_to_unitig
	assert len(edges[revnode(startpos)]) == 1
	assert len(edges[startpos]) == 1
	new_unitig = [startpos]
	belongs_to_unitig.add(startpos[1:])
	while True:
		assert len(edges[new_unitig[-1]]) == 1
		new_pos = getone(edges[new_unitig[-1]])
		assert len(edges[revnode(new_pos)]) == 1
		if new_pos == startpos: break
		assert new_pos[1:] not in belongs_to_unitig
		new_unitig.append(new_pos)
		belongs_to_unitig.add(new_pos[1:])
	unitigs.append(new_unitig)

def get_seq(unitig, node_seqs, edge_overlaps):
	result = node_seqs[unitig[0][1:]]
	if unitig[0][0] == "<": result = revcomp(result)
	for i in range(1, len(unitig)):
		add = node_seqs[unitig[i][1:]]
		if unitig[i][0] == "<": add = revcomp(add)
		add = add[edge_overlaps[(unitig[i-1], unitig[i])]:]
		result += add
	return result


node_seqs = {}
edges = {}
edge_overlaps = {}

for l in sys.stdin:
	parts = l.strip().split('\t')
	if parts[0] == "S":
		node_seqs[parts[1]] = parts[2]
		if ">" + parts[1] not in edges: edges[">" + parts[1]] = set()
		if "<" + parts[1] not in edges: edges["<" + parts[1]] = set()
	elif parts[0] == 'L':
		fromnode = (">" if parts[2] == "+" else "<") + parts[1]
		tonode = (">" if parts[4] == "+" else "<") + parts[3]
		if fromnode not in edges: edges[fromnode] = set()
		edges[fromnode].add(tonode)
		if revnode(tonode) not in edges: edges[revnode(tonode)] = set()
		edges[revnode(tonode)].add(revnode(fromnode))
		edge_overlaps[(fromnode, tonode)] = int(parts[5][:-1])
		edge_overlaps[(revnode(tonode), revnode(fromnode))] = int(parts[5][:-1])

belongs_to_unitig = set()
unitigs = []

for node in node_seqs:
	assert ">" + node in edges
	assert "<" + node in edges
	if len(edges[">" + node]) != 1:
		if node not in belongs_to_unitig: start_unitig("<" + node, unitigs, belongs_to_unitig, edges)
		for edge in edges[">" + node]:
			if edge[1:] not in belongs_to_unitig: start_unitig(edge, unitigs, belongs_to_unitig, edges)
	if len(edges["<" + node]) != 1:
		if node not in belongs_to_unitig: start_unitig(">" + node, unitigs, belongs_to_unitig, edges)
		for edge in edges["<" + node]:
			if edge[1:] not in belongs_to_unitig: start_unitig(edge, unitigs, belongs_to_unitig, edges)
	if len(edges[">" + node]) == 1 and getone(edges[">" + node])[1:] == node:
		if node not in belongs_to_unitig: start_unitig("<" + node, unitigs, belongs_to_unitig, edges)
	if len(edges["<" + node]) == 1 and getone(edges["<" + node])[1:] == node:
		if node not in belongs_to_unitig: start_unitig(">" + node, unitigs, belongs_to_unitig, edges)

for node in node_seqs:
	if node in belongs_to_unitig: continue
	start_circular_unitig(">" + node, unitigs, belongs_to_unitig, edges)

unitig_start = {}
unitig_end = {}
for i in range(0, len(unitigs)):
	unitig_start[unitigs[i][0]] = ">" + str(i)
	unitig_start[revnode(unitigs[i][-1])] = "<" + str(i)
	unitig_end[unitigs[i][-1]] = ">" + str(i)
	unitig_end[revnode(unitigs[i][0])] = "<" + str(i)

unitig_edges = set()
for node in node_seqs:
	assert node in belongs_to_unitig
	if ">" + node in unitig_end:
		for target in edges[">" + node]:
			assert target in unitig_start
			edge = (unitig_end[">" + node], unitig_start[target], edge_overlaps[(">" + node, target)])
			unitig_edges.add(edge)
	if "<" + node in unitig_end:
		for target in edges["<" + node]:
			assert target in unitig_start
			edge = (unitig_end["<" + node], unitig_start[target], edge_overlaps[("<" + node, target)])
			unitig_edges.add(edge)

for i in range(0, len(unitigs)):
	unitig_seq = get_seq(unitigs[i], node_seqs, edge_overlaps)
	print("S\t" + str(i) + "\t" + unitig_seq)

for edge in unitig_edges:
	print("L\t" + edge[0][1:] + "\t" + ("+" if edge[0][0] == ">" else "-") + "\t" + edge[1][1:] + "\t" + ("+" if edge[1][0] == ">" else "-") + "\t" + str(edge[2]) + "M")