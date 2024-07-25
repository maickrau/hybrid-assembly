#!/usr/bin/env python

import sys
import graph_functions as gf

# gfa from stdin
# gfa to stdout

def remove_graph_node(node, nodeseqs, edges):
	assert node in nodeseqs
	del nodeseqs[node]
	if ">" + node in edges:
		for edge in edges[">" + node]:
			assert gf.revnode(edge) in edges
			assert "<" + node in edges[gf.revnode(edge)]
			edges[gf.revnode(edge)].remove("<" + node)
		del edges[">" + node]
	if "<" + node in edges:
		for edge in edges["<" + node]:
			assert gf.revnode(edge) in edges
			assert ">" + node in edges[gf.revnode(edge)]
			edges[gf.revnode(edge)].remove(">" + node)
		del edges["<" + node]

def get_base_name(name):
	if "_" not in name: return name
	parts = name.split("_")
	if parts[-1][0:3] == "cut": return name
	return "_".join(parts[:-1])

nodeseqs = {}
edges = {}
edge_overlaps = {}
belongs_to_base = {}

for l in sys.stdin:
	parts = l.strip().split('\t')
	if parts[0] == 'S':
		nodeseqs[parts[1]] = parts[2]
		base = get_base_name(parts[1])
		if base not in belongs_to_base: belongs_to_base[base] = set()
		belongs_to_base[base].add(parts[1])
	elif parts[0] == 'L':
		fromnode = (">" if parts[2] == "+" else "<") + parts[1]
		tonode = (">" if parts[4] == "+" else "<") + parts[3]
		if fromnode not in edges: edges[fromnode] = set()
		edges[fromnode].add(tonode)
		if gf.revnode(tonode) not in edges: edges[gf.revnode(tonode)] = set()
		edges[gf.revnode(tonode)].add(gf.revnode(fromnode))
		frombase = get_base_name(fromnode)
		tobase = get_base_name(tonode)
		edge_overlaps[gf.canontip(frombase, gf.revnode(tobase))] = parts[5]

unresolve_number = {}
for base in belongs_to_base:
	unresolve_number[base] = 1

base_names = list(belongs_to_base.keys())
base_names.sort()

iteration = 0
while True:
	num_resolved = 0
	for base in base_names:
		assert len(belongs_to_base[base]) >= 1
		if len(belongs_to_base[base]) == 1: continue
		nodes_here = list(belongs_to_base[base])
		nodes_here.sort()
		outneighbor_groups = {}
		for node in nodes_here:
			out_neighbors = set()
			if ">" + node in edges: out_neighbors = edges[">" + node]
			out_neighbors = tuple(out_neighbors)
			if out_neighbors not in outneighbor_groups: outneighbor_groups[out_neighbors] = set()
			outneighbor_groups[out_neighbors].add(node)
		any_resolved = False
		for group in outneighbor_groups:
			assert len(outneighbor_groups[group]) >= 1
			if len(outneighbor_groups[group]) == 1: continue
			num_resolved += 1
			any_resolved = True
			new_node = base + "_unresolve" + str(unresolve_number[base])
			unresolve_number[base] += 1
			nodeseqs[new_node] = nodeseqs[gf.getone(belongs_to_base[base])]
			edges[">" + new_node] = set(group)
			for node in group:
				if gf.revnode(node) not in edges: print(group)
				assert gf.revnode(node) in edges
				edges[gf.revnode(node)].add("<" + new_node)
			edges["<" + new_node] = set()
			belongs_to_base[base].add(new_node)
			for node in outneighbor_groups[group]:
				if "<" + node not in edges: continue
				for edge in edges["<" + node]:
					edges["<" + new_node].add(edge)
					assert gf.revnode(edge) in edges
					edges[gf.revnode(edge)].add(">" + new_node)
			for node in outneighbor_groups[group]:
				remove_graph_node(node, nodeseqs, edges)
				belongs_to_base[base].remove(node)
			break # only do one per loop because of interactions between different outneighbor groups in weird cyclic tangles
		if any_resolved: continue
		inneighbor_groups = {}
		for node in nodes_here:
			in_neighbors = set()
			if "<" + node in edges: in_neighbors = edges["<" + node]
			in_neighbors = tuple(in_neighbors)
			if in_neighbors not in inneighbor_groups: inneighbor_groups[in_neighbors] = set()
			inneighbor_groups[in_neighbors].add(node)
		any_resolved = False
		for group in inneighbor_groups:
			assert len(inneighbor_groups[group]) >= 1
			if len(inneighbor_groups[group]) == 1: continue
			num_resolved += 1
			any_resolved = True
			new_node = base + "_unresolve" + str(unresolve_number[base])
			unresolve_number[base] += 1
			nodeseqs[new_node] = nodeseqs[gf.getone(belongs_to_base[base])]
			edges["<" + new_node] = set(group)
			for node in group:
				assert gf.revnode(node) in edges
				edges[gf.revnode(node)].add(">" + new_node)
			edges[">" + new_node] = set()
			belongs_to_base[base].add(new_node)
			for node in inneighbor_groups[group]:
				if ">" + node not in edges: continue
				for edge in edges[">" + node]:
					edges[">" + new_node].add(edge)
					assert gf.revnode(edge) in edges
					edges[gf.revnode(edge)].add("<" + new_node)
			for node in inneighbor_groups[group]:
				remove_graph_node(node, nodeseqs, edges)
				belongs_to_base[base].remove(node)
			break # only do one per loop because of interactions between different outneighbor groups in weird cyclic tangles
		if any_resolved: continue
	sys.stderr.write("iteration " + str(iteration) + " unresolved " + str(num_resolved) + "\n")
	iteration += 1
	if num_resolved == 0: break

sys.stderr.write("done unresolving, write graph" + "\n")

name_mapping = {}
for base in base_names:
	nodes_here = list(belongs_to_base[base])
	nodes_here.sort()
	for node in nodes_here:
		if len(belongs_to_base[base]) == 1:
			name_mapping[node] = base
		else:
			name_mapping[node] = node

node_names = list(nodeseqs)
node_names.sort()

for n in node_names:
	print("S\t" + name_mapping[n] + "\t" + nodeseqs[n])

edge_names = list(edges)
edge_names.sort()

for edge in edge_names:
	targets = list(edges[edge])
	targets.sort()
	for target in targets:
		from_base = get_base_name(edge)
		to_base = get_base_name(target)
		key = gf.canontip(from_base, gf.revnode(to_base))
		overlap = "0M"
		if key not in edge_overlaps:
			print(edge)
			print(target)
			print(from_base)
			print(to_base)
			print(key)
		if key in edge_overlaps: overlap = edge_overlaps[key]
		assert key in edge_overlaps
		print("L\t" + name_mapping[edge[1:]] + "\t" + ("+" if edge[0] == ">" else "-") + "\t" + name_mapping[target[1:]] + "\t" + ("+" if target[0] == ">" else "-") + "\t" + overlap)

sys.stderr.write("graph written" + "\n")



