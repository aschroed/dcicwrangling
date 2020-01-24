#!/usr/bin/env python3

import sys
import argparse
from datetime import datetime
from dcicutils.ff_utils import (
    get_authentication_with_server,
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
    parser.add_argument('infile1',
                        help="the datafile containing object data to import")
    parser.add_argument('infile2',
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

    disorders = {}
    q = 'search/?type=Phenotype&hpo_id={}'
    with open(args.infile1) as lostdis:
        for line in lostdis:
            disid, disname = line.split('\t')
            disorders[disid] = disname.strip().lower()

    dis2pheno = {}
    with open(args.infile2) as annot:
        for line in annot:
            fields = line.split('\t')
            if fields[0] in disorders:
                pheno = fields[3]
                res = search_metadata(q.format(pheno), auth)
                name = res[0].get('phenotype_name')
                dis2pheno.setdefault(fields[0], []).append((pheno, name))

    for dis in sorted(dis2pheno):
        print(dis, '\t', disorders[dis])
        for phe in sorted(dis2pheno[dis]):
            print('\t', phe[0], '\t', phe[1])


if __name__ == '__main__':  # pragma: no cover
    main()
