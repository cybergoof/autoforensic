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
from datetime import datetime, timedelta
import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    LOGGER.info(event)
    logGroup = os.environ['LOG_GROUP']
    readiness_log_group = os.environ['READINESS_LOG_GROUP']
    print(event)
    try:

        event = event['DiskProcess']

        updatedEvent = event

        logs = boto3.client('logs')
        ec2 = boto3.client('ec2')
        s3 = boto3.client('s3')

        LOGGER.info(
            f"Checking to see if instance {event['ForensicInstances'][0]} is ready to mount volume {event['ForensicVolumeID']}")
        LOGGER.info(
            f"Fetching Logs from log group {readiness_log_group} and log stream {event['ForensicInstances'][0]}")

        # TODO - I had to switch startFromHead to True so that this would find the log
        incronStatus = logs.get_log_events(
            logGroupName=readiness_log_group,
            logStreamName=event['ForensicInstances'][0],
            startFromHead=True
        )

        if incronStatus['events'][0]['message'] == 'incron is running':
            LOGGER.info(f"Mounting volume {event['ForensicVolumeID']} on  instance {event['ForensicInstances'][0]}")

            vol = ec2.attach_volume(
                Device='/dev/sdf',
                InstanceId=event['ForensicInstances'][0],
                VolumeId=event['ForensicVolumeID']
            )
            LOGGER.info(f"Volume Mounted")
            key = event['IncidentID'] + '/' + 'disk_evidence/' + event['SourceVolumeID'] + '.processedResources.json'
            LOGGER.info(f"Writing the event to bucket {event['EvidenceBucket']} with key {key}")
            obj = s3.put_object(
                Body=json.dumps(event),
                Bucket=event['EvidenceBucket'],
                Key=key,
            )

            writeToCW(updatedEvent, logGroup=logGroup)

        else:
            raise RuntimeError("incron is not ready on instance {}.".format(
                event['ForensicInstances'][0]
            ))

        return updatedEvent

    except Exception as e:
        print("Received error while processing runInstances request.  {}".format(
            repr(e)
        ))
        raise


def writeToCW(logEvent, logGroup):
    logs = boto3.client('logs')

    try:
        LOGGER.info(f"For log group {logGroup}, creating log stream  {logEvent['IncidentID']}")
        logs.create_log_stream(logGroupName=logGroup, logStreamName=logEvent['IncidentID'])
    except logs.exceptions.ResourceAlreadyExistsException:
        LOGGER.info("The log already existed, so can move on.")
        pass

    tokenresponse = logs.describe_log_streams(
        logGroupName=logGroup,
        logStreamNamePrefix=logEvent['IncidentID'],
    )
    LOGGER.info(f"Writing to log Group {logGroup} and log stream {logEvent['IncidentID']}")
    if 'uploadSequenceToken' in tokenresponse['logStreams'][0]:
        LOGGER.info("uploadSequenceToken was found, so writing with sequenceToken")
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
