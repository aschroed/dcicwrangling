#!/usr/bin/env python3

import sys
import argparse
# import json
# import re
# import ast
from datetime import datetime
# from uuid import uuid4
from dcicutils.ff_utils import (
    get_authentication_with_server,
    # get_metadata,
    # patch_metadata,
    # post_metadata,
    search_metadata,
)
from dcicwrangling.functions.script_utils import convert_key_arg_to_dict


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given an HPOA file generate phenotype annotations for that disorder as json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--env',
                        default='local',
                        help="The environment to use i.e. data, webdev, mastertest.\
                        Default is 'local')")
    parser.add_argument('--key',
                        default=None,
                        help="An access key dictionary including key, secret and server.\
                        {'key': 'ABCDEF', 'secret': 'supersecret', 'server': 'https://data.4dnucleome.org'}")
    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    parser.add_argument('--outfile',
                        help="the optional path and file to write output default is disorders.json",
                        default="unmapped.tsv")
    parser.add_argument('--pretty',
                        default=False,
                        action='store_true',
                        help="Default False - set True if you want json format easy to read, hard to parse")
    args = parser.parse_args()
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    q = 'search/?type=Disorder&q={}'
    with open(args.infile) as lostdis:
        with open(args.outfile, 'w') as of:
            for line in lostdis:
                disid, disname = line.split('\t')
                qname = disname.strip().lower()
                found = search_metadata(q.format(qname), auth, page_limit=200)
                cols = [disid, disname.strip(), str(len(found))]
                fcols = ['{} = {}'.format(d.get('disorder_id'), d.get('disorder_name')) for d in found]
                # print(fcols)
                if fcols:
                    cols.extend(fcols)
                # print(cols)
                of.write('\t'.join(cols) + '\n')
                print('For unmapped disorder {}\t{} found {} possibles'.format(disid, disname, len(found)))
                top_3 = [(d.get('disorder_id'), d.get('disorder_name')) for d in found[:3]]
                for (mondo_id, name) in top_3:
                    print('\t{}\t{}'.format(mondo_id, name))


if __name__ == '__main__':  # pragma: no cover
    main()
