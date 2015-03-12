import time
import boto.iam

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

BUCKET_PREFIX = 'palette-software-production-'

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
        time.sleep(3)

        bucket = s3_conn.create_bucket(bucket_name)
        try:
            bucket.set_policy(policy)
        except boto.exception.S3ResponseError:
            # try once more after an even longer sleep...
            time.sleep(3)
            bucket.set_policy(policy)

        return keys.access_key_id, keys.secret_access_key
