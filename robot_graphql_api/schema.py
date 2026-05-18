from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import strawberry
from strawberry.scalars import JSON

from api.models import (
    Drone,
    Mission,
    MissionParticipation,
    Robot,
    Task,
    TechnicalSpecification,
    TelemetryRecord,
)
from robot_graphql_api.types import (
    DroneType,
    LocationType,
    MissionParticipationType,
    MissionStatus,
    MissionType,
    ParticipationRole,
    RobotType,
    TaskType,
    TechnicalSpecificationType,
    TelemetryDataType,
    TelemetryRecordType,
)


def _robot_technical_specification(robot: Robot) -> Optional[TechnicalSpecificationType]:
    try:
        return to_technical_specification_type(robot.technical_specification, nest_agent=False)
    except TechnicalSpecification.DoesNotExist:
        return None


def _drone_technical_specification(drone: Drone) -> Optional[TechnicalSpecificationType]:
    try:
        return to_technical_specification_type(drone.technical_specification, nest_agent=False)
    except TechnicalSpecification.DoesNotExist:
        return None


def to_robot_type(robot: Robot, *, nest_spec: bool = True) -> RobotType:
    spec = _robot_technical_specification(robot) if nest_spec else None
    return RobotType(
        id=str(robot.id),
        name=robot.name,
        serial_number=robot.serial_number,
        battery_level=robot.battery_level,
        max_speed=robot.max_speed,
        is_active=robot.is_active,
        created_at=robot.created_at,
        technical_specification=spec,
    )


def to_drone_type(drone: Drone, *, nest_spec: bool = True) -> DroneType:
    spec = _drone_technical_specification(drone) if nest_spec else None
    return DroneType(
        id=str(drone.id),
        name=drone.name,
        serial_number=drone.serial_number,
        max_altitude=drone.max_altitude,
        payload_capacity=drone.payload_capacity,
        battery_level=drone.battery_level,
        is_autonomous=drone.is_autonomous,
        technical_specification=spec,
    )


def to_technical_specification_type(
    spec: TechnicalSpecification,
    *,
    nest_agent: bool = True,
) -> TechnicalSpecificationType:
    robot = None
    drone = None
    if nest_agent:
        if spec.robot_id:
            robot = to_robot_type(spec.robot, nest_spec=False)
        if spec.drone_id:
            drone = to_drone_type(spec.drone, nest_spec=False)
    return TechnicalSpecificationType(
        id=str(spec.id),
        cpu=spec.cpu,
        memory_gb=spec.memory_gb,
        firmware_version=spec.firmware_version,
        robot=robot,
        drone=drone,
    )


def to_mission_type(mission: Mission, *, nested: bool = True) -> MissionType:
    tasks = [to_task_type(task) for task in mission.tasks.all()] if nested else []
    participations = (
        [to_mission_participation_type(participation) for participation in mission.participations.all()]
        if nested
        else []
    )
    return MissionType(
        id=str(mission.id),
        name=mission.name,
        description=mission.description,
        start_time=mission.start_time,
        end_time=mission.end_time,
        status=MissionStatus(mission.status),
        tasks=tasks,
        participations=participations,
    )


def to_task_type(task: Task) -> TaskType:
    return TaskType(
        id=str(task.id),
        title=task.title,
        priority=task.priority,
        is_completed=task.is_completed,
        mission=to_mission_type(task.mission, nested=False),
    )


def to_mission_participation_type(participation: MissionParticipation) -> MissionParticipationType:
    return MissionParticipationType(
        id=str(participation.id),
        mission=to_mission_type(participation.mission, nested=False),
        agent_id=str(participation.agent_id),
        role=ParticipationRole(participation.role),
        assigned_at=participation.assigned_at,
    )


def to_telemetry_data_type(data: dict[str, Any]) -> TelemetryDataType:
    location = data["location"]
    return TelemetryDataType(
        location=LocationType(
            latitude=location["latitude"],
            longitude=location["longitude"],
        ),
        velocity=data["velocity"],
        orientation=data["orientation"],
        sensors=data["sensors"],
    )


def to_telemetry_record_type(record: TelemetryRecord) -> TelemetryRecordType:
    return TelemetryRecordType(
        id=str(record.id),
        agent_id=str(record.agent_id),
        timestamp=record.timestamp,
        data=to_telemetry_data_type(record.data),
    )


