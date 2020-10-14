#!/usr/bin/env python3

import sys
import argparse
import json
from dcicutils import ff_utils
from pathlib import Path
from functions import script_utils as scu


description = '''
Script for generating the static sections displayed in the hic-data-overview page.

It fetches Hi-C experiment sets from the portal and prepares the html tables.
The information for grouping datasets is written in files/dsg.json and needs to
be updated manually.

Structure of the json file:
"<dataset group name>": {
    (optional) "datasets": ["<dataset_1 name>", "<dataset_n name>"],
    (optional) "study": "<study name>",
    "study_group": "<study group name>"
}

Dataset group (dsg): a row in the html table. Can be one or more datasets.
Datasets: can be omitted if just one in the dsg. In this case, write dataset
name in place of dsg name.
Study: can be the same for multiple dsgs, e.g. "Neural Differentiation".
Study group: a static section ["Single Time Point and Condition", "Time Course",
"Disrupted or Atypical Cells"].

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
    parser.add_argument('--format',
                        default='html',
                        help="Generated output format: html|markdown. \
                        Default is html")
    parser.add_argument('--dryrun',
                        default=False,
                        action='store_true',
                        help="Run script without posting or patching. \
                        Default is False")
    args = parser.parse_args()
    if args.key and args.keyfile:
        args.key = scu.find_keyname_in_keyfile(args.key, args.keyfile)
    return args


def convert_pubs_list_to_lookup(pubs_search):
    '''
    Converts a list of publications (from a search), to a dictionary with
    publication @ids as keys. The resulting lookup table has short journal
    names and other selected fields (author, title, url).
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
    for pub in pubs_search:
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


def assemble_data_for_the_row(row, expset, dsg, dsg_link, pubs_dict, dsg_map):
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
        pub = [{"text": pubs_dict[pub_id]["pub_auth"],
                "link": pub_id},
               {"text": "(" + pubs_dict[pub_id]["pub_journal"] + ")",
                "link": pubs_dict[pub_id]["pub_url"]}]
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


def html_cell_maker(item):
    '''Builds an html cell'''

    outstr = ""
    if isinstance(item, str):
        outstr = item

    if isinstance(item, set):
        outstr = "<br>".join(item)

    if isinstance(item, list):
        for i in item:
            outstr += html_cell_maker(i) + "<br>"
        if len(item) > 0:
            outstr = outstr[:-4]

    if isinstance(item, dict):
        if item.get("link") is None:
            print("Dictionaries in the table should have link fields!\n{}".format(item))
        outstr = '<a href="' + item.get("link") + '">' + item.get("text") + '</a>'

    if not isinstance(outstr, str):
        print("type(outstr) = " + str(type(outstr)))

    return outstr


def html_table_maker(rows, keys, styles):
    '''Builds html table'''

    part1 = """
    <style>
      table.exp-type-static-table, table.exp-type-static-table th, table.exp-type-static-table td {
        border: 1px solid #ddd;
        font-size: 10.5pt;
      }
      table.exp-type-static-table th, table.exp-type-static-table td {
        text-align: center;   padding: 10px;
      }
      table.exp-type-static-table th {
        color: white;
      }
    </style>
    <table style="width:100%" class="exp-type-static-table">
      <thead>
        <tr>"""

    part2 = ""
    for key in keys:
        style = styles.get(key, "")
        part2 += '\n       <th style="background-color:#00616D' + style + '">' + key + ' </th>'
    part2 += """
        </tr>
      </thead>

    """

    part3 = ""
    for row in rows.values():
        row_str = "  <tr>\n"
        for key in keys:
            row_str += "    <td>" + html_cell_maker(row.get(key)) + "</td>\n"
        row_str += "  </tr>\n"
        part3 += row_str

    part4 = "</table>"

    return(part1 + part2 + part3 + part4)

def md_cell_maker(item):
    '''Builds a markdown cell'''

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
            print("Dictionaries in the table should have link fields!\n{}".format(item))
        outstr = "[{}]({})".format(item.get("text"), item.get("link").replace(")", "%29"))

    if not isinstance(outstr, str):
        print("type(outstr) = " + str(type(outstr)))

    return outstr.replace("'", "\\'")


def md_table_maker(rows, keys, jsx_key, col_widths = "[]"):
    '''Builds markdown table'''

    part1 = """
    <MdSortableTable
        key='{}'
        defaultColWidths={{{}}}
    >{{' \\
    """.format(jsx_key, col_widths)
    
    part2 = ""
    for key in keys:
        part2 += "|" + key
    part2 += "|\\\n" + ("|---" * len(keys)) + "|\\\n"

    part3 = ""
    for row in rows.values():
        row_str = ""
        for key in keys:
            row_str += "|" + md_cell_maker(row.get(key))
        row_str += "|\\\n"
        part3 += row_str

    part4 = "'}</MdSortableTable>"
    
    return (part1 + part2 + part3 + part4)

