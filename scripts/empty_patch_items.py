import sys
import argparse
from dcicutils import ff_utils as ff
from functions import script_utils as scu


def get_args():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description='Provide a search query suffix and get a list of item uuids',
        parents=[scu.create_ff_arg_parser(), scu.create_input_arg_parser()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():
    args = get_args()
    try:
        auth = ff.get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)
    print("Working on {}".format(auth.get('server')))
    itemids = scu.get_item_ids_from_args(args.input, auth, args.search)
    seen = []
    failed = []
    for itemid in itemids:
        print("Touching ", itemid)
        if args.dbupdate:
            try:
                res = ff.patch_metadata({}, itemid, auth)
                print(res.get('status'))
                if res.get('status') == 'success':
                    seen.append(itemid)
            except Exception:
                print(itemid, ' failed to patch')
                failed.append(itemid)
                continue
        else:
            print('dry run!')
    for i in seen:
        print(i)
    print("Failures")
    for f in failed:
        print(f)


if __name__ == '__main__':
    main()
