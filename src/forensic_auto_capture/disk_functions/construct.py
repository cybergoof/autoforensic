from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as _lambda
)
import pathlib
from typing import Union, List


class DiskFunctions(cdk.Construct):
    def __init__(self, scope: cdk.Construct, id: str,
                 evidence_bucket: s3.Bucket,
                 audit_log_group: logs.LogGroup,
                 readiness_log_group: logs.LogGroup,
                 evidence_key: kms.Key,
                 security_account_id: str,
                 supported_azs: List[str],
                 forensic_image: Union[ec2.MachineImage, ec2.IMachineImage],
                 ec2_forensic_profile: iam.CfnInstanceProfile,
                 ec2_forensic_role: iam.Role,
                 forensic_security_group: ec2.SecurityGroup,
                 vpc: ec2.Vpc) -> None:
        """
        Builds the Lambda functions used for this ".  Each Lambda function is a separate
        method of this construct class.
        :param evidence_bucket: The S3 bucket to send evidence logs and information.
        :param audit_log_group: Unsure
        :param evidence_key: KMS Key to encrypt/decrypt the data stored in the evidence bucket
        :param security_account_id: The ID of the security account. NOTE: Only tested with everything
        in a single account

        :ivar automation_role: The IAM role that assigned to the image forensics
        :ivar member_role: The IAM role used for cross account access
        """
        super().__init__(scope, id=id)

        # Need to create the Role
        self.audit_log_group = audit_log_group
        self.readiness_log_group = readiness_log_group
        self.evidence_key = evidence_key
        self.evidence_bucket = evidence_bucket
        self.security_account = security_account_id
        self.supported_azs = supported_azs
        self.forensic_image = forensic_image
        self.forensic_security_group = forensic_security_group
        self.ec2_forensic_profile = ec2_forensic_profile
        self.ec2_forensic_role = ec2_forensic_role
        self.vpc = vpc

        self.automation_role = self._disk_forensics_automation_role()
        self.member_role = self._disk_member_role()

        # TODO - I am not sure about this.  Each role seems to require the other role.  That feels strange
        self.automation_role.add_to_policy(iam.PolicyStatement(
            sid='STSPermissions',
            actions=['sts:AssumeRole'],
            resources=[self.member_role.role_arn],
            effect=iam.Effect.ALLOW
        ))

        self.check_copy_snapshot_lambda = self._build_check_copy_snapshot()
        self.check_snapshot_lambda = self._build_check_snapshot()
        self.create_snapshot_lambda = self._build_create_snapshot()
        self.copy_snapshot_lambda = self._build_copy_snapshot()
        self.share_snapshot_lambda = self._build_share_snapshot()
        self.final_copy_snapshot_lambda = self._build_final_copy_snapshot()
        self.final_check_copy_snapshot_lambda = self._build_final_check_snapshot()
        self.create_volume_lambda = self._build_create_volume()
        self.run_instance_lambda = self._build_run_instance()
        self.mount_volume_lambda = self._build_mount_volume()



    def _disk_forensics_automation_role(self) -> iam.Role:
        """
        diskFunctions.yaml -  line 16 - DiskForensicAutomationRole
        This Role is attached to all the Lambda functions for the purpose of performing the manipulating the running EC2's,
        using encryption keys, and writing to logs.
        This method depends on "self.member_role"

        TODO - Move from single IAM Role to specific roles to each Lambda function
        """
        role = iam.Role(self, "DiskForensicAutomationRole",
                        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                        description="Disk Forensic Automation Role to provide access for Lambda to invoke disk collection functions")
        role.add_to_policy(iam.PolicyStatement(
            sid='EC2Permissions',
            actions=['ec2:AttachVolume',
                     'ec2:CopySnapshot',
                     'ec2:CreateTags',
                     'ec2:CreateVolume',
                     'ec2:DescribeSnapshots',
                     'ec2:DescribeSubnets',
                     'ec2:RunInstances'
                     ],
            effect=iam.Effect.ALLOW,
            resources=["*"]
        ))
        role.add_to_policy(iam.PolicyStatement(
            sid='KMSPermissions',
            actions=['kms:CreateGrant',
                     'kms:Decrypt',
                     'kms:DescribeKey',
                     'kms:Encrypt',
                     'kms:GenerateDataKey*',
                     'kms:ReEncrypt*'
                     ],
            effect=iam.Effect.ALLOW,
            resources=[self.evidence_key.key_arn]
        ))
        role.add_to_policy(iam.PolicyStatement(
            sid='LogsPermissions',
            actions=['logs:CreateLogGroup',
                     'logs:CreateLogStream',
                     'logs:DescribeLogGroups',
                     'logs:DescribeLogStreams',
                     'logs:GetLogEvents',
                     'logs:PutLogEvents'
                     ],
            effect=iam.Effect.ALLOW,
            resources=["*"]
        ))
        role.add_to_policy(iam.PolicyStatement(
            sid='S3Permissions',
            actions=['s3:PutObject'],
            resources=[self.evidence_bucket.bucket_arn, f"{self.evidence_bucket.bucket_arn}/*"],
            effect=iam.Effect.ALLOW
        ))

        #role.grant_pass_role(self.ec2_forensic_role)
        self.ec2_forensic_role.grant_pass_role(role)
        return role

    def _disk_member_role(self) -> iam.Role:
        """
        diskMember.yaml, line 12, IRAutomationMemberRole creates role named IR-Automation-Member-Role
        build the member role.  This is taken from the IRAutomationMemberRole role in the diskMember.yaml CloudFormation template
        Allow the main account num/main account role name to assume role

        :return:
        """
        role = iam.Role(self, "MemberAutomationRole", assumed_by=self.automation_role)
        ec2_policy_statement = iam.PolicyStatement(
            sid='EC2Permissions',
            actions=['ec2:CopySnapshot',
                     'ec2:DescribeInstances',
                     'ec2:CreateTags',
                     'ec2:DescribeSnapshots',
                     'ec2:ModifySnapshotAttribute',
                     'ec2:CreateSnapshots',
                     'ec2:CreateSnapshot'
                     ],
            resources=["*"],
            effect=iam.Effect.ALLOW
        )
        role.add_to_policy(ec2_policy_statement)
        kms_policy_statement = iam.PolicyStatement(
            sid='KMSPermissions',
            actions=['kms:CreateGrant',
                     'kms:Decrypt',
                     'kms:DescribeKey',
                     'kms:Encrypt',
                     'kms:GenerateDataKey*',
                     'kms:ReEncrypt*'
                     ],
            resources=["*"],
            effect=iam.Effect.ALLOW
        )
        role.add_to_policy(kms_policy_statement)
        # TODO - This policy doesn't exist.  Need to figure out where it came from
        # role.add_managed_policy(iam.ManagedPolicy.from_managed_policy_name("IR-Automation-Member-Policy"))
        return role

    def _build_create_snapshot(self):
        """
        diskFunctions.yaml -  line 91 - DiskForensicsCreateSnapshot
        :return: 
        """
        lambda_function = _lambda.Function(self, f"CreateSnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           description="Create Snapshot Function",
                                           handler="lambda_function.lambda_handler",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/create_snapshot/')),
                                           timeout=cdk.Duration.seconds(180),
                                           role=self.automation_role,
                                           environment={"EVIDENCE_BUCKET": self.evidence_bucket.bucket_name,
                                                        "LOG_GROUP": self.audit_log_group.log_group_name,
                                                        "ROLE_NAME": self.member_role.role_name}
                                           )
        return lambda_function

    def _build_copy_snapshot(self):
        """
        diskFunctions.yaml -  line 130 - DiskForensicsCopySnapshot
        :return:
        """
        lambda_function = _lambda.Function(self, f"CopySnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Copy Snapshot Function",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/copy_snapshot/')),
                                           timeout=cdk.Duration.seconds(180),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"ROLE_NAME": self.member_role.role_name,
                                                        "KMS_KEY": self.evidence_key.key_arn}
                                           )
        return lambda_function

    def _build_check_snapshot(self) -> _lambda.Function:
        """
        Creates the Lambd function that checks to see if the snapshot has been created.
        Taken from the diskFunctions.yaml(111) CloudFormation template, lambda DiskForensicsCheckSnapshot
        :return:
        """
        lambda_function = _lambda.Function(self, f"CheckSnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Check Snapshot Function",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/check_snapshot/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"ROLE_NAME": self.member_role.role_name}
                                           )
        return lambda_function

    def _build_check_copy_snapshot(self) -> _lambda.Function:
        """
        Creates the Lambda function that checks to see if the copy of the snapshot has been made.
        Taken from the diskFunctions.yaml CloudFormation template - DiskForensicsCheckCopySnapshot
        :return: The lambda function created.
        """
        lambda_function = _lambda.Function(self, f"CheckCopySnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           description="Check Copy Snapshot Function",
                                           handler="lambda_function.lambda_handler",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/check_copy_snapshot/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"ROLE_NAME": self.member_role.role_name,
                                                        "KMS_KEY": self.evidence_key.key_arn}
                                           )
        return lambda_function

    def _build_share_snapshot(self):
        """
        diskFunctions.yaml -  line 166 - DiskForensicsShareSnapshot

        :return:
        """
        lambda_function = _lambda.Function(self, f"ShareSnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Share Snapshot Function",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/share_snapshot/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"ROLE_NAME": self.member_role.role_name,
                                                        "SECURITY_ACCOUNT": self.security_account}
                                           )
        return lambda_function

    def _build_final_copy_snapshot(self):
        """
        diskFunctions.yaml -  line 185 - DiskForensicsFinalCopySnapshot
        :return:
        """
        lambda_function = _lambda.Function(self, f"FinalCopySnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Final Copy Snapshot Function",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/final_copy_snapshot/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"KMS_KEY": self.evidence_key.key_arn}
                                           )
        return lambda_function

    def _build_final_check_snapshot(self):
        """
        diskFunctions.yaml -  line 204 - DiskForensicsFinalCheckSnapshot
        :return:
        """
        lambda_function = _lambda.Function(self, f"FinalCheckSnapshot",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Final Check Snapshot Function",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/final_check_snapshot/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role
                                           )
        return lambda_function

    def _build_create_volume(self):
        """
        diskFunctions.yaml -  line 218 - DiskForensicsCreateVolume
        :return:
        """
        lambda_function = _lambda.Function(self, f"CreateVolume",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Create Volume",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/create_volume/')),
                                           timeout=cdk.Duration.seconds(15),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"KMS_KEY": self.evidence_key.key_arn,
                                                        "SUPPORTED_AZS": f'["{self.supported_azs[0]}","{self.supported_azs[1]}"]'}
                                           )
        return lambda_function

    def _build_run_instance(self):
        """
        diskFunctions.yaml -  line 240 - DiskForensicsRunInstances
        :return:
        """
        lambda_function = _lambda.Function(self, f"RunInstances",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           handler="lambda_function.lambda_handler",
                                           description="Run Instances",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/run_instances/')),
                                           timeout=cdk.Duration.seconds(60),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"AMI_ID": self.forensic_image.get_image(self).image_id,
                                                        "VPC_ID": self.vpc.vpc_id,
                                                        "INSTANCE_PROFILE_NAME": self.ec2_forensic_profile.instance_profile_name,
                                                        "SECURITY_GROUP": self.forensic_security_group.security_group_id,
                                                        "INSTANCE_TYPE": "m5a.large"

                                                        }
                                           )
        return lambda_function

    def _build_mount_volume(self):
        """
        diskFunctions.yaml -  line 261 - DiskForensicsMountVolume
        :return:
        """
        lambda_function = _lambda.Function(self, f"MountVolume",
                                           runtime=_lambda.Runtime.PYTHON_3_8,
                                           description="Mount Volume Function",
                                           handler="lambda_function.lambda_handler",
                                           code=_lambda.Code.from_asset(
                                               str(pathlib.Path(__file__).parents[0] / 'assets/mount_volume/')),
                                           timeout=cdk.Duration.seconds(60),
                                           memory_size=128,
                                           role=self.automation_role,
                                           environment={"LOG_GROUP": self.audit_log_group.log_group_name,
                                                        "READINESS_LOG_GROUP": self.readiness_log_group.log_group_name}
                                           )
        return lambda_function

