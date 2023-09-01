import torch
import torch_geometric
import networkx as nx
import pandas as pd
from tqdm import tqdm


def graph_to_edge_list(G):
    # Returns the edge list of an nx.Graph.
    # The returned edge_list is a list of tuples
    # where each tuple is a tuple representing an edge connected
    # by two nodes.

    edge_list = list(G.edges)

    return edge_list


def edge_list_to_tensor(edge_list):
    # Transforms the edge_list to tensor.
    # The input edge_list is a list of tuples and the resulting
    # tensor should have the shape [2 x len(edge_list)].

    edge_index = torch.tensor(edge_list)
    edge_index = edge_index.type(torch.LongTensor)
    edge_index = torch.transpose(edge_index, 0, 1)

    return edge_index


def from_networkx(G, weight_key=None):
    r"""Converts a :obj:`networkx.Graph` or :obj:`networkx.DiGraph` to a
    :class:`torch_geometric.data.Data` instance.

    Args:
        G (networkx.Graph or networkx.DiGraph): A networkx graph.
    """

    G = nx.convert_node_labels_to_integers(G)
    G = G.to_directed() if not nx.is_directed(G) else G
    edge_index = torch.LongTensor(list(G.edges)).t().contiguous()

    data = {}

    for i, (_, feat_dict) in enumerate(G.nodes(data=True)):
        for key, value in feat_dict.items():
            data[str(key)] = [value] if i == 0 else data[str(key)] + [value]

    if weight_key is None:
        for i, (_, _, feat_dict) in enumerate(G.edges(data=True)):
            for key, value in feat_dict.items():
                data[str(key)] = [value] if i == 0 else data[str(key)] + [value]
    else:
        edges = list(G.edges(data=True))
        data[weight_key] = [x[2][weight_key] for x in edges]

    for key, item in data.items():
        try:
            data[key] = torch.tensor(item)
        except ValueError:
            pass

    data['edge_index'] = edge_index.view(2, -1)
    data = torch_geometric.data.Data.from_dict(data)
    data.num_nodes = G.number_of_nodes()

    return data


def generic_weighted_projected_graph(B, nodes, weight_function=None, num_cpus=4):
    r"""Weighted projection of B with a user-specified weight function.

    The bipartite network B is projected on to the specified nodes
    with weights computed by a user-specified function.  This function
    must accept as a parameter the neighborhood sets of two nodes and
    return an integer or a float.

    The nodes retain their attributes and are connected in the resulting graph
    if they have an edge to a common node in the original graph.

    Parameters
    ----------
    B : NetworkX graph
        The input graph should be bipartite.

    nodes : list or iterable
        Nodes to project onto (the "bottom" nodes).

    weight_function : function
        This function must accept as parameters the same input graph
        that this function, and two nodes; and return an integer or a float.
        The default function computes the number of shared neighbors.

    Returns
    -------
    Graph : NetworkX graph
       A graph that is the projection onto the given nodes.

    Notes
    -----
    No attempt is made to verify that the input graph B is bipartite.
    The graph and node properties are (shallow) copied to the projected graph.

    See :mod:`bipartite documentation <networkx.algorithms.bipartite>`
    for further details on how bipartite graphs are handled in NetworkX.

    See Also
    --------
    is_bipartite,
    is_bipartite_node_set,
    sets,
    weighted_projected_graph,
    collaboration_weighted_projected_graph,
    overlap_weighted_projected_graph,
    projected_graph

    """
    if B.is_directed():
        pred = B.pred
        G = nx.DiGraph()
    else:
        pred = B.adj
        G = nx.Graph()
    if weight_function is None:

        def weight_function(G, u, v):
            # Notice that we use set(pred[v]) for handling the directed case.
            return len(set(G[u]) & set(pred[v]))

    # G.graph.update(B.graph)
    # G.add_nodes_from((n, B.nodes[n]) for n in nodes)
    # for u in nodes:
    #     nbrs2 = {n for nbr in set(B[u]) for n in B[nbr]} - {u}
    #     for v in nbrs2:
    #         weight = weight_function(B, u, v)
    #         G.add_edge(u, v, weight=weight)

    def u_neighbors():
        nbrs2_dict = {}
        for u in tqdm(nodes):
            nbrs2_dict[u] = {n for nbr in set(B[u]) for n in B[nbr]} - {u}
        return nbrs2_dict

    def weight_calculation(row):
        return weight_function(B, row['u'], row['v'])

    nbrs2_dict = u_neighbors()
    uv_list = [(x, y) for x in nodes for y in nbrs2_dict[x]]
    df = pd.DataFrame(uv_list, columns=['u', 'v'])
    tqdm.pandas()
    df.loc[:, 'weight'] = df.progress_apply(lambda row: weight_calculation(row), axis=1)

    # np.random.seed(42)
    # df.loc[:, 'gp'] = np.random.randint(1, 21, df.shape[0])
    # def data2weight(data):
    #     data.loc[:, 'weight'] = data.progress_apply(lambda row: weight_calculation(row), axis=1)
    #     return data
    # list_df = p_map(data2weight, [g for _, g in df.groupby('gp')])
    # df = pd.concat(list_df)
    # df = df.drop(columns=['gp'])

    G.add_weighted_edges_from(list(df.to_records(index=False)))
    return G


