import os, sys
from pathlib import Path
os.environ['USE_PYGEOS'] = '0'
import numpy as np
import io
import networkx as nx
from collections import defaultdict
import matplotlib.pyplot as plt
import random
from tqdm import tqdm
import tensorflow as tf
from tensorflow import keras
from keras import layers

ROOT_dir = Path(__file__).parent.parent.parent
sys.path.append(ROOT_dir)
sys.path.insert(0, os.path.join(ROOT_dir, 'lib'))


def next_step(graph, previous, current, p, q):
    neighbors = list(graph.neighbors(current))

    weights = []
    # Adjust the weights of the edges to the neighbors with respect to p and q.
    for neighbor in neighbors:
        if neighbor == previous:
            # Control the probability to return to the previous node.
            weights.append(graph[current][neighbor]["weight"] / p)
        elif graph.has_edge(neighbor, previous):
            # The probability of visiting a local node.
            weights.append(graph[current][neighbor]["weight"])
        else:
            # Control the probability to move forward.
            weights.append(graph[current][neighbor]["weight"] / q)

    # Compute the probabilities of visiting each neighbor.
    weight_sum = sum(weights)
    probabilities = [weight / weight_sum for weight in weights]
    # Probabilistically select a neighbor to visit.
    next = np.random.choice(neighbors, size=1, p=probabilities)[0]
    return next


def create_dataset(targets, contexts, labels, weights, batch_size):
    inputs = {
        "target": targets,
        "context": contexts,
    }
    dataset = tf.data.Dataset.from_tensor_slices((inputs, labels, weights))
    dataset = dataset.shuffle(buffer_size=batch_size * 2)
    dataset = dataset.batch(batch_size, drop_remainder=True)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset


class WeightedNode2Vec:
    def __init__(self):
        self.G = nx.read_graphml("dbs/graphs/space_space_weekday1_holiday0_hex.graphml")
        self.vocabulary = None
        self.vocabulary_lookup = None
        self.walks = None

    def show_graph_info(self):
        print("Total number of graph nodes:", self.G.number_of_nodes())
        print("Total number of graph edges:", self.G.number_of_edges())
        degrees = []
        for node in tqdm(self.G.nodes):
            degrees.append(self.G.degree[node])
        print("Average node degree:", round(sum(degrees) / len(degrees), 2))
        self.vocabulary = ["NA"] + list(self.G.nodes)
        self.vocabulary_lookup = {token: idx for idx, token in enumerate(self.vocabulary)}

    def random_walk(self, num_walks, num_steps, p, q):
        self.walks = []
        nodes = list(self.G.nodes())
        # Perform multiple iterations of the random walk.
        for walk_iteration in range(num_walks):
            random.shuffle(nodes)

            for node in tqdm(
                nodes,
                position=0,
                leave=True,
                desc=f"Random walks iteration {walk_iteration + 1} of {num_walks}",
            ):
                # Start the walk with a random node from the graph.
                walk = [node]
                # Randomly walk for num_steps.
                while len(walk) < num_steps:
                    current = walk[-1]
                    previous = walk[-2] if len(walk) > 1 else None
                    # Compute the next node to visit.
                    next = next_step(self.G, previous, current, p, q)
                    walk.append(next)
                # Replace node ids (movie ids) in the walk with token ids.
                walk = [self.vocabulary_lookup[token] for token in walk]
                # Add the walk to the generated sequence.
                self.walks.append(walk)

    def generate_examples(self, window_size, num_negative_samples, vocabulary_size):
        example_weights = defaultdict(int)
        # Iterate over all sequences (walks).
        for sequence in tqdm(
            self.walks,
            position=0,
            leave=True,
            desc=f"Generating postive and negative examples",
        ):
            # Generate positive and negative skip-gram pairs for a sequence (walk).
            pairs, labels = keras.preprocessing.sequence.skipgrams(
                sequence,
                vocabulary_size=vocabulary_size,
                window_size=window_size,
                negative_samples=num_negative_samples,
            )
            for idx in range(len(pairs)):
                pair = pairs[idx]
                label = labels[idx]
                target, context = min(pair[0], pair[1]), max(pair[0], pair[1])
                if target == context:
                    continue
                entry = (target, context, label)
                example_weights[entry] += 1

        targets, contexts, labels, weights = [], [], [], []
        for entry in example_weights:
            weight = example_weights[entry]
            target, context, label = entry
            targets.append(target)
            contexts.append(context)
            labels.append(label)
            weights.append(weight)

        return np.array(targets), np.array(contexts), np.array(labels), np.array(weights)

    def create_model(self, embedding_dim):
        vocabulary_size = len(self.vocabulary)
        inputs = {
            "target": layers.Input(name="target", shape=(), dtype="int32"),
            "context": layers.Input(name="context", shape=(), dtype="int32"),
        }
        # Initialize item embeddings.
        embed_item = layers.Embedding(
            input_dim=vocabulary_size,
            output_dim=embedding_dim,
            embeddings_initializer="he_normal",
            embeddings_regularizer=keras.regularizers.l2(1e-6),
            name="item_embeddings",
        )
        # Lookup embeddings for target.
        target_embeddings = embed_item(inputs["target"])
        # Lookup embeddings for context.
        context_embeddings = embed_item(inputs["context"])
        # Compute dot similarity between target and context embeddings.
        logits = layers.Dot(axes=1, normalize=False, name="dot_similarity")(
            [target_embeddings, context_embeddings]
        )
        # Create the model.
        model = keras.Model(inputs=inputs, outputs=logits)
        return model