@strawberry.type
class Query:
    @strawberry.field
    def robots(self) -> list[RobotType]:
        qs = Robot.objects.prefetch_related("technical_specification")
        return [to_robot_type(robot) for robot in qs]

    @strawberry.field
    def robot(self, id: strawberry.ID) -> Optional[RobotType]:
        try:
            robot = Robot.objects.prefetch_related("technical_specification").get(pk=id)
        except Robot.DoesNotExist:
            return None
        return to_robot_type(robot)

    @strawberry.field
    def drones(self) -> list[DroneType]:
        qs = Drone.objects.prefetch_related("technical_specification")
        return [to_drone_type(drone) for drone in qs]

    @strawberry.field
    def drone(self, id: strawberry.ID) -> Optional[DroneType]:
        try:
            drone = Drone.objects.prefetch_related("technical_specification").get(pk=id)
        except Drone.DoesNotExist:
            return None
        return to_drone_type(drone)

    @strawberry.field
    def technical_specifications(self) -> list[TechnicalSpecificationType]:
        qs = TechnicalSpecification.objects.select_related("robot", "drone")
        return [to_technical_specification_type(spec) for spec in qs]

    @strawberry.field
    def technical_specification(self, id: strawberry.ID) -> Optional[TechnicalSpecificationType]:
        try:
            spec = TechnicalSpecification.objects.select_related("robot", "drone").get(pk=id)
        except TechnicalSpecification.DoesNotExist:
            return None
        return to_technical_specification_type(spec)

    @strawberry.field
    def missions(self, status: Optional[MissionStatus] = None) -> list[MissionType]:
        qs = Mission.objects.prefetch_related("tasks", "participations")
        if status is not None:
            qs = qs.filter(status=status.value)
        return [to_mission_type(mission) for mission in qs]

    @strawberry.field
    def mission(self, id: strawberry.ID) -> Optional[MissionType]:
        try:
            mission = Mission.objects.prefetch_related("tasks", "participations").get(pk=id)
        except Mission.DoesNotExist:
            return None
        return to_mission_type(mission)

    @strawberry.field
    def tasks(self, mission_id: Optional[strawberry.ID] = None) -> list[TaskType]:
        qs = Task.objects.select_related("mission")
        if mission_id is not None:
            qs = qs.filter(mission_id=mission_id)
        return [to_task_type(task) for task in qs]

    @strawberry.field
    def task(self, id: strawberry.ID) -> Optional[TaskType]:
        try:
            task = Task.objects.select_related("mission").get(pk=id)
        except Task.DoesNotExist:
            return None
        return to_task_type(task)

    @strawberry.field
    def mission_participations(
        self,
        mission_id: Optional[strawberry.ID] = None,
    ) -> list[MissionParticipationType]:
        qs = MissionParticipation.objects.select_related("mission")
        if mission_id is not None:
            qs = qs.filter(mission_id=mission_id)
        return [to_mission_participation_type(participation) for participation in qs]

    @strawberry.field
    def mission_participation(self, id: strawberry.ID) -> Optional[MissionParticipationType]:
        try:
            participation = MissionParticipation.objects.select_related("mission").get(pk=id)
        except MissionParticipation.DoesNotExist:
            return None
        return to_mission_participation_type(participation)

    @strawberry.field
    def telemetry_records(self, agent_id: Optional[strawberry.ID] = None) -> list[TelemetryRecordType]:
        qs = TelemetryRecord.objects.all()
        if agent_id is not None:
            qs = qs.filter(agent_id=agent_id)
        return [to_telemetry_record_type(record) for record in qs]

    @strawberry.field
    def telemetry_record(self, id: strawberry.ID) -> Optional[TelemetryRecordType]:
        try:
            record = TelemetryRecord.objects.get(pk=id)
        except TelemetryRecord.DoesNotExist:
            return None
        return to_telemetry_record_type(record)


def _telemetry_input_to_dict(data: TelemetryDataInput) -> dict[str, Any]:
    return {
        "location": {
            "latitude": data.location.latitude,
            "longitude": data.location.longitude,
        },
        "velocity": data.velocity,
        "orientation": data.orientation,
        "sensors": data.sensors,
    }


@strawberry.input
class LocationInput:
    latitude: float
    longitude: float


@strawberry.input
class TelemetryDataInput:
    location: LocationInput
    velocity: JSON
    orientation: JSON
    sensors: JSON


