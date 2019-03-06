from dcicutils import ff_utils
from dcicutils import s3Utils
from datetime import datetime
import json
from IPython.core.display import display, HTML
from operator import itemgetter

# Reference Files
bwa_index = {"human": "4DNFIZQZ39L9",
             "mouse": "4DNFI823LSI8",
             "fruit-fly": '4DNFIO5MGY32',
             "chicken": "4DNFIVGRYVQF"}

chr_size = {"human": "4DNFI823LSII",
            "mouse": "4DNFI3UBJ3HZ",
            "fruit-fly": '4DNFIBEEN92C',
            "chicken": "4DNFIQFZW4DX"}

re_nz = {"human": {'MboI': '/files-reference/4DNFI823L812/',
                   'DpnII': '/files-reference/4DNFIBNAPW3O/',
                   'HindIII': '/files-reference/4DNFI823MBKE/',
                   'NcoI': '/files-reference/4DNFI3HVU2OD/'
                   },
         "mouse": {'MboI': '/files-reference/4DNFIONK4G14/',
                   'DpnII': '/files-reference/4DNFI3HVC1SE/',
                   "HindIII": '/files-reference/4DNFI6V32T9J/'
                   },
         "fruit-fly": {'MboI': '/files-reference/4DNFIS1ZVUWO/'
                       },
         "chicken": {"HindIII": '/files-reference/4DNFITPCJFWJ/'
                     }
         }


def get_attribution(file_json):
    attributions = {
        'lab': file_json['lab']['@id'],
        'award': file_json['award']['@id']
    }
    cont_labs = []
    if file_json.get('contributing_labs'):
        cont_labs = [i['@id'] for i in file_json['contributing_labs']]

    appendFDN = True
    if attributions['lab'] == '/labs/4dn-dcic-lab/':
        appendFDN = False

    if cont_labs:
        if appendFDN:
            cont_labs.append('/labs/4dn-dcic-lab/')
            cont_labs = list(set(cont_labs))
        attributions['contributing_labs'] = cont_labs

    else:
        if appendFDN:
            cont_labs = ['/labs/4dn-dcic-lab/']
            attributions['contributing_labs'] = cont_labs
        else:
            pass
    return attributions


def extract_file_info(obj_id, arg_name, env, rename=[]):
    auth = ff_utils.get_authentication_with_server({}, ff_env=env)
    my_s3_util = s3Utils(env=env)

    raw_bucket = my_s3_util.raw_file_bucket
    out_bucket = my_s3_util.outfile_bucket
    """Creates the formatted dictionary for files.
    """
    # start a dictionary
    template = {"workflow_argument_name": arg_name}
    if rename:
        change_from = rename[0]
        change_to = rename[1]
    # if it is list of items, change the structure
    if isinstance(obj_id, list):
        object_key = []
        uuid = []
        buckets = []
        for obj in obj_id:
            metadata = ff_utils.get_metadata(obj, key=auth)
            object_key.append(metadata['display_title'])
            uuid.append(metadata['uuid'])
            # get the bucket
            if 'FileProcessed' in metadata['@type']:
                my_bucket = out_bucket
            else:  # covers cases of FileFastq, FileReference, FileMicroscopy
                my_bucket = raw_bucket
            buckets.append(my_bucket)
        # check bucket consistency
        try:
            assert len(list(set(buckets))) == 1
        except AssertionError:
            print('Files from different buckets', obj_id)
            return
        template['object_key'] = object_key
        template['uuid'] = uuid
        template['bucket_name'] = buckets[0]
        if rename:
            template['rename'] = [i.replace(change_from, change_to) for i in template['object_key']]

    # if obj_id is a string
    else:
        metadata = ff_utils.get_metadata(obj_id, key=auth)
        template['object_key'] = metadata['display_title']
        template['uuid'] = metadata['uuid']
        # get the bucket
        if 'FileProcessed' in metadata['@type']:
            my_bucket = out_bucket
        else:  # covers cases of FileFastq, FileReference, FileMicroscopy
            my_bucket = raw_bucket
        template['bucket_name'] = my_bucket
        if rename:
            template['rename'] = template['object_key'].replace(change_from, change_to)
    return template


