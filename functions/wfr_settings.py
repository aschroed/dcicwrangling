# Step Settings
def step_settings(step_name, my_organism, attribution, params={}):
    """Return a setting dict for given step, and modify variables in
    output files; genome assembly, file_type, desc, contributing lab."""
    genome = ""
    mapper = {'human': 'GRCh38', 'mouse': 'GRCm38', 'fruit-fly': 'dm6', 'chicken': 'galGal5'}
    genome = mapper.get(my_organism)

    out_n = "This is an output file of the Hi-C processing pipeline"
    int_n = "This is an intermediate file in the HiC processing pipeline"
    out_n_rep = "This is an output file of the RepliSeq processing pipeline"
    # int_n_rep = "This is an intermediate file in the Repliseq processing pipeline"

    wf_dict = [
        {
            'wf_name': 'md5',
            'wf_uuid': 'c77a117b-9a58-477e-aaa5-291a109a99f6',
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
                    'description': int_n}
            }
        },
        {
            'wf_name': 'hi-c-processing-bam',
            'wf_uuid': '023bfb3e-9a8b-42b9-a9d4-216079526f68',
            'parameters': {"nthreads_merge": 16, "nthreads_parse_sort": 16},
            'custom_pf_fields': {
                'annotated_bam': {
                    'genome_assembly': genome,
                    'file_type': 'alignment',
                    'description': out_n},
                'filtered_pairs': {
                    'genome_assembly': genome,
                    'file_type': 'contact list-replicate',
                    'description': out_n}
            }
        },
        {
            'wf_name': 'hi-c-processing-pairs',
            'wf_uuid': '4dn-dcic-lab:wf-hi-c-processing-pairs-0.2.7',
            'parameters': {"nthreads": 4,
                           "maxmem": "32g",
                           "max_split_cooler": 10,
                           "no_balance": False
                           },
            'custom_pf_fields': {
                'hic': {
                    'genome_assembly': genome,
                    'file_type': 'contact matrix',
                    'description': out_n},
                'mcool': {
                    'genome_assembly': genome,
                    'file_type': 'contact matrix',
                    'description': out_n},
                'merged_pairs': {
                    'genome_assembly': genome,
                    'file_type': 'contact list-combined',
                    'description': out_n}
            }
        },
        {
            'wf_name': 'repliseq-parta',
            'wf_uuid': '4dn-dcic-lab:wf-repliseq-parta-v16',
            "parameters": {"nthreads": 4, "memperthread": "2G"},
            'custom_pf_fields': {
                'filtered_sorted_deduped_bam': {
                    'genome_assembly': genome,
                    'file_type': 'alignment',
                    'description': out_n_rep},
                'count_bg': {
                    'genome_assembly': genome,
                    'file_type': 'counts',
                    'description': 'read counts per 5 kb bin, unfiltered, unnormalized'}
            }
        },
        {
            "wf_name": "bedGraphToBigWig",
            "wf_uuid": "667b14a7-a47e-4857-adf1-12a6393c4b8e",
            "parameters": {},
            "overwrite_input_extra": False
        },
        {
            "wf_name": "bedtobeddb",
            "wf_uuid": "9d575e99-5ffe-4ea4-b74f-ad40f621cd39",
            "parameters": {},
            "overwrite_input_extra": False
        },
        {
            "wf_name": "encode-chipseq-aln-chip",
            "wf_uuid": "4dn-dcic-lab:wf-encode-chipseq-aln-chip",
            "parameters": {},
            'custom_pf_fields': {
                'chip.first_ta': {
                    'genome_assembly': genome,
                    'file_type': 'read positions',
                    'description': 'Positions of aligned reads in bed format, one line per read mate, for control experiment, from ENCODE ChIP-Seq Pipeline'},
                'chip.first_ta_xcor': {
                    'genome_assembly': genome,
                    'file_type': 'intermediate file',
                    'description': 'Counts file used only for QC'}
            }
        },
        {
            "wf_name": "encode-chipseq-aln-ctl",
            "wf_uuid": "4dn-dcic-lab:wf-encode-chipseq-aln-ctl",
            "parameters": {},
            'custom_pf_fields': {
                'chip.first_ta_ctl': {
                    'genome_assembly': genome,
                    'file_type': 'read positions',
                    'description': 'Positions of aligned reads in bed format, one line per read mate, for control experiment, from ENCODE ChIP-Seq Pipeline'}
            }
        },
        {
            "wf_name": "encode-chipseq-postaln",
            "wf_uuid": "4dn-dcic-lab:wf-encode-chipseq-postaln",
            "parameters": {},
            'custom_pf_fields': {
                'chip.optimal_peak': {
                    'genome_assembly': genome,
                    'file_type': 'peaks',
                    'description': 'Peak calls from ENCODE ChIP-Seq Pipeline'},
                'chip.conservative_peak': {
                    'genome_assembly': genome,
                    'file_type': 'conservative peaks',
                    'description': 'Conservative peak calls from ENCODE ChIP-Seq Pipeline'},
                'chip.sig_fc': {
                    'genome_assembly': genome,
                    'file_type': 'signal fold change',
                    'description': 'ChIP-seq signal fold change over input control'}
            }
        },
        {
            "wf_name": "encode-atacseq-aln",
            "wf_uuid": "4dn-dcic-lab:wf-encode-atacseq-aln",
            "parameters": {},
            'custom_pf_fields': {
                'atac.first_ta': {
                    'genome_assembly': genome,
                    'file_type': 'read positions',
                    'description': 'Positions of aligned reads in bed format, one line per read mate, from ENCODE ATAC-Seq Pipeline'}
            }
        },
        {
            "wf_name": "encode-atacseq-postaln",
            "wf_uuid": "4dn-dcic-lab:wf-encode-atacseq-postaln",
            "parameters": {},
            'custom_pf_fields': {
                'atac.optimal_peak': {
                    'genome_assembly': genome,
                    'file_type': 'peaks',
                    'description': 'Peak calls from ENCODE ATAC-Seq Pipeline'},
                'atac.conservative_peak': {
                    'genome_assembly': genome,
                    'file_type': 'conservative peaks',
                    'description': 'Conservative peak calls from ENCODE ATAC-Seq Pipeline'},
                'atac.sig_fc': {
                    'genome_assembly': genome,
                    'file_type': 'signal fold change',
                    'description': 'ATAC-seq signal fold change'}
            }
        },
        {
            "wf_name": "mergebed",
            "wf_uuid": "2b10e472-065e-43ed-992c-fccad6417b65",
            "parameters": {"sortv": "0"},
            'custom_pf_fields': {
                'merged_bed': {
                    'genome_assembly': genome,
                    'file_type': 'read positions',
                    'description': 'Merged file, positions of aligned reads in bed format, one line per read mate'}
            }
        },
        {
            "wf_name": "merge-fastq",
            "wf_uuid": "e20ef13d-64d8-4d10-94b1-ed45e7d6a7c2",
            "parameters": {},
            'custom_pf_fields': {
                'fastq': {
                    'genome_assembly': genome,
                    'file_type': 'reads',
                    'description': 'Merged fastq file'}
            }
        }
    ]
    # if params, overwrite parameters

    template = [i for i in wf_dict if i['wf_name'] == step_name][0]

    update_config = {
        "ebs_type": "gp2",
        "spot_instance": False,
        "ebs_iops": "",
        "log_bucket": "tibanna-output",
        "key_name": "4dn-encode",
        "public_postrun_json": True,
        "behavior_on_capacity_limit": "retry_without_spot"
    }
    if template.get('config'):
        temp_conf = template['config']
        for a_key in update_config:
            if a_key not in temp_conf:
                temp_conf[a_key] = update_config[a_key]
    else:
        template['config'] = update_config


    if params:
        template['parameters'] = params

    if template.get('custom_pf_fields'):
        for a_file in template['custom_pf_fields']:
            template['custom_pf_fields'][a_file].update(attribution)
    template['wfr_meta'] = attribution
    return template
