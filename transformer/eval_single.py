#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals
import argparse
from rdkit import Chem
import pandas as pd
from rdkit import RDLogger

RDLogger.DisableLog('rdApp.*')

def canonicalize_smiles(smiles):
    data = smiles.replace("[SAH]", "[33S]").replace("[CoA]", "[34S]")
    smiles = data.split("|")[0]
    mol = Chem.MolFromSmiles(smiles, sanitize=False)
    try:
        '''
        mol = Chem.ReplaceSubstructs(mol,s33,coa)
        mol = Chem.ReplaceSubstructs(mol[0],s34, acp)
        for atom in mol[0].GetAtoms():
            try:
                atom.ClearProp("molAtomMapNumber")
            except:
                continue
        '''
        label = data.split("|")[1]
        #label = ""
        return Chem.MolToSmiles(mol, isomericSmiles=False) + "|" + label
    except:
        return ''

def get_rank(row, base, max_rank):
    for i in range(1, max_rank+1):
        #if row['target'] == row['{}{}'.format(base, i)]:
        if set(row['target'].split(".")) <= set(row['{}{}'.format(base, i)].split(".")):
            #print(row.index)
            return i
    return 0

def main(opt):
    with open(opt.targets, 'r') as f:
        targets = [canonicalize_smiles(''.join(line.strip().split(' '))) for line in f.readlines()]

    predictions = [[] for i in range(opt.beam_size)]

    test_df = pd.DataFrame(targets)
    test_df.columns = ['target']
    total = len(test_df)
    
    with open(opt.predictions, 'r') as f:
        for i, line in enumerate(f.readlines()):
            
            predictions[i % opt.beam_size].append(''.join(line.strip().split(' ')))

    for i, preds in enumerate(predictions):
        test_df['prediction_{}'.format(i + 1)] = preds
        test_df['canonical_prediction_{}'.format(i + 1)] = test_df['prediction_{}'.format(i + 1)].apply(
            lambda x: canonicalize_smiles(x))

    test_df['rank'] = test_df.apply(lambda row: get_rank(row, 'canonical_prediction_', opt.beam_size), axis=1)
    correct = 0
    for i in range(1, opt.beam_size+1):
        correct += (test_df['rank'] == i).sum()
        invalid_smiles = (test_df['canonical_prediction_{}'.format(i)] == '').sum()
        if opt.invalid_smiles:
            print('Top-{}: {:.1f}% || Invalid SMILES {:.2f}%'.format(i, correct/total*100,
                                                                     invalid_smiles/total*100))
        else:
            print('Top-{}: {:.1f}%'.format(i, correct / total * 100))



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='score_predictions.py',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #onmt.opts.add_md_help_argument(parser)

    parser.add_argument('-beam_size', type=int, default=5,
                       help='Beam size')
    parser.add_argument('-invalid_smiles', action="store_true",
                       help='Show % of invalid SMILES')
    parser.add_argument('-predictions', type=str, default="",
                       help="Path to file containing the predictions")
    parser.add_argument('-targets', type=str, default="",
                       help="Path to file containing targets")
    parser.add_argument('-sources', type=str, default="",
                       help="Path to file containing unique sources")
    parser.add_argument('-ranks', type=str, default="",
                       help="Path to file containing prediction ranks")
    opt = parser.parse_args()
    
    main(opt)