def run_json(input_files, env, wf_info, run_name):
    my_s3_util = s3Utils(env=env)
    out_bucket = my_s3_util.outfile_bucket
    """Creates the trigger json that is used by foufront endpoint.
    """
    input_json = {'input_files': input_files,
                  'output_bucket': out_bucket,
                  'workflow_uuid': wf_info['wf_uuid'],
                  "app_name": wf_info['wf_name'],
                  "wfr_meta": wf_info['wfr_meta'],
                  "parameters": wf_info['parameters'],
                  "config": {"ebs_type": "gp2",
                             "json_bucket": "4dn-aws-pipeline-run-json",
                             "ebs_iops": "",
                             "shutdown_min": "now",
                             "copy_to_s3": True,
                             "launch_instance": True,
                             "password": "",
                             "log_bucket": "tibanna-output",
                             "key_name": "4dn-encode"
                             },
                  "_tibanna": {"env": env,
                               "run_type": wf_info['wf_name'],
                               "run_id": run_name}
                  }
    # overwrite or add custom fields
    for a_key in ['config', 'custom_pf_fields', 'overwrite_input_extra']:
        if a_key in wf_info:
            input_json[a_key] = wf_info[a_key]
    return input_json


def find_pairs(my_rep_set, my_env, lookfor='pairs', exclude_miseq=True):
    auth = ff_utils.get_authentication_with_server({}, ff_env=my_env)
    my_s3_util = s3Utils(env=my_env)
    """Find fastq files from experiment set, exclude miseq.
    """
    report = {}
    rep_resp = my_rep_set['experiments_in_set']
    lab = [my_rep_set['lab']['@id']]
    enzymes = []
    organisms = []
    total_f_size = 0
    for exp in rep_resp:

        exp_resp = exp

        report[exp['accession']] = []
        if not organisms:
            biosample = exp['biosample']
            organisms = list(set([bs['individual']['organism']['name'] for bs in biosample['biosource']]))
            if len(organisms) != 1:
                print('multiple organisms in set', my_rep_set['accession'])
                break
        exp_files = exp['files']
        enzyme = exp.get('digestion_enzyme')
        if enzyme:
            enzymes.append(enzyme['display_title'])

        for fastq_file in exp_files:
            file_resp = ff_utils.get_metadata(fastq_file['uuid'], key=auth)
            if not file_resp.get('file_size'):
                print("WARNING!", file_resp['accession'], 'does not have filesize')
            else:
                total_f_size += file_resp['file_size']
            # skip pair no 2
            if file_resp.get('paired_end') == '2':
                continue
            # exclude miseq
            if exclude_miseq:
                if file_resp.get('instrument') == 'Illumina MiSeq':
                    # print 'skipping miseq files', exp
                    continue
            # Some checks before running
            # check if status is deleted
            if file_resp['status'] == 'deleted':
                print('deleted file', file_resp['accession'], 'in', my_rep_set['accession'])
                continue
            # if no uploaded file in the file item report and skip
            if not file_resp.get('filename'):
                print(file_resp['accession'], "does not have a file")
                continue
            # check if file is in s3

            head_info = my_s3_util.does_key_exist(file_resp['upload_key'], my_s3_util.raw_file_bucket)

            if not head_info:
                print(file_resp['accession'], "does not have a file in S3")
                continue
            # check that file has a pair
            f1 = file_resp['@id']
            f2 = ""
            paired = ""
            # is there a pair?
            try:
                relations = file_resp['related_files']
                paired_files = [relation['file']['@id'] for relation in relations if relation['relationship_type'] == 'paired with']
                assert len(paired_files) == 1
                f2 = paired_files[0]
                paired = "Yes"
            except:
                paired = "No"

            # for experiments with unpaired fastq files
            if lookfor == 'single':
                if paired == 'No':
                    report[exp_resp['accession']].append(f1)
                else:
                    print('expected single files, found paired end')
                    return
            # for experiments with paired files
            else:
                if paired != 'Yes':
                    print('expected paired files, found single end')
                    return
                f2 = ''
                relations = file_resp.get('related_files')

                if not relations:
                    print(f1, 'does not have a pair')
                    return
                for relation in relations:
                    if relation['relationship_type'] == 'paired with':
                        f2 = relation['file']['@id']
                if not f2:
                    print(f1, 'does not have a pair')
                    return

                report[exp_resp['accession']].append((f1, f2))
    # get the organism
    if len(list(set(organisms))) == 1:
        organism = organisms[0]
    else:
        organism = None

    # get the enzyme
    if len(list(set(enzymes))) == 1:
        enz = enzymes[0]
    else:
        enz = None

    bwa = bwa_index.get(organism)
    chrsize = chr_size.get(organism)
    if re_nz.get(organism):
        enz_file = re_nz[organism].get(enz)
    else:
        print('no enzyme information for the organism {}'.format(organism))
        enz_file = None

    return report, organism, enz, bwa, chrsize, enz_file, int(total_f_size / (1024 * 1024 * 1024)), lab


