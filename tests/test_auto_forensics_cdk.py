"""
Unit test for the CDK constructs
"""
import pytest
from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
)

import constants
import collections
from src.forensic_auto_capture.auto_forensics import AutoForensicsConstruct
StackEnvironment = collections.namedtuple('StackEnvironment', ['stack', 'vpc'])

"""
Testing the Auto Forensics
"""


@pytest.fixture(scope="session")
def stack_environment():
    app = cdk.App()
    stack = cdk.Stack(app, "TestDeploySimulation", env=cdk.Environment(account=constants.ACCOUNT_ID,
                                                                       region=constants.REGION))
    vpc = ec2.Vpc.from_lookup(stack, "TestVPC", vpc_name=constants.VPC_NAME)
    yield StackEnvironment(stack=stack, vpc=vpc)
    app.synth()


@pytest.fixture(scope="session")
def auto_forensics_construct(stack_environment):
    return AutoForensicsConstruct(stack_environment.stack, "UNITAutoForensics",
                                  member_account_id=constants.ACCOUNT_ID,
                                  security_account_id=constants.ACCOUNT_ID,
                                  region=constants.REGION,
                                  vpc=stack_environment.vpc,
                                  supported_azs=constants.SUPPORTED_AZS)


"""
Testing the forensics_construct
"""

@pytest.fixture(scope="session")
def machine_image():
   return ec2.LookupMachineImage(name=constants.MACHINE_LOOKUP_NAME, owners=[constants.IMAGE_ACCOUNT])


@pytest.mark.order(1)
def test_forensic_image(auto_forensics_construct, machine_image):
    auto_forensics_construct.forensic_image = machine_image
    assert True

@pytest.mark.order(2)
def test_forensic_resource(auto_forensics_construct):
    auto_forensics_construct.build_forensic_resource()
    assert True

@pytest.mark.order(3)
def test_build_functions(auto_forensics_construct):
    auto_forensics_construct.build_functions()
    assert True

@pytest.mark.order(4)
def test_build_step_function(auto_forensics_construct):
    auto_forensics_construct.build_step_function()
    assert True

@pytest.mark.order(5)
def test_build_invoke(auto_forensics_construct, machine_image):
    auto_forensics_construct.build_invoke()
    auto_forensics_construct.invoke_construct.invoke_from_securityhub()
    assert True
