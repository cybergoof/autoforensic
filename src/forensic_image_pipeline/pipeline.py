import os
from aws_cdk import (
    aws_imagebuilder as imagebuilder,
    core as cdk,
)


class BuilderPipeline(cdk.Construct):

    def __init__(self, scope: cdk.Construct,
                 id: str,
                 image_recipe: imagebuilder.CfnImageRecipe,
                 infrastructure_config: imagebuilder.CfnInfrastructureConfiguration,
                 distribution: imagebuilder.CfnDistributionConfiguration = None,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.pipeline = self.build_pipeline(image_recipe=image_recipe,
                                            infrastructure_config=infrastructure_config,
                                            distribution=distribution)

    def build_pipeline(self, image_recipe: imagebuilder.CfnImageRecipe,
                       infrastructure_config: imagebuilder.CfnInfrastructureConfiguration,
                       distribution: imagebuilder.CfnDistributionConfiguration = None) -> imagebuilder.CfnImagePipeline:
        if distribution is None:
            distro_attr = None
        else:
            distro_attr = distribution.attr_arn

        pipeline = imagebuilder.CfnImagePipeline(self, "forensic_pipeline",
                                                 name="forensic_pipeline",
                                                 description="Disk forensic AMI build pipeline",
                                                 enhanced_image_metadata_enabled=True,
                                                 image_recipe_arn=image_recipe.attr_arn,
                                                 distribution_configuration_arn=distro_attr,
                                                 infrastructure_configuration_arn=infrastructure_config.attr_arn,
                                                 schedule={
                                                     "pipelineExecutionStartCondition": "EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE",
                                                     "scheduleExpression": "cron(10,20,30,40,50 * * * ? *)"})

        return pipeline