def get_wfr_out(file_id, wfr_name, auth, versions, md_qc=False, run=100):
    """For a given files, fetches the status of last wfr_name
    If there is a successful run it will return the output files as a dictionary of
    file_format:file_id, else, will return the status. Some runs, like qc and md5,
    does not have any file_format output, so they will simply return 'complete'
    """
    emb_file = ff_utils.get_metadata(file_id, key=auth)
    workflows = emb_file.get('workflow_run_inputs')
    wfr = {}
    run_status = 'did not run'

    my_workflows = [i for i in workflows if i['display_title'].startswith(wfr_name)]
    if not my_workflows:
        return {'status': "no workflow in file"}
    for a_wfr in my_workflows:
        wfr_type, time_info = a_wfr['display_title'].split(' run ')
        wfr_type_base, wfr_version = wfr_type.strip().split(' ')
        # user submitted ones use run on insteand of run
        time_info = time_info.strip('on').strip()
        try:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S')
        a_wfr['run_hours'] = (datetime.utcnow() - wfr_time).total_seconds() / 3600
        a_wfr['run_type'] = wfr_type_base.strip()
        a_wfr['run_version'] = wfr_version.strip()
    my_workflows = [i for i in my_workflows if i['run_version'] in versions]
    if not my_workflows:
        return {'status': "no workflow in file with accepted version"}
    my_workflows = sorted(my_workflows, key=lambda k: k['run_hours'])
    last_wfr = [i for i in my_workflows if i['run_type'] == wfr_name][0]

    wfr = ff_utils.get_metadata(last_wfr['uuid'], key=auth)
    run_duration = last_wfr['run_hours']
    run_status = wfr['run_status']

    if run_status == 'complete':
        outputs = wfr.get('output_files')
        # some runs, like qc, don't have a real file output
        if md_qc:
            return {'status': 'complete'}
        # if expected output files, return a dictionary of file_type:file_id
        else:
            out_files = {}
            for output in outputs:
                if output.get('format'):
                    # with new file format objects, we need to parse the name
                    try:  # the new expected file format
                        f_format = output['format'].split('/')[2]
                    except IndexError:  # the old format
                        f_format = output['format']
                    out_files[f_format] = output['value']['@id']
            if out_files:
                out_files['status'] = 'complete'
                return out_files
            else:
                print('no output file was found, maybe this run is a qc?')
                return {'status': "no file found"}
    elif run_status != 'error' and run_duration < run:
        # print(run_duration)
        return {'status': "running"}
    else:
        return {'status': "no completed run"}


def get_wfr_out_file(file_id, wfr_name, auth, versions, md_qc=False, run=100):
    """For a given files, fetches the status of last wfr_name
    If there is a successful run it will return the output files as a dictionary of
    argument_name:file_id, else, will return the status. Some runs, like qc and md5,
    does not have any file_format output, so they will simply return 'complete'
    """
    emb_file = ff_utils.get_metadata(file_id, key=auth)
    workflows = emb_file.get('workflow_run_inputs')
    wfr = {}
    run_status = 'did not run'

    my_workflows = [i for i in workflows if i['display_title'].startswith(wfr_name)]
    if not my_workflows:
        return {'status': "no workflow in file"}
    for a_wfr in my_workflows:
        wfr_type, time_info = a_wfr['display_title'].split(' run ')
        wfr_type_base, wfr_version = wfr_type.strip().split(' ')
        # user submitted ones use run on insteand of run
        time_info = time_info.strip('on').strip()
        try:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            wfr_time = datetime.strptime(time_info, '%Y-%m-%d %H:%M:%S')
        a_wfr['run_hours'] = (datetime.utcnow() - wfr_time).total_seconds() / 3600
        a_wfr['run_type'] = wfr_type_base.strip()
        a_wfr['run_version'] = wfr_version.strip()
    my_workflows = [i for i in my_workflows if i['run_version'] in versions]
    if not my_workflows:
        return {'status': "no workflow in file with accepted version"}
    my_workflows = sorted(my_workflows, key=lambda k: k['run_hours'])
    last_wfr = [i for i in my_workflows if i['run_type'] == wfr_name][0]

    wfr = ff_utils.get_metadata(last_wfr['uuid'], key=auth)
    run_duration = last_wfr['run_hours']
    run_status = wfr['run_status']

    if run_status == 'complete':
        outputs = wfr.get('output_files')
        # some runs, like qc, don't have a real file output
        if md_qc:
            return {'status': 'complete'}
        # if expected output files, return a dictionary of argname:file_id
        else:
            out_files = {}
            for output in outputs:
                if output.get('format'):
                    # get the arg name
                    arg_name = output['workflow_argument_name']
                    out_files[arg_name] = output['value']['@id']
            if out_files:
                out_files['status'] = 'complete'
                return out_files
            else:
                print('no output file was found, maybe this run is a qc?')
                return {'status': "no file found"}
    elif run_status != 'error' and run_duration < run:
        # print(run_duration)
        return {'status': "running"}
    else:
        return {'status': "no completed run"}


