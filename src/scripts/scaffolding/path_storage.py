
import sys
import re
import shutil
import os
import networkx as nx
from numpy import argmax
import graph_functions
import logging


#All functions expect directed nodes in utig4-234+ format, paths may contain gapped node

#path nodes stored with orientation, "utig4-234+" tsv format
class PathStorage:
    def __init__(self, G):        
        #from IDs to array of oriented+- nodes
        self.paths = {}
        #ignoring overlaps but who cares
        self.path_lengths = {}
        self.hap_labels = {}
        self.G = G

    def getPathById(self, path_id):
        return self.paths[path_id]
    
    def getLength(self, path_id):
        return self.path_lengths[path_id]

    def getPathIds(self):
        return self.paths.keys()

#should not be used
    def getEdgeSequenceById(self, path_id):
        res = []
        for edge in self.paths[path_id]:
            #removing +- and gaps
            if edge[0] != "N":
                res.append(edge[:-1])
        return res
    
    def getPathString(self, path_id):
        return ",".join(self.paths[path_id])
    
    def getPathTsv(self, path_id):
        return path_id + "\t" + ",".join(self.paths[path_id]) + "\t" + self.hap_labels[path_id]
    
    def getPathGaf(self, path_id):
        return path_id + "\t" + graph_functions.tsv2gaf(",".join(self.paths[path_id])) + "\t" + self.hap_labels[path_id]

    def addPath(self, line):
        arr = line.strip().split()
        if len(arr) < 3:
            print (f"wrong path {line}")
            exit()
        separators = ">|<|,"
        edges = re.split(separators, arr[1])
        self.hap_labels[arr[0]] = arr[2]
        total_l = 0
        for edge in edges:
            node = edge
            if node in self.G.nodes:
                total_l += self.G.nodes[node]['length']
        edges = list(filter(None, edges))
        self.paths[arr[0]] = edges
        self.path_lengths[arr[0]] = total_l

    def addPathWithId(self, id, path):
        total_l = 0
        for edge in path:
            node = edge
            if node in self.G.nodes:
                total_l += self.G.nodes[node]['length']
        self.paths[id] = path
        self.path_lengths[id] = total_l
    
    def getLabel(self, path_id):
        return self.hap_labels[path_id]

    def readFromFile(self, rukki_file):
        for line in open(rukki_file):
            arr = line.strip().split()
            if arr[0] == "name":
                continue
            self.addPath(line.strip())
    
    def getEdgeMultiplicities(self):
        multiplicities = {}
        for path_id in self.getPathIds():
            for edge in self.getEdgeSequenceById(path_id):
                for dir in ["+", "-"]:
                    node = edge + dir      
                    if not node in multiplicities:
                        multiplicities[node] = 0
                    multiplicities[node] += 1
        return multiplicities
    
    # Can save seqs from gfa in graph structures to avoid additional input fasta but really do not want to make graphs huge.
    def writePathAsFasta(self, input_fasta, output_fasta):
        seqs = {}
        for line in open(input_fasta):
            if line[0] == ">":
                cur = line.strip()[1:]
            else:
                seqs[cur] = line.strip()
        with open(output_fasta, "a") as f:
            for id in sorted(self.paths.keys()):
                f.write(f">{id}\n")
                prev_over = 0
                for node_id in range (0, len (self.paths[id])):
                    node = self.paths[id][node_id]
                    nor_node = node[:-1]
                    if not nor_node in seqs:
                        arr = nor_node.split('N')
                        if len(arr) >= 2:
                            Nlen = int(arr[1])
                            N_str = ""
                            for i in range(Nlen):
                                N_str += "N"
                            f.write(N_str)
                        prev_over = 0
                        continue
                    else:
                        if node[-1] == "+":
                            f.write(seqs[nor_node][prev_over:])
                        else:
                            to_out = gf.rc_seq(seqs[nor_node][prev_over:])
                            f.write(to_out[prev_over:])
                        if node_id < len(self.paths[id]) - 1 and self.paths[id][node_id + 1][:-1] in seqs:
                            overlap = self.G.get_edge_data(nor_node, self.paths[id][node_id + 1][:-1])['overlap']
                        else:
                            overlap = 0
                f.write(f"\n")
