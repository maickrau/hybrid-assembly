#!/usr/bin/env python

import sys

mapping_file = sys.argv[1]
edge_overlap_file = sys.argv[2]
read_alignment_file = sys.argv[3]
paths_file = sys.argv[4]
nodelens_file = sys.argv[5]
# layout to stdout

min_read_len_fraction = 0.5

def revnode(n):
	assert len(n) >= 2
	assert n[0] == "<" or n[0] == ">"
	return (">" if n[0] == "<" else "<") + n[1:]

def canon(left, right):
	if revnode(right) + revnode(left) < left + right:
		return (revnode(right), revnode(left))
	return (left, right)

def get_leafs(path, mapping, edge_overlaps, raw_node_lens):
	path_len = 0
	for i in range(0, len(path)):
		path_len += raw_node_lens[path[i][1:]]
		if i > 0: path_len -= edge_overlaps[canon(path[i-1], path[i])]
	result = [(n, 0, raw_node_lens[n[1:]]) for n in path]
	overlaps = []
	for i in range(1, len(path)):
		overlaps.append(edge_overlaps[canon(path[i-1], path[i])])
	current_len = 0
	for i in range(0, len(result)):
		assert result[i][2] > result[i][1]
		assert result[i][2] <= raw_node_lens[result[i][0][1:]]
		assert result[i][1] >= 0
		current_len += result[i][2] - result[i][1]
		if i > 0: current_len -= overlaps[i-1]
	assert current_len == path_len
	while True:
		any_replaced = False
		new_result = []
		new_overlaps = []
		for i in range(0, len(result)):
			if result[i][0][1:] not in mapping:
				new_result.append(result[i])
				if i > 0: new_overlaps.append(overlaps[i-1])
			else:
				any_replaced = True
				part = [(n, 0, raw_node_lens[n[1:]]) for n in mapping[result[i][0][1:]][0]]
				part[0] = (part[0][0], part[0][1] + mapping[result[i][0][1:]][1], part[0][2])
				part[-1] = (part[-1][0], part[-1][1], part[-1][2] - mapping[result[i][0][1:]][2])
				if result[i][0][0] == "<":
					part = [(revnode(n[0]), raw_node_lens[n[0][1:]] - n[2], raw_node_lens[n[0][1:]] - n[1]) for n in part[::-1]]
				old_start_clip = result[i][1]
				old_end_clip = (raw_node_lens[result[i][0][1:]] - result[i][2])
				part[0] = (part[0][0], part[0][1] + old_start_clip, part[0][2])
				part[-1] = (part[-1][0], part[-1][1], part[-1][2] - old_end_clip)
				new_result += part
				if i > 0: new_overlaps.append(overlaps[i-1])
				for j in range(1, len(part)):
					new_overlaps.append(edge_overlaps[canon(part[j-1][0], part[j][0])])
		assert len(new_result) == len(new_overlaps)+1
		assert len(new_result) >= len(result)
		if not any_replaced: break
		result = new_result
		overlaps = new_overlaps
		current_len = 0
		for i in range(0, len(result)):
			# strangely, this assertion is not always true.
			# The ONT based k-mer increase can create a node where the overlap is greater than the initial MBG node size
			# and in that case the initial MBG node will have a "negative" length within the contig
			# assert result[i][2] > result[i][1]
			assert result[i][2] <= raw_node_lens[result[i][0][1:]]
			assert result[i][1] >= 0
			current_len += result[i][2] - result[i][1]
			if i > 0: current_len -= overlaps[i-1]
		assert current_len == path_len
	return (result, overlaps)

