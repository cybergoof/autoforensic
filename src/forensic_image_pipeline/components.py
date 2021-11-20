import pathlib
from aws_cdk import (
    aws_imagebuilder as imagebuilder,
    aws_s3_assets as assets,
    core as cdk,
)


class ImageComponents(cdk.Construct):
    def __init__(self, scope: cdk.Construct,
                 id: str,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.component_array = []
        self.prep_component = self.build_component(name="prep-image", version="1.0.0", file_name="prep-image.yml")
        self.component_array.append(self.prep_component)

    def build_component(self, name: str, version: str, file_name: str) -> imagebuilder.CfnComponent:
        """
        build_component is used to create basic components from a shell script uploaded to an S3 bucket.
        :param name: The name of the component.
        :param version: The Version number
        :param file_name: The file name and potentially subdirectory under "asset"
        :return: returns a CfnComponent object
        """
        file_path = str(pathlib.Path(__file__).parents[0] / "assets" / file_name)
        component_asset = assets.Asset(self, id=name + "_asset", path=file_path)

        component = imagebuilder.CfnComponent(self,
                                              id=name,
                                              name=name,
                                              platform="Linux",
                                              version=version,
                                              supported_os_versions=["Ubuntu 20", "Ubuntu 18", "Ubuntu 16"],
                                              uri=component_asset.s3_object_url)
        return component


class ImageRecipe(cdk.Construct):
    def __init__(self, scope: cdk.Construct,
                 id: str,
                 image_component_construct: ImageComponents,
                 image_name="DiskForensicRecipe",
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.image_component_construct = image_component_construct
        self.region = cdk.Stack.of(self).region
        self.image_name = image_name
        self.recipe = self.build_recipe()


    def build_recipe(self) -> imagebuilder.CfnImageRecipe:
        component_list = []
        component_list.append(
            {"componentArn": f"arn:aws:imagebuilder:{self.region}:aws:component/amazon-cloudwatch-agent-linux/1.0.0/1"})
        component_list.append(
            {"componentArn": f"arn:aws:imagebuilder:{self.region}:aws:component/aws-cli-version-2-linux/1.0.0/1"})

        for component in self.image_component_construct.component_array:
            component_list.append({"componentArn": component.attr_arn})
        image_recipe = imagebuilder.CfnImageRecipe(self,
                                                   self.image_name,
                                                   name=self.image_name,
                                                   version="0.0.1",
                                                   components=component_list,
                                                   parent_image=f"arn:aws:imagebuilder:{self.region}:aws:image/ubuntu-server-20-lts-x86/x.x.x",
                                                   working_directory="/tmp"
                                                   )
        return image_recipe
