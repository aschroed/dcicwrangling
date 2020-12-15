'''
Common functions for GEO Minimization of the JSON objects
'''


def same(value):
    return value


def boildown_title(any_object):
    '''get display_title'''
    return any_object['display_title']


def boildown_list_to_titles(list_of_objects):
    '''get comma-separated list of display_title'''
    return ', '.join([boildown_title(entry) for entry in list_of_objects])


def boildown_exp_display_title(display_title):
    '''shorten experiment display title if longer than 120, keeping accession at the end'''
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
            'biological_replicate_number': replicate['bio_rep_no'],
            'technical_replicate_number': replicate['tec_rep_no']
        })
    return output_list


def boildown_publication(publication):
    '''from publication embedded in ExpSet
    return PMID if available, else return display_title'''
    if publication['ID'].split(':')[0] == 'PMID':
        return publication['ID'].split(':')[1]
    else:
        return boildown_title(publication)


# def boildown_data_usage(static_headers):
#     text = ''
#     for header in static_headers:
#         if header['uuid'] == "621e8359-3885-40ce-965d-91894aa7b758":
#             text = header['content']
#     return text


def boildown_experiments_in_set(experiments_in_set):
    '''extract minimal info from the first experiment in an ExpSet
    This includes experiment type and organism'''
    output_dict = {}
    experiment = experiments_in_set[0]
    output_dict['experiment_type'] = get_experiment_type(experiment)
    output_dict['organism_id'] = get_organism_from_experiment(experiment)
    return output_dict


def get_experiment_type(experiment):
    '''get exp_type from experiment'''
    exp_type = experiment['experiment_type']
#     if exp_type.get('assay_subclass_short'):
#         return exp_type['assay_subclass_short']
#     else:
    return boildown_title(exp_type)


def get_organism_from_experiment(experiment):
    '''extract organism from experiment'''
    if len(experiment['biosample']['biosource']) > 1:
        return 'WARNING - multiple biosources'
    else:
        biosource = experiment['biosample']['biosource'][0]
    # organism = get_organism_id(biosource['individual'])
    organism = biosource['individual']['organism']['display_title']
    return organism


def get_organism_id(individual):
    '''NCBI Taxon ID is the second part of an Organism @id'''
    return individual['organism']['@id'].split('/')[2]


# for Experiment
def boildown_exp_categorizer(exp_categorizer_object):
    output = exp_categorizer_object.get('combined', '')
    return output


# def minimize_biosample(biosample_object):
#     '''embedded in Experiment'''
#     return biosample_object['biosource_summary'] + ' - ' + biosample_object['accession']


def boildown_biosample_quantity(biosample_quantity, biosample_quantity_units):
    if biosample_quantity_units == 'cells':
        quantity = str(int(biosample_quantity))
    else:
        quantity = str(biosample_quantity)
    return quantity + ' ' + biosample_quantity_units


def boildown_tissue_organ_info(tissue_organ_info):
    # only extract tissue, ignoring organ_system terms
    # this calc prop searches tissue in different places and also deals with mixed tissues
    return {'tissue_source': tissue_organ_info.get('tissue_source')}


# def boildown_sop_cell_line(biosource_id):
#     '''This field is not embedded, so need to GET Biosource'''
#     biosource = ff_utils.get_metadata(biosource_id, key=auth)
#     protocol_dict = {}
#     if biosource.get('SOP_cell_line'):
#         protocol_dict = boildown_protocol(biosource['SOP_cell_line'])
#     return protocol_dict

def boildown_related_files(related_files):
    # keep only "paired with" relationships
    relations = []
    for file in related_files:
        if file['relationship_type'] == "paired with":
            relations.append(file['file']['accession'])
#             relations.append(file['relationship_type'] + " " + file['file']['accession'])
    return ', '.join(relations)
