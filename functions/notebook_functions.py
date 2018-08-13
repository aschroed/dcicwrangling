from dcicutils import ff_utils
from uuid import UUID
import copy
import os
import json
import xlrd
import xlwt
from datetime import datetime


def get_key(keyname=None, keyfile='keypairs.json'):
    """get the key from your keypairs.json file
    if no keyname is given, use default key,
    but ask before moving on, if keyfile is given,
    keyname is a must"""
    # is there a different keyfile?
    if keyfile != 'keypairs.json':
        if not keyname:
            raise Exception('please provide keyname')
            keys = open(keyfile, 'r').read()
            my_key = json.loads(keys)['keyname']
    else:
        home_dir = os.path.expanduser("~") + "/"
        key_file = home_dir + keyfile
        keys = open(key_file, 'r').read()
        if not keyname:
            my_key = json.loads(keys)['default']
            print(my_key['server'])
            go_on = input("Using the 'default' key? (Y/N)")
            if go_on.lower() in ['y', 'yes']:
                pass
            else:
                raise Exception('please provide your keyname parameter')
        else:
            my_key = json.loads(keys)[keyname]
    return my_key


def get_query_or_linked(con_key, query="", linked=""):
    schema_name = get_schema_names(con_key)
    if query:
        items = ff_utils.search_metadata(query, key=con_key)
        store = {}
        # make a object type dictionary with raw jsons
        for an_item in items:
            obj_type = an_item['@type'][0]
            obj_key = schema_name[obj_type]
            if obj_key not in store:
                store[obj_key] = []
            store[obj_key].append(an_item)
    elif linked:
        store, uuids = record_object_es(linked, con_key, schema_name, store_frame='object')
    return store


def append_items_to_xls(input_xls, add_items, schema_name):
    output_file_name = "_with_items.".join(input_xls.split('.'))
    bookread = xlrd.open_workbook(input_xls)
    book_w = xlwt.Workbook()
    Sheets_read = bookread.sheet_names()

    # text styling for all columns
    style = xlwt.XFStyle()
    style.num_format_str = "@"

    for sheet in Sheets_read:
        active_sheet = bookread.sheet_by_name(sheet)
        first_row_values = active_sheet.row_values(rowx=0)

        # create a new sheet and write the data
        new_sheet = book_w.add_sheet(sheet)
        for write_row_index, write_item in enumerate(first_row_values):
            read_col_ind = first_row_values.index(write_item)
            column_val = active_sheet.col_values(read_col_ind)
            for write_column_index, cell_value in enumerate(column_val):
                new_sheet.write(write_column_index, write_row_index, cell_value, style)

        # get items to add
        items_to_add = add_items.get(schema_name[sheet])
        if items_to_add:
            formatted_items = format_items(items_to_add, first_row_values)
            for i, item in enumerate(formatted_items):
                for ix in range(len(first_row_values)):
                    write_column_index_II = write_column_index + 1 + i
                    new_sheet.write(write_column_index_II, ix, str(item[ix]), style)
        else:
            write_column_index_II = write_column_index

        # write 100 empty lines with text formatting
        for i in range(100):
            for ix in range(len(first_row_values)):
                write_column_index_III = write_column_index_II + 1 + i
                new_sheet.write(write_column_index_III, ix, '', style)
    book_w.save(output_file_name)
    print('new excel is stored as', output_file_name)
    return


def format_items(items_list, field_list):
    """For a given sheet, get all released items"""
    all_items = []
    # filter for fields that exist on the excel sheet
    for item in items_list:
        item_info = []
        for field in field_list:
            # required fields will have a star
            field = field.strip('*')
            # add # to skip existing items during submission
            if field == "#Field Name:":
                item_info.append("#")
            # the attachment field returns a dictionary
            elif field == "attachment":
                    item_info.append("")
            else:
                # add sub-embedded objects
                # 1) only add if the field is not enumerated
                # 2) only add the first item if there are multiple
                # any other option becomes confusing
                if "." in field:
                    main_field, sub_field = field.split('.')
                    temp_value = item.get(main_field)
                    if temp_value:
                        write_value = temp_value[0].get(sub_field, '')
                # usual cases
                else:
                    write_value = item.get(field, '')

                # take care of empty lists
                if not write_value:
                    write_value = ''

                # check for linked items
                if isinstance(write_value, dict):
                    write_value = write_value.get('@id')

                # when writing values, check for the lists and turn them into string
                if isinstance(write_value, list):
                    # check for linked items
                    if isinstance(write_value[0], dict):
                        write_value = [i.get('@id') for i in write_value]
                    write_value = ','.join(write_value)
                item_info.append(write_value)
        all_items.append(item_info)
    return all_items