@strawberry.input
class CreateRobotInput:
    name: str
    serial_number: str
    battery_level: int
    max_speed: float
    is_active: bool = True


@strawberry.input
class UpdateRobotInput:
    name: Optional[str] = None
    serial_number: Optional[str] = None
    battery_level: Optional[int] = None
    max_speed: Optional[float] = None
    is_active: Optional[bool] = None


@strawberry.input
class CreateDroneInput:
    name: str
    serial_number: str
    max_altitude: float
    payload_capacity: Decimal
    battery_level: int
    is_autonomous: bool = False


@strawberry.input
class UpdateDroneInput:
    name: Optional[str] = None
    serial_number: Optional[str] = None
    max_altitude: Optional[float] = None
    payload_capacity: Optional[Decimal] = None
    battery_level: Optional[int] = None
    is_autonomous: Optional[bool] = None


@strawberry.input
class CreateTechnicalSpecificationInput:
    cpu: str
    memory_gb: int
    firmware_version: str
    robot_id: Optional[strawberry.ID] = None
    drone_id: Optional[strawberry.ID] = None


@strawberry.input
class UpdateTechnicalSpecificationInput:
    cpu: Optional[str] = None
    memory_gb: Optional[int] = None
    firmware_version: Optional[str] = None


@strawberry.input
class CreateMissionInput:
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    status: MissionStatus = MissionStatus.PENDING


@strawberry.input
class UpdateMissionInput:
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[MissionStatus] = None


@strawberry.input
class CreateTaskInput:
    mission_id: strawberry.ID
    title: str
    priority: int
    is_completed: bool = False


@strawberry.input
class UpdateTaskInput:
    title: Optional[str] = None
    priority: Optional[int] = None
    is_completed: Optional[bool] = None


@strawberry.input
class CreateMissionParticipationInput:
    mission_id: strawberry.ID
    agent_id: strawberry.ID
    role: ParticipationRole