def add_processed_files(item_id, list_pc, auth):
    # patch the exp or set
    patch_data = {'processed_files': list_pc}
    ff_utils.patch_metadata(patch_data, obj_id=item_id, key=auth)
    return


def add_preliminary_processed_files(item_id, list_pc, auth, run_type="hic"):
    titles = {"hic": "HiC Processing Pipeline - Preliminary Files",
              "repliseq": "Repli-Seq Pipeline - Preliminary Files",
              'chip': "ENCODE ChIP-Seq Pipeline - Preliminary Files",
              'atac': "ENCODE ATAC-Seq Pipeline - Preliminary Files"}
    pc_set_title = titles[run_type]
    resp = ff_utils.get_metadata(item_id, key=auth)

    # check if this items are in processed files field
    # extract essential for comparison, unfold all possible ids into a list, and compare list_pc to that one
    ex_pc = resp.get('processed_files')
    if ex_pc:
        ex_pc_ids = [[a['@id'], a['uuid'], a['@id'].split('/')[2]] for a in ex_pc]
        ex_pc_ids = [a for i in ex_pc_ids for a in i]
        for i in list_pc:
            if i in ex_pc_ids:
                print('Error - Cannot add files to pc')
                print(i, 'is already in processed files')
                return

    # extract essential for comparison, unfold all possible ids into a list, and compare list_pc to that one
    ex_opc = resp.get('other_processed_files')
    if ex_opc:
        # check the titles
        all_existing_titles = [a['title'] for a in ex_opc]
        if pc_set_title in all_existing_titles:
            print('Error - Cannot add files to opc')
            print('The same title already in other processed files')
            return
        # check  the individual files
        ex_opc_ids = [[a['@id'], a['uuid'], a['@id'].split('/')[2]] for i in ex_opc for a in i['files']]
        ex_opc_ids = [a for i in ex_opc_ids for a in i]
        for i in list_pc:
            if i in ex_opc_ids:
                print('Error - Cannot add files to opc')
                print(i, 'is already in other processed files')
                return

    # we need raw to get the existing piece, to patch back with the new ones
    patch_data = ff_utils.get_metadata(item_id, key=auth, add_on='frame=raw').get('other_processed_files')
    if not patch_data:
        patch_data = []

    new_data = {'title': pc_set_title,
                'type': 'preliminary',
                'files': list_pc}
    patch_data.append(new_data)
    patch = {'other_processed_files': patch_data}
    ff_utils.patch_metadata(patch, obj_id=item_id, key=auth)


def release_files(set_id, list_items, auth, status=None):
    if status:
        item_status = status
    else:
        item_status = ff_utils.get_metadata(set_id, key=auth)['status']
    # bring files to same status as experiments and sets
    if item_status in ['released', 'released to project', 'pre-release']:
        for a_file in list_items:
            it_resp = ff_utils.get_metadata(a_file, key=auth)
            workflow = it_resp.get('workflow_run_outputs')
            # release the wfr that produced the file
            if workflow:
                ff_utils.patch_metadata({"status": item_status}, obj_id=workflow[0]['uuid'], key=auth)
            ff_utils.patch_metadata({"status": item_status}, obj_id=a_file, key=auth)


def run_missing_wfr(wf_info, input_files, run_name, auth, env):

    all_inputs = []
    for arg, files in input_files.items():
        inp = extract_file_info(files, arg, env)
        all_inputs.append(inp)
    # small tweak to get bg2bw working
    all_inputs = sorted(all_inputs, key=itemgetter('workflow_argument_name'))

    input_json = run_json(all_inputs, env, wf_info, run_name)
    e = ff_utils.post_metadata(input_json, 'WorkflowRun/run', key=auth)

    url = json.loads(e['input'])['_tibanna']['url']
    display(HTML("<a href='{}' target='_blank'>{}</a>".format(url, e['status'])))
    #time.sleep(30)


