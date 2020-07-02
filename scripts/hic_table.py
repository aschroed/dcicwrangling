#!/usr/bin/env python3

import sys
import argparse
import json
from dcicutils import ff_utils
from pathlib import Path
from dcicwrangling.functions import script_utils as scu


description = '''
Script for generating the static sections displayed in the hic-data-overview page.

It fetches Hi-C experiment sets from the portal and prepares the html tables.
The information for grouping datasets is written in files/dsg.json and needs to be updated manually.

Structure of the json file:
"<dataset group name>": {
    (optional) "datasets": ["<dataset_1 name>", "<dataset_n name>"],
    (optional) "study": "<study name>",
    "study_group": "<study group name>"
}

Dataset group (dsg): a row in the html table. Can be one or more datasets.
Datasets: can be omitted if just one in the dsg. In this case, write dataset name in place of dsg name.
Study: can be the same for multiple dsgs, e.g. "Neural Differentiation".
Study group: a static section ["Single Time Point and Condition", "Time Course", "Disrupted or Atypical Cells"].

'''


def get_args():
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--key',
                        default='default',
                        help="The keypair identifier from the keyfile.  \
                        Default is --key=default")
    parser.add_argument('--keyfile',
                        default=Path("~/keypairs.json").expanduser(),
                        help="The keypair file. Default is --keyfile={}".format(
                            Path("~/keypairs.json").expanduser()))
    args = parser.parse_args()
    if args.key and args.keyfile:
        args.key = scu.find_keyname_in_keyfile(args.key, args.keyfile)
    return args


def make_publication_table(publications):
    '''Make a table of publications from publication search
    '''
    journal_mapping = {
        "Science (New York, N.Y.)": "Science",
        "Genome biology": "Genome Biology",
        "Nature biotechnology": "Nature Biotech.",
        "Nature genetics": "Nature Gen.",
        "Nature communications": "Nature Comm.",
        "Proceedings of the National Academy of Sciences of the United States of America": "PNAS",
        "The Journal of biological chemistry": "JBC",
        "bioRxiv": "bioRxiv",
        "Cell": "Cell",
        "The EMBO journal": "EMBO journal",
        "Nature": "Nature",
        "The Journal of cell biology": "JCB",
        'Nature cell biology': "Nature Cell Bio.",
        'Molecular cell': "Mol. Cell ",
    }

    publications_table = {}
    for pub in publications:
        row_pub = {}
        try:
            row_pub["pub_journal"] = journal_mapping[pub["journal"]]
        except KeyError:
            row_pub["pub_journal"] = pub["journal"]
            print('WARNING: Journal {} missing from journal mapping! Using full name instead'.format(pub["journal"]))
        row_pub["pub_auth"] = pub["short_attribution"]
        row_pub["pub_title"] = pub["title"]
        row_pub["pub_url"] = pub["url"]
        publications_table[pub['@id']] = row_pub

    return publications_table


def make_table_row(row, expset, dsg, dsg_link, table_pub, dsg_map):
    '''Translate metadata from expset to a row in the table.
    Row is provided as input and is updated with the given expset information.
    '''
    row["Data Set"] = {"text": dsg, "link": dsg_link}

    row["Project"] = row.get("Project", set())
    row["Project"].add(expset["award"]["project"])

    exp_type = expset["experiments_in_set"][0]["experiment_type"]["display_title"]
    row["Replicate Sets"] = row.get("Replicate Sets", dict())
    row["Replicate Sets"][exp_type] = row["Replicate Sets"].get(exp_type, 0) + 1

    biosample = expset["experiments_in_set"][0]["biosample"]
    row["Species"] = row.get("Species", set())
    row["Species"].add(biosample["biosource"][0]["individual"]["organism"]["name"])

    biosource = biosample["biosource_summary"]
    cell_line = biosample["biosource"][0].get("cell_line")
    if cell_line is not None:
        biosource = cell_line["display_title"]
    row["Biosources"] = row.get("Biosources", set())
    row["Biosources"].add(biosource)

    pub = expset.get("produced_in_pub")
    if pub is not None:
        pub_id = pub["@id"]
        pub = [{"text": table_pub[pub_id]["pub_auth"],
                "link": pub_id},
               {"text": "(" + table_pub[pub_id]["pub_journal"] + ")",
                "link": table_pub[pub_id]["pub_url"]}]
        if row.get("Publication") is None:
            row["Publication"] = pub
        else:
            previous_pubs = [i["text"] for i in row["Publication"]]
            if pub[0]["text"] not in previous_pubs:
                row["Publication"].extend(pub)

    row["Study"] = dsg_map.get("study")

    row["Class"] = dsg_map.get("study_group")

    row["Lab"] = row.get("Lab", set())
    row["Lab"].add(expset["lab"]["display_title"])

    return row


