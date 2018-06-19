# Step Settings
def step_settings(step_name, my_organism, lab):
    """Return a setting dict for given step, and modify variables in
    output files; genome assembly, file_type, desc, contributing lab."""
    genome = ""
    mapper = {'human': 'GRCh38', 'mouse': 'GRCm38'}
    genome = mapper.get(my_organism)

    out_n = "This is an output file of the Hi-C processing pipeline"
    int_n = "This is an intermediate file in the HiC processing pipeline"
    out_n_rep = "This is an output file of the RepliSeq processing pipeline"
    int_n_rep = "This is an intermediate file in the Repliseq processing pipeline"

    wf_dict = [{
        'wf_name': 'md5',
        'wf_uuid': 'd3f25cd3-e726-4b3c-a022-48f844474b41',
        'parameters': {}
        },
        {
        'wf_name': 'fastqc-0-11-4-1',
        'wf_uuid': '2324ad76-ff37-4157-8bcc-3ce72b7dace9',
        'parameters': {}
        },
        {
        'wf_name': 'bwa-mem',
        'wf_uuid': '3feedadc-50f9-4bb4-919b-09a8b731d0cc',
        'parameters': {"nThreads": 16},
        'custom_pf_fields': {
            'out_bam': {
                'genome_assembly': genome,
                'file_type': 'intermediate file',
                'description': int_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'hi-c-processing-bam',
        'wf_uuid': '023bfb3e-9a8b-42b9-a9d4-216079526f68',
        'parameters': {"nthreads_merge": 16, "nthreads_parse_sort": 16},
        'custom_pf_fields': {
            'annotated_bam': {
                'genome_assembly': genome,
                'file_type': 'alignment',
                'description': out_n,
                'contributing_labs': lab},
            'filtered_pairs': {
                'genome_assembly': genome,
                'file_type': 'contact list-replicate',
                'description': out_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'hi-c-processing-pairs',
        'wf_uuid': 'c9e0e6f7-b0ed-4a42-9466-cadc2dd84df0',
        'parameters': {"nthreads": 1, "maxmem": "32g"},
        'custom_pf_fields': {
            'cooler_normvector': {
                'genome_assembly': genome,
                'file_type': 'juicebox norm vector',
                'description': out_n,
                'contributing_labs': lab},
            'hic': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'mcool': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'merged_pairs': {
                'genome_assembly': genome,
                'file_type': 'contact list-combined',
                'description': out_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'hi-c-processing-pairs-nore',
        'wf_uuid': 'c19ee11e-9d5a-454f-af50-600a0cf990b6',
        'parameters': {"nthreads": 1, "maxmem": "32g"},
        'custom_pf_fields': {
            'cooler_normvector': {
                'genome_assembly': genome,
                'file_type': 'juicebox norm vector',
                'description': out_n,
                'contributing_labs': lab},
            'hic': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'mcool': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'merged_pairs': {
                'genome_assembly': genome,
                'file_type': 'contact list-combined',
                'description': out_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'hi-c-processing-pairs-nonorm',
        'wf_uuid': 'bd6e25ea-f368-4758-a821-d30e0b5a4100',
        'parameters': {"nthreads": 1, "maxmem": "32g"},
        'custom_pf_fields': {
            'hic': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'mcool': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'merged_pairs': {
                'genome_assembly': genome,
                'file_type': 'contact list-combined',
                'description': out_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'hi-c-processing-pairs-nore-nonorm',
        'wf_uuid': '05b62bba-7bfa-46cc-8d8e-3d37f4feb8bd',
        'parameters': {"nthreads": 1, "maxmem": "32g"},
        'custom_pf_fields': {
            'hic': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'mcool': {
                'genome_assembly': genome,
                'file_type': 'contact matrix',
                'description': out_n,
                'contributing_labs': lab},
            'merged_pairs': {
                'genome_assembly': genome,
                'file_type': 'contact list-combined',
                'description': out_n,
                'contributing_labs': lab}
        }},
        {
        'wf_name': 'repliseq-parta',
        'wf_uuid': '146da22a-502d-4500-bf57-a7cf0b4b2364',
        "parameters": {"nthreads": 4, "memperthread": "2G"},
        'custom_pf_fields': {
            'filtered_sorted_deduped_bam': {
                'genome_assembly': genome,
                'file_type': 'alignment',
                'description': out_n_rep,
                'contributing_labs': lab},
            'count_bg': {
                'genome_assembly': genome,
                'file_type': 'read counts',
                'description': out_n_rep,
                'contributing_labs': lab}
        }}]
    return [i for i in wf_dict if i['wf_name'] == step_name][0]