def extract_nz_file(acc, auth):
    mapping = {"HindIII": "6", "DpnII": "4", "MboI": "4", "NcoI": "6"}
    exp_resp = ff_utils.get_metadata(acc, key=auth)
    exp_type = exp_resp.get('experiment_type')
    # get enzyme
    nz_num = ""
    nz = exp_resp.get('digestion_enzyme')
    if nz:
        nz_num = mapping.get(nz['display_title'])
    if nz_num:
        pass
    # Soo suggested assigning 6 for Chiapet
    # Burak asked for running all without an NZ with paramter 6
    elif exp_type in ['CHIA-pet', 'ChIA-PET', 'micro-C', 'DNase Hi-C', 'TrAC-loop']:
        nz_num = '6'
    else:
        return (None, None)
    # get organism
    biosample = exp_resp['biosample']
    organisms = list(set([bs['individual']['organism']['name'] for bs in biosample['biosource']]))
    chrsize = ''
    if len(organisms) == 1:
        chrsize = chr_size.get(organisms[0])
    # if organism is not available return empty
    if not chrsize:
        print(organisms[0], 'not covered')
        return (None, None)
    # return result if both exist
    return nz_num, chrsize


def get_chip_info(f_exp_resp, my_key):
    """Gether the following information from the first experiment in the chip set"""
    control = ""  # True or False (True if set in scope is control)
    control_set = ""  # None (if no control exp is set), or the control experiment for the one in scope
    target_type = "" # Histone or TF (or None for control)
    # get target
    target = f_exp_resp.get('targeted_factor')
    if target:
        target_type = 'tf' # set to tf default and switch to histone (this part might need some work later)
        target_dt = target['display_title']
        if target_dt.startswith('Protein:H2') or target_dt.startswith('Protein:H3'):
            target_type = 'histone'
    else:
        target_type = None

    # get organism
    biosample = f_exp_resp['biosample']
    organism = list(set([bs['individual']['organism']['name'] for bs in biosample['biosource']]))[0]

    # get control information
    exp_relation = f_exp_resp.get('experiment_relation')
    if exp_relation:
        rel_type = [i['relationship_type'] for i in exp_relation]
        if 'control for' in rel_type:
            control = True
        if 'controlled by' in rel_type:
            control = False
            controls = [i['experiment'] for i in exp_relation if i['relationship_type'] == 'controlled by']
            if len(controls) != 1:
                print('multiple control experiments')
            else:
                cont_exp_info = ff_utils.get_metadata(controls[0]['uuid'], my_key)['experiment_sets']
                control_set = [i['accession'] for i in cont_exp_info if i['@id'].startswith('/experiment-set-replicates/')][0]
    else:
        # if no relation is present
        # set it as if control when the target is None
        if not target_type:
            control = True
        # if there is target, but no relation, treat it as an experiment without control
        else:
            control = False
            control_set = None
    return control, control_set, target_type, organism


def get_chip_files(exp_resp, my_auth):
    files = []
    obj_key = []
    paired = ""
    exp_files = exp_resp['files']
    for a_file in exp_files:
        f_t = []
        o_t = []
        file_resp = ff_utils.get_metadata(a_file['uuid'], my_auth)
        # get pair end no
        pair_end = file_resp.get('paired_end')
        if pair_end == '2':
            paired = 'paired'
            continue
        # get paired file
        paired_with = ""
        relations = file_resp.get('related_files')
        if not relations:
            pass
        else:
            for relation in relations:
                if relation['relationship_type'] == 'paired with':
                    paired = 'paired'
                    paired_with = relation['file']['uuid']
        # decide if data is not paired end reads
        if not paired_with:
            if not paired:
                paired = 'single'
            else:
                if paired != 'single':
                    print('inconsistent fastq pair info')
                    continue
            f_t.append(file_resp['uuid'])
            o_t.append(file_resp['display_title'])
        else:
            f2 = ff_utils.get_metadata(paired_with, my_auth)
            f_t.append(file_resp['uuid'])
            o_t.append(file_resp['display_title'])
            f_t.append(f2['uuid'])
            o_t.append(f2['display_title'])
        files.append(f_t)
        obj_key.append(o_t)
    return files, obj_key, paired


