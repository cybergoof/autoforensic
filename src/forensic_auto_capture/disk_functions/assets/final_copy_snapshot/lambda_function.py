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

encryptionKey = os.environ['KMS_KEY']

def lambda_handler(event, context):
    try:
        
        event = event['DiskProcess']
        
        region = event['Region']
        findingID = event['FindingID']
        instanceID = event['InstanceID']
        snap = event['CopiedSnapshotID']
        updatedEvent = event

        ec2 = boto3.client('ec2')

        print("Copying snapshot {} in region {}".format(
            snap,
            region
        ))

        response = ec2.copy_snapshot(
            Description="Final Forensic Copy creation: {}".format(findingID),
            Encrypted=True,
            KmsKeyId=encryptionKey,
            SourceRegion=region,
            SourceSnapshotId=snap,
            TagSpecifications=[
                {
                    'ResourceType': 'snapshot',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'Forensic Copy Automated Snapshot creation'
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

        updatedEvent['FinalCopiedSnapshotID'] = response['SnapshotId']

        return updatedEvent

    except Exception as e:
        print("Received error while processing createSnapshot request.  {}".format(
            repr(e)
        ))
        raise