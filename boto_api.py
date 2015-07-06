import time
import boto.iam
from boto import ec2

import logging

logger = logging.getLogger('licensing')

# There can't be a newline or other character before the first brace.
POLICY = """{{
	"Id": "{title}Policy",
	"Statement": [
		{{
			"Sid": "{title}BucketACL",
			"Effect": "Allow",
			"Principal": {{
				"AWS": "{user_arn}"
			}},
			"Action": [
				"s3:GetBucketNotification",
				"s3:GetBucketCORS",
				"s3:ListBucketVersions",
				"s3:GetBucketRequestPayment",
				"s3:GetBucketTagging",
				"s3:ListBucket",
				"s3:GetBucketLogging",
				"s3:ListBucketMultipartUploads",
				"s3:GetBucketPolicy",
				"s3:GetLifecycleConfiguration",
				"s3:GetBucketLocation",
				"s3:GetBucketVersioning",
				"s3:GetBucketWebsite"
			],
			"Resource": "arn:aws:s3:::{name}"
		}},
		{{
			"Sid": "{title}BucketObjectsACL",
			"Effect": "Allow",
			"Principal": {{
				"AWS": "{user_arn}"
			}},
			"Action": [
				"s3:GetObjectVersionTorrent",
				"s3:AbortMultipartUpload",
				"s3:GetObjectAcl",
				"s3:GetObjectTorrent",
				"s3:RestoreObject",
				"s3:GetObjectVersion",
				"s3:DeleteObject",
				"s3:DeleteObjectVersion",
				"s3:GetObject",
				"s3:PutObjectAcl",
				"s3:PutObject",
				"s3:GetObjectVersionAcl"
			],
			"Resource": "arn:aws:s3:::{name}/*"
		}}
	]
}}
"""

BUCKET_PREFIX = 'palette-software-'

class BotoAPI(object):
    @classmethod
    def get_region_by_name(cls, name):
        result = 'us-east-1'
        if name == 'US East (Northern Virginia)':
            result = 'us-east-1'
        elif name == 'US West (Northern California)':
            result = 'us-west-1'
        elif name == 'US West (Oregon)':
            result = 'us-west-2'
        elif name == 'EU (Frankfurt)':
            result = 'eu-central-1'
        elif name == 'EU (Ireland)':
            result = 'eu-west-1'
        elif name == 'Asia Pacific (Sydney)':
            result = 'ap-southeast-2'
        elif name == 'Asia Pacific (Singapore)':
            result = 'ap-southeast-1'
        elif name == 'Asia Pacific (Tokyo)':
            result = 'ap-northeast-1'
        elif name == 'South America (Sao Paulo)':
            result = 'sa-east-1'
        return result

    @classmethod
    def create_s3(cls, entry):
        """ Creates a user and then gets access keys and then creates a bucket
            and bucket policy on S3
        """
        iam_name = BUCKET_PREFIX + entry.name
        bucket_name = BUCKET_PREFIX + entry.name

        logger.info('Boto: Creating user %s', iam_name)
        iam = boto.iam.connect_to_region('universal')
        if iam is None:
            logger.error('Boto: Could not get IAM region')
            return None

        try:
            res = iam.create_user(iam_name)
        except boto.exception.BotoServerError as error:
            logger.info('IAM user already exists %s', iam_name)
            res = iam.get_user(iam_name)

        user = res.user
        try:
            keys = iam.create_access_key(iam_name)
        except boto.exception.BotoServerError as error:
            logger.info('Coud not create access key %s %s', iam_name, error)
            return None

        data = {'name': iam_name,
                'title': iam_name.title(),
                'user_arn': user.arn}
        policy = POLICY.format(**data)

        logger.info('Creating bucket %s', bucket_name)
        s3_conn = boto.s3.connect_to_region('us-east-1')
        if s3_conn is None:
            logger.error('Boto: Could not get region "%s" for S3',
                         entry.aws_zone)
            return None

        # Sometimes it takes awhile for the user ARN to settle ?!
        time.sleep(2)

        bucket = s3_conn.create_bucket(bucket_name)
        while True:
            try:
                bucket.set_policy(policy)
                break
            except boto.exception.S3ResponseError:
                # try again
                time.sleep(2)
                logger.error('Trying to set bucket policy again')

        return keys.access_key_id, keys.secret_access_key

    @classmethod
    def get_instance_by_name(cls, name, region):
        """ Get an instance id by name and region
        """
        conn = ec2.connect_to_region(region)
        reservations = conn.get_all_reservations()
        instances = [i for r in reservations for i in r.instances]
        item = None
        for i in instances:
            if "Name" in i.tags and name == i.tags['Name']:
                item = i.id
                break
        return item

    @classmethod
    def terminate_instance(cls, name, region):
        """ Terminates an instance on AWS
        """
        if region is None:
            region = 'us-east-1'

        item = cls.get_instance_by_name(name, region)
        if item is not None:
            conn = ec2.connect_to_region(region)
            conn.terminate_instances(instance_ids=item)
        else:
            logger.error('Could not find instance named \'%s\' on AWS', name)

    @classmethod
    def delete_user(cls, name):
        """ Deletes an IAM user
        """
        user_name = BUCKET_PREFIX + name
        iam = boto.iam.connect_to_region('universal')
        try:
            access_keys = iam.get_all_access_keys(user_name)

            for i in access_keys['list_access_keys_response']\
                                ['list_access_keys_result']\
                                ['access_key_metadata']:
                iam.delete_access_key(i['access_key_id'], user_name=user_name)

            iam.delete_user(user_name)
        except boto.exception.BotoServerError as error:
            logger.error(error.message)

    @classmethod
    def delete_bucket(cls, name, region):
        """ Delete a bucket form S3
        """
        bucket_name = BUCKET_PREFIX + name
        bucket = None
        if region is None:
            region = 'us-east-1'

        try:
            s3_conn = boto.s3.connect_to_region(region)
            bucket = s3_conn.get_bucket(bucket_name)
        except boto.exception.S3ResponseError:
            logger.error('The specified bucket \'%s\' does not exist',
                         bucket_name)

        if bucket is not None:
            s3_conn.delete_bucket(bucket)




