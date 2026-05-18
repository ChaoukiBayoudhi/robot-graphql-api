import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import (
    Drone,
    Mission,
    MissionParticipation,
    Robot,
    Task,
    TechnicalSpecification,
    TelemetryRecord,
)

ROBOT_NAMES = ("Atlas", "Spot", "Curie", "Unit-7", "Rover-X", "Pathfinder", "Helios", "Vector")
DRONE_NAMES = ("Falcon", "Hawk", "Swift", "Aero-9", "Skyline", "Nimbus", "Zephyr", "Glide")
CPUS = ("ARM Cortex-A78", "Intel i7-12700", "RISC-V RV64", "NVIDIA Jetson Orin", "Apple M2")
FIRMWARE = ("1.0.0", "1.2.3", "2.0.1", "2.4.0-beta", "3.1.0")
MISSION_NAMES = (
    "Perimeter Patrol",
    "Warehouse Scan",
    "Search and Rescue",
    "Payload Delivery",
    "Mapping Run",
)
TASK_TITLES = (
    "Calibrate sensors",
    "Reach waypoint A",
    "Scan sector 3",
    "Return to base",
    "Upload telemetry",
    "Verify battery levels",
)


def sample_telemetry() -> dict:
    return {
        "location": {
            "latitude": round(random.uniform(48.8, 48.9), 6),
            "longitude": round(random.uniform(2.3, 2.4), 6),
        },
        "velocity": {"x": round(random.uniform(-2, 2), 2), "y": round(random.uniform(-2, 2), 2), "z": 0.0},
        "orientation": {"pitch": 0.0, "roll": 0.0, "yaw": round(random.uniform(0, 360), 1)},
        "sensors": [
            {"type": "lidar", "value": round(random.uniform(0.5, 30.0), 2)},
            {"type": "battery", "value": random.randint(20, 100)},
        ],
    }


