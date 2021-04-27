import networkx as nx
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def router_name_func(i):
    return f"router_{i}"


def bsm_name_func(i, j):
    return f"BSM_{i}_{j}"


parser = argparse.ArgumentParser()
parser.add_argument('l', type=int, help="l (int) – Number of cliques")
parser.add_argument('k', type=int, help="k (int) – Size of cliques")
parser.add_argument('group_n', type=int, help="group_n (int) - Number of "
                                              "groups for parallel simulation")
parser.add_argument('memo_size', type=int, help='number of memories per node')
parser.add_argument('qc_length', type=float,
                    help='distance between nodes (in km)')
parser.add_argument('qc_atten', type=float,
                    help='quantum channel attenuation (in dB/m)')
parser.add_argument('cc_delay', type=float,
                    help='classical channel delay (in ms)')
parser.add_argument('-o', '--output', type=str, default='out.json',
                    help='name of output config file')
parser.add_argument('-s', '--stop', type=float, default=float('inf'),
                    help='stop time (in s)')
parser.add_argument('-p', '--parallel', nargs=5,
                    help='optional parallel arguments: server ip, server port,'
                         ' num. processes, sync/async, lookahead')
parser.add_argument('-n', '--nodes', type=str,
                    help='path to csv file to provide process for each node')
args = parser.parse_args()

graph = nx.connected_caveman_graph(args.l, args.k)
mapping = {}
NODE_NUM = args.l * args.k
for i in range(NODE_NUM):
    mapping[i] = router_name_func(i)
nx.relabel_nodes(graph, mapping, copy=False)
# nx.draw(graph, with_labels=True)
# plt.show()

output_dict = {}

node_procs = {}
router_names = []

if args.nodes:
    # TODO: add length/proc assertions
    df = pd.read_csv(args.nodes)
    for name, group in zip(df['name'], df['group']):
        node_procs[name] = group
        router_names.append(name)
else:
    group_size = NODE_NUM / int(args.parallel[2])
    for i in range(NODE_NUM):
        name = router_name_func(i)
        node_procs[name] = int(i // group_size)
        router_names.append(name)

router_names = list(node_procs.keys())
nodes = [{Topology.NAME: name,
          Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
          Topology.SEED: i,
          RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size,
          RouterNetTopo.GROUP: node_procs[name]}
         for i, name in enumerate(router_names)]

cchannels = []
qchannels = []
bsm_nodes = []
for i, node_pair in enumerate(graph.edges):
    node1, node2 = node_pair
    bsm_name = bsm_name_func(node1, node2)
    bsm_node = {Topology.NAME: bsm_name,
                Topology.TYPE: RouterNetTopo.BSM_NODE,
                Topology.SEED: i,
                RouterNetTopo.GROUP: node_procs[node1]}
    bsm_nodes.append(bsm_node)

    for node in node_pair:
        qchannels.append({Topology.SRC: node,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: args.qc_length * 500,
                          Topology.ATTENUATION: args.qc_atten})

    for node in node_pair:
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node,
                          Topology.DELAY: args.cc_delay * 1e9})

        cchannels.append({Topology.SRC: node,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})

nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

for node1 in router_names:
    for node2 in router_names:
        if node1 == node2:
            continue
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})

output_dict[Topology.ALL_C_CHANNEL] = cchannels
output_dict[Topology.STOP_TIME] = args.stop * 1e12
if args.parallel:
    output_dict[RouterNetTopo.IS_PARALLEL] = True
    output_dict[RouterNetTopo.PROC_NUM] = int(args.parallel[2])
    output_dict[RouterNetTopo.IP] = args.parallel[0]
    output_dict[RouterNetTopo.PORT] = int(args.parallel[1])
    output_dict[RouterNetTopo.LOOKAHEAD] = int(args.parallel[4])
    if args.parallel[3] == "true":
        # set all to synchronous
        output_dict[RouterNetTopo.ALL_GROUP] = \
            [{RouterNetTopo.TYPE: RouterNetTopo.SYNC} for _ in
             range(int(args.parallel[2]))]
    else:
        output_dict[RouterNetTopo.ALL_GROUP] = \
            [{RouterNetTopo.TYPE: RouterNetTopo.ASYNC}] * int(args.parallel[2])
else:
    output_dict[RouterNetTopo.IS_PARALLEL] = False

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)
