from django.core.exceptions import ValidationError


def validate_telemetry_payload(value):
    """Ensure JSON matches the case-study telemetry shape (top-level keys)."""
    if not isinstance(value, dict):
        raise ValidationError("Telemetry data must be a JSON object.")
    for key in ("location", "velocity", "orientation", "sensors"):
        if key not in value:
            raise ValidationError(f"Missing required telemetry key: {key!r}.")


def agent_uuid_must_exist(agent_id):
    """Polymorphic agent_id must match an existing Robot or Drone primary key."""
    from .models import Drone, Robot

    if not Robot.objects.filter(pk=agent_id).exists() and not Drone.objects.filter(pk=agent_id).exists():
        raise ValidationError({"agent_id": "Must reference an existing robot or drone UUID."})