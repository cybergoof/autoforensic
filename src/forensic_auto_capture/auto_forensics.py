from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2
)
from typing import Union, List
from .forensics_resources.construct import ForensicResources
from .disk_functions.construct import DiskFunctions
from .step_function.construct import StepFunctionConstruct
from .invoke.construct import InvokeConstruct


class AutoForensicsConstruct(cdk.Construct):
    def __init__(self, scope: cdk.Construct, id: str,
                 member_account_id: str,
                 security_account_id: str,
                 region: str,
                 vpc: ec2.Vpc,
                 supported_azs: List[str],
                 readiness_log_name: str = "ForensicDiskReadiness") -> None:
        """
        Centralized CDK Construct that builds out the entire project
        """
        super().__init__(scope, id=id)
        self.member_account_id = member_account_id
        self.security_account_id = security_account_id
        self.region = region
        self.vpc = vpc
        self.supported_azs = supported_azs
        self._forensic_image = None
        self.forensic_resources_construct = None
        self.functions_construct = None

    @property
    def forensic_image(self): return self._forensic_image

    @forensic_image.setter
    def forensic_image(self, machine_image: ec2.IMachineImage):
        """
        Sets the Amazon Machine Image that will be used as the forensic image.
        :param machine_image: The machine image, in IMachineImage value, that will be the forensic
        VM image.
                """
        self._forensic_image = machine_image

    def build_forensic_resource(self, resource_stack: cdk.Stack = None):
        if resource_stack:
            stack = self.stack
        self.forensic_resources_construct = ForensicResources(self, "ForensicResource", vpc=self.vpc)

    def build_functions(self):
        self.functions_construct = DiskFunctions(scope=self,
                                                 id="DiskFunctions",
                                                 evidence_bucket=self.forensic_resources_construct.artifact_bucket,
                                                 audit_log_group=self.forensic_resources_construct.audit_log_group,
                                                 readiness_log_group=self.forensic_resources_construct.readiness_log_group,
                                                 evidence_key=self.forensic_resources_construct.encryption_key,
                                                 security_account_id=self.security_account_id,
                                                 supported_azs=self.supported_azs,
                                                 forensic_image=self._forensic_image,
                                                 ec2_forensic_profile=self.forensic_resources_construct.collection_profile,
                                                 ec2_forensic_role=self.forensic_resources_construct.collection_role,
                                                 forensic_security_group=self.forensic_resources_construct.forensic_security_group,
                                                 vpc=self.vpc)

    def build_step_function(self):
        self.step_function_construct = StepFunctionConstruct(scope=self, id="StepFunction",
                                                             functions_construct=self.functions_construct)
        return True

    def build_invoke(self):
        self.invoke_construct = InvokeConstruct(scope=self,
                                                id="InvokeConstruct",
                                                automation_role=self.functions_construct.automation_role,
                                                forensic_sfn=self.step_function_construct.state_machine)
        # Getting a circular reference problem, so hiding for now.
        # self.invoke_construct.node.add_dependency(self.step_function_construct.state_machine)
        # self.step_function_construct.state_machine.grant_execution(self.invoke_construct.disk_process.role,"states:StartExecution")