def md_cell_maker(item):
    '''Builds a markdown cell
    '''
    outstr = ""
    if isinstance(item, str):
        outstr = item

    if isinstance(item, set):
        outstr = "<br>".join(item)

    if isinstance(item, list):
        for i in item:
            outstr += md_cell_maker(i) + "<br>"
        if len(item) > 0:
            outstr = outstr[:-4]

    if isinstance(item, dict):
        if item.get("link") is None:
            print("dictionaries in the table should have link fields!!")
        outstr = "[{}]({})".format(item.get("text"), item.get("link"))

    if not isinstance(outstr, str):
        print("type(outstr) = " + str(type(outstr)))

    return outstr


def md_table_maker(rows, keys):
    '''Builds a markdown table'''

    header = "|"
    separator = "|"
    for key in keys:
        header += key + "|"
        separator += "---|"
    header += "\n"
    separator += "\n"

    content = ""
    for row in rows.values():
        row_str = "|"
        for key in keys:
            row_str += md_cell_maker(row.get(key)) + "|"
        row_str += "\n"
        content += row_str

    return(header + separator + content)


def jsx_table(rows, keys, styles, name):
    '''Makes md table and converts it to jsx'''
    table_md = md_table_maker(rows, keys)
    column_width = ""
    for key in keys:
        style = styles.get(key, "120")
        column_width += style + ","

    table_jsx = ("<MdSortableTable\n" +
                 " key=" + name.lower().replace(" ", "-") + "\n" +
                 " defaultColWidths={[" + column_width.rstrip(",") + "]}\n" +
                 ">{' \\\n")
    table_jsx += table_md.replace("'", "\'").replace("\n", " \\\n")
    table_jsx += table_md
    table_jsx += "'}</MdSortableTable>"

    return table_jsx


