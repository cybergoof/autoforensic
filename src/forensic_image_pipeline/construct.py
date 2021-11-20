from aws_cdk import (
    aws_ec2 as ec2,
    core as cdk,
)
from .components import ImageComponents, ImageRecipe
from .infrastructure import InfrastructureConfig
from .pipeline import BuilderPipeline
from .distro import ImageDistro

class ForensicImageBuilder(cdk.Construct):

    def __init__(self, scope: cdk.Construct,
                 id: str,
                 vpc: ec2.Vpc=None,
                 image_name: str="DiskForensicRecipe",
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if vpc==None:
            self.vpc = self.build_vpc()
        else:
            self.vpc = vpc

        self.image_name = image_name
        self.component_construct = ImageComponents(self, "Component")
        self.image_recipe_construct = ImageRecipe(self, "ImageRecipe",
                                             image_component_construct=self.component_construct)
        self.configuration = InfrastructureConfig(self, "InfraConfig", vpc=self.vpc)
        self.image_distro = ImageDistro(self, "ImageDistro", image_name=self.image_name)
        self.image_pipeline = BuilderPipeline(self, "ImagePipeline",
                                         image_recipe=self.image_recipe_construct.recipe,
                                         infrastructure_config=self.configuration.configuration,
                                         distribution=self.image_distro.image_distro)

    def build_vpc(self)->ec2.Vpc:
        vpc = ec2.Vpc(self, id="AMI_VPC",
                           #cidr="10.1.0.0/16",
                           enable_dns_hostnames=True,
                           enable_dns_support=True,
                           max_azs=1,
                           subnet_configuration=[
                               ec2.SubnetConfiguration(
                                   cidr_mask=24,
                                   name="public",
                                   subnet_type=ec2.SubnetType.PUBLIC
                               ),
                           ])
        return vpc