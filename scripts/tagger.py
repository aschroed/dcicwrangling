import sys
import argparse
from dcicutils.ff_utils import get_authentication_with_server, get_metadata, patch_metadata
from functions import script_utils as scu


def make_tag_patch(item, tag):
    if item.get('tags'):
        tags = item['tags']
        tags.append(tag)
    else:
        tags = [tag]
    return {'tags': tags}


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Add a tag to provided items (and optionally their children)',
        parents=[scu.create_input_arg_parser(), scu.create_ff_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('tag',
                        help="The tag you want to add - eg. '4DN Standard'")
    parser.add_argument('--taglinked',
                        default=False,
                        action='store_true',
                        help='Tag items linked to items that are input')
    parser.add_argument('--types2exclude',
                        nargs='+',
                        help="List of Item Types to Explicitly Exclude Tagging - \
                        you may have some linked items that can get tags but may \
                        not want to tag them with this tag")
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    args = get_args()
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    itemids = scu.get_item_ids_from_args(args.input, auth, args.search)
    taggable = scu.get_types_that_can_have_field(auth, 'tags')
    if args.types2exclude is not None:
        # remove explicitly provide types not to tag
        taggable = [t for t in taggable if t not in args.types2exclude]

    seen = []   # only need to add tag once so this keeps track of what's been seen
    to_patch = {}   # keep track of those to patch
    # main loop through the top level item ids
    for itemid in itemids:
        items2tag = {}
        if args.taglinked:
            # need to get linked items and tag them
            linked = scu.get_linked_items(auth, itemid, {})
            items2tag = scu.filter_dict_by_value(linked, taggable, include=True)
        else:
            # only want to tag provided items
            itype = scu.get_item_type(auth, itemid)
            if itype in taggable:
                items2tag = {itemid: itype}
        for i, t in items2tag.items():
            if i not in seen:
                seen.append(i)
                item = get_metadata(i, auth)
                if not scu.has_field_value(item, 'tags', args.tag):
                    # not already tagged with this tag so make a patch and add 2 dict
                    to_patch[i] = make_tag_patch(item, args.tag)

    # now do the patching or reporting
    for pid, patch in to_patch.items():
        if args.dbupdate:
            pres = patch_metadata(patch, pid, auth)
            print(pres['status'])
        else:
            print("DRY RUN: patch ", pid, " with ", patch)


if __name__ == '__main__':  # pragma: no cover
    main()
