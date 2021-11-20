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
import time
import json

roleName = os.environ['ROLE_NAME']
evidenceBucket = os.environ['EVIDENCE_BUCKET']
logGroup = os.environ['LOG_GROUP']

def lambda_handler(event, context):
    try:
        event = event['DiskProcess']

        instanceID = event['Resource']['Id']
        region = event['Resource']['Region']
        findingID = event['FindingId']
        incidentID = event['FindingId'].split('finding/')[1]
        event['EvidenceBucket'] = evidenceBucket
        event['IncidentID'] = incidentID

        client = boto3.client('sts')

        response = client.assume_role(
            RoleArn='arn:{}:iam::{}:role/{}'.format(
                os.environ.get("Partition", 'aws'),
                event['AwsAccountId'],
                roleName
            ),
            RoleSessionName="{}-snapshot-creation".format(
                instanceID
            )
        )

        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )

        ec2 = session.client('ec2', region_name=region)

        print("Received request to create snapshots for instance {} in region {}".format(
            instanceID,
            region
        ))

        response = ec2.describe_instances(
            InstanceIds=[instanceID]
        )

        Output = event
        Output['CapturedSnapshots'] = []

        ######## If looking for simplicity and the least amount of API calls, consider using createSnapshots API. If additional filtering is required, use the iterative approach below ########
        #snaps = ec2.create_snapshots(
        #    Description="Automated Snapshot creation: {}".format(findingID),
        #    InstanceSpecification={
        #        'InstanceId': instanceID,
        #        'ExcludeBootVolume': False
        #    }
        #)

        #for snap in snaps['Snapshots']:
        #    Output['CapturedSnapshots'].append({'SourceSnapshotID': snap['SnapshotId'], 'SourceVolumeID': snap['VolumeId'], 'VolumeSize': snap['VolumeSize'], 'InstanceID': instanceID, 'FindingID': findingID, 'AccountID': event['AwsAccountId'], 'Region': region})


        for res in response['Reservations']:
            for item in res['Instances']:
                for vol in item['BlockDeviceMappings']:
                    if vol['Ebs']['Status'] == 'attached':
                        # create snapshot
                        print("Initiating snapshot creation for volume {} on instance {} in region {}".format(
                            vol['Ebs']['VolumeId'],
                            instanceID,
                            region
                        ))

                        snap = ec2.create_snapshot(
                            Description="Automated Snapshot creation: {}".format(findingID),
                            VolumeId=vol['Ebs']['VolumeId'],
                            TagSpecifications=[
                                {
                                    'ResourceType': 'snapshot',
                                    'Tags': [
                                        {
                                            'Key': 'Name',
                                            'Value': 'Forensic Automated Snapshot creation'
                                        },
                                        {
                                            'Key': 'InstanceID',
                                            'Value': instanceID
                                        },
                                        {
                                            'Key': 'VolumeID',
                                            'Value': vol['Ebs']['VolumeId']
                                        },
                                        {
                                            'Key': 'FindingID',
                                            'Value': findingID
                                        },
                                        {
                                            'Key': 'SourceDeviceName',
                                            'Value': vol['DeviceName']
                                        }
                                    ]
                                }
                            ]
                        )

                        Output['CapturedSnapshots'].append({'SourceSnapshotID': snap['SnapshotId'], 'SourceVolumeID': snap['VolumeId'], 'SourceDeviceName': vol['DeviceName'], 'VolumeSize': snap['VolumeSize'], 'InstanceID': instanceID, 'FindingID': findingID, 'IncidentID': incidentID, 'AccountID': event['AwsAccountId'], 'Region': region, 'EvidenceBucket': evidenceBucket})

        writeToCW(Output)

        return Output

    except Exception as e:
        print("Received error while processing createSnapshot request.  {}".format(
            repr(e)
        ))
        raise

def writeToCW(logEvent):

    logs = boto3.client('logs')

    try:
       logs.create_log_stream(logGroupName=logGroup, logStreamName=logEvent['IncidentID'])
    except logs.exceptions.ResourceAlreadyExistsException:
       pass

    tokenresponse = logs.describe_log_streams(
        logGroupName=logGroup,
        logStreamNamePrefix=logEvent['IncidentID'],
    )

    if 'uploadSequenceToken' in tokenresponse['logStreams'][0]:
        response = logs.put_log_events(
            logGroupName=logGroup,
            logStreamName=logEvent['IncidentID'],
            logEvents=[
                {
                    'timestamp': int(round(time.time() * 1000)),
                    'message': json.dumps(logEvent)
                },
            ],
            sequenceToken=tokenresponse['logStreams'][0]['uploadSequenceToken']
        )
    else:
        response = logs.put_log_events(
            logGroupName=logGroup,
            logStreamName=logEvent['IncidentID'],
            logEvents=[
                {
                    'timestamp': int(round(time.time() * 1000)),
                    'message': json.dumps(logEvent)
                },
            ]
        )