def get_matches(path, node_poses, contig_nodeseqs, raw_node_lens, edge_overlaps, pathleftclip, pathrightclip, readleftclip, readrightclip, readlen, readstart, readend, gap):
	node_path_start_poses = []
	node_path_end_poses = []
	current_pos = 0
	for i in range(0, len(path)):
		if i > 0:
			current_pos -= edge_overlaps[canon(path[i-1], path[i])]
			assert current_pos > 0
		node_path_start_poses.append(current_pos)
		current_pos += raw_node_lens[path[i][1:]]
		node_path_end_poses.append(current_pos)
	raw_path_start = pathleftclip
	raw_path_end = node_path_end_poses[-1] - pathrightclip
	path_length = node_path_end_poses[-1] - pathleftclip - pathrightclip
	start_in_node = []
	end_in_node = []
	for i in range(0, len(path)):
		if node_path_start_poses[i] < pathleftclip:
			start_in_node.append(pathleftclip - node_path_start_poses[i])
			node_path_start_poses[i] = pathleftclip
		else:
			start_in_node.append(0)
		if node_path_end_poses[i] > raw_path_end:
			end_in_node.append(raw_node_lens[path[i][1:]] - (node_path_end_poses[i] - raw_path_end))
			node_path_end_poses[i] = raw_path_end
		else:
			end_in_node.append(raw_node_lens[path[i][1:]])
		assert start_in_node[i] >= 0
		assert end_in_node[i] > start_in_node[i]
		assert end_in_node[i] <= raw_node_lens[path[i][1:]]
		node_path_start_poses[i] -= pathleftclip
		node_path_end_poses[i] -= pathleftclip
		assert node_path_start_poses[i] >= 0
		assert node_path_end_poses[i] <= path_length
		assert node_path_end_poses[i] > node_path_start_poses[i]
	assert node_path_start_poses[0] == 0
	assert node_path_end_poses[-1] == path_length
	node_read_start_poses = []
	node_read_end_poses = []
	read_aln_length = readlen - (readleftclip + readrightclip)
	for i in range(0, len(path)):
		start_fraction = float(node_path_start_poses[i]) / float(path_length)
		end_fraction = float(node_path_end_poses[i]) / float(path_length)
		node_read_start_poses.append(int(start_fraction * read_aln_length) + readleftclip)
		node_read_end_poses.append(int(end_fraction * read_aln_length) + readleftclip)
		assert node_read_end_poses[i] > node_read_start_poses[i]
	assert node_read_start_poses[0] == readleftclip
	assert node_read_end_poses[-1] == readlen - readrightclip
	result = []
	for i in range(0, len(path)):
		assert node_read_end_poses[i] > node_read_start_poses[i]
		if path[i][1:] not in node_poses: continue
		for startpos in node_poses[path[i][1:]]:
			(contig, index, fw) = startpos
			if path[i][0] == '<': fw = not fw
			assert (not fw) or contig_nodeseqs[contig][index][0] == path[i]
			assert (fw) or revnode(contig_nodeseqs[contig][index][0]) == path[i]
			node_min_start = contig_nodeseqs[contig][index][1]
			node_max_end = contig_nodeseqs[contig][index][2]
			if node_min_start == node_max_end: continue
			assert node_min_start >= 0
			if node_min_start > node_max_end:
				print(startpos)
			assert node_min_start <= node_max_end
			assert node_max_end <= raw_node_lens[path[i][1:]]
			nodestart = start_in_node[i]
			nodeend = end_in_node[i]
			if not fw:
				(nodestart, nodeend) = (nodeend, nodestart)
				nodestart = raw_node_lens[path[i][1:]] - nodestart
				nodeend = raw_node_lens[path[i][1:]] - nodeend
			if nodestart >= node_max_end or nodeend <= node_min_start: continue
			readstart = node_read_start_poses[i]
			readend = node_read_end_poses[i]
			if nodestart < node_min_start:
				readstart += node_min_start - nodestart
				nodestart = 0
			else:
				nodestart -= node_min_start
			if nodeend > node_max_end:
				readend -= nodeend - node_max_end
				nodeend = node_max_end
			if not fw:
				(nodestart, nodeend) = (nodeend, nodestart)
				nodestart = node_max_end - (nodestart + node_min_start) + node_min_start
				nodeend = node_max_end - (nodeend + node_min_start) + node_min_start
			assert nodestart >= 0
			assert nodeend > nodestart
			assert nodeend <= raw_node_lens[path[i][1:]]
			assert readstart >= 0
			assert readend > readstart
			assert readend <= readlen
			match_bp_len = readend - readstart
			result.append((match_bp_len, contig, index, fw, i, nodestart, nodeend, readstart, readend, readlen, gap))
	return result

raw_node_lens = {}
with open(nodelens_file) as f:
	for l in f:
		parts = l.strip().split('\t')
		assert parts[0] not in raw_node_lens or raw_node_lens[parts[0]] == int(parts[1])
		raw_node_lens[parts[0]] = int(parts[1])

edge_overlaps = {}
with open(edge_overlap_file) as f:
	for l in f:
		parts = l.strip().split('\t')
		assert parts[0] == "L"
		fromnode = (">" if parts[2] == "+" else "<") + parts[1]
		tonode = (">" if parts[4] == "+" else "<") + parts[3]
		overlap = int(parts[5][:-1])
		key = canon(fromnode, tonode)
		if key in edge_overlaps: assert edge_overlaps[key] == overlap
		edge_overlaps[key] = overlap

node_mapping = {}
with open(mapping_file) as f:
	for l in f:
		parts = l.strip().split('\t')
		assert parts[0] not in node_mapping
		path = parts[1].split(':')[0].replace('<', "\t<").replace('>', "\t>").strip().split('\t')
		left_clip = int(parts[1].split(':')[1])
		right_clip = int(parts[1].split(':')[2])
		node_mapping[parts[0]] = (path, left_clip, right_clip)
		left_len = raw_node_lens[parts[0]]
		right_len = 0
		for i in range(0, len(path)):
			right_len += raw_node_lens[path[i][1:]]
			if i > 0: right_len -= edge_overlaps[canon(path[i-1], path[i])]
		assert left_len == right_len - left_clip - right_clip

