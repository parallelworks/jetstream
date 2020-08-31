import os
import subprocess
from uuid import uuid4
from .base import CloudStorageSession, path_conversion, is_remote_uri

class SharedNFSStorage(CloudStorageSession):
    config_key = 'shared_nfs_params'
    
        def __init__(self, client_nfs_root='/mnt/efs/pworks', workers_nfs_root='/mnt/shared/pworks'):
        # self._key_name = str(uuid4())
        self.client_nfs_root = client_nfs_root
        self.workers_nfs_root = workers_nfs_root
        
    # def _generate_temp_keypair(self):
    #     self._priv_key_path = os.path.join('/tmp', self._key_name)
    #     self._pub_key_path = os.path.join('/tmp', self._key_name + '.pub')
    #     subprocess.call(
    #         ['ssh-keygen', '-t', 'ed25519', '-N', '""', '-f', self._priv_key_path],
    #         stdout=open(os.devnull, 'w')
    #     )
    
    def remote_download_cmd(self, remote_downloads_blobs=None):
        return ''
        # remote_download_cmd_template = (
        #     'mkdir -p {blobpath_dirname};ln -s {remote_filepath} {worker_local_filepath}\n'
        # )
        # remote_download_cmd = ''
        # for remote_download_blobpath in remote_downloads_blobs or list():
        #     if is_remote_uri(remote_download_blobpath):
        #         # TODO There is currently no mechanism to tell wget where to put the file
        #         url_filepath = urllib.parse.urlparse(remote_download_blobpath).path
        #         remote_download_cmd += 'if [[ ! -f "{}" ]];then wget {};fi\n'.format(
        #             os.path.basename(url_filepath),
        #             remote_download_blobpath
        #         )
        #     else:
        #         remote_download_blobpath = path_conversion(remote_download_blobpath)
        # 
        # 
        #         remote_download_cmd += remote_download_cmd_template.format(
        #             remote_filepath=os.path.join(self.root, remote_download_blobpath),
        #             worker_local_filepath=remote_download_blobpath,
        #             blobpath_dirname=os.path.dirname(remote_download_blobpath)
        #         )
        # 
        # return remote_download_cmd
    
    def remote_upload_cmd(self, remote_uploads_filepaths=None):
        return ''
        # remote_upload_cmd_template = (
        #     'singularity exec {aws_sif_path} aws s3 cp {blobpath} s3://{container}/{blobpath};\n'
        #     'mv '
        # )
        # remote_upload_cmd = self._get_credentials_exports()
        # for remote_upload_filepath in remote_uploads_filepaths or list():
        #     remote_upload_filepath = path_conversion(remote_upload_filepath)
        #     remote_upload_cmd += remote_upload_cmd_template.format(
        #         blobpath=remote_upload_filepath.strip('/'),
        #         blobpath_dirname=os.path.dirname(remote_upload_filepath),
        #         aws_sif_path=self.aws_sif_path,
        #         container=self.container
        #     )
        # 
        # return remote_upload_cmd
        
    def download_blob(self, filepath, blobpath=None, container=None):
        if not os.path.exists(filepath):
            source_filepath = os.path.join(self.client_nfs_root, path_conversion(filepath))
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            subprocess.call(['rsync', '-avzP', source_filepath, filepath])
            # print(f'**Down: rsync -avzP {source_filepath} {filepath}')
        
    def upload_blob(self, filepath, blobpath=None, container=None):
        sink_filepath = os.path.join(self.client_nfs_root, path_conversion(filepath))
        if not os.path.exists(sink_filepath):
            os.makedirs(os.path.dirname(sink_filepath), exist_ok=True)
            subprocess.call(['rsync', '-avzP', filepath, sink_filepath])
            # print(f'$$Up: rsync -avzP {filepath} {sink_filepath}')
            
    def task_cmd_prehook(self):
        return 'cd {}'.format(self.workers_nfs_root)
    
    def task_cmd_posthook(self):
        return ''