#!/usr/bin/env python3

import sys
import argparse
import json
from datetime import datetime
from uuid import uuid4
from dcicutils.ff_utils import (
    get_authentication_with_server,
    post_metadata,
    get_metadata,
    patch_metadata,
)
from functions.script_utils import create_ff_arg_parser, convert_key_arg_to_dict
''' Will attempt to load data from a file into the database using the load_data endpoint if it can
    or post/patch_metadata if not
    The file can be a simple list of json items in which case you need to specify an item type
    with the --itype option (file created by generate_ontology is like this) or the file can
    specify a dictionary with item types as keys and list of jsons as values.

    If the --as_file option is used the json items must contain a uuid and the endpoint will
    attempt to read the file from the request - no ordering and if there are dependencies to
    linked items those items must either already be loaded or present in the file
    WARNING: currently only works locally or if file is uploaded as part of the app file system
'''

ORDER = [
    'user',
    'award',
    'lab',
    'static_section',
    'higlass_view_config',
    'page',
    'ontology',
    'ontology_term',
    'file_format',
    'badge',
    'organism',
    'genomic_region',
    'gene',
    'bio_feature',
    'target',
    'imaging_path',
    'publication',
    'publication_tracking',
    'document',
    'image',
    'vendor',
    'construct',
    'modification',
    'protocol',
    'sop_map',
    'biosample_cell_culture',
    'individual_human',
    'individual_mouse',
    'individual_fly',
    'individual_chicken',
    'biosource',
    'antibody',
    'enzyme',
    'treatment_rnai',
    'treatment_agent',
    'biosample',
    'quality_metric_fastqc',
    'quality_metric_bamqc',
    'quality_metric_pairsqc',
    'quality_metric_dedupqc_repliseq',
    'quality_metric_chipseq',
    'quality_metric_atacseq',
    'microscope_setting_d1',
    'microscope_setting_d2',
    'microscope_setting_a1',
    'microscope_setting_a2',
    'file_fastq',
    'file_processed',
    'file_reference',
    'file_calibration',
    'file_microscopy',
    'file_set',
    'file_set_calibration',
    'file_set_microscope_qc',
    'file_vistrack',
    'experiment_hi_c',
    'experiment_capture_c',
    'experiment_repliseq',
    'experiment_atacseq',
    'experiment_chiapet',
    'experiment_damid',
    'experiment_seq',
    'experiment_tsaseq',
    'experiment_mic',
    'experiment_set',
    'experiment_set_replicate',
    'data_release_update',
    'software',
    'analysis_step',
    'workflow',
    'workflow_mapping',
    'workflow_run_sbg',
    'workflow_run_awsem'
]


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Given a file of item jsons try to load into database',
        parents=[create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('infile',
                        help="the datafile containing json formatted items")
    parser.add_argument('--itypes',
                        nargs='*',
                        help="The item type(s) to load if not specified in the file by store key(s)")
    parser.add_argument('--id-field',
                        help="Field name to used as identifier for items (all item types in file)")
    parser.add_argument('--as-file',
                        default=False,
                        action='store_true',
                        help="Will attempt to load and process the file directly in the request. "
                             "This currently only works locally or if the file has been uploaded to "
                             "the apps file system")
    args = parser.parse_args()
    if args.key:
        args.key = convert_key_arg_to_dict(args.key)
    return args


def patch_jsons(auth, to_patch):
    for item in to_patch:
        uid = item.get('uuid')
        try:
            patch_metadata(item, uid, auth)
        except Exception as e:
            print(e)


def load_json(auth, itype, item_list, chunk_size=50):
    list_length = len(item_list)
    curr_pos = 0
    while curr_pos < list_length:
        slice_for = chunk_size if (chunk_size and chunk_size <= (list_length - curr_pos)) else list_length - curr_pos
        new_end = curr_pos + slice_for
        chunk = item_list[curr_pos: new_end]
        store = {itype: chunk}
        payload = {'store': store, 'overwrite': True}
        if 'localhost' in auth.get('server', ''):
            payload['config_uri'] = 'development.ini'
        try:
            post_metadata(payload, 'load_data', auth)
        except Exception as e:
            print("PROBLEM WITH POST")
            print(e)
        curr_pos = new_end


def load_file(auth, itype, filename):
    payload = {'in_file': filename, 'overwrite': True, 'itype': itype}
    if 'localhost' in auth.get('server', ''):
        payload['config_uri'] = 'development.ini'
    try:
        post_metadata(payload, 'load_data', auth)
    except Exception:
        raise


def get_item(val, auth):
    try:
        return get_metadata(val, auth).get('uuid')
    except:
        return None


def check_for_existing(item, itype, idfields, auth):
    uid = None
    for ifield in idfields:
        id2chk = item.get(ifield)
        if id2chk:
            if ifield == 'aliases':
                for a in id2chk:
                    uid = get_item(a, auth)
                    if uid:
                        return uid
            else:
                chkid = itype + '/' + id2chk
                uid = get_item(chkid, auth)
                if uid:
                    return uid
    return uid


def main():  # pragma: no cover
    start = datetime.now()
    print(str(start))
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    print('working on ', auth.get('server'))
    if args.as_file:
        if not args.dbupdate:
            print("DRY RUN - use --dbupdate to update the database")
        else:
            try:
                load_file(auth, args.itype, args.infile)
            except Exception as e:
                print(e)
    else:
        with open(args.infile) as ifile:
            item_store = json.loads(ifile.read())
            if not args.itype:
                if not isinstance(item_store, dict):
                    print("File is not in correct format")
                    sys.exit(1)
            else:
                if not isinstance(item_store, list):
                    print("File is not in correct format")
                    sys.exit(1)
                item_store = {args.itype: item_store}
            for itype, items in sorted(item_store.items(), key=lambda x: ORDER.index(x[0])):
                if not args.dbupdate:
                    print('DRY RUN - would try to load {} {} items'.format(len(items), itype))
                    continue
                if args.id_field:
                    identifiers = [args.id_field]
                else:
                    schema_path = 'profiles/' + itype + '.json'
                    schema_info = get_metadata(schema_path, auth)
                    identifiers = schema_info.get('identifyingProperties')
                # checking to see if an item exists
                # if no can use load_data endpoint
                # if yes do it the old fashioned way
                to_patch = []
                to_post = []
                for item in items:
                    uid = item.get('uuid')
                    if uid:
                        exists = get_item(uid, auth)
                        if exists:  # try a patch
                            to_patch.append(item)
                        else:
                            to_post.append(item)
                    else:
                        uid = check_for_existing(item, itype, identifiers, auth)
                        if uid:  # try a patch
                            item['uuid'] = uid
                            to_patch.append(item)
                        else:
                            uid = str(uuid4())
                            item['uuid'] = uid
                            to_post.append(item)
                if to_post:
                    load_json(auth, itype, to_post, chunk_size=1000)
                if to_patch:
                    patch_jsons(auth, to_patch)
    stop = datetime.now()
    print(str(stop))


if __name__ == '__main__':  # pragma: no cover
    main()