def is_uuid(value):
    #md5 qualifies as uuid
    if '-' not in value:
        return False
    try:
        UUID(value, version=4)
        return True
    except:  # noqa
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


def remove_keys(my_dict, remove_list):
    if remove_list:
        for a_ig_f in remove_list:
            if a_ig_f in my_dict.keys():
                del my_dict[a_ig_f]
    return my_dict


def record_object(uuid, con_key, schema_name, store_frame='raw',
                  add_pc_wfr=False, store={}, item_uuids=[], ignore_field=[]):
    """starting from a single uuid, tracks all linked items,
    keeps a list of uuids, and dictionary of items for each schema in the given store_frame"""
    #keep list of fields that only exist in frame embedded (revlinks) that you want connected
    if add_pc_wfr:
        add_from_embedded = {'file_fastq': ['workflow_run_inputs', 'workflow_run_outputs'],
                             'file_processed': ['workflow_run_inputs', 'workflow_run_outputs']
                             }
    else:
        add_from_embedded = {}

    #find schema name, store as obj_key, create empty list if missing in store
    object_resp = ff_utils.get_metadata(uuid, key=con_key, add_on='frame=object')
    object_resp = remove_keys(object_resp, ignore_field)

    obj_type = object_resp['@type'][0]
    try:
        obj_key = schema_name[obj_type]
    except:  # noqa
        print('CAN NOT FIND', obj_type, uuid)
        return store, item_uuids
    if obj_key not in store:
        store[obj_key] = []

    raw_resp = ff_utils.get_metadata(uuid, key=con_key, add_on='frame=raw')
    raw_resp = remove_keys(raw_resp, ignore_field)

    # if resp['status'] not in ['current', 'released']:
    #     print(obj_key, uuid, resp['status'])

    # add raw frame to store and uuid to list
    if uuid not in item_uuids:
        if store_frame == 'object':
            store[obj_key].append(object_resp)
        else:
            store[obj_key].append(raw_resp)
        item_uuids.append(uuid)
    # this case should not happen actually
    else:
        return store, item_uuids

    fields_to_check = copy.deepcopy(raw_resp)

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
        if key in ['uuid', 'blob_id', "attachment", "sbg_task_id"]:
            continue
        uuid_in_val = find_uuids(value)

        for a_uuid in uuid_in_val:
            if a_uuid not in item_uuids:
                store, item_uuids = record_object(a_uuid, con_key, schema_name, store_frame, add_pc_wfr, store, item_uuids)
    return store, item_uuids


def record_object_es(uuid_list, con_key, schema_name, store_frame='raw', add_pc_wfr=False, ignore_field=[]):
    """starting from a single uuid, tracks all linked items,
    keeps a list of uuids, and dictionary of items for each schema in the given store_frame"""
    #keep list of fields that only exist in frame embedded (revlinks) that you want connected
    if add_pc_wfr:
        add_from_embedded = {'file_fastq': ['workflow_run_inputs', 'workflow_run_outputs'],
                             'file_processed': ['workflow_run_inputs', 'workflow_run_outputs']
                             }
    else:
        add_from_embedded = {}
    store = {}
    item_uuids = []
    while uuid_list:
        # chunk the requests - don't want to hurt es performance
        chunk = 100
        #find schema name, store as obj_key, create empty list if missing in store
        chunked_uuids = [uuid_list[i:i + chunk] for i in range(0, len(uuid_list), chunk)]
        all_responses = []
        for a_chunk in chunked_uuids:
            all_responses.extend(ff_utils.get_es_metadata(a_chunk, key=con_key))
        uuids_to_check = []
        for ES_item in all_responses:
            uuid = ES_item['uuid']
            object_resp = ES_item['object']
            object_resp = remove_keys(object_resp, ignore_field)

            obj_type = object_resp['@type'][0]
            obj_key = schema_name[obj_type]
            if obj_key not in store:
                store[obj_key] = []
            raw_resp = ES_item['properties']
            raw_resp = remove_keys(raw_resp, ignore_field)
            raw_resp['uuid'] = uuid
            # add raw frame to store and uuid to list
            if uuid not in item_uuids:
                if store_frame == 'object':
                    store[obj_key].append(object_resp)
                else:
                    store[obj_key].append(raw_resp)
                item_uuids.append(uuid)
            # this case should not happen actually
            else:
                print('Problem encountered - skipped - check')
                continue

            #get linked items from es
            for key in ES_item['links']:
                # if link is from ignored_field, skip
                if key in ignore_field:
                    continue
                uuids_to_check.extend(ES_item['links'][key])

            # check if any field from the embedded frame is required
            add_fields = add_from_embedded.get(obj_key)
            if add_fields:
                emb_resp = ES_item['embedded']
                for a_field in add_fields:
                    field_val = emb_resp.get(a_field)
                    if field_val:
                        #turn it into string
                        field_val = str(field_val)
                        # check if any of embedded uuids is in the field value
                        for a_uuid in ES_item['embedded_uuids']:
                            if a_uuid in field_val:
                                uuids_to_check.append(a_uuid)
        # get uniques
        uuids_to_check = list(set(uuids_to_check))
        uuid_list = []
        for an_uuid in uuids_to_check:
            if an_uuid not in item_uuids:
                uuid_list.append(an_uuid)
    return store, item_uuids


