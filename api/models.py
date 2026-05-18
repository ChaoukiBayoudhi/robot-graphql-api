import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

from .validators import agent_uuid_must_exist, validate_telemetry_payload

serial_validator = RegexValidator(
    regex=r"^[A-Za-z0-9-]+$",
    message="Serial numbers may only contain letters, digits, and hyphens.",
)


class Robot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=64, unique=True, validators=[serial_validator], db_index=True)
    battery_level = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_speed = models.FloatField(validators=[MinValueValidator(0.0)])
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(battery_level__gte=0) & Q(battery_level__lte=100),
                name="robot_battery_0_100",
            ),
            models.CheckConstraint(condition=Q(max_speed__gte=0), name="robot_max_speed_gte_0"),
        ]
        db_table = "robot"

    def clean(self):
        super().clean()
        if self.is_active and self.battery_level is not None and self.battery_level <= 10:
            raise ValidationError({"battery_level": "Active robots must have battery level greater than 10%."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"


class Drone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=64, unique=True, validators=[serial_validator], db_index=True)
    max_altitude = models.FloatField()
    payload_capacity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    battery_level = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_autonomous = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(battery_level__gte=0) & Q(battery_level__lte=100),
                name="drone_battery_0_100",
            ),
            models.CheckConstraint(
                condition=Q(max_altitude__gt=0) & Q(max_altitude__lte=10000),
                name="drone_max_altitude_range",
            ),
            models.CheckConstraint(condition=Q(payload_capacity__gte=0), name="drone_payload_gte_0"),
        ]
        db_table = "drone"

    def clean(self):
        super().clean()
        if self.is_autonomous and self.battery_level is not None and self.battery_level <= 20:
            raise ValidationError(
                {"battery_level": "Autonomous drones must have battery level greater than 20%."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"


class TechnicalSpecification(models.Model):
    robot = models.OneToOneField(
        Robot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="technical_specification",
    )
    drone = models.OneToOneField(
        Drone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="technical_specification",
    )
    cpu = models.CharField(max_length=255)
    memory_gb = models.IntegerField(validators=[MinValueValidator(1)])
    firmware_version = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(memory_gb__gt=0), name="techspec_memory_gb_gt_0"),
            models.CheckConstraint(
                condition=(Q(robot__isnull=False) & Q(drone__isnull=True))
                | (Q(robot__isnull=True) & Q(drone__isnull=False)),
                name="techspec_exactly_one_of_robot_drone",
            ),
        ]
        db_table = "technical_specification"

    def clean(self):
        super().clean()
        has_robot = self.robot_id is not None
        has_drone = self.drone_id is not None
        if has_robot == has_drone:
            raise ValidationError("Exactly one of robot or drone must be set.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.robot_id:
            return f"Spec for robot {self.robot_id}"
        return f"Spec for drone {self.drone_id}"


class Mission(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=models.F("start_time")), name="mission_end_after_start"),
        ]
        indexes = [
            models.Index(fields=["status", "start_time"], name="mission_status_start_idx"),
        ]
        db_table = "mission"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "end_time must be greater than start_time."})
        if self.status == self.Status.ACTIVE and self.pk:
            from django.apps import apps

            MP = apps.get_model("api", "MissionParticipation")
            if not MP.objects.filter(mission=self).exists():
                raise ValidationError(
                    {"status": "Mission must have at least one participant before it can be ACTIVE."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    priority = models.PositiveIntegerField(db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(priority__gt=0), name="task_priority_gt_0"),
        ]
        indexes = [
            models.Index(fields=["mission", "priority", "is_completed"], name="task_mission_priority_done_idx"),
        ]
        db_table = "task"

    def clean(self):
        super().clean()
        if self.is_completed and self.mission_id:
            if self.mission.status not in (Mission.Status.ACTIVE, Mission.Status.COMPLETED):
                raise ValidationError(
                    {"is_completed": "Completed tasks may only exist for ACTIVE or COMPLETED missions."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class MissionParticipation(models.Model):
    class Role(models.TextChoices):
        LEADER = "LEADER", "Leader"
        FOLLOWER = "FOLLOWER", "Follower"
        SCOUT = "SCOUT", "Scout"
        CARRIER = "CARRIER", "Carrier"
        OBSERVER = "OBSERVER", "Observer"

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="participations")
    agent_id = models.UUIDField(db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mission", "agent_id"], name="missionpart_unique_mission_agent"),
        ]
        indexes = [
            models.Index(fields=["mission", "role"], name="missionpart_mission_role_idx"),
        ]
        db_table = "mission_participation"

    def clean(self):
        super().clean()
        agent_uuid_must_exist(self.agent_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.mission} ← {self.agent_id}"


class TelemetryRecord(models.Model):
    agent_id = models.UUIDField(db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    data = models.JSONField(validators=[validate_telemetry_payload])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agent_id", "timestamp"], name="telemetry_unique_agent_ts"),
        ]
        indexes = [
            models.Index(fields=["agent_id", "-timestamp"], name="telemetry_agent_ts_desc_idx"),
        ]
        db_table = "telemetry_record"

    def clean(self):
        super().clean()
        agent_uuid_must_exist(self.agent_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.agent_id} @ {self.timestamp}"