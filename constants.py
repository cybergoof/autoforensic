import os
from aws_cdk import (
    core as cdk
)

"""
If you want to pull your forensic image from another account, these constants should be uncommented
"""
MACHINE_LOOKUP_NAME = "DiskForensicRec*"
IMAGE_ACCOUNT = os.environ["CDK_DEFAULT_ACCOUNT"]


VPC_NAME = "baker221b-VPC"

READINESS_LOG_NAME = "ForensicDiskReadiness"

ACCOUNT_ID = os.environ["CDK_DEFAULT_ACCOUNT"]
REGION = os.environ["CDK_DEFAULT_REGION"]

# This needs to be changed for deployment.  Better to create a VPC and subnet in CDK
SUPPORTED_AZS = [f"{REGION}a", f"{REGION}b"]

# In future versions, the security account could be different than the victim account
SECURITY_ENVIRONMENT = cdk.Environment(
    account=ACCOUNT_ID,
    region=REGION)

MEMBER_ENVIRONMENT = SECURITY_ENVIRONMENT