contig_lens = {}
contig_nodeseqs = {}
contig_nodeoverlaps = {}
contig_node_offsets = {}
with open(paths_file) as f:
	for l in f:
		parts = l.strip().split('\t')
		pathname = parts[0]
		path = parts[1].replace('<', '\t<').replace('>', '\t>').strip().split('\t')
		(path, overlaps) = get_leafs(path, node_mapping, edge_overlaps, raw_node_lens)
		contig_nodeseqs[pathname] = path
		contig_nodeoverlaps[pathname] = overlaps
		contig_node_offsets[pathname] = []
		pos = 0
		for i in range(0, len(path)-1):
			contig_node_offsets[pathname].append(pos)
			pos += path[i][2] - path[i][1]
			pos -= overlaps[i]
		contig_node_offsets[pathname].append(pos)
		contig_lens[pathname] = contig_node_offsets[pathname][-1] + path[-1][2] - path[-1][1]
		check_len = 0
		for i in range(0, len(path)):
			check_len += path[i][2] - path[i][1]
			if i > 0: check_len -= overlaps[i-1]
		assert contig_lens[pathname] == check_len
		pathstr = ""
		for i in range(0, len(path)):
			pathstr += path[i][0] + ":" + str(path[i][1]) + ":" + str(path[i][2]) + "(" + str(contig_node_offsets[pathname][i]) + ")"
			if i < len(path)-1: pathstr += "-" + str(overlaps[i])
		# sys.stderr.write(pathname + "\t" + "".join(str(n[0]) + ":" + str(n[1]) + ":" + str(n[2]) for n in path) + "\n")
		sys.stderr.write(pathname + "\t" + pathstr + "\n")

node_poses = {}
for contigname in contig_nodeseqs:
	for i in range(0, len(contig_nodeseqs[contigname])):
		nodename = contig_nodeseqs[contigname][i][0][1:]
		if contig_nodeseqs[contigname][i][0][0] == ">":
			if nodename not in node_poses: node_poses[nodename] = []
			node_poses[nodename].append((contigname, i, True))
		else:
			if nodename not in node_poses: node_poses[nodename] = []
			node_poses[nodename].append((contigname, i, False))

read_name_to_id = {}
next_read_id = 0

matches_per_read = {}
with open(read_alignment_file) as f:
	for l in f:
		parts = l.strip().split('\t')
		readname = parts[0].split(' ')[0]
		if readname not in read_name_to_id:
			read_name_to_id[readname] = next_read_id
			next_read_id += 1
		readlen = int(parts[1])
		readleftclip = int(parts[2])
		readrightclip = int(parts[1]) - int(parts[3])
		readstart = int(parts[2])
		readend = int(parts[3])
		if not readstart < readend: print(l)
		assert readstart < readend
		pathleftclip = int(parts[7])
		pathrightclip = int(parts[6]) - int(parts[8])
		path = parts[5].replace('>', "\t>").replace('<', "\t<").strip().split('\t')
		gap = False
		for node in path:
			if node[1:4] == "gap":
				gap = True
				break
		matches = get_matches(path, node_poses, contig_nodeseqs, raw_node_lens, edge_overlaps, pathleftclip, pathrightclip, readleftclip, readrightclip, readlen, readstart, readend, gap)
		if len(matches) == 0: continue
		if readname not in matches_per_read: matches_per_read[readname] = []
		matches_per_read[readname] += matches

contig_contains_reads = {}
for readname in matches_per_read:
	for match in matches_per_read[readname]:
		(match_bp_size, contig, contigstart, fw, pathstart, node_start_offset, node_end_offset, readstart, readend, readlen, gap) = match
		assert readstart < readend
		if fw:
			contigpos = contig_node_offsets[contig][contigstart]
			contigpos += node_start_offset
			contigpos -= readstart
			if contig not in contig_contains_reads: contig_contains_reads[contig] = {}
			if readname not in contig_contains_reads[contig]: contig_contains_reads[contig][readname] = []
			len_readstart = readstart
			len_readend = readend
			if contigstart == 0 and node_start_offset <= 50: len_readstart = 0
			if contigstart == len(contig_node_offsets[contig]) - 1 and node_end_offset >= contig_nodeseqs[contig][contigstart][2]-50: len_readend = readlen
			if gap:
				len_readstart = 0
				len_readend = readlen
			contig_contains_reads[contig][readname].append((contigpos, contigpos + readlen, len_readstart, len_readend, readlen, readstart, readend))
		else:
			contigpos = contig_node_offsets[contig][contigstart]
			contigpos += contig_nodeseqs[contig][contigstart][2] - contig_nodeseqs[contig][contigstart][1]
			contigpos -= node_start_offset
			contigpos += readstart
			contigpos -= readlen
			if contig not in contig_contains_reads: contig_contains_reads[contig] = {}
			if readname not in contig_contains_reads[contig]: contig_contains_reads[contig][readname] = []
			len_readstart = readstart
			len_readend = readend
			if contigstart == 0 and node_end_offset >= contig_nodeseqs[contig][contigstart][2]-50: len_readend = readlen
			if contigstart == len(contig_node_offsets[contig]) - 1 and node_start_offset <= 50: len_readstart = 0
			if gap:
				len_readstart = 0
				len_readend = readlen
			contig_contains_reads[contig][readname].append((contigpos + readlen, contigpos, len_readstart, len_readend, readlen, readstart, readend))

