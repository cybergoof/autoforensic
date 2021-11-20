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

encryptionKey = os.environ['KMS_KEY']
availabilityZonesSuppported = os.environ['SUPPORTED_AZS']

def lambda_handler(event, context):
    print(event)
    try:
        
        event = event['DiskProcess']
        
        snap = event['FinalCopiedSnapshotID']
        region = event['Region']
        azList = json.loads(availabilityZonesSuppported)
        
        if event['VolumeSize'] >= 500:
            volumeType = 'st1'
        else:
            volumeType = 'standard'
        
        updatedEvent = event
        
        ec2 = boto3.client('ec2')
        
        print("Creating forensic volume from snapshot {} in region {}".format(
            snap,
            region
        ))
        
        response = ec2.create_volume(
            AvailabilityZone=random.choice(azList),
            SnapshotId=snap,
            Encrypted=True,
            KmsKeyId=encryptionKey,
            VolumeType=volumeType,
            TagSpecifications=[
                {
                    "ResourceType": "volume",
                    "Tags": [
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
                        }
                    ]
                }
            ]
        )
        
        updatedEvent['ForensicVolumeID'] = response['VolumeId']
        updatedEvent['VolumeAZ'] = response['AvailabilityZone']

        return updatedEvent

    except Exception as e:
        print("Received error while processing createVolume request.  {}".format(
            repr(e)
        ))
        raise