def run_missing_chip1(control, wf_info, organism, target_type, paired, files, obj_keys, my_env, my_key, run_name):
    my_s3_util = s3Utils(env=my_env)
    raw_bucket = my_s3_util.raw_file_bucket
    out_bucket = my_s3_util.outfile_bucket

    if organism == "human":
        org = 'hs'
        input_files = [{
            "object_key": "4DNFIZQB369V.bwaIndex.tar",
            "rename": "GRCh38_no_alt_analysis_set_GCA_000001405.15.fasta.tar",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.bwa_idx_tar",
            "uuid": "38077b98-3862-45cd-b4be-8e28e9494549"
        },
            {
            "object_key": "4DNFIZ1TGJZR.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.blacklist",
            "uuid": "9562ffbd-9f7a-4bd7-9c10-c335137d8966"
        },
            {
            "object_key": "4DNFIZJB62D1.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.chrsz",
            "uuid": "9866d158-da3c-4d9b-96a9-1d59632eabeb"
        }]

    elif organism == "mouse":
        org = 'mm'
        input_files = [{
            "object_key": "4DNFIZ2PWCC2.bwaIndex.tar",
            "rename": "mm10_no_alt_analysis_set_ENCODE.fasta.tar",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.bwa_idx_tar",
            "uuid": "f4b63d31-65d8-437f-a76a-6bedbb52ae6f"
        },
            {
            "object_key": "4DNFIZ3FBPK8.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.blacklist",
            "uuid": "a32747a3-8a9e-4a9e-a7a1-4db0e8b65925"
        },
            {
            "object_key": "4DNFIBP173GC.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.chrsz",
            "uuid": "be0a9819-d2ce-4422-be4b-234fb1677dd9"
        }]
    if control:
        input_files.append({"object_key": obj_keys,
                            "bucket_name": raw_bucket,
                            "workflow_argument_name": "chip.ctl_fastqs",
                            "uuid": files})
    else:
        input_files.append({"object_key": obj_keys,
                            "bucket_name": raw_bucket,
                            "workflow_argument_name": "chip.fastqs",
                            "uuid": files})

    if paired == 'single':
        chip_p = False
    elif paired == 'paired':
        chip_p = True
    if control:
        parameters = {
            "chip.pipeline_type": target_type,
            "chip.paired_end": chip_p,
            "chip.choose_ctl.always_use_pooled_ctl": True,
            "chip.gensz": org,
            "chip.bam2ta_ctl.regex_grep_v_ta": "chr[MUE]|random|alt",
            "chip.bwa_ctl.cpu": 8,
            "chip.merge_fastq_ctl.cpu": 8,
            "chip.filter_ctl.cpu": 8,
            "chip.bam2ta_ctl.cpu": 8,
            "chip.align_only": True
        }
    else:
        parameters = {
            "chip.pipeline_type": target_type,
            "chip.paired_end": chip_p,
            "chip.choose_ctl.always_use_pooled_ctl": True,
            "chip.gensz": org,
            "chip.bam2ta.regex_grep_v_ta": "chr[MUE]|random|alt",
            "chip.bwa.cpu": 8,
            "chip.merge_fastq.cpu": 8,
            "chip.filter.cpu": 8,
            "chip.bam2ta.cpu": 8,
            "chip.xcor.cpu": 8,
            "chip.align_only": True
        }
    if paired == 'single':
        frag_temp = [300]
        fraglist = frag_temp * len(files)
        parameters['chip.fraglen'] = fraglist

    tag = '1.1.1'
    """Creates the trigger json that is used by foufront endpoint.
    """
    input_json = {'input_files': input_files,
                  'output_bucket': out_bucket,
                  'workflow_uuid': wf_info['wf_uuid'],
                  "app_name": wf_info['wf_name'],
                  "wfr_meta": wf_info['wfr_meta'],
                  "parameters": parameters,
                  "config": wf_info['config'],
                  "custom_pf_fields": wf_info['custom_pf_fields'],
                  "_tibanna": {"env": my_env,
                               "run_type": wf_info['wf_name'],
                               "run_id": run_name},
                  "tag": tag
                  }
    # r = json.dumps(input_json)
    # print(r)
    e = ff_utils.post_metadata(input_json, 'WorkflowRun/run', key=my_key)
    url = json.loads(e['input'])['_tibanna']['url']
    display(HTML("<a href='{}' target='_blank'>{}</a>".format(url, e['status'])))