@strawberry.input
class CreateTelemetryRecordInput:
    agent_id: strawberry.ID
    timestamp: datetime
    data: TelemetryDataInput


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_robot(self, input: CreateRobotInput) -> RobotType:
        robot = Robot.objects.create(
            name=input.name,
            serial_number=input.serial_number,
            battery_level=input.battery_level,
            max_speed=input.max_speed,
            is_active=input.is_active,
        )
        return to_robot_type(robot)

    @strawberry.mutation
    def update_robot(self, id: strawberry.ID, input: UpdateRobotInput) -> RobotType:
        robot = Robot.objects.get(pk=id)
        if input.name is not None:
            robot.name = input.name
        if input.serial_number is not None:
            robot.serial_number = input.serial_number
        if input.battery_level is not None:
            robot.battery_level = input.battery_level
        if input.max_speed is not None:
            robot.max_speed = input.max_speed
        if input.is_active is not None:
            robot.is_active = input.is_active
        robot.save()
        return to_robot_type(Robot.objects.prefetch_related("technical_specification").get(pk=robot.pk))

    @strawberry.mutation
    def delete_robot(self, id: strawberry.ID) -> bool:
        deleted, _ = Robot.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_drone(self, input: CreateDroneInput) -> DroneType:
        drone = Drone.objects.create(
            name=input.name,
            serial_number=input.serial_number,
            max_altitude=input.max_altitude,
            payload_capacity=input.payload_capacity,
            battery_level=input.battery_level,
            is_autonomous=input.is_autonomous,
        )
        return to_drone_type(drone)

    @strawberry.mutation
    def update_drone(self, id: strawberry.ID, input: UpdateDroneInput) -> DroneType:
        drone = Drone.objects.get(pk=id)
        if input.name is not None:
            drone.name = input.name
        if input.serial_number is not None:
            drone.serial_number = input.serial_number
        if input.max_altitude is not None:
            drone.max_altitude = input.max_altitude
        if input.payload_capacity is not None:
            drone.payload_capacity = input.payload_capacity
        if input.battery_level is not None:
            drone.battery_level = input.battery_level
        if input.is_autonomous is not None:
            drone.is_autonomous = input.is_autonomous
        drone.save()
        return to_drone_type(Drone.objects.prefetch_related("technical_specification").get(pk=drone.pk))

    @strawberry.mutation
    def delete_drone(self, id: strawberry.ID) -> bool:
        deleted, _ = Drone.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_technical_specification(self, input: CreateTechnicalSpecificationInput) -> TechnicalSpecificationType:
        spec = TechnicalSpecification(
            cpu=input.cpu,
            memory_gb=input.memory_gb,
            firmware_version=input.firmware_version,
            robot_id=input.robot_id,
            drone_id=input.drone_id,
        )
        spec.save()
        return to_technical_specification_type(
            TechnicalSpecification.objects.select_related("robot", "drone").get(pk=spec.pk)
        )

    @strawberry.mutation
    def update_technical_specification(
        self,
        id: strawberry.ID,
        input: UpdateTechnicalSpecificationInput,
    ) -> TechnicalSpecificationType:
        spec = TechnicalSpecification.objects.select_related("robot", "drone").get(pk=id)
        if input.cpu is not None:
            spec.cpu = input.cpu
        if input.memory_gb is not None:
            spec.memory_gb = input.memory_gb
        if input.firmware_version is not None:
            spec.firmware_version = input.firmware_version
        spec.save()
        return to_technical_specification_type(
            TechnicalSpecification.objects.select_related("robot", "drone").get(pk=spec.pk)
        )

    @strawberry.mutation
    def delete_technical_specification(self, id: strawberry.ID) -> bool:
        deleted, _ = TechnicalSpecification.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_mission(self, input: CreateMissionInput) -> MissionType:
        mission = Mission.objects.create(
            name=input.name,
            description=input.description,
            start_time=input.start_time,
            end_time=input.end_time,
            status=input.status.value,
        )
        return to_mission_type(mission)

    @strawberry.mutation
    def update_mission(self, id: strawberry.ID, input: UpdateMissionInput) -> MissionType:
        mission = Mission.objects.get(pk=id)
        if input.name is not None:
            mission.name = input.name
        if input.description is not None:
            mission.description = input.description
        if input.start_time is not None:
            mission.start_time = input.start_time
        if input.end_time is not None:
            mission.end_time = input.end_time
        if input.status is not None:
            mission.status = input.status.value
        mission.save()
        return to_mission_type(Mission.objects.prefetch_related("tasks", "participations").get(pk=mission.pk))

    @strawberry.mutation
    def delete_mission(self, id: strawberry.ID) -> bool:
        deleted, _ = Mission.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_task(self, input: CreateTaskInput) -> TaskType:
        task = Task.objects.create(
            mission_id=input.mission_id,
            title=input.title,
            priority=input.priority,
            is_completed=input.is_completed,
        )
        return to_task_type(Task.objects.select_related("mission").get(pk=task.pk))

    @strawberry.mutation
    def update_task(self, id: strawberry.ID, input: UpdateTaskInput) -> TaskType:
        task = Task.objects.select_related("mission").get(pk=id)
        if input.title is not None:
            task.title = input.title
        if input.priority is not None:
            task.priority = input.priority
        if input.is_completed is not None:
            task.is_completed = input.is_completed
        task.save()
        return to_task_type(Task.objects.select_related("mission").get(pk=task.pk))

    @strawberry.mutation
    def delete_task(self, id: strawberry.ID) -> bool:
        deleted, _ = Task.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_mission_participation(self, input: CreateMissionParticipationInput) -> MissionParticipationType:
        participation = MissionParticipation.objects.create(
            mission_id=input.mission_id,
            agent_id=input.agent_id,
            role=input.role.value,
        )
        return to_mission_participation_type(
            MissionParticipation.objects.select_related("mission").get(pk=participation.pk)
        )

    @strawberry.mutation
    def delete_mission_participation(self, id: strawberry.ID) -> bool:
        deleted, _ = MissionParticipation.objects.filter(pk=id).delete()
        return deleted > 0

    @strawberry.mutation
    def create_telemetry_record(self, input: CreateTelemetryRecordInput) -> TelemetryRecordType:
        record = TelemetryRecord.objects.create(
            agent_id=input.agent_id,
            timestamp=input.timestamp,
            data=_telemetry_input_to_dict(input.data),
        )
        return to_telemetry_record_type(record)

    @strawberry.mutation
    def delete_telemetry_record(self, id: strawberry.ID) -> bool:
        deleted, _ = TelemetryRecord.objects.filter(pk=id).delete()
        return deleted > 0


schema = strawberry.Schema(query=Query, mutation=Mutation)
