#!/usr/bin/env python3
'''
Given a list of Repsets IDs and a title of the opf group
will transfer processed_files to other_processed_files
'''
import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, get_metadata, patch_metadata
from functions import script_utils as scu


def get_args(args):
    parser = argparse.ArgumentParser(
        parents=[scu.create_input_arg_parser(), scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--title',
                        default='Set of preliminary processed files',
                        help="The title for the group of other processed files.")
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    print('#', auth.get('server'))
    id_list = scu.get_item_ids_from_args(args.input, auth, args.search)

    for itemid in id_list:
        # get the existing data in other p
        item_data = get_metadata(itemid, auth, add_on='frame=raw')
        pfiles = item_data.get('processed_files')
        if not pfiles:
            continue
        patch_data = item_data.get('other_processed_files', [])
        if patch_data:
            # does the same title exist
            if args.title in [i['title'] for i in patch_data]:
                print(itemid, 'already has preliminary results')
                continue

        patch_data.append({'title': args.title,
                           'type': 'preliminary',
                           'files': pfiles})
        if patch_data:
            patch = {'other_processed_files': patch_data}
            if args.dbupdate:
                res = patch_metadata(patch, obj_id=itemid, key=auth, add_on='delete_fields=processed_files')
                print(res.get('status'))
            else:
                print("DRY RUN -- will patch")
                print(patch)
                print('and delete processed_files field value')


if __name__ == '__main__':  # pragma: no cover
    main()