read_clusters = {}
for contig in contig_contains_reads:
	for readname in contig_contains_reads[contig]:
		if readname not in read_clusters: read_clusters[readname] = []
		lines = contig_contains_reads[contig][readname]
		assert len(lines) > 0
		readlen = lines[0][4]
		lines.sort(key=lambda x: min(x[0], x[1]))
		fwcluster = None
		bwcluster = None
		for line in lines:
			fw = line[1] > line[0]
			contigstart = min(line[0], line[1])
			contigend = max(line[0], line[1])
			readstart = line[2]
			readend = line[3]
			real_readstart = line[5]
			real_readend = line[6]
			assert readstart < readend
			if fw:
				if fwcluster is None:
					fwcluster = (contigstart, contigend, readstart, readend, real_readstart, real_readend)
				elif contigstart < fwcluster[0] + 50 and contigend < fwcluster[1] + 50:
					fwcluster = (contigstart, contigend, min(fwcluster[2], readstart), max(fwcluster[3], readend), min(fwcluster[4], real_readstart), max(fwcluster[5], real_readend))
				else:
					if fwcluster[3] - fwcluster[2] >= readlen * min_read_len_fraction: read_clusters[readname].append((contig, fwcluster[0], fwcluster[1], fwcluster[4], fwcluster[5]))
					fwcluster = (contigstart, contigend, readstart, readend, real_readstart, real_readend)
			else:
				if bwcluster is None:
					bwcluster = (contigstart, contigend, readstart, readend, real_readstart, real_readend)
				elif contigstart < bwcluster[0] + 50 and contigend < bwcluster[1] + 50:
					bwcluster = (contigstart, contigend, min(bwcluster[2], readstart), max(bwcluster[3], readend), min(bwcluster[4], real_readstart), max(bwcluster[5], real_readend))
				else:
					if bwcluster[3] - bwcluster[2] >= readlen * min_read_len_fraction: read_clusters[readname].append((contig, bwcluster[1], bwcluster[0], bwcluster[4], bwcluster[5]))
					bwcluster = (contigstart, contigend, readstart, readend, real_readstart, real_readend)
		if fwcluster is not None:
			if fwcluster[3] - fwcluster[2] >= readlen * min_read_len_fraction: read_clusters[readname].append((contig, fwcluster[0], fwcluster[1], fwcluster[4], fwcluster[5]))
		if bwcluster is not None:
			if bwcluster[3] - bwcluster[2] >= readlen * min_read_len_fraction: read_clusters[readname].append((contig, bwcluster[1], bwcluster[0], bwcluster[4], bwcluster[5]))

contig_actual_lines = {}
for readname in read_clusters:
	longest = []
	for line in read_clusters[readname]:
		if len(longest) == 0:
			longest.append(line)
		elif line[4] - line[3] > longest[0][4] - longest[0][3]:
			longest = []
			longest.append(line)
		elif line[4] - line[3] == longest[0][4] - longest[0][3]:
			longest.append(line)
	for line in longest:
		if line[0] not in contig_actual_lines: contig_actual_lines[line[0]] = []
		contig_actual_lines[line[0]].append((readname, line[1], line[2]))

for contig in contig_actual_lines:
	if len(contig_actual_lines[contig]) == 0: continue
	assert len(contig_actual_lines[contig]) > 0
	contig_actual_lines[contig].sort(key=lambda x: min(x[1], x[2]))
	start_pos = contig_actual_lines[contig][0][1]
	end_pos = contig_actual_lines[contig][0][1]
	for line in contig_actual_lines[contig]:
		start_pos = min(start_pos, line[1])
		start_pos = min(start_pos, line[2])
		end_pos = max(end_pos, line[1])
		end_pos = max(end_pos, line[2])
	print("tig\t" + contig)
	print("len\t" + str(end_pos - start_pos))
	print("rds\t" + str(len(contig_actual_lines[contig])))
	for line in contig_actual_lines[contig]:
		print(line[0] + "\t" + str(line[1] - start_pos) + "\t" + str(line[2] - start_pos))
	print("end")
