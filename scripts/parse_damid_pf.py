#!/usr/bin/env python3
import sys
import argparse
import xlrd
import datetime
import re
from dcicutils.ff_utils import (
    get_authentication_with_server,
    patch_metadata, search_metadata,
    get_metadata)
from dcicwrangling.functions import script_utils as scu
'''
Parsing damid processed file worksheet to generate the various bins
of other processed files using information from the linked_dataset column
with the expectation that the linked_dataset will be an identifier for the
experiment or replicate set to which the file should be linked.

As the bin used for 'official' processed files - as opposed to supplementary
files can change depending on the target or experiment type (damid vs. pA-damid)
the PF_BIN specifies which bin to use

NOTE: there are variations that can deal with incomplete information - i.e. not
specifying the experiments but just using replicate set ids and then info in aliases
to match up replicates - see Andy if needed
'''

PF_BIN = '5kb bin'  # the bin for which a subset of files should be considered processed_files rather than opfs


def reader(filename, sheetname=None):
    """Read named sheet or first and only sheet from xlsx file.
        from submit4dn import_data"""
    book = xlrd.open_workbook(filename)
    if sheetname is None:
        sheet, = book.sheets()
    else:
        try:
            sheet = book.sheet_by_name(sheetname)
        except xlrd.XLRDError:
            print(sheetname)
            print("ERROR: Can not find the collection sheet in excel file (xlrd error)")
            return
    datemode = sheet.book.datemode
    for index in range(sheet.nrows):
        yield [cell_value(cell, datemode) for cell in sheet.row(index)]


def extract_rows(infile):
    data = []
    row = reader(infile, sheetname='FileProcessed')
    fields = next(row)
    fields = [f.replace('*', '') for f in fields]
    types = next(row)
    fields.pop(0)
    types.pop(0)
    for values in row:
        if values[0].startswith('#'):
            continue
        values.pop(0)
        meta = dict(zip(fields, values))
        data.append(meta)
    return data


def cell_value(cell, datemode):
    """Get cell value from excel.
        from submit4dn import_data"""
    # This should be always returning text format if the excel is generated
    # by the get_field_info command
    ctype = cell.ctype
    value = cell.value
    if ctype == xlrd.XL_CELL_ERROR:  # pragma: no cover
        raise ValueError(repr(cell), 'cell error')
    elif ctype == xlrd.XL_CELL_BOOLEAN:
        return str(value).upper().strip()
    elif ctype == xlrd.XL_CELL_NUMBER:
        if value.is_integer():
            value = int(value)
        return str(value).strip()
    elif ctype == xlrd.XL_CELL_DATE:
        value = xlrd.xldate_as_tuple(value, datemode)
        if value[3:] == (0, 0, 0):
            return datetime.date(*value[:3]).isoformat()
        else:  # pragma: no cover
            return datetime.datetime(*value).isoformat()
    elif ctype in (xlrd.XL_CELL_TEXT, xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return value.strip()
    raise ValueError(repr(cell), 'unknown cell type')  # pragma: no cover


def is_processed_bin(desc, meta):
    ''' Putting bam files and select files in bin specified by PF_BIN into the
        processed file bin this is a specific check for those attributes
    '''
    if 'mapped reads' in desc:
        return True
    if desc.startswith(PF_BIN):
        if (meta.get('file_type') == 'normalized counts' and meta.get('file_format') == 'bw') or (
                meta.get('file_type') == 'LADs' and meta.get('file_format') == 'bed'):
            return True
    return False


def create_patch(item, label, rep=None):
    patch = {}
    if rep:
        label = label + ' ' + rep
    item_pfs = item.get('processed_files')
    item_opfs = item.get('other_processed_files')
    if not (item_pfs or item_opfs):
        print("NO FILES FOR {}".format(item.get('uuid')))
        return
    if item_pfs:
        patch['processed_files'] = item_pfs
    if item_opfs:
        for bin, opfs in item_opfs.items():
            if bin == 'Other':
                opftitle = 'Other files - non-binned'
                opfdesc = 'Non-bin specific files for {}'.format(label)
            elif bin == PF_BIN:
                opftitle = 'Additional {}ned files'.format(bin)
                opfdesc = 'Additional files associated with the {} size processing of data for {}'.format(bin, label)
            else:
                opftitle = '{}ned files'.format(bin)
                opfdesc = 'The files associated with the {} size processing of data for {}'.format(bin, label)
            patch.setdefault('other_processed_files', []).append(
                {'title': opftitle, 'description': opfdesc, 'type': 'supplementary', 'files': opfs})
    return patch


def get_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[scu.create_ff_arg_parser(), scu.create_input_arg_parser()],
    )
    args = parser.parse_args()
    if args.key:
        args.key = scu.convert_key_arg_to_dict(args.key)
    return args


