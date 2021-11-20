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

roleName = os.environ['ROLE_NAME']
encryptionKey = os.environ['KMS_KEY']

def lambda_handler(event, context):
    try:

        event = event['DiskProcess']
        
        region = event['Region']
        findingID = event['FindingID']
        instanceID = event['InstanceID']
        snap = event['SourceSnapshotID']
        updatedEvent = event

        client = boto3.client('sts')

        response = client.assume_role(
            RoleArn='arn:{}:iam::{}:role/{}'.format(
                os.environ.get("Partition", 'aws'),
                event['AccountID'],
                roleName
            ),
            RoleSessionName="{}-{}-snapshot-copy".format(
                instanceID,
                snap
            )
        )
        print("assume role")
        print(response)
        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )

        ec2 = session.client('ec2', region_name=region)

        print("Copying snapshot {} in region {}".format(
            snap,
            region
        ))

        response = ec2.copy_snapshot(
            Description="Forensic Copy Automated Snapshot creation: {}".format(findingID),
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
        
        print(response)
        
        updatedEvent['CopiedSnapshotID'] = response['SnapshotId']
        updatedEvent['EncryptionKey'] = encryptionKey

        return updatedEvent

    except Exception as e:
        print("Received error while processing createSnapshot request.  {}".format(
            repr(e)
        ))
        raise
