'''
Common functions for GEO Minimization of the JSON objects
'''
URL = 'https://data.4dnucleome.org'


def add_value_to_output_dict(key, value, output_dictionary):
    '''add to the output_dictionary either a single key:value pair or
    all the key:values if value is a dictionary'''
    if isinstance(value, dict):
        for inner_key, inner_value in value.items():
            if inner_value:  # skip if None
                output_dictionary[inner_key] = inner_value
    else:
        if value:  # skip if None
            output_dictionary[key] = value
    return


def boildown_at_id(at_id):
    return {'url': URL + at_id}


def boildown_title(any_object):
    '''get display_title'''
    return any_object['display_title']


def boildown_list_to_titles(list_of_objects):
    '''get comma-separated list of display_title'''
    return ', '.join([boildown_title(entry) for entry in list_of_objects])


def boildown_protocol(protocol_object):
    '''used for both protocol and document items'''
    protocol_dict = {}
    protocol_simple_interesting_values = ['description', 'url']  # 'protocol_type'
    for key in protocol_object:
        if key == 'attachment':
            protocol_dict['download'] = URL + protocol_object['@id'] + protocol_object['attachment']['href']
        elif key in protocol_simple_interesting_values:
            protocol_dict[key] = protocol_object[key]
    return protocol_dict


def boildown_protocols(protocols):
    '''return list of protocols(dictionaries)'''
    return [boildown_protocol(p) for p in protocols]


def boildown_exp_display_title(display_title):
    '''shorten experiment display title if longer than 120,
    keeping accession at the end'''
    if len(display_title) > 120:
        accession = display_title[-15:]
        display_title = display_title[:102] + '...' + accession
    return display_title


def boildown_award(award_object):
    '''get award number, extracted from the @id'''
    return award_object['@id'].split('/')[2]


def boildown_date_modified(date_modified_object):
    '''get date_modified'''
    return date_modified_object['date_modified'].split('T')[0]


def boildown_external_references(external_references_list):
    '''join list of validated dbxrefs (from which this calcprop derives)'''
    refs = []
    for reference in external_references_list:
        # get ref only if 'uri' was calculated correctly
        if reference.get('uri'):
            refs.append(reference['ref'])
    return ', '.join(refs)


# additional functions for ExpSet
def boildown_replicate_exps(replicate_exps):
    '''return list of dict with Exp accession, biorep and techrep'''
    output_list = []
    for replicate in replicate_exps:
        output_list.append({
            'replicate': replicate['replicate_exp']['accession'],
            '@id': replicate['replicate_exp']['@id'],
            'biological_replicate_number': replicate['bio_rep_no'],
            'technical_replicate_number': replicate['tec_rep_no']
        })
    return output_list


def boildown_publication(publication):
    '''returns a dictionary with one key
    produced_in_pub: PMID if present, otherwise series_citation: display_title'''
    if publication['ID'].split(':')[0] == 'PMID':
        pub = {'produced_in_pub': publication['ID'].split(':')[1]}
    else:
        pub = {'series_citation': publication['display_title']}
    return pub


def boildown_experiments_in_set(experiments_in_set):
    '''extract experiment_type from the first experiment in an ExpSet'''
    output_dict = {}
    experiment = experiments_in_set[0]
    output_dict['experiment_type'] = experiment['experiment_type']['display_title']
    # output_dict['organism_id'] = get_organism_from_experiment(experiment)
    return output_dict


# def get_experiment_type(experiment):
#     '''get exp_type from experiment'''
#     exp_type = boildown_title(experiment['experiment_type'])
# #     if exp_type.get('assay_subclass_short'):
# #         return exp_type['assay_subclass_short']
# #     else:
#     return exp_type
#
#
# def get_organism_id(individual):
#     '''NCBI Taxon ID is the second part of an Organism @id'''
#     return individual['organism']['@id'].split('/')[2]
def boildown_organism(organism_object):
    '''Return interesting organism values from organism_object'''
    organism_dict = {}
    organism_dict['organism_name'] = organism_object['scientific_name']
    organism_dict['organism_id'] = organism_object['taxon_id']
    return organism_dict


# for Experiment
def boildown_exp_categorizer(exp_categorizer_object):
    output = exp_categorizer_object.get('combined', '')
    return output


def boildown_biosample_quantity(experiment_object):
    unit = experiment_object.get('biosample_quantity_units', '')
    quantity = experiment_object.get('biosample_quantity', '')
    if unit == 'cells':
        quantity = str(int(quantity))
    else:
        quantity = str(quantity)
    return quantity + ' ' + unit


def boildown_tissue_organ_info(tissue_organ_info):
    # only extract tissue, ignoring organ_system terms
    # this calc prop searches tissue in different places and also deals with mixed tissues
    return {'tissue_source': tissue_organ_info.get('tissue_source')}


def boildown_related_files(related_files):
    # keep only "paired with" relationships
    relations = []
    for file in related_files:
        if file['relationship_type'] == "paired with":
            relations.append(file['file']['accession'])
#             relations.append(file['relationship_type'] + " " + file['file']['accession'])
    return ', '.join(relations)


file_quality_metric_interesting_values = [
    'Sequence length',  # raw_file
    'Total Sequences'
]

file_interesting_values = [
    'paired_end',  # raw_file
    'accession',
    'display_title',  # raw_file
    'file_type',
    # 'file_type_detailed',  # has also file_format['display_title']
    'file_classification',
    'instrument',  # raw_file
    'genome_assembly',
    'md5sum',  # raw_file
    # 'content_md5sum',
]


def boildown_file(file_object):
    file_dictionary = {}
    for key, value in file_object.items():
        if key in file_interesting_values:
            if isinstance(value, list):
                if len(value) > 0:
                    file_dictionary[key] = ', '.join(value)
            else:
                file_dictionary[key] = str(value)
        elif key == 'file_format':  # raw_file
            file_dictionary[key] = boildown_title(value)
        elif key == 'quality_metric':
            for k in value.keys():
                if k in file_quality_metric_interesting_values:
                    file_dictionary[k] = str(value[k])
        elif key == 'related_files':
            file_dictionary[key] = boildown_related_files(value)
        elif key == 'workflow_run_outputs' and len(value) > 0:
            wfr = value[0]  # file derives only from the first wfr in the list
            file_dictionary['workflow_run'] = URL + wfr['@id']
#             file_dictionary['workflow'] = wfr['workflow']['display_title']
            file_dictionary['derived_from'] = ", ".join([
                infile['value']['display_title'] for infile in wfr['input_files']
            ])
    return file_dictionary