def main():  # pragma: no cover
    # initial set up
    args = get_args(sys.argv[1:])
    try:
        auth = get_authentication_with_server(args.key, args.env)
    except Exception:
        print("Authentication failed")
        sys.exit(1)

    repre = re.compile(r'_r\d+_')
    binre = re.compile(r'^\S+ bin')
    erepnore = re.compile(r'replicate\s\d+')

    # this if for parsing excel but could use fourfront query
    infile = args.input[0]
    query = None
    if len(args.input) > 1:
        query = args.input[1]

    metadata = extract_rows(infile)
    patch_items = {}
    seen_esets = {}  # if you are dealing with an experiment want to use the dataset_label and condition
    # of the replicate set to create the label
    # going row by row to add file to correct spot
    for meta in metadata:
        # checking if we have linked dataset info in sheet - should be either an
        # experiment set or experiment
        linked_dataset_id = meta.get('#linked datasets')
        if not linked_dataset_id:
            print("Can not get dataset_id for {}".format(meta))
            continue
        file_alias = meta.get('aliases')

        # build basic ds for the set
        if linked_dataset_id not in patch_items:
            item = get_metadata(linked_dataset_id, auth)  # either experiment or eset
            euuid = item.get('uuid')
            if not euuid:
                print("Can't get uuid for {} - skipping".format(linked_dataset_id))
                continue
            if 'experiments_in_set' in item:  # we've got an experiment set
                label = item.get('dataset_label') + ' ' + item.get('condition')
            else:  # we've got an experiment
                esets = item.get('experiment_sets')
                if len(esets) != 1:  # some sort of unusual situation
                    raise(Exception, 'experiment linked to multiple experiment sets -- abort!')
                esetid = esets[0].get('uuid')
                if esetid not in seen_esets:
                    eset = get_metadata(esetid, auth)
                    label = eset.get('dataset_label') + ' ' + eset.get('condition')
                    seen_esets[esetid] = label
                else:
                    label = seen_esets[esetid]

            patch_items[linked_dataset_id] = {'uuid': euuid, 'label': label, 'processed_files': [], 'other_processed_files': {}, 'experiments': {}}
        # use description to get replicate number if any and bin size if any
        desc = meta.get('description')

        bin = binre.match(desc)

        if is_processed_bin(desc, meta):
            patch_items[linked_dataset_id]['processed_files'].append(file_alias)
        else:
            if bin:
                bin = bin.group()
            else:
                bin = 'Other'
            patch_items[linked_dataset_id]['other_processed_files'].setdefault(bin, []).append(file_alias)

    patch_data = {}
    for e in patch_items.values():
        label = e.get('label')
        patch = create_patch(e, label)
        if patch:
            euid = e.get('uuid')
            existing_item = get_metadata(euid, auth)
            ipf = existing_item.get('processed_files')
            if ipf:
                if 'processed_files' in patch:
                    patch['processed_files'].extend(ipf)
            opf = existing_item.get('other_processed_files')
            if opf:
                if 'other_processed_files' in patch:
                    patch['other_processed_files'].extend(opf)

            patch_data[e.get('uuid')] = patch

    if patch_data:
        for puuid, pdata in patch_data.items():
            print(puuid, '\n', pdata, '\n\n')
            if args.dbupdate:
                try:
                    res = patch_metadata(pdata, puuid, auth)
                    print(res.get('status'))
                except Exception:
                    print("Can't patch {iid} with\n\t{p}".format(iid=puuid, p=pdata))


if __name__ == '__main__':
    main()
