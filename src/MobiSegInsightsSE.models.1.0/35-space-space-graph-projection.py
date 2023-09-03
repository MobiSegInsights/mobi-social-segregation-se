import os, sys
from pathlib import Path
os.environ['USE_PYGEOS'] = '0'
import numpy as np
import pickle
import pandas as pd
import sqlalchemy
import networkx as nx
from networkx.algorithms import bipartite
from torch_sparse import SparseTensor
import torch

ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))

import preprocess as preprocess
from graphworkers import from_networkx, generic_weighted_projected_graph


def my_weight(G, u, v, weight="weight"):
    w = 0
    for nbr in set(G[u]) & set(G[v]):
        w += G[u][nbr].get(weight, 1) + G[v][nbr].get(weight, 1)
    return w


class GraphGenerator:
    def __init__(self):
        self.ice_hex = None
        self.hex = None
        self.zone_ice_mapping = None
        self.user = preprocess.keys_manager['database']['user']
        self.password = preprocess.keys_manager['database']['password']
        self.port = preprocess.keys_manager['database']['port']
        self.db_name = preprocess.keys_manager['database']['name']

    def ice_hex_process(self):
        print('Loading hexagons and their ice values.')
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')

        self.ice_hex = pd.read_sql(sql="""SELECT hex, time_seq, ice_birth, num_visits_wt, num_unique_uid
                                          FROM segregation.mobi_seg_hex
                                          WHERE weekday=1 AND holiday=0;""", con=engine)
        print(f"Before dropping nan, number of records: {len(self.ice_hex)}")
        self.ice_hex = self.ice_hex.dropna()
        self.ice_hex = self.ice_hex.loc[self.ice_hex['num_unique_uid'] >= 5, :]
        print("After dropping nan and unreliable results, numbers of records and zones: ",
              f"{len(self.ice_hex), self.ice_hex.hex.nunique()}")
        self.ice_hex = self.ice_hex.groupby(['hex']).\
            apply(lambda x: pd.Series({'ice_birth': np.average(x['ice_birth'], weights=x['num_visits_wt'])})).\
            reset_index()
        self.ice_hex.loc[:, 'ice_birth_cat'] = pd.cut(self.ice_hex.ice_birth,
                                                      bins=[-1, -0.6, -0.2, 0.2, 0.6, 1],
                                                      labels=['F2', 'F1', 'N', 'D1', 'D2'])
        self.zone_ice_mapping = dict(zip(self.ice_hex.hex, self.ice_hex.ice_birth_cat))

    def hex_visitation_process(self):
        engine = sqlalchemy.create_engine(
            f'postgresql://{self.user}:{self.password}@localhost:{self.port}/{self.db_name}?gssencmode=disable')
        self.hex = pd.read_sql(sql="""SELECT * FROM bipartite_graph.hex;""", con=engine)
        print(f"Before dropping nan, number of records: {len(self.hex)}")
        self.hex = self.hex.loc[self.hex.zone.isin(self.ice_hex['hex'].unique()), :]
        print(f"After dropping nan hexagons, numbers of records and zones: {len(self.hex), self.hex.zone.nunique()}")

    def space_projection_graph(self, df_edges, weight=False, test=False):
        if test:
            df_edges = df_edges.sample(100000)
        zones = df_edges.zone.unique()
        B = nx.Graph()
        B.add_weighted_edges_from(list(df_edges.loc[:, ['uid', 'zone', 'count']].to_records(index=False)))
        if weight:
            G = generic_weighted_projected_graph(B, nodes=zones, weight_function=my_weight, num_cpus=20)
        else:
            G = bipartite.projected_graph(B, nodes=zones)
        nx.set_node_attributes(G, self.zone_ice_mapping, "ice")
        mapping = dict(zip(sorted(G.nodes()), range(1, G.number_of_nodes() + 1)))
        G = nx.relabel.convert_node_labels_to_integers(G, first_label=1, ordering='default', label_attribute='zone')
        return G, mapping

    def graph_making(self, weight=True, test=False, format='.pt'):
        # Projected graph
        print('Making graph...')
        G_hex, mapping = self.space_projection_graph(self.hex, weight=weight, test=test)
        print('Graph done!')

        if not test:
            print(f'Saving graph as {format}')
            if format == '.pt':
                G_t = from_networkx(G_hex, weight_key='weight')
                G_t.adj_t = SparseTensor(row=G_t.edge_index[0],
                                         col=G_t.edge_index[1],
                                         value=G_t.weight,
                                         sparse_sizes=(G_t.num_nodes, G_t.num_nodes))
                G_t.ice_dict = {h: h_index for h_index, h in zip(range(0, len(set(G_t.ice))), set(G_t.ice))}
                ice_labels = [G_t.ice_dict[x] for x in G_t.ice]
                G_t.y = torch.reshape(torch.tensor(ice_labels), (len(ice_labels), 1))
                torch.save(G_t, os.path.join(ROOT_dir, f"dbs/graphs/space_space_weekday1_holiday0_hex{format}"))
            else:
                nx.write_graphml(G_hex, f"dbs/graphs/space_space_weekday1_holiday0_hex{format}")
                with open("dbs/graphs/space_space_weekday1_holiday0_hex_mapping.pickle", 'wb') as handle:
                    pickle.dump(mapping, handle, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            nx.write_graphml(G_hex, f"dbs/graphs/space_space_weekday1_holiday0_hex_sample{format}")
            with open("dbs/graphs/space_space_weekday1_holiday0_hex_mapping.pickle", 'wb') as handle:
                pickle.dump(mapping, handle, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    gg = GraphGenerator()
    gg.ice_hex_process()
    gg.hex_visitation_process()
    gg.graph_making(weight=True, test=False, format='.graphml')
