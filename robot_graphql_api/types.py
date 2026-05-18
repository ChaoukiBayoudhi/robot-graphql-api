from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

import strawberry
from strawberry.scalars import JSON

from api.models import Mission, MissionParticipation

MissionStatus = strawberry.enum(Mission.Status)
ParticipationRole = strawberry.enum(MissionParticipation.Role)


@strawberry.type
class LocationType:
    latitude: float
    longitude: float


@strawberry.type
class TelemetryDataType:
    location: LocationType
    velocity: JSON
    orientation: JSON
    sensors: JSON


@strawberry.type
class RobotType:
    id: strawberry.ID
    name: str
    serial_number: str
    battery_level: int
    max_speed: float
    is_active: bool
    created_at: datetime
    technical_specification: Optional[TechnicalSpecificationType] = None


@strawberry.type
class DroneType:
    id: strawberry.ID
    name: str
    serial_number: str
    max_altitude: float
    payload_capacity: Decimal
    battery_level: int
    is_autonomous: bool
    technical_specification: Optional[TechnicalSpecificationType] = None


@strawberry.type
class TechnicalSpecificationType:
    id: strawberry.ID
    cpu: str
    memory_gb: int
    firmware_version: str
    robot: Optional[RobotType] = None
    drone: Optional[DroneType] = None


@strawberry.type
class MissionType:
    id: strawberry.ID
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    status: MissionStatus
    tasks: list[TaskType]
    participations: list[MissionParticipationType]


@strawberry.type
class TaskType:
    id: strawberry.ID
    title: str
    priority: int
    is_completed: bool
    mission: MissionType


@strawberry.type
class MissionParticipationType:
    id: strawberry.ID
    mission: MissionType
    agent_id: strawberry.ID
    role: ParticipationRole
    assigned_at: datetime


@strawberry.type
class TelemetryRecordType:
    id: strawberry.ID
    agent_id: strawberry.ID
    timestamp: datetime
    data: TelemetryDataType
