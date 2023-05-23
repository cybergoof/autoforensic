from aws_cdk import (
    core as cdk,
    aws_s3 as s3,
    aws_kms as kms,
    aws_logs as logs,
    aws_iam as iam,
    aws_ec2 as ec2
)

class ForensicResources(cdk.Construct):
    def __init__(self, scope: cdk.Construct, id: str, vpc: [ec2.Vpc, ec2.IVpc],
                 readiness_log_name: str = "ForensicDiskReadiness") -> None:
        """
        Build out the forensic resources as mirrored in the forensicsResources.yaml CloudFormation file
        """
        super().__init__(scope, id=id)

        self.encryption_key = None
        self.artifact_bucket = None
        self.audit_log_group = None
        self.readiness_log_name = readiness_log_name
        self.readiness_log_group = None
        self.capture_log_group = None
        self.collection_role = None
        self.forensic_security_group = None
        self.collection_profile = None
        self.vpc = vpc
        self.build_key_bucket()
        self.build_logs()
        self.build_role()
        self.build_security_group()
        return

    def build_key_bucket(self) -> None:
        policy_document = iam.PolicyDocument(statements=[
            iam.PolicyStatement(
                actions=["kms:*"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        ])
        self.encryption_key = kms.Key(self, "ForensicKey", alias="alias/ForensicEncryptionKey",
                                      policy=policy_document)
        # Versioning should be turned on for production systems, but it is harder for dev.  more to delete
        self.artifact_bucket = s3.Bucket(self, "ArtifactBucket",
                                         encryption_key=self.encryption_key,
                                         encryption=s3.BucketEncryption.KMS,
                                         versioned=False,
                                         removal_policy=cdk.RemovalPolicy.DESTROY,
                                         #auto_delete_objects=True
                                         )
        return

    def build_logs(self) -> None:
        self.audit_log_group = logs.LogGroup(self, "ForensicAuditLogGroup",
                                             log_group_name="ForensicAuditLogGroup",
                                             removal_policy=cdk.RemovalPolicy.DESTROY)
        # Was ForensicReadinessLogGroup
        self.readiness_log_group = logs.LogGroup(self, "ForensicReadinessLogGroup",
                                                 log_group_name=self.readiness_log_name,
                                                 removal_policy=cdk.RemovalPolicy.DESTROY)

        self.capture_log_group = logs.LogGroup(self, "ForensicCaptureLogGroup",
                                               log_group_name="ForensicCaptureLogGroup",
                                               removal_policy=cdk.RemovalPolicy.DESTROY)
        return

    def build_role(self) -> None:
        self.collection_role = iam.Role(self, "EC2ForensicsCollectionRole",
                                        assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                                        description="Role to provide access for EC2 to write forensic artifacts",
                                        role_name="EC2ForensicRole",
                                        managed_policies=[
                                            iam.ManagedPolicy.from_aws_managed_policy_name(
                                                "AmazonSSMManagedInstanceCore")
                                        ]
                                        )
        self.collection_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[self.encryption_key.key_arn],
            actions=["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"]
        ))
        self.collection_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["logs:CreateLogStream", "logs:DescribeLogGroups", "logs:DescribeLogStreams", "logs:PutLogEvents"]
        ))
        self.collection_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[self.artifact_bucket.bucket_arn, f"{self.artifact_bucket.bucket_arn}/*"],
            actions=["s3:PutObject"]
        ))

        self.collection_profile = iam.CfnInstanceProfile(self, "CollectionProfile",
                                                         roles=[self.collection_role.role_name],
                                                         instance_profile_name="EC2ForensicProfile")

        return

    def build_security_group(self) -> None:
        self.forensic_security_group = ec2.SecurityGroup(self, "CaptureSecurityGroup",
                                                         vpc=self.vpc,
                                                         allow_all_outbound=True,
                                                         security_group_name="ForensicsInstanceSG")
        self.forensic_security_group.add_egress_rule(
            peer=ec2.Peer.ipv4("0.0.0.0/0"),
            connection=ec2.Port.all_icmp(),
            description="Allow output to S3 and Logs to client host"
        )
        return
