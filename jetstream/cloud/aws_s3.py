import os
import subprocess

from .base import CloudStorageSession, is_remote_uri, path_conversion

class AWSS3StorageSession(CloudStorageSession):
    config_key = 'aws_params'
    
    def __init__(self, aws_sif_path=None, aws_profile='default', aws_region=None, aws_output=None,
                 aws_access_key_id=None, aws_secret_access_key=None, container=None):
        super().__init__(container=container)
        self.aws_sif_path = aws_sif_path or 'docker://amazon/aws-cli'
        singularity_available = subprocess.call(['which', 'singularity'], stdout=open(os.devnull, 'w')) == 0
        self.aws_execution_call = (
            f'singularity exec --bind /mnt:/mnt {self.aws_sif_path} aws'
            if singularity_available
            else 'aws'
        )
        
        # Set credentials information
        self.aws_region = aws_region or self._get_credential('region', profile=aws_profile)
        self.aws_output = aws_output or self._get_credential('output', profile=aws_profile)
        self.aws_access_key_id = aws_access_key_id or self._get_credential('aws_access_key_id', profile=aws_profile)
        self.aws_secret_access_key = aws_secret_access_key or self._get_credential('aws_secret_access_key', profile=aws_profile)
        
        os.environ['AWS_DEFAULT_REGION'] = self.aws_region
        os.environ['AWS_DEFAULT_OUTPUT'] = self.aws_output
        os.environ['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
        os.environ['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
        
        # If a container name is not given, then create a temporary container
        if container is None:
            self.create_container(self.container)
    
    def _get_credential(self, credential, profile):
        print(f'Getting credential {credential} from AWS credentials file')
        return subprocess.check_output(
            self.aws_execution_call.split() + ['configure', 'get', f'{profile}.{credential}']
        ).decode().strip()
        
    def _get_credentials_exports(self):
        return f"""
        export AWS_DEFAULT_REGION={self.aws_region};
        export AWS_DEFAULT_OUTPUT={self.aws_output};
        export AWS_ACCESS_KEY_ID={self.aws_access_key_id};
        export AWS_SECRET_ACCESS_KEY={self.aws_secret_access_key};
        """
    
    def create_container(self, container_name):
        print(f'Creating container s3://{container_name}')
        return subprocess.check_output(
            self.aws_execution_call.split()
            + ['s3', 'mb', f's3://{container_name}']
        )
    
    def blob_exists(self, s3_path):
        return subprocess.call(
            self.aws_execution_call.split()
            + ['s3', 'ls', f'{s3_path}'],
            stdout=open(os.devnull, 'w')
        ) == 0
    
    def upload_blob(self, filepath, blobpath=None, container=None, force=False):
        """
        Overidden
        """
        try:
            container = container or self.container
            blobpath = blobpath or os.path.basename(filepath)
            s3_path = 's3://{}/{}'.format(container, blobpath.strip('/'))
            
            if not self.blob_exists(s3_path) or force:
                subprocess.call(
                    self.aws_execution_call.split()
                    + ['s3', 'cp', filepath, s3_path]
                )
            else:
                print(f'{filepath} already exists, skipping upload')
        except Exception as e:
            import traceback
            print(e)
            print(traceback.format_exc)
    
    def download_blob(self, filepath, blobpath=None, container=None):
        """
        Overridden
        """
        container = container or self.container
        blobpath = blobpath or os.path.basename(filepath)
        s3_path = 's3://{}/{}'.format(container, blobpath.strip('/'))
        
        subprocess.call(
            self.aws_execution_call.split()
            + ['s3', 'cp', s3_path, filepath]
        )
    
    def remote_download_cmd(self, remote_downloads_blobs=None):
        remote_download_cmd_template = (
            'if [[ ! -f "{blobpath}" ]];then mkdir -p {blobpath_dirname}; '
            'singularity exec {aws_sif_path} aws s3 cp s3://{container}/{blobpath} {blobpath};fi\n'
        )
        remote_download_cmd = self._get_credentials_exports()
        for remote_download_blobpath in remote_downloads_blobs or list():
            if is_remote_uri(remote_download_blobpath):
                # TODO There is currently no mechanism to tell wget where to put the file
                url_filepath = urllib.parse.urlparse(remote_download_blobpath).path
                remote_download_cmd += 'if [[ ! -f "{}" ]];then wget {};fi\n'.format(
                    os.path.basename(url_filepath),
                    remote_download_blobpath
                )
            else:
                remote_download_blobpath = path_conversion(remote_download_blobpath)
                remote_download_cmd += remote_download_cmd_template.format(
                    blobpath=remote_download_blobpath.strip('/'),
                    blobpath_dirname=os.path.dirname(remote_download_blobpath),
                    aws_sif_path=self.aws_sif_path,
                    container=self.container
                )
        
        return remote_download_cmd
        
    def remote_upload_cmd(self, remote_uploads_filepaths=None):
        remote_upload_cmd_template = (
            'singularity exec {aws_sif_path} aws s3 cp {blobpath} s3://{container}/{blobpath};\n'
        )
        remote_upload_cmd = self._get_credentials_exports()
        for remote_upload_filepath in remote_uploads_filepaths or list():
            remote_upload_filepath = path_conversion(remote_upload_filepath)
            remote_upload_cmd += remote_upload_cmd_template.format(
                blobpath=remote_upload_filepath.strip('/'),
                blobpath_dirname=os.path.dirname(remote_upload_filepath),
                aws_sif_path=self.aws_sif_path,
                container=self.container
            )
            
        return remote_upload_cmd