def run_missing_chip2(control_set, wf_info, organism, target_type, paired,
                      ta, ta_xcor, ta_cnt, my_env, my_key, run_ids):
    my_s3_util = s3Utils(env=my_env)
    raw_bucket = my_s3_util.raw_file_bucket
    out_bucket = my_s3_util.outfile_bucket

    if organism == "human":
        org = 'hs'
        input_files = [{
            "object_key": "4DNFIZ1TGJZR.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.blacklist",
            "uuid": "9562ffbd-9f7a-4bd7-9c10-c335137d8966"
        },
            {
            "object_key": "4DNFIZJB62D1.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.chrsz",
            "uuid": "9866d158-da3c-4d9b-96a9-1d59632eabeb"
        }]

    elif organism == "mouse":
        org = 'mm'
        input_files = [{
            "object_key": "4DNFIZ3FBPK8.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.blacklist",
            "uuid": "a32747a3-8a9e-4a9e-a7a1-4db0e8b65925"
        },
            {
            "object_key": "4DNFIBP173GC.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "chip.chrsz",
            "uuid": "be0a9819-d2ce-4422-be4b-234fb1677dd9"
        }]

    ta_f = extract_file_info(ta, 'chip.tas', my_env, rename=['bed', 'tagAlign'])
    input_files.append(ta_f)
    ta_xcor_f = extract_file_info(ta_xcor, 'chip.bam2ta_no_filt_R1.ta', my_env, rename=['bed', 'tagAlign'])
    input_files.append(ta_xcor_f)
    if control_set:
        ta_cnt = extract_file_info(ta_cnt, 'chip.ctl_tas', my_env, rename=['bed', 'tagAlign'])
        input_files.append(ta_cnt)

    if paired == 'single':
        chip_p = False
    elif paired == 'paired':
        chip_p = True
    if not control_set:
        if target_type == 'histone':
            print('HISTONE WITHOUT CONTROL NEEDS ATTENTION (change to tf), skipping for now')
            return

    parameters = {
        "chip.pipeline_type": target_type,
        "chip.paired_end": chip_p,
        "chip.choose_ctl.always_use_pooled_ctl": True,
        "chip.qc_report.name": run_ids['run_name'],
        "chip.qc_report.desc": run_ids['desc'],
        "chip.gensz": org,
        "chip.xcor.cpu": 4,
        "chip.spp_cpu": 4
    }

    if paired == 'single':
        frag_temp = [300]
        fraglist = frag_temp * len(ta)
        parameters['chip.fraglen'] = fraglist

    tag = '1.1.1'
    """Creates the trigger json that is used by foufront endpoint.
    """
    input_json = {'input_files': input_files,
                  'output_bucket': out_bucket,
                  'workflow_uuid': wf_info['wf_uuid'],
                  "app_name": wf_info['wf_name'],
                  "wfr_meta": wf_info['wfr_meta'],
                  "parameters": parameters,
                  "config": wf_info['config'],
                  "custom_pf_fields": wf_info['custom_pf_fields'],
                  "_tibanna": {"env": my_env,
                               "run_type": wf_info['wf_name'],
                               "run_id": run_ids['run_name']},
                  "tag": tag
                  }
    # r = json.dumps(input_json)
    # print(r)
    e = ff_utils.post_metadata(input_json, 'WorkflowRun/run', key=my_key)
    url = json.loads(e['input'])['_tibanna']['url']
    display(HTML("<a href='{}' target='_blank'>{}</a>".format(url, e['status'])))


def run_missing_atac1(wf_info, organism, paired, files, obj_keys, my_env, my_key, run_name):
    my_s3_util = s3Utils(env=my_env)
    raw_bucket = my_s3_util.raw_file_bucket
    out_bucket = my_s3_util.outfile_bucket

    if organism == "human":
        org = 'hs'
        input_files = [{
            "object_key": "4DNFIMQPTYDY.bowtie2Index.tar",
            "rename": "GRCh38_no_alt_analysis_set_GCA_000001405.15.fasta.tar",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.bowtie2_idx_tar",
            "uuid": "28ab6265-f426-4a23-bb8a-f28467ad505b"
        },
            {
            "object_key": "4DNFIZ1TGJZR.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.blacklist",
            "uuid": "9562ffbd-9f7a-4bd7-9c10-c335137d8966"
        },
            {
            "object_key": "4DNFIZJB62D1.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.chrsz",
            "uuid": "9866d158-da3c-4d9b-96a9-1d59632eabeb"
        }]

    elif organism == "mouse":
        org = 'mm'
        input_files = [{
            "object_key": "4DNFI2493SDN.bowtie2Index.tar",
            "rename": "mm10_no_alt_analysis_set_ENCODE.fasta.tar",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.bowtie2_idx_tar",
            "uuid": "63e22058-79c6-4e24-8231-ca4afac29dda"
        },
            {
            "object_key": "4DNFIZ3FBPK8.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.blacklist",
            "uuid": "a32747a3-8a9e-4a9e-a7a1-4db0e8b65925"
        },
            {
            "object_key": "4DNFIBP173GC.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.chrsz",
            "uuid": "be0a9819-d2ce-4422-be4b-234fb1677dd9"
        }]

    input_files.append({"object_key": obj_keys,
                        "bucket_name": raw_bucket,
                        "workflow_argument_name": "atac.fastqs",
                        "uuid": files})

    if paired == 'single':
        chip_p = False
    elif paired == 'paired':
        chip_p = True
    parameters = {
        "atac.pipeline_type": 'atac',
        "atac.paired_end": chip_p,
        "atac.gensz": org,
        "atac.bam2ta.regex_grep_v_ta": "chr[MUE]|random|alt",
        "atac.disable_ataqc": True,
        "atac.enable_xcor": False,
        "atac.trim_adapter.auto_detect_adapter": True,
        "atac.bowtie2.cpu": 4,
        "atac.filter.cpu": 4,
        "atac.bam2ta.cpu": 4,
        "atac.trim_adapter.cpu": 4,
        "atac.align_only": True
    }

    if paired == 'single':
        frag_temp = [300]
        fraglist = frag_temp * len(files)
        parameters['atac.fraglen'] = fraglist

    tag = '1.1.1'
    """Creates the trigger json that is used by foufront endpoint.
    """
    input_json = {'input_files': input_files,
                  'output_bucket': out_bucket,
                  'workflow_uuid': wf_info['wf_uuid'],
                  "app_name": wf_info['wf_name'],
                  "wfr_meta": wf_info['wfr_meta'],
                  "parameters": parameters,
                  "config": wf_info['config'],
                  "custom_pf_fields": wf_info['custom_pf_fields'],
                  "_tibanna": {"env": my_env,
                               "run_type": wf_info['wf_name'],
                               "run_id": run_name},
                  "tag": tag
                  }
    # r = json.dumps(input_json)
    # print(r)
    e = ff_utils.post_metadata(input_json, 'WorkflowRun/run', key=my_key)
    url = json.loads(e['input'])['_tibanna']['url']
    display(HTML("<a href='{}' target='_blank'>{}</a>".format(url, e['status'])))


