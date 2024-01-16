import os
from time import time
from queue import Queue

from graphviz import Digraph
from rdkit import Chem
from rdkit.Chem import Draw

CARBON_IDX = 6


def draw_mol(smi):
    mol = Chem.MolFromSmiles(smi)
    time_stamp = int(time()*10000)
    if not os.path.exists('images_tmp'):
        os.makedirs('images_tmp')
    save_path = f'images_tmp/{time_stamp}.png'
    Draw.MolToFile(
        mol,  # mol对象
        save_path,  # 图片存储地址
        size=(300, 300),
        kekulize=True,
        wedgeBonds=True,
        imageType=None,
        fitImage=False,
        options=None,
    )
    return os.path.abspath(save_path)


class SynRoute(object):
    def __init__(self, target_mol, succ_value, search_status):
        self.target_mol = target_mol
        self.mols = [target_mol]
        self.values = [None]
        self.templates = [None]
        self.types = [None]
        self.parents = [-1]
        self.children = [None]
        self.optimal = False
        self.costs = {}
        self.costs_T = {}
        self.costs_R = {}
        self.num_rxns = [None]
        self.ref_rxns = [None]
        self.succ_value = succ_value
        self.total_cost = 0
        self.length = 0
        self.search_status = search_status
        if self.succ_value <= self.search_status:
            self.optimal = True

    def _add_mol(self, mol, parent_id):
        self.mols.append(mol)
        self.values.append(None)
        self.types.append(None)
        self.templates.append(None)
        self.num_rxns.append(None)
        self.ref_rxns.append(None)
        self.parents.append(parent_id)
        self.children.append(None)

        self.children[parent_id].append(len(self.mols)-1)

    def set_value(self, mol, value):
        assert mol in self.mols

        mol_id = self.mols.index(mol)
        self.values[mol_id] = value

    def add_reaction(self, mol, value, template, reactants, cost, type, num_rxns, ref_rxns):
        assert mol in self.mols

        self.total_cost += cost[0]
        self.length += 1

        parent_id = self.mols.index(mol)
        self.values[parent_id] = value
        self.templates[parent_id] = template
        self.num_rxns[parent_id] = num_rxns
        self.ref_rxns[parent_id] = ref_rxns
        self.types[parent_id] = type
        self.children[parent_id] = []
        self.costs[parent_id] = cost[0]
        self.costs_T[parent_id] = cost[1]
        self.costs_R[parent_id] = cost[2]
        for reactant in reactants:
            self._add_mol(reactant, parent_id)

    def viz_route(self, viz_file):
        G = Digraph('G', filename=viz_file)
        G.attr('node', shape='box')
        G.format = 'svg'

        names = []
        for i in range(len(self.mols)):
            name = self.mols[i]
            # if self.templates[i] is not None:
            #     name += ' | %s' % self.templates[i]
            names.append(name)

        node_queue = Queue()
        node_queue.put((0,-1))   # target mol idx, and parent idx
        while not node_queue.empty():
            idx, parent_idx = node_queue.get()

            if parent_idx >= 0:
                G.node(name=names[parent_idx], image=draw_mol(names[parent_idx]), label=names[parent_idx], labelloc='top')
                G.node(name=names[idx], image=draw_mol(names[idx]), label=names[idx], labelloc='top')
                G.edge(names[parent_idx], names[idx], label="cost: %.4f" % self.costs[parent_idx])

            if self.children[idx] is not None:
                for c in self.children[idx]:
                    node_queue.put((c, idx))

        G.render()

    def serialize_reaction(self, idx):
        s = self.mols[idx]
        if self.templates[idx] is None:
            self.templates[idx] = ""
        if self.children[idx] is None:
            return s
        s += '>%.4f' % self.costs[idx]
        s += ',%.4f' % self.costs_T[idx]
        s += ',%.4f' % self.costs_R[idx]
        s += ',' + self.templates[idx]
        s += ',%d' % self.num_rxns[idx]
        s += ',' + self.ref_rxns[idx]
        s += ',' + self.types[idx]+'>'
        s += self.mols[self.children[idx][0]]
        for i in range(1, len(self.children[idx])):
            s += '.'
            s += self.mols[self.children[idx][i]]

        return s

    def serialize(self):
        s = self.serialize_reaction(0)
        for i in range(1, len(self.mols)):
            if self.children[i] is not None:
                s += '|'
                s += self.serialize_reaction(i)

        return s

    def serialize_reaction_with_score(self, idx):
        s = self.mols[idx]
        if self.templates[idx] is None:
            self.templates[idx] = ""
        if self.children[idx] is None:
            return s
        s += '>%.4f' % self.costs[idx]
        s += ',%.4f' % self.costs_T[idx]
        s += ',%.4f' % self.costs_R[idx]
        s += ',' + self.templates[idx]
        s += ',%d' % self.num_rxns[idx]
        s += ',' + self.ref_rxns[idx]
        s += ',' + self.types[idx]+'>'
        s += self.mols[self.children[idx][0]]
        for i in range(1, len(self.children[idx])):
            s += '.'
            s += self.mols[self.children[idx][i]]

        return s, self.costs[idx]

    def serialize_with_score(self):
        s = self.serialize_reaction(0)
        total_cost = 1
        for i in range(1, len(self.mols)):
            if self.children[i] is not None:
                s += '|'
                react, cost = self.serialize_reaction_with_score(i)
                s += react
                total_cost *= cost

        return s, self.total_cost