def main():

    # getting authentication keys
    args = get_args()
    try:
        auth = ff_utils.get_authentication_with_server(args.key)
    except Exception as e:
        print("Authentication failed", e)
        sys.exit(1)

    dryrun = args.dryrun
    if dryrun:
        print("\nThis is a dry run\n")

    # collecting publication and expset search results
    hic_types = ['in+situ+Hi-C', 'Dilution+Hi-C', 'DNase+Hi-C', 'Micro-C', 'TCC']
    query_pub = '/search/?type=Publication'
    query_exp = '/search/?type=ExperimentSetReplicate&status=released'
    for type in hic_types:
        query_pub += '&exp_sets_prod_in_pub.experiments_in_set.experiment_type.display_title=' + type
        query_exp += '&experiments_in_set.experiment_type.display_title=' + type
    pubs_search = ff_utils.search_metadata(query_pub, key=auth)
    expsets_search = ff_utils.search_metadata(query_exp, key=auth)

    # building publications dictionary
    pubs_dict = convert_pubs_list_to_lookup(pubs_search)

    # loading dataset groups from json file
    repo_path = Path(__file__).resolve().parents[1]
    dsg_filename = repo_path.joinpath('files', 'dsg.json')
    if dsg_filename.exists():
        with open(dsg_filename) as dsg_fn:
            dsgs = json.load(dsg_fn)
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
        dsg_link = "dataset_label=" + dataset
        for group, elements in datasets_of_dsg.items():
            if dataset in elements:
                dsg_link = ("dataset_label=" + "&dataset_label=".join(elements))
                dsg = group
                break
        dsg_link = "/browse/?" + dsg_link.replace("+", "%2B").replace("/", "%2F").replace(" ", "+")

        study_groups.add(dsgs[dsg].get("study_group"))

        row = table.get(dsg, {})
        table[dsg] = assemble_data_for_the_row(row, expset, dsg, dsg_link, pubs_dict, dsgs[dsg])

    # summarize number of experiment sets of each experiment type in a string
    for dsg, row in table.items():
        exp_type_summary = ""
        for exp_type, count in row["Replicate Sets"].items():
            if count > 0:
                exp_type_summary += str(count) + " " + exp_type + "<br>"
        if len(exp_type_summary) > 0:
            row['Replicate Sets'] = exp_type_summary[:-4] #remove <br> at the end
        else:
            row['Replicate Sets'] = ""

    # if new datasets are not in the json, ask what to do
    if new_datasets:
        print("New datasets found (not present in the json file):")
        for ds in new_datasets:
            print(ds)
        print("(i)gnore datasets or (e)xit to manually add them? [i/e]")
        response = None
        while response not in ['i', 'e']:
            response = input()
        if response == 'e':
            sys.exit("Add new dataset to dsg.json before generating table")

    # patch the static section for each study group
    skipped = []
    posted = []
    patched = []
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
         
        name = alias = output = filetype = None
        if args.format == 'markdown':
            name = "data-highlights.hic." + studygroup + ".md"
            name = name.lower().replace(" ", "-")
            alias = "4dn-dcic-lab:" + name
            filetype = 'jsx'
            default_col_widths = "[-1,100,-1,100,-1,-1,-1,-1]"
            if "Study" not in keys:
                default_col_widths = "[-1,100,-1,120,250,-1,170]"
            output = md_table_maker(table_dsg, keys, name, default_col_widths)
        else:
            name = "data-highlights.hic." + studygroup
            name = name.lower().replace(" ", "-")
            alias = "4dn-dcic-lab:" + name
            filetype = 'html'
            styles = {
                'Data Set': ";width:20%;min-width:120px",
                'Replicate Sets': ";width:150px",
                'Publication': ";width:200px"
            }
            output = html_table_maker(table_dsg, keys, styles)

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
                skipped.append(alias)
                continue
            else:
                post = True

        # post or patch static section
        if post:
            post_body = {
                "name": name,
                "aliases": [alias],
                "body": output,
                "section_type": "Page Section",
                "title": studygroup,
                "options": {
                    "collapsible": True,
                    "default_open": True,
                    "filetype": filetype
                }
            }
            if not dryrun:
                res = ff_utils.post_metadata(post_body, "StaticSection", key=auth)
            posted.append(alias)
        else:
            patch_body = {"body": output}
            if not dryrun:
                res = ff_utils.patch_metadata(patch_body, alias, key=auth)
            patched.append(alias)
        if not dryrun:
            print("{}: {}".format(alias, res['status']))

    # summarize results
    print("Static sections summary: {} patched, {} posted, {} skipped".format(
        len(patched), len(posted), len(skipped)))
    if posted:
        print("Remember to add the new static section(s) to the hic-data-overview page:")
        for item in posted:
            print(item)
    if skipped:
        print("Skipped sections:")
        for item in skipped:
            print(item)


if __name__ == '__main__':  # pragma: no cover
    main()
