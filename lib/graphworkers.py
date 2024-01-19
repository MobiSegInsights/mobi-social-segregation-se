import torch
import torch_geometric
import networkx as nx
import pandas as pd
from tqdm import tqdm
# import umap
import matplotlib.pyplot as plt
import seaborn as sns


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


def embeddings_umap(emb=None, labels=None, field_label=None):
    """
    :param emb: numpy array, n x 64 array of embeddings
    :param labels: numpy array, categorical level of each sample row
    :param field_label: string, column name for the new dataframe
    :return: dataframe, ['x', 'y', field_label] after reducing dimensions
    """
    reducer = umap.UMAP()
    embedded_data = reducer.fit_transform(emb)
    df_emb2d = pd.DataFrame(embedded_data, columns=['x', 'y'])
    df_emb2d.loc[:, field_label] = labels
    return df_emb2d


def embeddings_umap_plot(data=None, cat=None, labels=None, colors=None):
    """
    :param data: dataframe, reduced dimensions from umap
    :param cat: string, column name of the categorical variable
    :param labels: list of strings, levels of cat for visualizing
    :param colors: list of strings, colors for the visualized levels of cat
    :return: None
    """
    plt.figure(figsize=(10, 8))
    if labels is not None:
        sns.scatterplot(data=data.loc[data[cat].isin(labels), :],
                        x="x", y="y", hue=cat, hue_order=labels,
                        palette=colors, alpha=0.5, s=20)
    else:
        sns.scatterplot(data=data,
                        x="x", y="y", hue=cat, hue_order=labels,
                        palette=colors, alpha=0.5, s=20)
    plt.title('UMAP Visualization of Dataset')
    plt.xlabel('UMAP Dimension 1')
    plt.ylabel('UMAP Dimension 2')
    plt.show()


def projection_plot(data=None, cat=None, labels=None, colors=None,
                    x_field=None, y_field=None,
                    x_lb=None, y_lb=None, multi=True):
    """
    :param y_lb: string, y-axis label
    :param x_lb: string, x-axis label
    :param y_field: string, column to put on the y-axis
    :param x_field: string, column to put on the x-axis
    :param data: dataframe, reduced dimensions from umap
    :param cat: string, column name of the categorical variable
    :param labels: list of strings, levels of cat for visualizing
    :param colors: list of strings, colors for the visualized levels of cat
    :return: None
    """
    plt.figure(figsize=(8, 8))
    if multi:
        if labels is not None:
            sns.scatterplot(data=data.loc[data[cat].isin(labels), :],
                            x=x_field, y=y_field, hue=cat, hue_order=labels,
                            palette=colors, alpha=0.5, s=20)
        else:
            sns.scatterplot(data=data,
                            x=x_field, y=y_field, hue=cat, hue_order=labels,
                            palette=colors, alpha=0.5, s=20)
    else:
        sns.scatterplot(data=data, x=x_field, y=y_field, alpha=0.5, s=20)
    plt.title('POI projections')
    plt.xlabel(x_lb)
    plt.ylabel(y_lb)
    plt.show()


def scatter_plot(data=None, x_field=None, y_field=None, cat=None, labels=None, colors=None):
    """
    :param y_field: string, y column name
    :param x_field: string, x column name
    :param data: dataframe, reduced dimensions from umap
    :param cat: string, column name of the categorical variable
    :param labels: list of strings, levels of cat for visualizing
    :param colors: list of strings, colors for the visualized levels of cat
    :return: None
    """
    plt.figure(figsize=(10, 8))
    if labels is not None:
        sns.scatterplot(data=data.loc[data[cat].isin(labels), :],
                        x=x_field, y=y_field, hue=cat, hue_order=labels,
                        palette=colors, alpha=0.5, s=20)
    else:
        sns.scatterplot(data=data, x=x_field, y=y_field, alpha=0.5, s=20)
    plt.xlabel(x_field)
    plt.ylabel(y_field)
    plt.show()


def single_dimension_proj(df=None, dim=None, dim_name=None):
    labels = ["D", "N", "F"]
    colors = ["#af887f", "gray", "#7f88af"]
    f, ax = plt.subplots(figsize=(4, 4))
    df2plot_f = df.loc[:, [dim, 'ice_birth_cat']]
    sns.histplot(data=df2plot_f, x=dim, hue='ice_birth_cat',
                 bins=35, stat="probability", common_norm=False,
                 hue_order=labels, ax=ax, fill=False, alpha=0.7, linewidth=2,
                 palette=colors, element='poly', legend=False)
    f.legend(labels=labels, loc='upper right',
             frameon=False, prop={'size': 12}, labelcolor='0.2', ncol=2)

    ax.set(ylabel='Fraction of zones', xlabel=f"Projection")
    ax.set_title(dim_name, weight='bold', loc='left', size=14)
    for axis in ['bottom', 'left']:
        ax.spines[axis].set_linewidth(1)
        ax.spines[axis].set_color('0.2')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.tick_params(width=1, color='0.2')

    plt.xticks(size=14, color='0.2')
    plt.yticks(size=14, color='0.2')
    ax.set_ylim(0, 0.2)
    ax.set_xlabel(ax.get_xlabel(), fontsize=14, color='0.2')
    ax.set_ylabel(ax.get_ylabel(), fontsize=14, color='0.2')
    plt.tight_layout()
    return f


def single_dimension_proj_poi(df=None, dim=None, dim_name=None, grp='D'):
    f, ax = plt.subplots(figsize=(6, 6))
    df2plot_f = df.loc[:, [dim, 'poi_type']]
    poi_types = df.poi_type.unique()
    sns.histplot(data=df2plot_f, x=dim, hue='poi_type',
                 bins=50, stat="probability", common_norm=False,
                 ax=ax, fill=False, alpha=0.8, linewidth=1.5,
                 element='poly', legend=False)
    f.legend(labels=poi_types,
             loc='upper right',
             frameon=False,
             prop={'size': 12},
             labelcolor='0.2',
             ncol=1)

    ax.set(ylabel='Fraction of POIs', xlabel=f"Projection on {dim_name}")
    # ax.set_title(dim_name, weight='bold', loc='left', size=14)
    for axis in ['bottom', 'left']:
        ax.spines[axis].set_linewidth(1)
        ax.spines[axis].set_color('0.2')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.tick_params(width=1, color='0.2')

    plt.xticks(size=14, color='0.2')
    plt.yticks(size=14, color='0.2')
    # ax.set_yscale('log')
    if grp == 'D':
        ax.set_xlim(0.8, 1)
        ax.set_ylim(0, 0.1)
    else:
        ax.set_xlim(-1, -0.8)
    ax.set_xlabel(ax.get_xlabel(), fontsize=14, color='0.2')
    ax.set_ylabel(ax.get_ylabel(), fontsize=14, color='0.2')
    plt.tight_layout()
    return f