class Command(BaseCommand):
    help = "Insert fake robots, drones, missions, tasks, and telemetry into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing api data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_data()

        robots = self._create_robots()
        drones = self._create_drones()
        self._create_technical_specifications(robots, drones)
        missions = self._create_missions()
        agents = [r.id for r in robots] + [d.id for d in drones]
        self._create_participations(missions, agents)
        self._activate_missions(missions)
        self._create_tasks(missions)
        self._create_telemetry(agents)

        self.stdout.write(self.style.SUCCESS("Fake data inserted successfully."))
        self._print_summary()

    def _clear_data(self):
        TelemetryRecord.objects.all().delete()
        Task.objects.all().delete()
        MissionParticipation.objects.all().delete()
        Mission.objects.all().delete()
        TechnicalSpecification.objects.all().delete()
        Drone.objects.all().delete()
        Robot.objects.all().delete()
        self.stdout.write("Cleared existing data.")

    def _create_robots(self) -> list[Robot]:
        robots = []
        for index, name in enumerate(ROBOT_NAMES, start=1):
            is_active = random.choice([True, True, False])
            battery = random.randint(15, 100) if is_active else random.randint(0, 100)
            if is_active and battery <= 10:
                battery = random.randint(11, 100)
            robots.append(
                Robot(
                    name=name,
                    serial_number=f"ROB-{index:03d}",
                    battery_level=battery,
                    max_speed=round(random.uniform(0.5, 4.0), 2),
                    is_active=is_active,
                )
            )
        Robot.objects.bulk_create(robots)
        robots = list(Robot.objects.order_by("serial_number"))
        self.stdout.write(f"  Robots: {len(robots)}")
        return robots

    def _create_drones(self) -> list[Drone]:
        drones = []
        for index, name in enumerate(DRONE_NAMES, start=1):
            is_autonomous = random.choice([True, False, False])
            battery = random.randint(25, 100) if is_autonomous else random.randint(0, 100)
            if is_autonomous and battery <= 20:
                battery = random.randint(21, 100)
            drones.append(
                Drone(
                    name=name,
                    serial_number=f"DRN-{index:03d}",
                    max_altitude=round(random.uniform(50, 5000), 1),
                    payload_capacity=Decimal(str(round(random.uniform(0.5, 25.0), 2))),
                    battery_level=battery,
                    is_autonomous=is_autonomous,
                )
            )
        Drone.objects.bulk_create(drones)
        drones = list(Drone.objects.order_by("serial_number"))
        self.stdout.write(f"  Drones: {len(drones)}")
        return drones

    def _create_technical_specifications(self, robots: list[Robot], drones: list[Drone]) -> None:
        specs = []
        for robot in robots[:6]:
            specs.append(
                TechnicalSpecification(
                    robot=robot,
                    cpu=random.choice(CPUS),
                    memory_gb=random.choice([4, 8, 16, 32]),
                    firmware_version=random.choice(FIRMWARE),
                )
            )
        for drone in drones[:5]:
            specs.append(
                TechnicalSpecification(
                    drone=drone,
                    cpu=random.choice(CPUS),
                    memory_gb=random.choice([8, 16, 64]),
                    firmware_version=random.choice(FIRMWARE),
                )
            )
        for spec in specs:
            spec.save()
        self.stdout.write(f"  Technical specifications: {len(specs)}")

    def _create_missions(self) -> list[Mission]:
        now = timezone.now()
        missions = []
        statuses = [
            Mission.Status.PENDING,
            Mission.Status.PENDING,
            Mission.Status.ACTIVE,
            Mission.Status.ACTIVE,
            Mission.Status.COMPLETED,
            Mission.Status.CANCELLED,
        ]
        for index, (name, status) in enumerate(zip(MISSION_NAMES, statuses, strict=False), start=1):
            start = now - timedelta(days=random.randint(1, 14), hours=index)
            end = start + timedelta(hours=random.randint(2, 48))
            mission = Mission(
                name=name,
                description=f"Automated mission #{index}: {name.lower()} across sector {index}.",
                start_time=start,
                end_time=end,
                status=Mission.Status.PENDING,
            )
            mission.save()
            mission._target_status = status
            missions.append(mission)
        self.stdout.write(f"  Missions: {len(missions)}")
        return missions

    def _create_participations(self, missions: list[Mission], agents: list) -> None:
        participations = []
        roles = list(MissionParticipation.Role)
        for mission in missions:
            count = random.randint(2, min(4, len(agents)))
            for agent_id in random.sample(agents, count):
                participations.append(
                    MissionParticipation(
                        mission=mission,
                        agent_id=agent_id,
                        role=random.choice(roles),
                    )
                )
        for participation in participations:
            participation.save()
        self.stdout.write(f"  Mission participations: {len(participations)}")

    def _activate_missions(self, missions: list[Mission]) -> None:
        for mission in missions:
            target = getattr(mission, "_target_status", Mission.Status.PENDING)
            if target == Mission.Status.ACTIVE:
                mission.status = Mission.Status.ACTIVE
                mission.save()
            elif target in (Mission.Status.COMPLETED, Mission.Status.CANCELLED):
                mission.status = target
                mission.save()

    def _create_tasks(self, missions: list[Mission]) -> None:
        tasks = []
        for mission in missions:
            for priority, title in enumerate(random.sample(TASK_TITLES, k=3), start=1):
                is_completed = False
                if mission.status in (Mission.Status.ACTIVE, Mission.Status.COMPLETED):
                    is_completed = random.choice([True, False])
                tasks.append(
                    Task(
                        mission=mission,
                        title=title,
                        priority=priority,
                        is_completed=is_completed,
                    )
                )
        for task in tasks:
            task.save()
        self.stdout.write(f"  Tasks: {len(tasks)}")

    def _create_telemetry(self, agents: list) -> None:
        now = timezone.now()
        records = []
        for agent_id in agents:
            for offset in range(3):
                records.append(
                    TelemetryRecord(
                        agent_id=agent_id,
                        timestamp=now - timedelta(minutes=offset * 5 + random.randint(0, 3)),
                        data=sample_telemetry(),
                    )
                )
        for record in records:
            record.save()
        self.stdout.write(f"  Telemetry records: {len(records)}")

    def _print_summary(self) -> None:
        self.stdout.write(
            f"Totals — robots: {Robot.objects.count()}, drones: {Drone.objects.count()}, "
            f"missions: {Mission.objects.count()}, tasks: {Task.objects.count()}, "
            f"telemetry: {TelemetryRecord.objects.count()}"
        )
