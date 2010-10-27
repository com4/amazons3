from django.conf import settings
from amazons3 import S3

from django.core.files.storage import Storage


class S3Error(Exception):
    "Misc. S3 Service Error"
    pass

class S3Storage(Storage):
    options = None

    def __init__(self, options=None):
        if not options:
            options = settings.S3_SETTINGS
            self.options = options
        self.perm_tuple = (
            'private',
            'public-read',
            'public-read-write',
            'authenticated-read'
        )
        if self.options['default_perm'] not in self.perm_tuple:
            self.options['default_perm'] = 'private'

        self.connect()

    def connect(self):
        self.conn = S3.AWSAuthConnection(self.options['aws_key'], self.options['aws_secret_key'])

        res = self.conn.check_bucket_exists(self.options['bucket'])

        if res.status != 200:
            res = self.conn.create_bucket(self.options['bucket'])
            if res.http_response.status != 200:
                raise S3Error, 'Unable to create bucket %s' % (self.options['bucket'])

        return True

    def exists(self, filename):
        import os
        contents = self.conn.list_bucket(self.options['bucket'], {'prefix': os.path.dirname(filename)})
        if filename in [f.key for f in contents.entries]:
            return True
        else:
            return False

    def size(self, filename):
        contents = self.conn.list_bucket(self.options['bucket'])
        for f in contents.entries:
            if f.name == filename:
                return f.size

        return False

    def url(self, filename):
        server = self.options['bucket']
        if not self.options['vanity_url']:
            server += '.s3.amazonaws.com'
        else:
            server = self.options['vanity_url']
        return 'http://' + server + '/' + filename


    def _save(self, filename, content):
        # a stupid hack
        try:
            content.url = self.url
        except AttributeError, e:
            content = content.file

        try:
            data = content.read()
        except IOError, err:
            raise S3Error, 'Unable to read %s: %s' % (filename, err.strerror)

        guess_type = False
        try:
            content.content_type
        except AttributeError, e:
            guess_type = True
        
        if guess_type or not content.content_type:
            import mimetypes
            content_type = mimetypes.guess_type(filename)[0]
            if content_type is None:
                content_type = 'text/plain'
        else:
            content_type = content.content_type

        perm = self.options['default_perm']

        res = self.conn.put(
            self.options['bucket'],
            filename,
            S3.S3Object(data),
            {
                'x-amz-acl': perm,
                'Content-Type': content_type
            }
        )

        if res.http_response.status != 200:
            raise S3Error, 'Unable to upload file %s: Error code %s: %s' % (filename, self.options['bucket'], res.body)


        content.filename = filename
        content.url = self.url(filename)

        return filename

    def delete(self, filename):
        res = self.conn.delete(self.options['bucket'], filename)
        if res.http_response.status != 204:
            pass
            #raise S3Error, 'Unable to delete file %s' % (filename)

        return (res.http_response.status == 204)

    def path(self, filename):
        raise NotImplementedError

    def open(self, filename, mode):
        from urllib import urlopen
        return urlopen(self.url(filename))

    def get_available_name(self, filename):
        import os
        basefilename = os.path.splitext(filename)
        i = 1
        while self.exists(filename):
            i += 1
            filename = '%s-%d%s' % (basefilename[0], i, basefilename[1])

        return filename

class CxStorage(S3Storage):
    """
    This storage engine provides the naming scheme for phonese3. It hashes
    the file names before storage.
    To use, set DEFAULT_STORAGE_ENGINE="CxStorage"
    
    Author: Jason Braegger
    License: AGPLv3
    Source: http://code.twi.gs/phonese3/
    """
    def get_valid_name(self, name):
        """
        This returns a hashed name to use for storage on the filesystem
        """
        import os.path
        from hashlib import md5
        import time
        
        extension = os.path.splitext(name)[1].lower()
        # Ensure an ascii string for .hexdigest() later.
        name = name.encode('ascii', 'ignore')

        return str(md5(str(time.time()) + name).hexdigest()) + \
            str(extension)
