#!/usr/bin/env python3

import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, get_metadata, patch_metadata
from functions import script_utils as scu


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        parents=[scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('old',
                        help="The uuid or ID of the Biorxiv publication")
    parser.add_argument('new',
                        help="The uuid or ID of the Published Journal Article")
    parser.add_argument('--vals2skip',
                        nargs='+',
                        help="A list of values or IDs (uuids, accessions ...) to not transfer")

    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def remove_skipped_vals(val, vals2skip=None, auth=None):
    if not (val and vals2skip):
        return val
    is_string = False
    if isinstance(val, str):
        val = [val]
        is_string = True
    val = [v for v in val if v not in vals2skip]
    if auth:
        vuuids = [scu.get_item_uuid(v, auth) for v in val]
        skuids = [scu.get_item_uuid(v, auth) for v in vals2skip]
        for i, v in enumerate(vuuids):
            if v is not None:
                if v in skuids:
                    del val[i]
    if val:
        if is_string:
            return val[0]
        return val
    return None


def create_patch_for_new_from_old(old, new, fields2move, vals2skip=None):
    # build the patch dictionary
    ja_patch_dict = {}
    skipped = {}  # has info on skipped fields
    for f in fields2move:
        val = old.get(f)
        val = remove_skipped_vals(val, vals2skip)
        if val:
            jval = new.get(f)  # see if the field already has data in new item
            if jval:
                skipped[f] = {'old': val, 'new': jval}
                continue
            if isinstance(val, list):
                litems = []
                for v in val:
                    if isinstance(v, dict):
                        uid = v.get('uuid')
                        if uid is not None:
                            litems.append(uid)
                    else:
                        litems.append(v)
                if litems:
                    ja_patch_dict[f] = litems
            else:
                ja_patch_dict[f] = val
    return ja_patch_dict, skipped


def move_old_url_to_new_aka(biorxiv, jarticle, patch={}, skip={}):
    if 'url' in biorxiv:
        if 'aka' in jarticle:
            skip['aka'] = {'old': jarticle['aka'], 'new': biorxiv['url']}
        else:
            patch['aka'] = biorxiv['url']
    return patch, skip


def patch_and_report(auth, patch_d, skipped, uuid2patch, dryrun):
    # report and patch
    if dryrun:
        print('DRY RUN - nothing will be patched to database')
    if skipped:
        print('WARNING! - SKIPPING for', uuid2patch)
        for f, v in skipped.items():
            print('Field: %s\tHAS: %s\tNOT ADDED: %s' % (f, v['new'], v['old']))

    if not patch_d:
        print('NOTHING TO PATCH - ALL DONE!')
    else:
        print('PATCHING -', uuid2patch)
        for f, v in patch_d.items():
            print(f, '\t', v)

        if not dryrun:
            # do the patch
            res = patch_metadata(patch_d, uuid2patch, auth)
            if res['status'] == 'success':
                print("SUCCESS!")
                return True
            else:
                print("FAILED TO PATCH", uuid2patch, "RESPONSE STATUS", res['status'], res['description'])
                return False
    return True


def find_and_patch_item_references(auth, olduuid, newuuid, dryrun):
    search = "type=Item&references.uuid=" + olduuid
    itemids = scu.get_item_ids_from_args([search], auth, True)
    complete = True
    if not itemids:
        print("No references to %s found." % olduuid)
    for iid in itemids:
        ok = patch_and_report(auth, {'references': [newuuid]}, None, iid, dryrun)
        if not ok and complete:
            complete = False
    return complete


def main():  # pragma: no cover
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    dryrun = not args.dbupdate

    biorxiv = get_metadata(args.old, auth)
    jarticle = get_metadata(args.new, auth)

    if biorxiv.get('status') == 'error':
        print('Biorxiv record %s cannot be found' % args.old)
        sys.exit(1)
    if jarticle.get('status') == 'error':
        print('Journal Article record %s cannot be found' % args.new)
        sys.exit(1)
    # make sure we can get the uuid to patch
    juuid = jarticle.get('uuid')
    # build the patch dictionary
    fields2transfer = ['categories', 'exp_sets_prod_in_pub', 'exp_sets_used_in_pub', 'published_by']
    patch_dict, skipped = create_patch_for_new_from_old(biorxiv, jarticle, fields2transfer, args.vals2skip)
    patch_dict, skipped = move_old_url_to_new_aka(biorxiv, jarticle, patch_dict, skipped)

    # do the patch
    ok = patch_and_report(auth, patch_dict, skipped, juuid, dryrun)

    if not ok:
        sys.exit(1)  # bail out if initial transfer doesn't work

    # find items with reference to old paper
    buuid = biorxiv.get('uuid')
    complete = find_and_patch_item_references(auth, buuid, juuid, dryrun)
    if not complete:
        print("ALL REFERENCES POINTING TO %s NOT UPDATED - CHECK AND FIX!" % buuid)


if __name__ == '__main__':
    main()