def dump_results_to_json(store, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    for a_type in store:
        filename = folder + '/' + a_type + '.json'
        with open(filename, 'w') as outfile:
            json.dump(store[a_type], outfile, indent=4)


def get_wfr_report(wfrs, con_key):
    # for a given list of wfrs, produce a simpler report
    wfr_report = []
    for wfr_data in wfrs:
        wfr_rep = {}
        """For a given workflow_run item, grabs details, uuid, run_status, wfr name, date, and run time"""
        wfr_uuid = wfr_data['uuid']
        wfr_data = ff_utils.get_metadata(wfr_uuid, key=con_key)
        wfr_status = wfr_data['run_status']
        try:
            wfr_name = wfr_data['title'].split(' run ')[0].strip()
        except:  # noqa
            print('ProblematicCase')
            print(wfr_data['uuid'], wfr_data.get('display_title', 'no title'))
            continue
        wfr_time = datetime.strptime(wfr_data['date_created'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
        run_hours = (datetime.utcnow() - wfr_time).total_seconds() / 3600
        wfr_name_list = wfr_data['title'].split(' run ')[0].split('/')
        wfr_name = wfr_name_list[0].strip()
        try:
            wfr_rev = wfr_name_list[1].strip()
        except:  # noqa
            wfr_rev = "0"
        output_files = wfr_data.get('output_files', None)
        output_uuids = []
        if output_files:
            for i in output_files:
                if i.get('value', None):
                    output_uuids.append(i['value']['uuid'])

        wfr_rep = {'wfr_uuid': wfr_data['uuid'],
                   'wfr_status': wfr_data['run_status'],
                   'wfr_name': wfr_name,
                   'wfr_rev': wfr_rev,
                   'wfr_date': wfr_time,
                   'run_time': run_hours,
                   'status': wfr_status,
                   'outputs': output_uuids}
        wfr_report.append(wfr_rep)
    wfr_report = sorted(wfr_report, key=lambda k: (k['wfr_date'], k['wfr_name']))
    return wfr_report


def printTable(myDict, colList=None):
    """ Pretty print a list of dictionaries Author: Thierry Husson"""
    if not colList:
        colList = list(myDict[0].keys() if myDict else [])
    myList = [colList] # 1st row = header
    for item in myDict:
        myList.append([str(item[col] or '') for col in colList])
    colSize = [max(map(len, col)) for col in zip(*myList)]
    formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
    myList.insert(1, ['-' * i for i in colSize]) # Seperating line
    for item in myList:
        print(formatStr.format(*item))


# get order from loadxl.py in fourfront
ORDER = ['user', 'award', 'lab', 'static_section', 'page', 'ontology', 'ontology_term', 'badge', 'organism',
         'genomic_region', 'target', 'imaging_path', 'publication', 'publication_tracking', 'document',
         'image', 'vendor', 'construct', 'modification', 'protocol', 'sop_map', 'biosample_cell_culture',
         'individual_human', 'individual_mouse', 'individual_fly', 'biosource', 'antibody', 'enzyme', 'treatment_rnai',
         'treatment_agent', 'biosample',
         'quality_metric_fastqc', 'quality_metric_bamqc', 'quality_metric_pairsqc', 'quality_metric_dedupqc_repliseq',
         'microscope_setting_d1', 'microscope_setting_d2', 'microscope_setting_a1', 'microscope_setting_a2',
         'file_fastq', 'file_fasta', 'file_processed', 'file_reference', 'file_calibration',
         'file_microscopy', 'file_set', 'file_set_calibration', 'file_set_microscope_qc',
         'experiment_hi_c', 'experiment_capture_c', 'experiment_repliseq', 'experiment_atacseq', 'experiment_chiapet',
         'experiment_damid', 'experiment_seq', 'experiment_tsaseq', 'experiment_mic',
         'experiment_set', 'experiment_set_replicate',
         'data_release_update', 'software', 'analysis_step',
         'workflow', 'workflow_mapping', 'workflow_run_sbg', 'workflow_run_awsem']
