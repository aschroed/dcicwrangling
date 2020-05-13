from dcicutils import ff_utils
from datetime import datetime

# accepted workflows
# workflow name, accepted revision numbers (0 if none), accetable run time (hours)
workflow_details = [
    # TODO: take this info from foursight
    # common ones
    ['md5', ['0.0.4', '0.2.6'], 12],
    ['fastqc-0-11-4-1', ['0.2.0'], 50],
    # 4dn ones
    ['bwa-mem', ['0.2.6'], 50],
    ['pairsqc-single', ['0.2.5', '0.2.6'], 100],
    ['hi-c-processing-bam', ['0.2.6'], 50],
    ['hi-c-processing-pairs', ['0.2.6', '0.2.7'], 200],
    ['hi-c-processing-pairs-nore', ['0.2.6'], 200],
    ['hi-c-processing-pairs-nonorm', ['0.2.6'], 200],
    ['hi-c-processing-pairs-nore-nonorm', ['0.2.6'], 200],
    ['imargi-processing-fastq', ["1.1.1_dcic_4"], 200],
    ['imargi-processing-bam', ["1.1.1_dcic_4"], 200],
    ['imargi-processing-pairs', ["1.1.1_dcic_4"], 200],
    ['repliseq-parta', ['v13.1', 'v14', 'v16'], 200],
    ['bedGraphToBigWig', ['v4'], 24],
    ['bedtobeddb', ['v2'], 24],
    ['encode-chipseq-aln-chip', ['1.1.1'], 200],
    ['encode-chipseq-aln-ctl', ['1.1.1'], 200],
    ['encode-chipseq-postaln', ['1.1.1'], 200],
    ['encode-atacseq-aln', ['1.1.1'], 200],
    ['encode-atacseq-postaln', ['1.1.1'], 200],
    ['mergebed', ['v1'], 200],
    ['merge-fastq', ['v1'], 200],
    ['bamqc', ['v2', 'v3'], 200],
    ['encode-rnaseq-stranded', ['1.1'], 200],
    ['encode-rnaseq-unstranded', ['1.1'], 200],
    ['rna-strandedness', ['v2'], 200],
    ['fastq-first-line', ['v2'], 200],
    ['re_checker_workflow', ['v1.1', 'v1.2'], 200],
    ['mad_qc_workflow', ['1.1_dcic_2'], 200],
    # cgap ones
    ['workflow_bwa-mem_no_unzip-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 48],
    ['workflow_add-readgroups-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_merge-bam-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_picard-MarkDuplicates-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_sort-bam-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_gatk-BaseRecalibrator', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_gatk-ApplyBQSR-check', ['v9', 'v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_index-sorted-bam', ['v9'], 12],
    ['workflow_gatk-HaplotypeCaller', ['v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_gatk-CombineGVCFs', ['v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_gatk-GenotypeGVCFs-check', ['v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_gatk-VQSR-check', ['v10', 'v11', 'v12', 'v13'], 12],
    ['workflow_qcboard-bam', ['v9'], 12],
    ['workflow_cram2fastq', ['v12', 'v13'], 12],
]

workflow_names = [i[0] for i in workflow_details]


def fetch_pf_associated(pf_id_or_dict, my_key):
    """Given a file accession, find all related items
    1) QCs
    2) wfr producing the file, and other outputs from the same wfr
    3) wfrs this file went as input, and all files/wfrs/qcs around it
    The returned list might contain duplicates, uuids and display titles for qcs"""
    file_as_list = []
    if isinstance(pf_id_or_dict, dict):
        pf_info = pf_id_or_dict
    else:
        pf_info = ff_utils.get_metadata(pf_id_or_dict, my_key)
    file_as_list.append(pf_info['uuid'])
    if pf_info.get('quality_metric'):
        file_as_list.append(pf_info['quality_metric']['uuid'])
    inp_wfrs = pf_info.get('workflow_run_inputs', [])
    for inp_wfr in inp_wfrs:
        file_as_list.extend(fetch_wfr_associated(inp_wfr['uuid'], my_key))
    out_wfrs = pf_info.get('workflow_run_outputs', [])
    for out_wfr in out_wfrs:
        file_as_list.extend(fetch_wfr_associated(out_wfr['uuid'], my_key))
    return list(set(file_as_list))


def fetch_wfr_associated(wfr_id_or_resp, my_key):
    """Given wfr_uuid, find associated output files and qcs"""
    wfr_as_list = []
    if isinstance(wfr_id_or_resp, dict):
        wfr_info = wfr_id_or_resp
    else:
        wfr_info = ff_utils.get_metadata(wfr_id_or_resp, my_key)
    wfr_as_list.append(wfr_info['uuid'])
    if wfr_info.get('output_files'):
        for o in wfr_info['output_files']:
            if o.get('value'):
                wfr_as_list.append(o['value']['uuid'])
            elif o.get('value_qc'):
                wfr_as_list.append(o['value_qc']['uuid'])
    if wfr_info.get('output_quality_metrics'):
        for qc in wfr_info['output_quality_metrics']:
            if qc.get('value'):
                wfr_as_list.append(qc['value']['uuid'])
    if wfr_info.get('quality_metric'):
        wfr_as_list.append(wfr_info['quality_metric']['uuid'])
    return wfr_as_list


def get_wfr_report(wfrs):
    # for a given list of wfrs, produce a simpler report
    wfr_report = []
    for wfr_data in wfrs:
        wfr_rep = {}
        """For a given workflow_run item, grabs details, uuid, run_status, wfr name, date, and run time"""
        wfr_type, time_info = wfr_data['display_title'].split(' run ')
        # skip all style awsem runs
        try:
            wfr_type_base, wfr_version = wfr_type.strip().split(' ')
        except:
            continue
        time_info = time_info.strip('on').strip()
        try:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S')
        run_hours = (datetime.utcnow() - wfr_time).total_seconds() / 3600
        # try:
        #     wfr_time = datetime.strptime(wfr_data['date_created'], '%Y-%m-%dT%H:%M:%S.%f+00:00')
        # except ValueError:  # if it was exact second, no fraction is in value
        #     print("wfr time bingo", wfr_uuid)
        #     wfr_time = datetime.strptime(wfr_data['date_created'], '%Y-%m-%dT%H:%M:%S+00:00')
        output_files = wfr_data.get('output_files', None)
        output_uuids = []
        qc_uuids = []

        # add wfr qc to the qc list
        if wfr_data.get('quality_metric'):
            qc_uuids.append(wfr_data['quality_metric']['uuid'])

        if output_files:
            for i in output_files:
                if i.get('value', None):
                    output_uuids.append(i['value']['uuid'])
                if i.get('value_qc', None):
                    qc_uuids.append(i['value_qc']['uuid'])

        wfr_rep = {'wfr_uuid': wfr_data['uuid'],
                   'wfr_status': wfr_data['run_status'],
                   'wfr_name': wfr_type_base.strip(),
                   'wfr_version': wfr_version.strip(),
                   'wfr_date': wfr_time,
                   'run_time': run_hours,
                   'status': wfr_data['status'],
                   'outputs': output_uuids,
                   'qcs': qc_uuids}
        wfr_report.append(wfr_rep)
    wfr_report = sorted(wfr_report, key=lambda k: (k['wfr_date'], k['wfr_name']))
    return wfr_report


def delete_wfrs(file_resp, my_key, delete=False, stash=None):
    # file_resp in embedded frame
    # stash: all related wfrs for file_resp
    deleted_wfrs = []
    wfr_report = []
    file_type = file_resp['@id'].split('/')[1]
    # special clause until we sort input_wfr_switch issue
    # do not delete output wfrs of control files
    output_wfrs = file_resp.get('workflow_run_outputs')
    if not output_wfrs:
        if file_type == 'files-processed':
            # user submtted processed files
            return
        else:
            # raw files:
            pass
    else:
        output_wfr = output_wfrs[0]
        wfr_type, time_info = output_wfr['display_title'].split(' run ')
        if wfr_type == 'encode-chipseq-aln-ctl 1.1.1':
            print('skipping control file for wfr check', file_resp['accession'])
            return

    wfr_uuids = [i['uuid'] for i in file_resp.get('workflow_run_inputs')]
    wfrs = []
    if wfr_uuids:
        # fetch them from stash
        if stash:
            wfrs = [i for i in stash if i['uuid'] in wfr_uuids]
            assert len(wfrs) == len(wfr_uuids)
        # if no stash, get from database
        else:
            wfrs = [i['embedded'] for i in ff_utils.get_es_metadata(wfr_uuids, sources=['embedded.*'], key=my_key)]
    # look for md5s on files without wfr_run_output (file_microscopy ...)
    else:
        if file_type not in ['files-fastq', 'files-processed']:
            wfrs_url = ('/search/?type=WorkflowRun&type=WorkflowRun&workflow.title=md5+0.2.6&workflow.title=md5+0.0.4'
                        '&input_files.value.accession=') + file_resp['accession']
            wfrs = ff_utils.search_metadata(wfrs_url, key=my_key)
    # Skip sbg and file provenance
    wfrs = [i for i in wfrs if not i['@id'].startswith('/workflow-runs-sbg/')]
    wfrs = [i for i in wfrs if not i['display_title'].startswith('File Provenance Tracking')]
    # CLEAN UP IF FILE IS DELETED
    if file_resp['status'] == 'deleted':
        if file_resp.get('quality_metric'):
            if delete:
                qc_uuid = file_resp['quality_metric']['uuid']
                ff_utils.delete_field(file_resp, 'quality_metric', key=my_key)
                # delete quality metrics object
                patch_data = {'status': "deleted"}
                ff_utils.patch_metadata(patch_data, obj_id=qc_uuid, key=my_key)
        # delete all workflows for deleted files
        if not wfrs:
            return
        else:
            wfr_report = get_wfr_report(wfrs)
            for wfr_to_del in wfr_report:
                if wfr_to_del['status'] != 'deleted':
                    if wfr_to_del['wfr_name'] not in workflow_names:
                        print('Unlisted Workflow', wfr_to_del['wfr_name'], 'deleted file workflow',
                              wfr_to_del['wfr_uuid'], file_resp['accession'])
                    ####################################################
                    # TEMPORARY PIECE##################################
                    if wfr_to_del['status'] == 'released to project':
                        print('saved from deletion', wfr_to_del['wfr_name'], 'deleted file workflow',
                              wfr_to_del['wfr_uuid'], file_resp['accession'])
                        return
                    if wfr_to_del['status'] == 'released':
                        print('delete released!!!!!', wfr_to_del['wfr_name'], 'deleted file workflow',
                              wfr_to_del['wfr_uuid'], file_resp['accession'])
                        return
                    #####################################################
                    print(wfr_to_del['wfr_name'], 'deleted file workflow', wfr_to_del['wfr_uuid'], file_resp['accession'])
                    if delete:
                        patch_data = {'description': "This workflow run is deleted", 'status': "deleted"}
                        deleted_wfrs.append(wfr_to_del['wfr_uuid'])
                        ff_utils.patch_metadata(patch_data, obj_id=wfr_to_del['wfr_uuid'], key=my_key)
                        # delete output files of the deleted workflow run
                        if wfr_to_del['outputs']:
                            for out_file in wfr_to_del['outputs']:
                                ff_utils.patch_metadata({'status': "deleted"}, obj_id=out_file, key=my_key)
                        if wfr_to_del.get('qcs'):
                            for out_qc in wfr_to_del['qcs']:
                                ff_utils.patch_metadata({'status': "deleted"}, obj_id=out_qc, key=my_key)

    else:
        # get a report on all workflow_runs
        if not wfrs:
            return
        else:
            wfr_report = get_wfr_report(wfrs)
            # printTable(wfr_report, ['wfr_name', 'run_time', 'wfr_version', 'run_time', 'wfr_status'])
            # check if any unlisted wfr in report
            my_wfr_names = [i['wfr_name'] for i in wfr_report]
            unlisted = [x for x in my_wfr_names if x not in workflow_names]
            # report the unlisted ones
            if unlisted:
                print('Unlisted Workflow', unlisted, 'skipped in', file_resp['accession'])
            for wf_name, accepted_rev, accepted_run_time in workflow_details:
                # for each type of worklow make a list of old ones, and patch status and description
                sub_wfrs = [i for i in wfr_report if i['wfr_name'] == wf_name]
                if sub_wfrs:
                    active_wfr = sub_wfrs[-1]
                    old_wfrs = sub_wfrs[:-1]
                    # check the status of the most recent workflow
                    if active_wfr['wfr_status'] != 'complete':
                        if (active_wfr['wfr_status'] in ['running', 'started'] and active_wfr['run_time'] < accepted_run_time):
                            print(wf_name, 'still running for', file_resp['accession'])
                        else:
                            old_wfrs.append(active_wfr)
                    elif active_wfr['wfr_version'] not in accepted_rev:
                        old_wfrs.append(active_wfr)
                    if old_wfrs:
                        for wfr_to_del in old_wfrs:
                            if wfr_to_del['status'] != 'deleted':
                                if wfr_to_del['status'] in ['archived', 'replaced']:
                                    print(wfr_to_del['wfr_name'], wfr_to_del['status'], ' wfr found, skipping ',
                                          wfr_to_del['wfr_uuid'], file_resp['accession'])
                                    continue
                                ####################################################
                                # TEMPORARY PIECE
                                if wfr_to_del['status'] == 'released to project':
                                    print('saved from deletion', wfr_to_del['wfr_name'], 'old style or dub',
                                          wfr_to_del['wfr_uuid'], file_resp['accession'])
                                    continue
                                if wfr_to_del['status'] == 'released':
                                    print('delete released????', wfr_to_del['wfr_name'], 'old style or dub',
                                          wfr_to_del['wfr_uuid'], file_resp['accession'])
                                    continue
                                ####################################################

                                print(wfr_to_del['wfr_name'], 'old style or dub',
                                      wfr_to_del['wfr_uuid'], file_resp['accession'])
                                if delete:
                                    patch_data = {'description': "This workflow run is deleted", 'status': "deleted"}
                                    deleted_wfrs.append(wfr_to_del['wfr_uuid'])
                                    ff_utils.patch_metadata(patch_data, obj_id=wfr_to_del['wfr_uuid'], key=my_key)
                                    # delete output files of the deleted workflow run
                                    if wfr_to_del['outputs']:
                                        for out_file in wfr_to_del['outputs']:
                                            ff_utils.patch_metadata({'status': "deleted"}, obj_id=out_file, key=my_key)
                                    if wfr_to_del.get('qcs'):
                                        for out_qc in wfr_to_del['qcs']:
                                            ff_utils.patch_metadata({'status': "deleted"}, obj_id=out_qc, key=my_key)
    return deleted_wfrs
