import os
import subprocess
from uuid import uuid4
from .base import CloudStorageSession

class SharedNFSStorage(CloudStorageSession):
    config_key = 'shared_nfs_params'
    
    def __init__(self, nfs_root='/mnt'):
        self._key_name = str(uuid4())
        
    def _generate_temp_keypair(self):
        self._priv_key_path = os.path.join('/tmp', self._key_name)
        self._pub_key_path = os.path.join('/tmp', self._key_name + '.pub')
        subprocess.call(
            ['ssh-keygen', '-t', 'ed25519', '-N', '""', '-f', self._priv_key_path],
            stdout=open(os.devnull, 'w')
        )