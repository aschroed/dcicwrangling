import os
from uuid import UUID
import copy
import argparse
from dcicutils import submit_utils
from dcicutils.ff_utils import search_metadata


def create_ff_arg_parser():
    ff_arg_parser = argparse.ArgumentParser(add_help=False)
    ff_arg_parser.add_argument('--key',
                               default='default',
                               help="The keypair identifier from the keyfile.  \
                               Default is --key=default")
    ff_arg_parser.add_argument('--keyfile',
                               default=os.path.expanduser("~/keypairs.json"),
                               help="The keypair file.  Default is --keyfile=%s" %
                               (os.path.expanduser("~/keypairs.json")))
    ff_arg_parser.add_argument('--dbupdate',
                               default=False,
                               action='store_true',
                               help="Do UPDATES on database objects.  Default is False \
                               and will only UPDATE with user override")
    return ff_arg_parser


def create_input_arg_parser():
    input_arg_parser = argparse.ArgumentParser(add_help=False)
    input_arg_parser.add_argument('input', nargs='+',
                                  help="A list of item ids, a file with item ids one per line \
                                  or a search string (use with --search option)")
    input_arg_parser.add_argument('--search',
                                  default=False,
                                  action='store_true',
                                  help='Include if you are passing in a search string \
                                  eg. type=Biosource&biosource_type=primary cell')
    return input_arg_parser


def get_item_ids_from_args(id_input, connection, is_search=False):
    '''depending on the args passed return a list of item ids'''
    if is_search:
        def search_callback(hit, results):
            try:
                hit.get('uuid')
                results.append(hit.get('uuid'))
            except AttributeError:
                pass
        query = 'search/?' + id_input[0]
        results = []
        safe_search_with_callback(connection, query, results, search_callback)
        return list(set(results))
    try:
        with open(id_input[0]) as inf:
            return [l.strip() for l in inf]
    except FileNotFoundError:
        return id_input


def safe_search_with_callback(fdn_conn, query, container, callback, limit=20, frame='embedded'):
    """
    Somewhat temporary function to avoid making search queries that cause
    memory issues. Takes a ff_utils fdn_conn, a search query (without 'limit' or
    'from' parameters), a container to put search results in after running
    them through a given callback function, which should take a search hit as
    its first parameter and the container as its second parameter.
    """
    last_total = None
    curr_from = 0
    while not last_total or last_total == limit:
        print('...', curr_from)
        search_query = ''.join([query, '&from=', str(curr_from), '&limit=', str(limit)])
        search_res = search_metadata(search_query, connection=fdn_conn, frame=frame)
        if not search_res:  # 0 results
            break
        last_total = len(search_res)
        curr_from += last_total
        for hit in search_res:
            callback(hit, container)


def get_item_uuid(iid, connection):
    """return a uuid for an item passed another id type"""
    if is_uuid(iid):
        return iid
    res = submit_utils.get_FDN(iid, connection)
    return res.get('uuid')


def is_uuid(value):
    """Does the string look like a uuid"""
    if '-' not in value:
        # md5checksums are valid uuids but do not contain dashes so this skips those
        return False
    try:
        UUID(value, version=4)
        return True
    except ValueError:  # noqa: E722
        return False


def find_uuids(val):
    """Find any uuids in the value"""
    vals = []
    if not val:
        return []
    elif isinstance(val, str):
        if is_uuid(val):
            vals = [val]
        else:
            return []
    else:
        text = str(val)
        text_list = [i for i in text. split("'") if len(i) == 36]
        vals = [i for i in text_list if is_uuid(i)]
    return vals


def get_item_type(connection, item):
    try:
        return item['@type'].pop(0)
    except (KeyError, TypeError):
        res = submit_utils.get_FDN(item, connection)
        try:
            return res['@type'][0]
        except AttributeError:  # noqa: E722
            print("Can't find a type for item %s" % item)
    return None


def filter_dict_by_value(dictionary, values, include=True):
    """Will filter items from a dictionary based on values
        can be either an inclusive or exclusive filter
        if include=False will remove the items with given values
        else will remove items that don't match the given values
    """
    if include:
        return {k: v for k, v in dictionary.items() if v in values}
    else:
        return {k: v for k, v in dictionary.items() if v not in values}


def has_field_value(item_dict, field, value=None, val_is_item=False):
    """Returns True if the field is present in the item
        BUT if there is value parameter only returns True if value provided is
        the field value or one of the values if the field is an array
        How fancy do we want to make this?"""
    # 2 simple cases
    if field not in item_dict:
        return False
    if not value and field in item_dict:
        return True

    # now checking value
    val_in_item = item_dict.get(field)

    if isinstance(val_in_item, list):
        if value in val_in_item:
            return True
    elif isinstance(val_in_item, str):
        if value == val_in_item:
            return True

    # only check dict val_is_item param is True and only
    # check @id and link_id - uuid raw format will have been
    # checked above
    if val_in_item:
        if isinstance(val_in_item, dict):
            ids = [val_in_item.get('@id'), val_in_item.get('link_id')]
            if value in ids:
                return True
    return False


def get_types_that_can_have_field(connection, field):
    """find items that have the passed in fieldname in their properties
        even if there is currently no value for that field"""
    profiles = submit_utils.get_FDN('/profiles/', connection=connection, frame='raw')
    types_w_field = []
    for t, j in profiles.items():
        if j['properties'].get(field):
            types_w_field.append(t)
    return types_w_field


def get_linked_items(connection, itemid, found_items={},
                     no_children=['Publication', 'Lab', 'User', 'Award']):
    """Given an ID for an item all descendant linked item uuids (as given in 'frame=raw')
        are stored in a dict with each item type as the value.
        All descendants are retrieved recursively except the children of the types indicated
        in the no_children argument.
        The relationships between descendant linked items are not preserved - i.e. you don't
        know who are children, grandchildren, great grandchildren ... """
    # import pdb; pdb.set_trace()
    if not found_items.get(itemid):
        res = submit_utils.get_FDN(itemid, connection=connection, frame='raw')
        if 'error' not in res['status']:
            # create an entry for this item in found_items
            try:
                obj_type = submit_utils.get_FDN(itemid, connection=connection)['@type'][0]
                found_items[itemid] = obj_type
            except AttributeError:  # noqa: E722
                print("Can't find a type for item %s" % itemid)
            if obj_type not in no_children:
                fields_to_check = copy.deepcopy(res)
                id_list = []
                for key, val in fields_to_check.items():
                    # could be more than one item in a value
                    foundids = find_uuids(val)
                    if foundids:
                        id_list.extend(foundids)
                if id_list:
                    id_list = [i for i in list(set(id_list)) if i not in found_items]
                    for uid in id_list:
                        found_items.update(get_linked_items(connection, uid, found_items))
    return found_items
