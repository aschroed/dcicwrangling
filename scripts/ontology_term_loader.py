#!/usr/bin/env python3

import sys
import argparse
import json
from datetime import datetime
from dcicutils.ff_utils import fdn_connection
from dcicutils.submit_utils import get_FDN, patch_FDN, new_FDN
from dcicwrangling.scripts.script_utils import create_ff_arg_parser


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of ontology term jsons (one per line) load into db',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    args = parser.parse_args()
    return args


def get_id(term):
    id_tag = term.get('uuid')
    if not id_tag:
        term.get('term_id')
    if not id_tag:
        term.get('term_name')
    return id_tag


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        connection = fdn_connection(args.keyfile, keyname=args.key)
    except Exception as e:
        print("Connection failed")
        sys.exit(1)

    phase2 = {}
    # assumes a single line corresponds to json for single term
    if not args.dbupdate:
        print("DRY RUN - use --dbupdate to update the database")
    with open(args.infile) as terms:
        for t in terms:
            phase2json = {}
            term = json.loads(t)
            id_tag = get_id(term)
            if id_tag is None:
                print("No Identifier for ", term)
            else:
                tid = '/ontology-terms/' + id_tag
                # look for parents and remove for phase 2 loading if they are there
                if 'parents' in term:
                    phase2json['parents'] = term['parents']
                    del term['parents']
                if 'slim_terms' in term:
                    phase2json['slim_terms'] = term['slim_terms']
                    del term['slim_terms']

                dbterm = get_FDN(tid, connection)
                op = ''
                if 'OntologyTerm' in dbterm['@type']:
                    if args.dbupdate:
                        e = patch_FDN(dbterm["uuid"], connection, term)
                    else:
                        e = {'status': 'dry run'}
                    op = 'PATCH'
                else:
                    if args.dbupdate:
                        e = new_FDN(connection, 'OntologyTerm', term)
                    else:
                        e = {'status': 'dry run'}
                    op = 'POST'
                status = e.get('status')
                if status and status == 'dry run':
                    print(op, status)
                elif status and status == 'success':
                    print(op, status, e['@graph'][0]['uuid'])
                    if phase2json:
                        phase2[e['@graph'][0]['uuid']] = phase2json
                else:
                    print('FAILED', tid, e)

    print("START LOADING PHASE2 at ", str(datetime.now()))
    for tid, data in phase2.items():
        if args.dbupdate:
            e = patch_FDN(tid, connection, data)
        else:
            e = {'status': 'dry run'}
        status = e.get('status')
        if status and status == 'dry run':
            print('PATCH', status)
        elif status and status == 'success':
            print('PATCH', status, e['@graph'][0]['uuid'])
        else:
            print('FAILED', tid, e)
    end = datetime.now()
    print("FINISHED - START: ", str(start), "\tEND: ", str(end))


if __name__ == '__main__':  # pragma: no cover
        main()
