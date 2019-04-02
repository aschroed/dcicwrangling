from dcicutils import ff_utils
from uuid import UUID
import os
import json
import xlrd
import xlwt


def get_key(keyname=None, keyfile='keypairs.json'):
    """get the key from your keypairs.json file
    if no keyname is given, use default key,
    but ask before moving on, if keyfile is given,
    keyname is a must"""
    # is there a different keyfile?
    if keyfile != 'keypairs.json':
        if not keyname:
            raise Exception('please provide keyname')
        if keyfile.startswith('~'):
            keyfile = os.path.expanduser("~") + keyfile[1:]
        with open(keyfile, 'r') as key_file:
            keys = key_file.read()
        my_key = json.loads(keys)[keyname]
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


def append_items_to_xls(input_xls, add_items, schema_name, comment=True):
    output_file_name = "_with_items.".join(input_xls.split('.'))
    # if xlsx, change to xls, can not store xlsx properly
    output_file_name = output_file_name.replace(".xlsx", ".xls")
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
        # exception for microscopy paths
        if sheet == 'ExperimentMic_Path':
            items_to_add = add_items.get(schema_name['ExperimentMic'])
        else:
            items_to_add = add_items.get(schema_name[sheet])
        if items_to_add:
            formatted_items = format_items(items_to_add, first_row_values, comment)
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


def format_items(items_list, field_list, comment):
    """For a given sheet, get all released items"""
    all_items = []
    # filter for fields that exist on the excel sheet
    for item in items_list:

        print_info = False
        if 'imaging_paths' in item:
            print_info = True

        item_info = []
        for field in field_list:
            write_value = ''
            # required fields will have a star
            field = field.strip('*')
            # add # to skip existing items during submission
            if field == "#Field Name:":
                if comment:
                    item_info.append("#")
                else:
                    item_info.append("")
            # the attachment field returns a dictionary
            elif field == "attachment":
                item_info.append("")
            else:
                # add sub-embedded objects
                # 1) only add if the field is not enumerated
                # 2) only add the first item if there are multiple
                # if you want to add more, accumulate all key value pairs in a single dictionary
                # [{main.sub1:a, main.sub2:b ,main.sub1-1:c, main.sub2-1:d,}]
                # and prepare the excel with these fields
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
    # md5 qualifies as uuid, not strictly uuid4: modify
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


def dump_results_to_json(store, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    for a_type in store:
        filename = folder + '/' + a_type + '.json'
        with open(filename, 'w') as outfile:
            json.dump(store[a_type], outfile, indent=4)


def printTable(myDict, colList=None):
    """ Pretty print a list of dictionaries Author: Thierry Husson"""
    if not colList:
        colList = list(myDict[0].keys() if myDict else [])
    myList = [colList]  # 1st row = header
    for item in myDict:
        myList.append([str(item[col] or '') for col in colList])
    colSize = [max(map(len, col)) for col in zip(*myList)]
    formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
    myList.insert(1, ['-' * i for i in colSize])  # Seperating line
    for item in myList:
        print(formatStr.format(*item))


def clean_for_reupload(file_acc, key, clean_release_dates=False, delete_runs=True):
    """Rare cases we want to reupload the file, and this needs some cleanupself.
    If you want to delete release dates too, set 'clean_release_dates' to True"""
    resp = ff_utils.get_metadata(file_acc, key=key)
    clean_fields = ['extra_files', 'md5sum', 'content_md5sum', 'file_size', 'filename', 'quality_metric']
    if clean_release_dates:
        clean_fields.extend(['public_release', 'project_release'])
    if delete_runs:
        runs = resp.get('workflow_run_inputs', [])
        if runs:
            for a_run in runs:
                ff_utils.patch_metadata({'status': 'deleted'}, obj_id=a_run['uuid'], key=key)
    if resp.get('quality_metric'):
        ff_utils.patch_metadata({'status': 'deleted'}, obj_id=resp['quality_metric']['uuid'], key=key)
    del_f = []
    for field in clean_fields:
        if field in resp:
            del_f.append(field)
    del_add_on = 'delete_fields=' + ','.join(del_f)
    ff_utils.patch_metadata({'status': 'uploading'}, obj_id=resp['uuid'], key=key, add_on=del_add_on)


# get order from loadxl.py in fourfront
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
