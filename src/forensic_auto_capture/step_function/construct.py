from aws_cdk import (
    core as cdk,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_sns as sns,
    aws_lambda as _lambda
)
from ..disk_functions.construct import DiskFunctions

# TODO - May need to assign an IAM role to the step function
class StepFunctionConstruct(cdk.Construct):
    def __init__(self, scope: cdk.Construct, id: str, functions_construct: DiskFunctions):
        super().__init__(scope, id=id)
        self.functions_construct = functions_construct

        self._build_other_tasks()
        self._build_all_lambda_tasks()
        self._iterator_group = self._create_iterator_group()
        self._map_state = self._create_map_state()
        self._process_incident_task = self._create_process_incident_task()
        self._state_definition = self.build_state_machine()
        self.state_machine = stepfunctions.StateMachine(self, "StateMachine", definition=self._state_definition,
                                                         timeout=cdk.Duration.minutes(20))

    def _build_other_tasks(self) -> None:
        self._error_alert_sns = sns.Topic(scope=self, id="ErrorTopic", display_name="Disk Forensics Error Topic",
                                          topic_name="DiskForensicsErrorTopic")
        self._error_alert_task = tasks.SnsPublish(self, "PublishError", topic=self._error_alert_sns,
                                                  message=stepfunctions.TaskInput.from_text('"Input.$":"$.error-info"'))
        self._map_error_alert_task = tasks.SnsPublish(self, "MapErrorAlert", topic=self._error_alert_sns,
                                                      message=stepfunctions.TaskInput.from_text(
                                                          '"Input.$":"$.error-info"'))

        self._instance_wait_task = stepfunctions.Wait(self,
                                                      "CreateInstanceWait",
                                                      time=stepfunctions.WaitTime.duration(cdk.Duration.seconds(120)))

    def _build_all_lambda_tasks(self) -> None:
        self._create_snapshot_task = self._create_lambda_task("CreateSnapshotTask",
                                                              function=self.functions_construct.create_snapshot_lambda,
                                                              task_input={"DiskProcess.$": "$"})

        self._check_snapshot_task = self._create_lambda_task("CheckSnapshotTask",
                                                             self.functions_construct.check_snapshot_lambda,
                                                             retry=True)
        self._copy_snapshot_task = self._create_lambda_task("CopySnapshotTask",
                                                            function=self.functions_construct.copy_snapshot_lambda,
                                                            task_input={"DiskProcess.$": "$"})
        self._check_copy_snapshot_task = self._create_lambda_task("CheckCopySnapshotTask",
                                                                  function=self.functions_construct.check_copy_snapshot_lambda,
                                                                  catch_alert=self._map_error_alert_task,
                                                                  retry=True)

        self._share_snapshot_task = self._create_lambda_task("ShareSnapshotTask",
                                                             function=self.functions_construct.share_snapshot_lambda,
                                                             catch_alert=self._map_error_alert_task)
        self._final_copy_snapshot_task = self._create_lambda_task("FinalCopySnapshot",
                                                                  function=self.functions_construct.final_copy_snapshot_lambda,
                                                                  catch_alert=self._map_error_alert_task)
        self._final_check_snapshot_task = self._create_lambda_task("FinalCheckSnapshot",
                                                                   function=self.functions_construct.final_check_copy_snapshot_lambda,
                                                                   catch_alert=self._map_error_alert_task,
                                                                   retry=True)
        self._create_volume_task = self._create_lambda_task("CreateVolume",
                                                            function=self.functions_construct.create_volume_lambda,
                                                            catch_alert=self._map_error_alert_task)
        self._run_instance_task = self._create_lambda_task("RunInstance",
                                                           function=self.functions_construct.run_instance_lambda,
                                                           catch_alert=self._map_error_alert_task)
        self._mount_volume_task = self._create_lambda_task("MountVolume",
                                                           function=self.functions_construct.mount_volume_lambda,
                                                           catch_alert=self._map_error_alert_task,
                                                           retry=True)

    def _create_error_sns(self) -> sns.Topic:
        return sns.Topic(scope=self, id="ErrorTopic", display_name="Disk Forensics Error Topic",
                         topic_name="DiskForensicsErrorTopic")

    def _create_lambda_task(self, id: str, function: _lambda.Function,
                            task_input: {} = {"DiskProcess.$": "$.Payload"},
                            catch_alert: stepfunctions.Task = None,
                            retry: bool = False) -> tasks:
        if task_input is None:
            payload = None
        else:
            payload = stepfunctions.TaskInput.from_object(task_input)
        task = tasks.LambdaInvoke(self, id=id,
                                  lambda_function=function,
                                  payload=payload,
                                  retry_on_service_exceptions=False)
        if catch_alert:
            task.add_catch(handler=catch_alert,
                           errors=["States.ALL"],
                           result_path="$.error-info")
        if retry:
            task.add_retry(errors=["RuntimeError"],
                           interval=cdk.Duration.seconds(30),
                           backoff_rate=1.5,
                           max_attempts=60)
        return task

    def _create_map_state(self) -> stepfunctions.Map:
        map_state = stepfunctions.Map(self, "ProcessSnaps",
                                      max_concurrency=0,
                                      items_path=stepfunctions.JsonPath.string_at("$.Payload.CapturedSnapshots"))
        map_state.iterator(self._iterator_group)
        return map_state

    def _create_iterator_group(self) -> stepfunctions.Chain:
        state_definition = stepfunctions.Chain \
            .start(self._copy_snapshot_task) \
            .next(self._check_copy_snapshot_task) \
            .next(self._share_snapshot_task) \
            .next(self._final_copy_snapshot_task) \
            .next(self._final_check_snapshot_task) \
            .next(self._create_volume_task) \
            .next(self._run_instance_task) \
            .next(self._instance_wait_task) \
            .next(self._mount_volume_task)
        return state_definition

    def _create_process_incident_task(self) -> tasks:
        parallel = stepfunctions.Parallel(self, "ProcessActions")
        # TODO - The branch is here to support additional applications such as grabbing logs, performing memory capture, etc

        parallel.branch(self._map_state)
        return parallel

    def build_state_machine(self):
        state_definition = stepfunctions.Chain \
            .start(self._create_snapshot_task) \
            .next(self._check_snapshot_task) \
            .next(self._process_incident_task)
        return state_definition