if __name__ == '__main__':
    wn = WeightedNode2Vec()
    wn.show_graph_info()
    print('Generate training data using the biased random walk.')
    # Random walk return parameter.
    p = 1
    # Random walk in-out parameter.
    q = 1
    # Number of iterations of random walks.
    num_walks = 10
    # Number of steps of each random walk.
    num_steps = 20
    wn.random_walk(num_walks, num_steps, p, q)
    print("Number of walks generated:", len(wn.walks))

    print('Generate positive and negative examples.')
    num_negative_samples = 1
    targets, contexts, labels, weights = wn.generate_examples(
        window_size=num_steps,
        num_negative_samples=num_negative_samples,
        vocabulary_size=len(wn.vocabulary),
    )
    print(f"Targets shape: {targets.shape}")
    print(f"Contexts shape: {contexts.shape}")
    print(f"Labels shape: {labels.shape}")
    print(f"Weights shape: {weights.shape}")

    print('Convert the data into tf.data.Dataset objects.')
    batch_size = 1024
    dataset = create_dataset(
        targets=targets,
        contexts=contexts,
        labels=labels,
        weights=weights,
        batch_size=batch_size,
    )

    print('Train the skip-gram model.')
    learning_rate = 0.001
    embedding_dim = 64
    num_epochs = 10
    model = wn.create_model(embedding_dim)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate),
        loss=keras.losses.BinaryCrossentropy(from_logits=True),
    )
    keras.utils.plot_model(
        model,
        show_shapes=True,
        show_dtype=True,
        show_layer_names=True,
    )
    history = model.fit(dataset, epochs=num_epochs)
    plt.plot(history.history["loss"])
    plt.ylabel("loss")
    plt.xlabel("epoch")
    plt.show()

    print('Analyze the learnt embeddings.')
    space_embeddings = model.get_layer("item_embeddings").get_weights()[0]
    print("Embeddings shape:", space_embeddings.shape)

    print('Save the embeddings.')
    out_v = io.open(os.path.join(ROOT_dir, "dbs/graphs/embeddings.tsv"), "w", encoding="utf-8")
    out_m = io.open(os.path.join(ROOT_dir, "dbs/graphs/metadata.tsv"), "w", encoding="utf-8")

    for idx, space_id in enumerate(wn.vocabulary[1:]):
        vector = space_embeddings[idx]
        out_v.write("\t".join([str(x) for x in vector]) + "\n")
        out_m.write(space_id + "\n")

    out_v.close()
    out_m.close()
