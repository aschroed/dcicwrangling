#!/usr/bin/env python3

import sys
import argparse
import json
from datetime import datetime
from dcicutils.ff_utils import (
    get_authentication_with_server,
    get_metadata,
    patch_metadata,
    post_metadata,
)
from functions.script_utils import create_ff_arg_parser, convert_key_arg_to_dict


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of ontology term jsons (one per line) load into db',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing object data to import")
    args = parser.parse_args()
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def get_id(term):
    id_tag = term.get('uuid')
    if not id_tag:
        id_tag = term.get('term_id')
    if not id_tag:
        id_tag = term.get('term_name')
    return id_tag


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
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

                try:
                    dbterm = get_metadata(tid, auth)
                except:  # noqa
                    dbterm = None
                op = ''
                if dbterm and 'OntologyTerm' in dbterm.get('@type', []):
                    if args.dbupdate:
                        e = patch_metadata(term, dbterm["uuid"], auth)
                    else:
                        e = {'status': 'dry run'}
                    op = 'PATCH'
                else:
                    if args.dbupdate:
                        e = post_metadata(term, 'OntologyTerm', auth)
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
            e = patch_metadata(data, tid, auth)
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
