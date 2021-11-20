"""
Unit test for the CDK constructs
"""
import botocore.stub
import pytest
from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
)
import pathlib
import json
import constants
import collections
import boto3
from string import Template

from moto import mock_cloudwatch, mock_logs, mock_ec2, mock_s3, mock_stepfunctions
from src.forensic_auto_capture.auto_forensics import AutoForensicsConstruct
from src.forensic_auto_capture.disk_functions.assets.mount_volume.lambda_function import lambda_handler as mount_volume_handler
from src.forensic_auto_capture.invoke.assets.disk_invoke_guardduty import buildEvent as invoke_guardduty_buildevent
StackEnvironment = collections.namedtuple('StackEnvironment', ['stack', 'vpc'])

@pytest.fixture(scope="session")
def auto_forensics_construct(stack_environment):
    return AutoForensicsConstruct(stack_environment.stack, "UNITAutoForensics",
                                  member_account_id=constants.ACCOUNT_ID,
                                  security_account_id=constants.ACCOUNT_ID,
                                  region=constants.REGION,
                                  vpc=stack_environment.vpc,
                                  supported_azs=constants.SUPPORTED_AZS)


@pytest.fixture(scope="session")
def machine_image():
   return ec2.LookupMachineImage(name=constants.MACHINE_LOOKUP_NAME, owners=[constants.IMAGE_ACCOUNT])
@pytest.fixture(scope="session")
def stack_environment():
    app = cdk.App()
    stack = cdk.Stack(app, "TestDeploySimulation", env=cdk.Environment(account=constants.ACCOUNT_ID,
                                                                       region=constants.REGION))
    vpc = ec2.Vpc.from_lookup(stack, "TestVPC", vpc_name=constants.VPC_NAME)
    yield StackEnvironment(stack=stack, vpc=vpc)
    app.synth()

#@mock_logs
#@mock_s3
#@mock_ec2
def test_mount_volume(auto_forensics_construct, machine_image, monkeypatch):
    #monkeypatch.setenv("LOG_GROUP", auto_forensics_construct.forensic_resources_construct.audit_log_group)
    #monkeypatch.setenv("READINESS_LOG_GROUP", auto_forensics_construct.forensic_resources_construct.readiness_log_group)
    # LogGroup is ForensicAuditLogGroup
    # Readiness_log_Group is ForensicReadinessLogGroup is
    # Write to the logs
    input_json = json.loads((pathlib.Path(__file__).parents[0] / 'assets/mount_fail2.json').read_text())
    readiness_log_message = json.loads((pathlib.Path(__file__).parents[0] / 'assets/readiness_log_group.json').read_text())
    """
    EVIDENCE_BUCKET=input_json["DiskProcess"]["EvidenceBucket"]
    READINESS_LOG_GROUP = "ReadinessGroup"
    READINESS_STREAM = input_json["DiskProcess"]['ForensicInstances'][0]

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    ec2_client = boto3.client("ec2",
                              region_name="us-east-1",
                              aws_access_key_id="fake_access_key",
                              aws_secret_access_key="fake_secret_key")

    log_client = boto3.client("logs",
                          region_name="us-east-1",
                          aws_access_key_id="fake_access_key",
                          aws_secret_access_key="fake_secret_key")
    log_client.create_log_group(logGroupName=READINESS_LOG_GROUP)
    log_client.create_log_stream(logGroupName=READINESS_LOG_GROUP,
                                 logStreamName=READINESS_STREAM)
    log_client.put_log_events(
        logGroupName=READINESS_LOG_GROUP,
        logStreamName=READINESS_STREAM,
        logEvents=[{
            'timestamp': int(round(time.time()* 1000)),
            'message': "incron is running"
        }]

    )

    boto3.client("s3").create_bucket(Bucket=EVIDENCE_BUCKET)
    """
    monkeypatch.setenv("LOG_GROUP", "ForensicAuditLogGroup")
    monkeypatch.setenv("READINESS_LOG_GROUP", "ForensicDiskReadiness")

    mount_volume_handler(event=input_json, context="")

@mock_stepfunctions
def test_invoke_guardduty(monkeypatch):
    sfn_client = boto3.client("stepfunctions")
    definition_template = Template("""
     {
       "StartAt": "ListIds",
       "States": {
         "ListIds": {
           "Type": "Task",
           "Resource": "${ListIdsLambdaArn}",
           "ResultPath": "$.cluster_ids",
           "End": true
         }
       }
     }
     """)
    list_ids_lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my.pkg.emr.list_ids"
    definition = definition_template.safe_substitute(ListIdsLambdaArn=list_ids_lambda_arn)

    state_machine_arn = sfn_client.create_state_machine(
        name="test-role", definition=definition, roleArn="arn:aws:iam::012345678901:role/DummyRole"
    )["stateMachineArn"]
    monkeypatch.setenv("ForensicSFNARN", state_machine_arn)
    input_json = json.loads((pathlib.Path(__file__).parents[0] / 'assets/guardduty_cc.json').read_text())
    invoke_guardduty_buildevent(event=input_json)