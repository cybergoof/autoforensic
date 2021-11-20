These are the step by step instructions for what is happening in this automated workflow.




## On the Forensic Disk
User data creates an /etc/environment file that holds three pieces of information:
- DESTINATION_BUCKET = The location of the bucket
- IMAGE_NAME = The volume
- INCIDENT_ID = the ID of this incident

The image is setup with a number of applications and cron jobs
- install [dc3dd](https://www.kali.org/tools/dc3dd/#:~:text=dc3dd%20is%20a%20patched%20version,pattern%20wiping).  A patched verion of [dd](https://en.wikipedia.org/wiki/Dd_(Unix)) that is used to convert and copy files
- install [incron](https://wiki.archlinux.org/title/Incron#:~:text=incron%20is%20a%20daemon%20which,in%20system%20and%20user%20tables).  A daemon which monitors file system events and executes commands.  Think crontab for file system changes.  We will use this to detect when the volume has successfully been mounted.

There are some scripts that are created on the base image
- /home/ubuntu/collector.sh - Collects data bout the attached volume and stores it in the DESTINATION appliation above.
- /home/ubuntu/orchestrator.sh - loads the environment variables from /etc/environment and executes collector.sh.  This is run by incrontab.
- /home/ubuntu/incronChecker.sh - Tests if the INCRON service is running and stores it into the /home/ubuntu/readiness.log.  This log is grabbed by the CloudWatch agent and loaded one of our Log Groups.  Which is monitored by our "Check Mount" to see if incron is loaded before starting to mount the file.  This script is run by crontab every second


The CloudWatch agent is configured to grab logs and send them to log groups for tracking, and also to provide action to the step function.
- /home/ubuntu/cloudwatch.log is sent to the group ForensicDiskCapture
- /home/ubuntu/readiness.log is sent to ForensicDiskReadiness log group



