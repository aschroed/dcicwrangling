#!/usr/bin/env python3

import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server
from dcicwrangling.scripts.script_utils import create_ff_arg_parser, convert_key_arg_to_dict


def get_args(args):
    parser = argparse.ArgumentParser(
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args(args)
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def switcher(case, x, term2id):
    switcher = {
        'aliases': lambda x: {'aliases': x + '_bf'},
        'description': lambda x: {'description': x},
        'targeted_genes': lambda x: {'relevant_genes': [x], 'feature_type': term2id['gene']},
        'targeted_proteins': lambda x: {'relevant_genes': [x], 'feature_type': term2id['polypeptide']},
        'targeted_rnas': lambda x: {'relevant_genes': [x], 'feature_type': term2id['transcript']},
        'targeted_structure': lambda x: {'cellular_structure': x, 'feature_type': term2id['cellular_component']},
        'targeted_genome_regions': lambda x: {'genome_location': [x], 'feature_type': term2id['region']},
        'lab': lambda x: {'lab': x},
        'award': lambda x: {'award': x},
    }
    return switcher.get(case, lambda x: {'field': 'Unknown'})(x)


def main():  # pragma: no cover
    args = get_args(sys.argv[1:])
    try:
        get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    # setup
    terms = ['gene', 'polypeptide', 'transcript', 'region', 'cellular_component']
    # local inserts
    ids = ["38184c75-56ae-4ccb-b7c7-28f5a99c7f6e", "e4addd27-69e1-47d2-8ff4-a7ada5fc48a5",
           "e8f56a24-20ce-4e7c-9e8d-a4f409398574", "bca12371-0380-402a-ac1f-fafe552c2cba",
           "e47e2bea-bc1e-4989-881c-521fc0b33529"]
    term2id = dict(zip(terms, ids))
    # TODO: need function to get info from db once doing in anger

    biofeats = {}
    infile = 'all_target_info.txt'
    inf = open(infile)
    hl = inf.readline()
    fields = [h.strip() for h in hl.split('\t')]
    for l in inf:
        info = {}
        vals = [v.strip() for v in l.split('\t')]
        data = dict(zip(fields, vals))
        for f, v in data.items():
            if v == 'None':
                continue
            if f == '#id':
                key = v
            else:
                info.update(switcher(f, v, term2id))
        biofeats[key] = info
    for bf in biofeats.values():
        print(bf)


if __name__ == '__main__':  # pragma: no cover
    main()
