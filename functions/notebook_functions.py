from dcicutils import ff_utils
from uuid import UUID
import copy
import os
import json


def is_uuid(value):
    #md5 qualifies as uuid
    if '-' not in value:
        return False
    try:
        UUID(value, version=4)
        return True
    except:
        return False


def find_uuids(val):
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


def get_schema_names(con_key):
    schema_name = {}
    profiles = ff_utils.get_metadata('/profiles/', key=con_key, add_on='frame=raw')
    for key, value in profiles.items():
        schema_name[key] = value['id'].split('/')[-1][:-5]
    return schema_name


def record_object(uuid, store, item_uuids, con_key, schema_name, add_pc_wfr=False):
    #keep list of fields that only exist in frame embedded (revlinks) that you want connected
    if add_pc_wfr:
        add_from_embedded = {'file_fastq': ['workflow_run_inputs', 'workflow_run_outputs'],
                             'file_processed': ['workflow_run_inputs', 'workflow_run_outputs']
                             }
    else:
        add_from_embedded = {}

    #find schema name, store as obj_key, create empty list if missing in store

    obj_type = ff_utils.get_metadata(uuid, key=con_key, add_on='frame=object')['@type'][0]

    try:
        obj_key = schema_name[obj_type]
    except:
        #print 'CAN NOT FIND', obj_type, uuid
        return store, item_uuids
    if obj_key not in store:
        store[obj_key] = []

    resp = ff_utils.get_metadata(uuid, key=con_key, add_on='frame=raw')

    if resp['status'] not in ['current', 'released']:
        print(obj_key, uuid, resp['status'])

    # add raw frame to store and uuid to list
    if uuid not in item_uuids:
        store[obj_key].append(resp)
        item_uuids.append(uuid)
    # this case should not happen actually
    else:
        return store, item_uuids

    fields_to_check = copy.deepcopy(resp)

    # check if any field from the embedded frame is required
    add_fields = add_from_embedded.get(obj_key)
    if add_fields:
        emb_resp = ff_utils.get_metadata(uuid, key=con_key, add_on='frame=embedded')
        for a_field in add_fields:
            field_val = emb_resp.get(a_field)
            if field_val:
                fields_to_check[a_field] = field_val

    for key, value in fields_to_check.items():
        # uuid formatted fields to skip
        if key in ['uuid', 'blob_id', "attachment"]:
            continue
        uuid_in_val = find_uuids(value)

        for a_uuid in uuid_in_val:
            if a_uuid not in item_uuids:
                store, item_uuids = record_object(a_uuid, store, item_uuids, con_key, schema_name, add_pc_wfr)
    return store, item_uuids


def dump_results_to_json(store, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    for a_type in store:
        filename = folder + '/' + a_type + '.json'
        with open(filename, 'w') as outfile:
            json.dump(store[a_type], outfile, indent=4)