def main():

    # getting authentication keys
    args = get_args()
    try:
        auth = ff_utils.get_authentication_with_server(args.key)
    except Exception as e:
        print("Authentication failed", e)
        sys.exit(1)

    # collecting publication and expset search results
    hic_types = ['in+situ+Hi-C', 'Dilution+Hi-C', 'DNase+Hi-C', 'Micro-C', 'TCC']
    query_pub = '/search/?type=Publication'
    query_exp = '/search/?type=ExperimentSetReplicate&status=released'
    for type in hic_types:
        query_pub += '&exp_sets_prod_in_pub.experiments_in_set.experiment_type.display_title=' + type
        query_exp += '&experiments_in_set.experiment_type.display_title=' + type
    pubs_search = ff_utils.search_metadata(query_pub, key=auth)
    expsets_search = ff_utils.search_metadata(query_exp, key=auth)

    # building table of publications
    table_pub = make_publication_table(pubs_search)

    # loading dataset groups from json file
    repo_path = Path(__file__).resolve().parents[1]
    dsgs_fn = repo_path.joinpath('files', 'dsg.json')
    if dsgs_fn.exists():
        with open(dsgs_fn) as dsgs_f:
            dsgs = json.load(dsgs_f)
    else:
        sys.exit("ERROR: Dataset grouping file not found")

    # making dataset list and mapping to dataset group
    dataset_list = []
    datasets_of_dsg = {}
    for k, v in dsgs.items():
        if v.get("datasets"):
            dataset_list.extend(v["datasets"])
            datasets_of_dsg[k] = v["datasets"]
        else:
            # if a dsg does not have datasets, then the dsg itself is the dataset
            dataset_list.append(k)

    # building the output table
    table = {}
    new_datasets = set()
    study_groups = set()

    for expset in expsets_search:
        dataset = expset.get("dataset_label")
        if dataset not in dataset_list:
            new_datasets.add(dataset)
            continue

        dsg = dataset
        dsg_link = "/browse/?dataset_label=" + dataset
        for group, elements in datasets_of_dsg.items():
            if dataset in elements:
                dsg_link = ("/browse/?dataset_label=" + "&dataset_label=".join(elements))
                dsg = group
                break
        dsg_link = dsg_link.replace("+", "%2B").replace("/", "%2F").replace(" ", "+")

        study_groups.add(dsgs[dsg].get("study_group"))

        row = table.get(dsg, {})
        table[dsg] = make_table_row(row, expset, dsg, dsg_link, table_pub, dsgs[dsg])

    # summarize number of experiment sets of each experiment type in a string
    for dsg, row in table.items():
        exp_type_summary = ""
        for exp_type, count in row["Replicate Sets"].items():
            if count > 0:
                exp_type_summary += str(count) + " " + exp_type + "<br>"
        row['Replicate Sets'] = exp_type_summary

    # new datasets found
    if new_datasets:
        print("New datasets found (not present in the json file):\n{}".format(new_datasets))
        print("(i)gnore datasets or (e)xit to manually add them? [i/e]")
        response = None
        while response not in ['i', 'e']:
            response = input()
        if response == 'e':
            sys.exit("Add new dataset to dsg.json before generating table")

    # patch the static section for each study group
    for studygroup in list(study_groups):

        # prepare static section
        table_dsg = {}
        for dsg in dsgs:
            if table.get(dsg):
                if table[dsg].get("Class") != studygroup:
                    continue
                else:
                    table_dsg[dsg] = table.get(dsg)

        keys = ['Data Set', 'Project', 'Replicate Sets', 'Species', 'Biosources', 'Publication', 'Study', 'Lab']
        if studygroup == "Single Time Point and Condition":
            keys.remove('Study')
        styles = {
            'Data Set': '250',
            'Project': '90',
            'Replicate Sets': '150',
            'Species': '90',
            'Biosources': '150',
            'Publication': '180'
        }
        jsx = jsx_table(table_dsg, keys, styles, studygroup)

        name = "data-highlights.hic." + studygroup
        name = name.lower().replace(" ", "-")
        alias = "4dn-dcic-lab:" + name

        # check if static section exists
        post = False
        try:
            ff_utils.get_metadata(alias, auth)
        except Exception:
            print("'{}' static section cannot be patched because it does not exist".format(studygroup))
            print("Do you want to (p)ost or (s)kip this static section? [p/s]")
            response = None
            while response not in ['p', 's']:
                response = input()
            if response == 's':
                continue
            else:
                post = True
                print('Remember to add the static section {} to the hic-data-overview page'.format(alias))
                input('Press any key to continue')

        # post or patch static section
        if post:
            post_body = {
                "name": name,
                "aliases": [alias],
                "body": jsx,
                "section_type": "Page Section",
                "title": studygroup,
                "options": {
                    "collapsible": True,
                    "default_open": True,
                    "filetype": "jsx"
                }
            }
            res = ff_utils.post_metadata(post_body, "StaticSection", key=auth)
        else:
            patch_body = {"body": jsx, "title": studygroup}
            res = ff_utils.patch_metadata(patch_body, alias, key=auth)
        print("{}: {}".format(studygroup, res['status']))


if __name__ == '__main__':  # pragma: no cover
    main()
