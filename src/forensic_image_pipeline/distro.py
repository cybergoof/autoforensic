from aws_cdk import (
    aws_imagebuilder as imagebuilder,
    core as cdk,
)


class ImageDistro(cdk.Construct):

    def __init__(self, scope: cdk.Construct,
                 id: str,
                 image_name="DiskForensicRecipe",
                 regions=["us-east-1", "us-west-1", "us-east-2", "us-west-2", "ca-central-1"],
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.regions = regions
        self.image_distro = self.build_image_distro(name=image_name)

    def build_image_distro(self, name: str) -> imagebuilder.CfnDistributionConfiguration:
        distributions = []
        for region in self.regions:
            distributions.append(imagebuilder.CfnDistributionConfiguration.DistributionProperty(
                region=region,
                ami_distribution_configuration={'Name': name + ' {{imagebuilder:buildDate}}',
                                                'LaunchPermissionConfiguration': {"UserGroups": ["all"]}
                                                # 'LaunchPermissionConfiguration': {"UserIds": ["502579121406"]}
                                                }
            ))

        distro_config = imagebuilder.CfnDistributionConfiguration(self, id=name, name=name, distributions=distributions)
        return distro_config
