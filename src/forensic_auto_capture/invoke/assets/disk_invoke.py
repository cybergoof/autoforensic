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

sfnArn = os.environ['ForensicSFNARN']


def buildEvent(event):
    triggeredEvent = {}
    triggeredEvent['AwsAccountId'] = event['AwsAccountId']
    triggeredEvent['Types'] = event['Types']
    triggeredEvent['FirstObservedAt'] = event['FirstObservedAt']
    triggeredEvent['LastObservedAt'] = event['LastObservedAt']
    triggeredEvent['CreatedAt'] = event['CreatedAt']
    triggeredEvent['UpdatedAt'] = event['UpdatedAt']
    triggeredEvent['Severity'] = event['Severity']
    triggeredEvent['Title'] = event['Title']
    triggeredEvent['Description'] = event['Description']
    triggeredEvent['FindingId'] = event['ProductFields']['aws/securityhub/FindingId']

    for item in event['Resources']:
        if item['Type'] == "AwsEc2Instance":
            triggeredEvent['Resource'] = {}
            arn = item['Id'].split("/")
            triggeredEvent['Resource']['Type'] = item['Type']
            triggeredEvent['Resource']['Arn'] = item['Id']
            triggeredEvent['Resource']['Id'] = arn[1]
            triggeredEvent['Resource']['Partition'] = item['Partition']
            triggeredEvent['Resource']['Region'] = item['Region']
            triggeredEvent['Resource']['Details'] = item['Details']
            if 'Tags' in item:
                triggeredEvent['Resource']['Tags'] = item['Tags']

            print(triggeredEvent)
            invokeStep(triggeredEvent)


def invokeStep(event):
    client = boto3.client('stepfunctions')

    response = client.start_execution(
        stateMachineArn=sfnArn,
        name=str(time.time()) + "-" + event['Resource']['Id'],
        input=json.dumps(event)
    )

    print(response)


def lambda_handler(event, context):
    print(event)
    for item in event['Resources']:
        ### Add More filters here to invoke only for certain evens such as different finding Types. event['Types']
        if item['Type'] == "AwsEc2Instance":
            triggeredEvent = buildEvent(event)
            break
