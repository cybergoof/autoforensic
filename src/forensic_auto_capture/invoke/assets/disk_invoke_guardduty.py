#  Copyright 2017 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This file is licensed to you under the AWS Customer Agreement (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at http://aws.amazon.com/agreement/ .
#  This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
#  See the License for the specific language governing permissions and limitations under the License.

import json
import os
import boto3
import time




def buildEvent(event):
    triggeredEvent = {}
    triggeredEvent['AwsAccountId'] = event["detail"]['accountId']
    triggeredEvent['Types'] = event["detail"]['type']
    triggeredEvent['FirstObservedAt'] = event["detail"]['createdAt']
    triggeredEvent['LastObservedAt'] = event["detail"]['updatedAt']
    triggeredEvent['CreatedAt'] = event["detail"]['createdAt']
    triggeredEvent['UpdatedAt'] = event["detail"]['updatedAt']
    triggeredEvent['Severity'] = event["detail"]['severity']
    triggeredEvent['Title'] = event["detail"]['title']
    triggeredEvent['Description'] = event["detail"]['description']
    triggeredEvent['FindingId'] = f"finding/{event['detail']['id']}"
    triggeredEvent['Resource'] = {}
    triggeredEvent['Resource']['Type'] = event["detail"]['resource']['resourceType']
    triggeredEvent['Resource']['Arn'] = ""
    triggeredEvent['Resource']['Id'] = event["detail"]['resource']['instanceDetails']['instanceId']
    triggeredEvent['Resource']['Partition'] = event["detail"]['partition']
    triggeredEvent['Resource']['Region'] = event["detail"]['region']
    triggeredEvent['Resource']['Details'] = event["detail"]['resource']["instanceDetails"]
    if 'Tags' in event["detail"]["resource"]["instanceDetails"]:
        triggeredEvent['Resource']['Tags'] = event["detail"]["resource"]["instanceDetails"]['Tags']

    print(triggeredEvent)
    # TODO - Removing so we can test more easily
    invokeStep(triggeredEvent)


def invokeStep(event):
    client = boto3.client('stepfunctions')
    sfnArn = os.environ['ForensicSFNARN']
    response = client.start_execution(
        stateMachineArn=sfnArn,
        name=str(time.time()) + "-" + event['Resource']['Id'],
        input=json.dumps(event)
    )

    print(response)


def lambda_handler(event, context):
    print(event)
        ### Add More filters here to invoke only for certain evens such as different finding Types. event['Types']
    if (event['source'] == "aws.guardduty") and (event['detail']['resource']['resourceType'] == "Instance"):
        triggeredEvent = buildEvent(event)
