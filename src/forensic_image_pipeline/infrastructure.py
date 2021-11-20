from aws_cdk import (
    aws_ec2 as ec2,
    aws_imagebuilder as imagebuilder,
    aws_iam as iam,

    core as cdk,
)


class InfrastructureConfig(cdk.Construct):
    def __init__(self, scope: cdk.Construct,
                 id: str,
                 vpc: ec2.Vpc,
                 terminate_on_failure: bool = True,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.vpc = vpc

        self.security_group = self.build_security_group()
        self.iam_role_profile = self.build_iam_role()
        self.configuration = self.build_config(terminate_on_failure=terminate_on_failure)

    def build_security_group(self) -> ec2.SecurityGroup:
        security_group = ec2.SecurityGroup(self, id="image_builder_sg",
                                           vpc=self.vpc,
                                           description="Security Group for building with Image Builder")
        security_group.add_ingress_rule(peer=ec2.Peer.any_ipv4(),
                                        connection=ec2.Port.tcp(22))
        return security_group

    def build_iam_role(self) -> iam.CfnInstanceProfile:
        role = iam.Role(self, "ForensicImageBuilderRole",
                        role_name="ForensicImageBuilder",
                        assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
                        description="Instance Role to provide access for Image Builder to create base image",
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                            iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilder")]
                        )
        profile = iam.CfnInstanceProfile(self, "ForensicImageBuilderProfile",
                                         roles=[role.role_name],
                                         instance_profile_name="ForensicImageBuilderProfile"
                                         )
        return profile

    def build_config(self, terminate_on_failure: bool = True) -> imagebuilder.CfnInfrastructureConfiguration:
        infrastructure_config = imagebuilder.CfnInfrastructureConfiguration(self,
                                                                            "DiskForensicInfrastructureConfig",
                                                                            name="DiskForensicInfrastructureConfig",
                                                                            description="Infrastructure config used to build disk forensic AMI",
                                                                            terminate_instance_on_failure=terminate_on_failure,
                                                                            instance_types=["t2.micro"],
                                                                            instance_profile_name=self.iam_role_profile.instance_profile_name,
                                                                            subnet_id=self.vpc.public_subnets[0].subnet_id,
                                                                            security_group_ids=[
                                                                                self.security_group.security_group_id]
                                                                            )
        return infrastructure_config
