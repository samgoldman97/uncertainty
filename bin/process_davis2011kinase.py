import matplotlib.pyplot as plt
import numpy as np
import random
import seaborn as sns

from utils import mkdir_p

np.random.seed(0)
random.seed(0)

def load_kds(fname):
    with open(fname) as f:
        header = f.readline().rstrip().split(',')
        chems = header[3:]

        Kds, genes, prots = [], [], []
        for line in f:
            fields = line.rstrip().split(',')
            genes.append(fields[1])
            prots.append(fields[2])
            Kds.append([ float(field) if field != '' else 10000.
                       for field in fields[3:] ])

    Kds = np.array(Kds).T
    Kds = Kds.max() - Kds
    #Kds = -np.log10(Kds / Kds.max())

    return Kds, chems, genes, prots

def featurize_chems(fname, chems):
    chem2feature = {}
    with open(fname) as f:
        for line in f:
            if line.startswith('>'):
                name = line[1:].rstrip()
                chem2feature[name] = [
                    int(field) for field in f.readline().rstrip().split()
                ]
    assert(len(set(chems) - set(chem2feature.keys())) == 0)
    return chem2feature

def featurize_prots(fname, prots):
    prot2feature = {}

    with open(fname) as f:
        for line in f:
            if line.startswith('>'):
                name = line[1:].rstrip()

                # Handle phosphorylation.
                if '-phosphorylated' in name:
                    phospho = 1
                else:
                    phospho = 0

                prot2feature[name] = [
                    float(field) for field in f.readline().rstrip().split()
                ] + [ phospho ]

    assert(len(set(prots) - set(prot2feature.keys())) == 0)

    return prot2feature

def split_data(Kds, chems, genes, prots, chem2feature, prot2feature):
    prots = np.array(prots)
    prot_idx_train, prot_idx_test = [], []

    gene2idxs = {}
    for idx, gene in enumerate(genes):
        if gene not in gene2idxs:
            gene2idxs[gene] = []
        gene2idxs[gene].append(idx)

    for uniq_idx, gene in enumerate(gene2idxs):
        if uniq_idx % 2 == 0:
            prot_idx_train += gene2idxs[gene]
        else:
            prot_idx_test += gene2idxs[gene]

    idx_train, idx_test = [], []

    chem_idxs = list(range(len(chems)))
    random.shuffle(chem_idxs)

    for pos, i in enumerate(chem_idxs):
        if pos % 4 == 0:
            [ idx_train.append((i, j)) for j in range(len(prots)) ]
        #elif pos % 4 == 1:
        #    [ idx_train.append((i, j)) for j in prot_idx_train ]
        #    [ idx_test.append((i, j)) for j in prot_idx_test ]
        else:
            [ idx_test.append((i, j)) for j in range(len(prots)) ]

    assert(len(set(idx_train) & set(idx_test)) == 0)

    X_train, y_train = [], []
    for i, j in idx_train:
        chem = chems[i]
        prot = prots[j]
        X_train.append(chem2feature[chem] + prot2feature[prot])
        y_train.append(Kds[i, j])
    X_train, y_train = np.array(X_train), np.array(y_train)

    X_test, y_test = [], []
    for i, j in idx_test:
        chem = chems[i]
        prot = prots[j]
        X_test.append(chem2feature[chem] + prot2feature[prot])
        y_test.append(Kds[i, j])
    X_test, y_test = np.array(X_test), np.array(y_test)

    # For runtime debugging:
    #X_train = X_train[:10]
    #y_train = y_train[:10]
    #X_test = X_test[:10]
    #y_test = y_test[:10]

    return X_train, y_train, idx_train, X_test, y_test, idx_test

def visualize_heatmap(chem_prot, suffix=''):
    plt.figure()
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    sns.heatmap(chem_prot, cmap=cmap)
    mkdir_p('figures/')
    if suffix == '':
        plt.savefig('figures/heatmap.png', dpi=300)
    else:
        plt.savefig('figures/heatmap_{}.png'.format(suffix), dpi=300)
    plt.close()

def process():
    Kds, chems, genes, prots = load_kds('data/davis2011kinase/nbt.1990-S4.csv')

    visualize_heatmap(Kds, 'logKd')

    chem2feature = featurize_chems(
        'data/davis2011kinase/chem_fingerprints.txt', chems
    )
    prot2feature = featurize_prots(
        'data/davis2011kinase/prot_embeddings.txt', prots
    )
    X_obs, y_obs, idx_obs, X_unk, y_unk, idx_unk = split_data(
        Kds, chems, genes, prots, chem2feature, prot2feature
    )

    process_data = {
        'Kds': Kds,
        'chems': chems,
        'genes': genes,
        'prots': prots,
        'X_obs': X_obs,
        'y_obs': y_obs,
        'idx_obs': idx_obs,
        'X_unk': X_unk,
        'y_unk': y_unk,
        'idx_unk': idx_unk,
    }

    return process_data


if __name__ == '__main__':
    process_data = process()

    Kds = process_data['Kds']
    idx_obs = process_data['idx_obs']
    idx_unk = process_data['idx_unk']

    n_chems = max([ idx[0] for idx in idx_obs ] +
                  [ idx[0] for idx in idx_unk]) + 1
    n_prots = max([ idx[1] for idx in idx_obs ] +
                  [ idx[1] for idx in idx_unk]) + 1

    obs_unk = np.zeros(Kds.shape)
    for i, j in idx_unk:
        obs_unk[i, j] = 1.
    visualize_heatmap(obs_unk, 'obs_unk')
