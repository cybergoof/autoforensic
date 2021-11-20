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
from src.forensic_image_pipeline import ForensicImageBuilder
from src.forensic_image_pipeline.components import ImageComponents, ImageRecipe
from src.forensic_image_pipeline.infrastructure import InfrastructureConfig
from src.forensic_image_pipeline.pipeline import BuilderPipeline
from src.forensic_image_pipeline.distro import ImageDistro

StackEnvironment = collections.namedtuple('StackEnvironment', ['stack', 'vpc'])


@pytest.fixture()
def stack_environment():
    app = cdk.App()
    stack = cdk.Stack(app, "TestDeploySimulation", env=cdk.Environment(account=constants.ACCOUNT_ID,
                                                                       region=constants.REGION))
    vpc = ec2.Vpc.from_lookup(stack, "TestVPC", vpc_name=constants.VPC_NAME)
    yield StackEnvironment(stack=stack, vpc=vpc)
    app.synth()


@pytest.fixture()
def base_machine_image():
    return ec2.LookupMachineImage(name=constants.MACHINE_LOOKUP_NAME, owners=[constants.IMAGE_ACCOUNT])


@pytest.fixture()
def vpc(stack_environment):
    return ec2.Vpc.from_lookup(stack_environment.stack, "VPC", vpc_name=constants.VPC_NAME)

@pytest.fixture()
def vpc_request(stack_environment, request):
    if request.param:
        return None
    else:
        return ec2.Vpc.from_lookup(stack_environment.stack, "VPC", vpc_name=constants.VPC_NAME)

@pytest.mark.parametrize("vpc_request", [True, False], indirect = True)
def test_image_builder(stack_environment, vpc_request):
    image_construct = ForensicImageBuilder(stack_environment.stack, "UNITImagePipeline",
                                           vpc=vpc_request
                                           )
    assert True


def test_image_components(stack_environment):
    component_construct = ImageComponents(stack_environment.stack, "Component")
    component_construct.build_component(name="prepImage", version="1.0.0", file_name="prep-image.yml")
    assert True


def test_image_recipe(stack_environment):
    component_construct = ImageComponents(stack_environment.stack, "Component")
    image_recipe_construct = ImageRecipe(stack_environment.stack, "ImageRecipe",
                                         image_component_construct=component_construct)
    assert True


def test_infrastructure(stack_environment, vpc):
    configuration = InfrastructureConfig(stack_environment.stack, "InfraConfig", vpc=vpc)
    assert True


def test_distro(stack_environment):
    image_distro = ImageDistro(stack_environment.stack, "ImageDistro")
    assert True


def test_pipeline(stack_environment, vpc):
    component_construct = ImageComponents(stack_environment.stack, "Component")
    image_recipe_construct = ImageRecipe(stack_environment.stack, "ImageRecipe",
                                         image_component_construct=component_construct)
    configuration = InfrastructureConfig(stack_environment.stack, "InfraConfig", vpc=vpc)
    image_distro = ImageDistro(stack_environment.stack, "ImageDistro")
    image_pipeline = BuilderPipeline(stack_environment.stack, "ImagePipeline",
                                     image_recipe=image_recipe_construct.recipe,
                                     infrastructure_config=configuration.configuration,
                                     distribution=image_distro.image_distro)
    assert True
