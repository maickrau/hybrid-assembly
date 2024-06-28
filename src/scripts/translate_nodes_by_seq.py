#!/usr/bin/env python

import sys
import graph_functions as gf

old_graph = sys.argv[1]
new_graph = sys.argv[2]
# old uniques from stdin
# new uniques to stdout

old_uniques = set()
for l in sys.stdin:
	old_uniques.add(l.strip())

old_unique_seqs = set()
with open(old_graph) as f:
	for l in f:
		parts = l.strip().split('\t')
		if parts[0] == 'S':
			if parts[1] in old_uniques: 
				old_unique_seqs.add(parts[2])
				old_unique_seqs.add(gf.revcomp(parts[2]))

with open(new_graph) as f:
	for l in f:
		parts = l.strip().split('\t')
		if parts[0] == 'S':
			is_new_unique = False
			for seq in old_unique_seqs:
				if seq in parts[2]:
					is_new_unique = True
					break
			if is_new_unique: print(parts[1])