def run_missing_atac2(wf_info, organism, paired, ta,
                      my_env, my_key, run_name):
    my_s3_util = s3Utils(env=my_env)
    raw_bucket = my_s3_util.raw_file_bucket
    out_bucket = my_s3_util.outfile_bucket

    if organism == "human":
        org = 'hs'
        input_files = [{
            "object_key": "4DNFIZ1TGJZR.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.blacklist",
            "uuid": "9562ffbd-9f7a-4bd7-9c10-c335137d8966"
        },
            {
            "object_key": "4DNFIZJB62D1.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.chrsz",
            "uuid": "9866d158-da3c-4d9b-96a9-1d59632eabeb"
        }]

    elif organism == "mouse":
        org = 'mm'
        input_files = [{
            "object_key": "4DNFIZ3FBPK8.bed.gz",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.blacklist",
            "uuid": "a32747a3-8a9e-4a9e-a7a1-4db0e8b65925"
        },
            {
            "object_key": "4DNFIBP173GC.chrom.sizes",
            "bucket_name": raw_bucket,
            "workflow_argument_name": "atac.chrsz",
            "uuid": "be0a9819-d2ce-4422-be4b-234fb1677dd9"
        }]

    ta_f = extract_file_info(ta, 'atac.tas', my_env, rename=['bed', 'tagAlign'])
    input_files.append(ta_f)

    if paired == 'single':
        chip_p = False
    elif paired == 'paired':
        chip_p = True

    parameters = {
        "atac.pipeline_type": 'atac',
        "atac.paired_end": chip_p,
        "atac.gensz": org,
        "atac.disable_ataqc": True,
        "atac.enable_xcor": False,
    }

    if paired == 'single':
        frag_temp = [300]
        fraglist = frag_temp * len(ta)
        parameters['atac.fraglen'] = fraglist

    tag = '1.1.1'
    """Creates the trigger json that is used by foufront endpoint.
    """
    input_json = {'input_files': input_files,
                  'output_bucket': out_bucket,
                  'workflow_uuid': wf_info['wf_uuid'],
                  "app_name": wf_info['wf_name'],
                  "wfr_meta": wf_info['wfr_meta'],
                  "parameters": parameters,
                  "config": wf_info['config'],
                  "custom_pf_fields": wf_info['custom_pf_fields'],
                  "_tibanna": {"env": my_env,
                               "run_type": wf_info['wf_name'],
                               "run_id": run_name},
                  "tag": tag
                  }
    # r = json.dumps(input_json)
    # print(r)
    e = ff_utils.post_metadata(input_json, 'WorkflowRun/run', key=my_key)
    url = json.loads(e['input'])['_tibanna']['url']
    display(HTML("<a href='{}' target='_blank'>{}</a>".format(url, e['status'])))


def select_best_2(file_list, my_key):
    scores = []
    # run it for list with at least 3 elements
    if len(file_list) < 3:
        return(file_list)

    for f in file_list:
        f_resp = ff_utils.get_metadata(f, my_key)
        qc = f_resp.get('quality_metric')
        if not qc:
            print('No qc found on file', f)
            return
        qc_resp = ff_utils.get_metadata(qc['uuid'], my_key)
        try:
            score = qc_resp['nodup_flagstat_qc'][0]['mapped']
        except Exception:
            score = qc_resp['ctl_nodup_flagstat_qc'][0]['mapped']
        scores.append((score, f))
    scores = sorted(scores, key=lambda x: -x[0])
    return [scores[0][1], scores[1][1]]
