from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2
)
import constants
from src.forensic_auto_capture.auto_forensics import AutoForensicsConstruct
from src.forensic_image_pipeline import ForensicImageBuilder

app = cdk.App()


image_stack = cdk.Stack(app, "ImageBuilderStack", env=constants.MEMBER_ENVIRONMENT)
#vpc = ec2.Vpc.from_lookup(image_stack, "VPC", vpc_name=constants.VPC_NAME)
image_builder_construct = ForensicImageBuilder(image_stack, "DiskForensicRecipe",
                                               image_name="DiskForensicRecipe")




stack = cdk.Stack(app, "AutoForensicTest", env=constants.MEMBER_ENVIRONMENT)
stack.add_dependency(target=image_stack)
vpc = ec2.Vpc.from_lookup(stack, "VPC", vpc_name=constants.VPC_NAME)

# We could pull some specific VM.  But fr thi


forensic_image = ec2.LookupMachineImage(name="DiskForensicRecipe*", owners=[constants.IMAGE_ACCOUNT])

auto_forensics_construct = AutoForensicsConstruct(stack, "Builder",
                                                  member_account_id=constants.ACCOUNT_ID,
                                                  security_account_id=constants.ACCOUNT_ID,
                                                  region=constants.REGION,
                                                  vpc=vpc,
                                                  supported_azs=constants.SUPPORTED_AZS,
                                                  readiness_log_name=constants.READINESS_LOG_NAME)


auto_forensics_construct.forensic_image = forensic_image
auto_forensics_construct.build_forensic_resource()
auto_forensics_construct.build_functions()
auto_forensics_construct.build_step_function()
auto_forensics_construct.build_invoke()

app.synth()
