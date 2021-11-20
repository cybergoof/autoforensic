'''
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import boto3
import os
import uuid
import random
import json
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    amiID = os.environ['AMI_ID']
    instanceProfile = os.environ['INSTANCE_PROFILE_NAME']
    targetVPC = os.environ['VPC_ID']
    securityGroup = os.environ['SECURITY_GROUP']
    instance_type = os.environ['INSTANCE_TYPE']

    try:
        print(event)
        event = event['DiskProcess']
        
        updatedEvent = event

        ec2 = boto3.client('ec2')
        
        userData = '#!/bin/bash\necho DESTINATION_BUCKET='+event['EvidenceBucket']+' >> /etc/environment\necho IMAGE_NAME='+event['SourceVolumeID']+' >> /etc/environment\necho INCIDENT_ID='+event['IncidentID']+' >> /etc/environment'
        AZS=event['VolumeAZ']
        print(AZS)
        subnets = ec2.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [
                        targetVPC,
                    ]
                },
                {
                    'Name': 'availability-zone',
                    'Values': [
                        event['VolumeAZ'],
                    ]
                }

            ]
        )
        print(subnets)
        supportedSubnets = []
        
        for sub in subnets['Subnets']:
            supportedSubnets.append(sub['SubnetId'])
        print(supportedSubnets)
        targetSubnet = random.choice(supportedSubnets)
        
        print("Creating forensic instance for volume {} in subnet {} in AZ {}".format(
            event['ForensicVolumeID'],
            targetSubnet,
            event['VolumeAZ']
        ))
        print(f"Running Instances with amiID={amiID}, instancetype={instance_type} securitygroup={securityGroup}, subnet={targetSubnet}, role={instanceProfile}")
        response = ec2.run_instances(
            ImageId=amiID,
            InstanceType=instance_type,
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[
                securityGroup,
            ],
            SubnetId=targetSubnet,
            UserData=userData,
            EbsOptimized=True,
            IamInstanceProfile={
                'Name': instanceProfile
            },
            InstanceInitiatedShutdownBehavior='terminate',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': event['InstanceID'] + "-" + event['SourceVolumeID']
                        },
                        {
                            'Key': 'InstanceID',
                            'Value': event['InstanceID']
                        },
                        {
                            'Key': 'VolumeID',
                            'Value': event['SourceVolumeID']
                        },
                        {
                            'Key': 'FindingID',
                            'Value': event['FindingID']
                        },
                        {
                            'Key': 'SourceDeviceName',
                            'Value': event['SourceDeviceName']
                        },
                    ]
                },
            ],
        )

        updatedEvent['ForensicInstances'] = []
        updatedEvent['DiskImageLocation'] = "s3://"+event['EvidenceBucket']+"/"+event['IncidentID']+"/disk_evidence/"+event['SourceVolumeID']+".image.dd"

        for item in response['Instances']:
            updatedEvent['ForensicInstances'].append(item['InstanceId'])

        return updatedEvent

    except Exception as e:
        print("Received error while processing runInstances request.  {}".format(
            repr(e)
        ))
        raise
